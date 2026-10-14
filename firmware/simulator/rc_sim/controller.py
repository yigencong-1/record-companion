"""ABC 唱片与曲库统一控制器的纯软件模拟（RC-08B-01）。

不依赖 ESP32、NFC 或 SD。所有输入都是确定性事件：
  - 物理：card_inserted / card_removed / reader_fault / reader_recovered / tick
  - 命令：select_track / pause_audio / resume_audio / stop_audio / mode_next / mode_play /
          mode_exit / start_held / execute_binding
  - 音频回调：audio_eof(gen)
  - 内容：save_playlist / save_binding / delete_track / delete_playlist / media_published

规则来源以 product/decisions.md 的 D 编号为准，每个分支旁注明依据。
跨 B/C 替换按 D089：先预检，再完整替换；旧模式不自动恢复。
"""

from __future__ import annotations

import json
import copy
import uuid

from .store import Store

# 音频状态
STOPPED = "STOPPED"            # 普通停止（无会话或会话已清理）
PLAYING = "PLAYING"
STARTING = "STARTING"
PAUSED = "PAUSED"
STOPPED_USER = "STOPPED_USER"  # B/C 内 STOP_AUDIO：音频停、模式在、禁止自动循环（D075）
STOP_ERROR = "STOP_ERROR"      # B/C 内全部不可播：音频停、模式在（D080）

DEFAULT_FAULT_THRESHOLD_MS = 3000  # 候选参数，仅用于检验规则；真实阈值待实测（D072）


