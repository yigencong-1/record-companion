"""带持久化语义的虚拟内容存储（RC-08C-01、RC-08C-02）。

保存内容：曲目、歌单、唱片绑定、生日入口引用，以及按 request_id 记录的提交回执。
配置和回执放在同一个 JSON 文件里，整体写入临时文件后用 os.replace 替换，
所以重启后配置和去重回执始终一致。

注意：这只模拟“替换式写入”的语义，不代表真实 SD 卡或 FAT 文件系统掉电安全（未验证）。
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field


class StoreWriteError(Exception):
    """注入的写入失败。"""


@dataclass
class Receipt:
    request_id: str
    ok: bool
    commit_seq: int | None
    error: str | None
    payload_key: str


@dataclass
class Store:
    path: str
    tracks: dict = field(default_factory=dict)        # track_id -> {"ok": bool, "start_ok": bool, "media_version": int}
    playlists: dict = field(default_factory=dict)     # playlist_id -> {"revision": int, "tracks": [track_id]}
    bindings: dict = field(default_factory=dict)      # uid -> {"kind": "A"|"B"|"C", "target": {...}, "revision": int}
    birthday: dict | None = None                      # {"track": id} 或 {"playlist": id}
    commit_seq: int = 0
    receipts: dict = field(default_factory=dict)      # request_id -> Receipt 字典
    fail_next_write: bool = False                     # 故障注入

    # ---------- 持久化 ----------
    @classmethod
    def load(cls, path: str) -> "Store":
        s = cls(path=path)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            s.tracks = data["tracks"]
            s.playlists = data["playlists"]
            s.bindings = data["bindings"]
            s.birthday = data["birthday"]
            s.commit_seq = data["commit_seq"]
            s.receipts = data["receipts"]
        return s

    def _snapshot(self) -> dict:
        return {
            "tracks": self.tracks,
            "playlists": self.playlists,
            "bindings": self.bindings,
            "birthday": self.birthday,
            "commit_seq": self.commit_seq,
            "receipts": self.receipts,
        }

    def _flush(self) -> None:
        if self.fail_next_write:
            self.fail_next_write = False
            raise StoreWriteError("injected write failure")
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._snapshot(), f, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, self.path)

    # ---------- 事务式提交 ----------
    def commit(self, request_id: str, payload_key: str, mutate) -> dict:
        """执行一次带去重的提交。

        - 同一 request_id、同一载荷：直接返回原回执，不再执行（D085 幂等）。
        - 同一 request_id、不同载荷：拒绝，不改变配置。
        - mutate 返回错误字符串表示业务拒绝（例如删除被引用）；拒绝也记录回执，
          这样重试得到同样的结果。
        - 写入失败：内存回滚，既不改配置也不留回执。
        """
        old = self.receipts.get(request_id)
        if old is not None:
            if old["payload_key"] != payload_key:
                return {"request_id": request_id, "ok": False, "commit_seq": None,
                        "error": "REQUEST_ID_PAYLOAD_MISMATCH", "payload_key": payload_key,
                        "replayed": False}
            return dict(old, replayed=True)

        backup = copy.deepcopy(self._snapshot())
        error = mutate()
        if error is None:
            self.commit_seq += 1
            receipt = {"request_id": request_id, "ok": True, "commit_seq": self.commit_seq,
                       "error": None, "payload_key": payload_key}
        else:
            receipt = {"request_id": request_id, "ok": False, "commit_seq": None,
                       "error": error, "payload_key": payload_key}
        self.receipts[request_id] = receipt
        try:
            self._flush()
        except StoreWriteError:
            # 回滚到提交前状态：失败的提交不改变已保存配置（D085）
            self.tracks = backup["tracks"]
            self.playlists = backup["playlists"]
            self.bindings = backup["bindings"]
            self.birthday = backup["birthday"]
            self.commit_seq = backup["commit_seq"]
            self.receipts = backup["receipts"]
            return {"request_id": request_id, "ok": False, "commit_seq": None,
                    "error": "WRITE_FAILED", "payload_key": payload_key, "replayed": False}
        return dict(receipt, replayed=False)

    # ---------- 初始数据（测试夹具用，不走去重） ----------
    def seed(self, tracks=None, playlists=None, bindings=None, birthday=None) -> None:
        for tid, info in (tracks or {}).items():
            self.tracks[tid] = {"ok": True, "start_ok": True, "media_version": 1, **info}
        for pid, items in (playlists or {}).items():
            self.playlists[pid] = {"revision": 1, "tracks": list(items)}
        for uid, b in (bindings or {}).items():
            self.bindings[uid] = {"revision": 1, **b}
        self.birthday = birthday
        self._flush()