class Controller:
    def __init__(self, store: Store, present_uid: str | None = None,
                 fault_threshold_ms: int = DEFAULT_FAULT_THRESHOLD_MS, *, async_audio=False):
        self.store = store
        self.fault_threshold_ms = fault_threshold_ms
        self.async_audio = async_audio
        self.clock_ms = 0
        self.event_seq = 0
        self._next_placement = 1
        self._next_session = 1
        self.gen = 0                    # 音频代次：迟到回调靠它失效
        self.boot_id = uuid.uuid4().hex  # 对外回调信封隔离重启前事件
        self.plain_selection = copy.deepcopy(store.ordinary_selection)
        self.binding_page = False
        self.binding_capture = None
        self.requires_replacement = False
        self.reader_identity_confirmed = True
        self.placement = None           # {"uid","placement_id","consumed","held"}
        self.session = None             # B/C 会话
        self.audio = {"state": STOPPED, "track_id": None, "position_ms": 0, "owner_session": None}
        self.fault_since = None
        self.fault_protection_exit = False
        self.last_error = None
        self.log: list[dict] = []
        if present_uid is not None:
            # D052/D073：开机已有片只识别，等待显式启动；旧 C 不跨重启恢复
            self.placement = self._new_placement(present_uid, held=True)
        self._record("BOOT")

    # ================= 内部工具 =================
    def _new_placement(self, uid, held=False):
        p = {"uid": uid, "placement_id": self._next_placement, "consumed": False, "held": held}
        self._next_placement += 1
        return p

    def _record(self, event, **detail):
        self.event_seq += 1
        s = self.session
        sel = self._selected_track()
        b = self.store.bindings.get(self.placement["uid"]) if self.placement else None
        self.log.append({
            "event_seq": self.event_seq,
            "event": event,
            "detail": detail,
            "placement_id": self.placement["placement_id"] if self.placement else None,
            "session_id": s["session_id"] if s else None,
            "mode_kind": s["kind"] if s else None,
            "audio_state": self.audio["state"],
            "playing_track_id": self.audio["track_id"],
            "selected_track_id": sel,
            "playlist_snapshot_revision": s["snapshot_revision"] if s else None,
            "media_revision": self.store.tracks.get(sel, {}).get("media_version") if sel else None,
            "saved_binding_revision": b["revision"] if b else None,
            "successful_commit_seq": self.store.commit_seq,
            "last_error": self.last_error,
        })

    def _selected_track(self):
        if self.session:
            return self.session["tracks"][self.session["index"]]
        return (self.plain_selection or {}).get("track_id")

    def audio_token(self):
        """实际适配器应回传整个信封；整数 gen 只保留给旧PC用例。"""
        return {"boot_id": self.boot_id, "gen": self.gen,
                "session_id": self.audio["owner_session"],
                "track_id": self.audio["track_id"],
                "media_version": self.audio.get("media_version")}

    def _current_audio(self, token):
        return token == (self.audio_token() if isinstance(token, dict) else self.gen)

    def _remember_plain(self, selection):
        def mutate():
            self.store.ordinary_selection = copy.deepcopy(selection)
        request_id = f"selection:{self.boot_id}:{self.event_seq}:{self.gen}"
        receipt = self.store.commit(request_id, self._key("SELECT", selection), mutate)
        if not receipt["ok"]:
            self.last_error = receipt["error"]
            return False
        self.plain_selection = copy.deepcopy(selection)
        return True

    def _playable(self, tid):
        t = self.store.tracks.get(tid)
        return bool(t and t["ok"] and t["start_ok"])

    def _activate_audio(self, tid, owner_session=None, position_ms=0, media_version=None):
        self.gen += 1
        self.last_error = None
        self.audio = {"state": STARTING if self.async_audio else PLAYING,
                      "track_id": tid, "position_ms": position_ms,
                      "owner_session": owner_session,
                      "media_version": (self.store.tracks[tid]["media_version"]
                                        if media_version is None else media_version)}
        if self.session and not self.async_audio:
            self.session["has_started"] = True

    def _stop_audio_hard(self):
        self.gen += 1
        self.audio = {"state": STOPPED, "track_id": None, "position_ms": 0, "owner_session": None}

    def _exit_session(self):
        """完整退出 B/C：停止并清空模式播放任务（D066、D075）。"""
        if self.session is not None:
            self.session = None
            self._stop_audio_hard()

    def _start_plain(self, tid):
        """A 点播或本体/网页点歌：普通播放，不属于任何会话。"""
        if not self.plain_selection or self.plain_selection.get("track_id") != tid:
            self.plain_selection = {"track_id": tid, "playlist_id": None}
        if not self._playable(tid):
            # D074：实际启动失败 → 报错并停止，不回滚旧模式
            self._stop_audio_hard()
            self.last_error = "START_FAILED"
            return False
        self._activate_audio(tid)
        return True

    def _session_play_from(self, index):
        """在会话中从 index 开始播放；坏曲记录并跳过，本会话不无限重试（D080）。"""
        s = self.session
        n = len(s["tracks"])
        for step in range(n):
            i = (index + step) % n
            tid = s["tracks"][i]
            version = self.store.tracks.get(tid, {}).get("media_version")
            if tid in s["bad"] and s["bad"][tid] == version:
                continue
            if not self._playable(tid):
                s["bad"][tid] = version
                self.last_error = f"TRACK_READ_ERROR:{tid}"
                continue
            s["index"] = i
            self._activate_audio(tid, s["session_id"])
            return
        # 全部不可播：停止音频并报错，模式保持（D080）
        self.gen += 1
        self.audio = {"state": STOP_ERROR, "track_id": None, "position_ms": 0,
                      "owner_session": s["session_id"]}
        self.last_error = "ALL_TRACKS_UNPLAYABLE"

    def _resolve_target(self, binding):
        """预检：返回曲目列表、歌单编号和歌单版本；无效返回 None（D074）。"""
        t = binding["target"]
        if "track" in t:
            if t["track"] not in self.store.tracks:
                return None
            return [t["track"]], None, None
        if "playlist" in t:
            pl = self.store.playlists.get(t["playlist"])
            if not pl or not pl["tracks"]:
                return None
            return list(pl["tracks"]), t["playlist"], pl["revision"]
        return None

    def _trigger(self, placement, force=False):
        """按本体保存的绑定解释一次放置（D069）。"""
        uid = placement["uid"]
        binding = self.store.bindings.get(uid)
        if binding is None:
            self.last_error = "UNBOUND"            # 预检失败，旧模式保留（D074）
            return
        kind = binding["kind"]

        if kind == "A":
            resolved = self._resolve_target(binding)
            if resolved is None or "track" not in binding["target"]:
                self.last_error = "TARGET_INVALID"
                return
            self._exit_session()                   # 有效新 A 先完整退出 B/C（D068）
            self.last_error = None
            self.plain_selection = {"track_id": resolved[0][0], "playlist_id": None}
            self._start_plain(resolved[0][0])
            placement["consumed"] = True
            return

        # B / C
        s = self.session
        if (not force and kind == "C" and s and s["kind"] == "C" and s["origin_uid"] == uid):
            # D071：活动 C 同片取走再放入，不重启、不改进度、不解除 STOP
            placement["consumed"] = True
            self.last_error = None
            return
        resolved = self._resolve_target(binding)
        if resolved is None:
            self.last_error = "TARGET_INVALID"
            return
        tracks, playlist_id, rev = resolved
        # D089/D074：新目标通过预检后完整替换旧会话，启动失败也不回滚。
        self._exit_session()
        self.session = {
            "kind": kind,
            "session_id": self._next_session,
            "owner_placement": placement["placement_id"] if kind == "B" else None,
            "origin_uid": uid,
            "playlist_id": playlist_id,
            "snapshot_revision": rev,      # 进入时的歌单快照（D077）
            "tracks": tracks,
            "index": 0,
            "bad": {},
            "has_started": False,
        }
        self._next_session += 1
        placement["consumed"] = True
        self.last_error = None
        # 首次启动与运行中坏曲分离：D074不允许首次失败自动尝试下一首。
        if not self._playable(tracks[0]):
            self.gen += 1
            self.audio = {"state": STOP_ERROR, "track_id": None, "position_ms": 0,
                          "owner_session": self.session["session_id"]}
            self.last_error = "START_FAILED"
        else:
            self._session_play_from(0)

    # ================= 物理事件 =================
    def card_inserted(self, uid):
        if self.fault_since is not None or self.requires_replacement:
            self._record("CARD_INSERTED_IGNORED_DURING_FAULT", uid=uid)
            return
        if self.placement is not None:
            if self.placement["uid"] == uid:
                # 持续在位的重复读取不是新放置（D046、L02）
                self._record("DUPLICATE_READ_IGNORED", uid=uid)
                return
            # 座上已有片又读到别的 UID：不凭一次身份变化切换（L16）
            self.last_error = "SEAT_CONFLICT"
            self._record("CARD_INSERTED", uid=uid)
            return
        self.placement = self._new_placement(uid)
        self.reader_identity_confirmed = True
        if self.binding_page:
            self.placement["consumed"] = True
            self.binding_capture = dict(self.placement)
        else:
            self._trigger(self.placement)
        self._record("CARD_INSERTED", uid=uid)

    def card_removed(self, placement_id):
        p = self.placement
        if p is None or p["placement_id"] != placement_id:
            self._record("CARD_REMOVED_STALE", placement_id=placement_id)
            return
        self.placement = None
        if self.fault_since is None:
            self.requires_replacement = False
            self.reader_identity_confirmed = True
        s = self.session
        if s and s["kind"] == "B" and s["owner_placement"] == placement_id:
            # D066：B 确认取走即退出，停止并清空；STOP 状态下同样退出（D075、L26）
            self._exit_session()
        self._record("CARD_REMOVED", placement_id=placement_id)

    def reader_fault(self):
        if self.fault_since is None:
            self.fault_since = self.clock_ms      # 重复故障报告不延后 D072 保护时限
        self._record("READER_FAULT")

    def tick(self, ms):
        self.clock_ms += ms
        if (self.fault_since is not None and not self.fault_protection_exit
                and self.clock_ms - self.fault_since >= self.fault_threshold_ms):
            s = self.session
            if s and s["kind"] == "B":
                # D072：持续故障超阈值 → 停止清空退出 B，记故障而非取走
                self._exit_session()
                self.fault_protection_exit = True
                self.requires_replacement = True
                if self.placement:
                    self.placement["consumed"] = True
                self.last_error = "READER_FAULT_PROTECTION_EXIT"
                self._record("FAULT_PROTECTION_EXIT")
                return
        self._record("TICK", ms=ms)

    def reader_recovered(self, seen_uid, *, trusted_empty=False):
        """健康恢复与空座证据独立；None只表示未读到身份。"""
        p = self.placement
        if trusted_empty and seen_uid is None:
            self.fault_since = None
            self.fault_protection_exit = False
            if p is not None:
                self.card_removed(p["placement_id"])
            self.requires_replacement = False
            self.reader_identity_confirmed = True
            self._record("READER_RECOVERED", seen=None)
            return
        if p is not None and p["uid"] == seen_uid:
            self.fault_since = None
            self.fault_protection_exit = False
            self.reader_identity_confirmed = True
            # 短故障恢复同片：不是新放置（D072）；保护退出后仍为已消费，不自启（L28）
            self._record("READER_RECOVERED", seen=seen_uid)
            return
        # 不伪造CARD_REMOVED，也不从一次恢复观测创建新放置。
        self.reader_identity_confirmed = False
        if self.fault_since is None:
            self.fault_since = self.clock_ms
        self.last_error = "NEEDS_RESEAT"
        self._record("READER_RECOVERED", seen=seen_uid)

    # ================= 用户命令 =================
    def enter_binding_page(self):
        self.binding_page, self.binding_capture = True, None
        self._record("BINDING_PAGE_ENTERED")

    def leave_binding_page(self):
        self.binding_page, self.binding_capture = False, None
        self._record("BINDING_PAGE_LEFT")  # 不补发自动放片；已捕获放置继续已消费

    def save_captured_binding(self, request_id, kind, target):
        p = self.placement
        if (not self.binding_page or not p or not self.binding_capture
                or p["placement_id"] != self.binding_capture["placement_id"]
                or self.fault_since is not None or not self.reader_identity_confirmed):
            self.last_error = "NO_TRUSTED_BINDING_CAPTURE"
            self._record("BINDING_CAPTURE_REJECTED")
            return {"ok": False, "error": self.last_error}
        return self.save_binding(request_id, p["uid"], kind, target)

    def _card_start_allowed(self):
        if self.binding_page:
            self.last_error = "BINDING_PAGE_ACTIVE"
        elif self.requires_replacement or not self.reader_identity_confirmed:
            self.last_error = "REPLACEMENT_REQUIRED"
        elif self.fault_since is not None:
            self.last_error = "READER_UNHEALTHY"
        else:
            return True
        return False

    def start_held(self):
        """D052：开机已有片，用户显式启动。"""
        p = self.placement
        if self._card_start_allowed() and p and p["held"] and not p["consumed"]:
            p["held"] = False
            self._trigger(p)
        self._record("START_HELD")

    def execute_binding(self):
        """D078：用户明确执行在位唱片的新绑定；先预检，失败不动旧会话（D074）。"""
        p = self.placement
        if not self._card_start_allowed():
            pass
        elif p is None:
            self.last_error = "NO_CARD"
        else:
            b = self.store.bindings.get(p["uid"])
            if b is None or self._resolve_target(b) is None:
                self.last_error = "TARGET_INVALID"
            else:
                self._exit_session()
                self._trigger(p, force=True)
        self._record("EXECUTE_BINDING")

    def select_track(self, tid):
        """本体或网页主动点歌（D068、D074）。"""
        if tid not in self.store.tracks:
            self.last_error = "TRACK_NOT_FOUND"   # 预检失败，保留旧模式
        elif self._remember_plain({"track_id": tid, "playlist_id": None}):
            self._exit_session()
            self.last_error = None
            self._start_plain(tid)
        self._record("SELECT_TRACK", track_id=tid)

    def select_playlist(self, playlist_id, track_id=None):
        """普通独立歌单选择；不创建B/C，不在这里新增自动循环规则。"""
        playlist = self.store.playlists.get(playlist_id)
        if not playlist or not playlist["tracks"]:
            self.last_error = "PLAYLIST_NOT_FOUND"
        else:
            track_id = track_id or playlist["tracks"][0]
            if track_id not in playlist["tracks"] or track_id not in self.store.tracks:
                self.last_error = "TRACK_NOT_FOUND"
            elif self._remember_plain({"playlist_id": playlist_id, "track_id": track_id}):
                self._exit_session()
                self.last_error = None
                self._start_plain(track_id)
        self._record("SELECT_PLAYLIST", playlist_id=playlist_id)

    def play(self):
        """明确普通播放与模式播放；唱片启动仍用独立的start_held。"""
        if self.session:
            self.mode_play()
            return
        if self.audio["state"] == PAUSED:
            self.resume_audio()
            return
        selection = self.plain_selection
        if not selection or selection["track_id"] not in self.store.tracks:
            self.last_error = "SELECTED_TARGET_MISSING"
        elif selection.get("playlist_id") and selection["playlist_id"] not in self.store.playlists:
            self.last_error = "SELECTED_TARGET_MISSING"
        elif self.audio["state"] not in (PLAYING, STARTING):
            self.last_error = None
            self._start_plain(selection["track_id"])
        self._record("PLAY")

    def pause_audio(self):
        if self.audio["state"] == PLAYING:
            self.gen += 1
            self.audio["state"] = PAUSED          # 保留位置，不退出模式（D068）
        self._record("PAUSE_AUDIO")

    def next_track(self):
        if self.session:
            self.mode_next()
            return
        selection = self.plain_selection or {}
        playlist = self.store.playlists.get(selection.get("playlist_id"))
        tid = selection.get("track_id")
        if self.audio["state"] == STARTING:
            self.last_error = "CONTROL_STATE_UNSPECIFIED"
        elif not playlist or tid not in playlist["tracks"]:
            self.last_error = "NO_PLAYLIST_SELECTION"
        elif playlist["tracks"].index(tid) + 1 >= len(playlist["tracks"]):
            self.last_error = "ORDINARY_QUEUE_END_UNSPECIFIED"
        else:
            next_tid = playlist["tracks"][playlist["tracks"].index(tid) + 1]
            previous_state = self.audio["state"]
            if self._remember_plain({"playlist_id": selection["playlist_id"], "track_id": next_tid}):
                self.last_error = None
                if previous_state == PLAYING:
                    self._start_plain(next_tid)
                else:
                    self._stop_audio_hard()
                    if previous_state == PAUSED:
                        self.audio["state"] = PAUSED
        self._record("NEXT_TRACK")

    def resume_audio(self):
        if self.audio["state"] == PAUSED:
            if self.audio["track_id"] is None:
                if self.session:
                    self._session_play_from(self.session["index"])
                elif self.plain_selection:
                    self._start_plain(self.plain_selection["track_id"])
            else:
                self._activate_audio(self.audio["track_id"], self.audio["owner_session"],
                                     self.audio["position_ms"], self.audio.get("media_version"))
        self._record("RESUME_AUDIO")

    def stop_audio(self):
        if self.session is not None:
            self.gen += 1                          # 让在途 EOF 失效
            self.audio = {"state": STOPPED_USER, "track_id": None, "position_ms": 0,
                          "owner_session": self.session["session_id"]}
        else:
            self._stop_audio_hard()
        self._record("STOP_AUDIO")

    def mode_next(self):
        s = self.session
        if s is None:
            self.last_error = "NO_MODE"
        elif self.audio["state"] == STARTING:
            self.last_error = "CONTROL_STATE_UNSPECIFIED"
        elif self.audio["state"] in (STOPPED_USER, STOP_ERROR, PAUSED):
            # D082：STOP 后 NEXT 只选曲，保持静音
            s["index"] = (s["index"] + 1) % len(s["tracks"])
            if self.audio["state"] == PAUSED:
                self.gen += 1
                self.audio = {"state": PAUSED, "track_id": None, "position_ms": 0,
                              "owner_session": s["session_id"]}
        else:
            self._session_play_from((s["index"] + 1) % len(s["tracks"]))
        self._record("MODE_NEXT")

    def mode_play(self):
        s = self.session
        if s is None:
            self.last_error = "NO_MODE"
        elif self.audio["state"] == PAUSED:
            self.resume_audio()
        elif self.audio["state"] in (STOPPED_USER, STOP_ERROR):
            # D079/D082：从当前选中歌曲 0:00 播放
            self._session_play_from(s["index"])
        self._record("MODE_PLAY")

    def mode_exit(self):
        self._exit_session()
        if self.placement:
            self.placement["consumed"] = True     # D067：同片仍在位不得自动重新激活
        self._record("MODE_EXIT")

    # ================= 音频回调 =================
    def audio_started(self, token):
        if self._current_audio(token) and self.audio["state"] == STARTING:
            self.audio["state"] = PLAYING
            if self.session:
                self.session["has_started"] = True
        self._record("AUDIO_STARTED", token=token)

    def audio_start_failed(self, token):
        if not self._current_audio(token) or self.audio["state"] != STARTING:
            self._record("AUDIO_START_FAILED_IGNORED")
            return
        if self.session and self.session["has_started"]:
            # 已运行模式打开下一首失败才采用D080。
            self.audio["state"] = PLAYING
            self.audio_read_error(token)
        else:
            sid = self.audio["owner_session"]
            self._stop_audio_hard()
            if self.session:
                self.audio["state"], self.audio["owner_session"] = STOP_ERROR, sid
            self.last_error = "START_FAILED"
        self._record("AUDIO_START_FAILED", token=token)

    def advance(self, ms):
        if self.audio["state"] == PLAYING:
            self.audio["position_ms"] += ms
        self._record("ADVANCE", ms=ms)

    def audio_eof(self, gen):
        if not self._current_audio(gen) or self.audio["state"] != PLAYING:
            # 迟到或已失效的回调：不续播、不切歌（L15、L20、D082）
            self._record("AUDIO_EOF_IGNORED", gen=gen)
            return
        s = self.session
        if s is not None and self.audio["owner_session"] == s["session_id"]:
            self._session_play_from((s["index"] + 1) % len(s["tracks"]))   # D067 循环
        else:
            self._stop_audio_hard()                                          # A/点歌：单曲结束
        self._record("AUDIO_EOF", gen=gen)

    def audio_read_error(self, token):
        """补充版MEDIA-OLD语义：旧媒体错误不可屏蔽已发布的新版本。"""
        if not self._current_audio(token) or self.audio["state"] != PLAYING:
            self._record("AUDIO_ERROR_IGNORED")
            return
        tid = self.audio["track_id"]
        version = self.audio.get("media_version")
        if self.session:
            if self.store.tracks.get(tid, {}).get("media_version") == version:
                self.session["bad"][tid] = version
            self._session_play_from((self.session["index"] + 1) % len(self.session["tracks"]))
        else:
            self._stop_audio_hard()
        if self.audio["state"] != STOP_ERROR:
            self.last_error = f"TRACK_READ_ERROR:{tid}"
        self._record("AUDIO_READ_ERROR", track_id=tid, media_version=version)

    # ================= 内容管理 =================
    @staticmethod
    def _key(*parts):
        return json.dumps(parts, ensure_ascii=False, sort_keys=True)

    def save_playlist(self, request_id, playlist_id, tracks):
        def mutate():
            if any(t not in self.store.tracks for t in tracks):
                return "TRACK_NOT_FOUND"
            old = self.store.playlists.get(playlist_id, {"revision": 0})
            self.store.playlists[playlist_id] = {"revision": old["revision"] + 1,
                                                 "tracks": list(tracks)}
            return None
        r = self.store.commit(request_id, self._key("SAVE_PLAYLIST", playlist_id, tracks), mutate)
        self._record("SAVE_PLAYLIST", request_id=request_id, receipt=r)
        return r

    def save_binding(self, request_id, uid, kind, target):
        def mutate():
            if kind == "A" and "track" not in target:
                return "A_REQUIRES_SINGLE_TRACK"
            if "track" in target and target["track"] not in self.store.tracks:
                return "TRACK_NOT_FOUND"
            if "playlist" in target and target["playlist"] not in self.store.playlists:
                return "PLAYLIST_NOT_FOUND"
            old = self.store.bindings.get(uid, {"revision": 0})
            self.store.bindings[uid] = {"kind": kind, "target": dict(target),
                                        "revision": old["revision"] + 1}
            return None
        r = self.store.commit(request_id, self._key("SAVE_BINDING", uid, kind, target), mutate)
        # D078：保存不伪造新放置，不切换活动会话
        self._record("SAVE_BINDING", request_id=request_id, receipt=r)
        return r

    def track_references(self, tid):
        refs = []
        for uid, b in self.store.bindings.items():
            if b["target"].get("track") == tid:
                refs.append(f"binding:{uid}")
        for pid, pl in self.store.playlists.items():
            if tid in pl["tracks"]:
                refs.append(f"playlist:{pid}")
        if self.store.birthday and self.store.birthday.get("track") == tid:
            refs.append("birthday")
        if self.audio["track_id"] == tid:
            refs.append("now_playing")
        if self.session and tid in self.session["tracks"]:
            refs.append(f"session:{self.session['session_id']}")
        return refs

    def playlist_references(self, pid):
        refs = [f"binding:{uid}" for uid, b in self.store.bindings.items()
                if b["target"].get("playlist") == pid]
        if self.store.birthday and self.store.birthday.get("playlist") == pid:
            refs.append("birthday")
        if self.session and self.session["playlist_id"] == pid:
            refs.append(f"session:{self.session['session_id']}")
        return refs

    def delete_track(self, request_id, tid):
        def mutate():
            refs = self.track_references(tid)      # 提交时重查引用（D076、E04）
            if refs:
                return "REFERENCED:" + ",".join(refs)
            self.store.tracks.pop(tid, None)
            return None
        r = self.store.commit(request_id, self._key("DELETE_TRACK", tid), mutate)
        self._record("DELETE_TRACK", request_id=request_id, receipt=r)
        return r

    def delete_playlist(self, request_id, pid):
        def mutate():
            refs = self.playlist_references(pid)   # D083
            if refs:
                return "REFERENCED:" + ",".join(refs)
            self.store.playlists.pop(pid, None)    # 不删除歌曲文件
            return None
        r = self.store.commit(request_id, self._key("DELETE_PLAYLIST", pid), mutate)
        self._record("DELETE_PLAYLIST", request_id=request_id, receipt=r)
        return r

    def media_corrupted(self, tid):
        """测试辅助：文件变坏。"""
        self.store.tracks[tid]["ok"] = False
        self._record("MEDIA_CORRUPTED", track_id=tid)

    def media_published(self, tid, verified):
        """D084：修复文件完整校验并成功发布后，才解除本会话坏曲标记；不插播。"""
        if verified and tid in self.store.tracks:
            t = self.store.tracks[tid]
            t["ok"] = True
            t["start_ok"] = True
            t["media_version"] += 1
            if self.session:
                self.session["bad"].pop(tid, None)
        self._record("MEDIA_PUBLISHED", track_id=tid, verified=verified)

    # ================= 对外状态 =================
    def device_state(self):
        """本体与网页共同读取的权威状态（D085：两端显示最新成功保存结果）。"""
        return {
            "commit_seq": self.store.commit_seq,
            "bindings": {u: dict(b) for u, b in self.store.bindings.items()},
            "playlists": {p: dict(v) for p, v in self.store.playlists.items()},
            "mode_kind": self.session["kind"] if self.session else None,
            "audio_state": self.audio["state"],
            "selected_track_id": self._selected_track(),
            "ordinary_selection": copy.deepcopy(self.plain_selection),
            "position_ms": self.audio["position_ms"],
            "binding_page": self.binding_page,
            "binding_capture": copy.deepcopy(self.binding_capture),
            "placement_id": self.placement["placement_id"] if self.placement else None,
            "session_id": self.session["session_id"] if self.session else None,
            "audio_token": self.audio_token(),
            "last_error": self.last_error,
        }
