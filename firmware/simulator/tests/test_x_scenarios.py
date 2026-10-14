"""product/validation.md 中 RC-08 的 X01–X12 确定性回放场景。"""

import unittest

from helpers import SimTestCase
from rc_sim import PLAYING, STOP_ERROR, STOPPED, STOPPED_USER


class TestX(SimTestCase):
    def test_x01_a_plays_once_and_continues_after_removal(self):
        self.insert("uidA")
        gen = self.ctl.gen
        self.assertEqual(self.audio["state"], PLAYING)
        self.assertEqual(self.audio["track_id"], "t1")
        # 同片持续在位，读卡重复返回同 UID：不是新放置
        pid = self.ctl.placement["placement_id"]
        self.ctl.card_inserted("uidA")
        self.assertEqual(self.ctl.placement["placement_id"], pid)
        self.assertEqual(self.ctl.gen, gen)               # 没有重新点播
        self.remove()
        self.assertEqual(self.audio["state"], PLAYING)   # A 取走继续
        self.assertIsNone(self.session)                  # A 不创建常驻模式

    def test_x02_b_exits_on_removal_even_when_paused_or_stopped(self):
        self.insert("uidB")
        self.ctl.pause_audio()
        self.ctl.stop_audio()
        self.assertEqual(self.session["kind"], "B")
        self.assertEqual(self.audio["state"], STOPPED_USER)
        self.remove()
        self.assertIsNone(self.session)
        self.assertEqual(self.audio["state"], STOPPED)

    def test_x03_c_return_stop_next_play(self):
        self.insert("uidC")
        sid = self.session["session_id"]
        self.eof(2)                                       # 正在第 3 首
        self.remove()
        self.insert("uidC")                               # D071：不重新触发
        self.assertEqual(self.session["session_id"], sid)
        self.assertIsNone(self.ctl.last_error)            # 是 D071 规则，不是“跨模式未确认”
        self.assertEqual(self.audio["track_id"], "t3")
        self.ctl.stop_audio()
        self.ctl.mode_next()                              # D082：只选曲、保持静音
        self.assertEqual(self.audio["state"], STOPPED_USER)
        self.assertEqual(self.ctl._selected_track(), "t4")
        self.ctl.mode_play()                              # 从新选曲 0:00 开始
        self.assertEqual(self.audio["state"], PLAYING)
        self.assertEqual(self.audio["track_id"], "t4")
        self.assertEqual(self.audio["position_ms"], 0)

    def test_x04_boot_with_card_waits_for_explicit_start(self):
        self.insert("uidC")
        self.restart(present_uid="uidC")                  # D073：旧 C 不恢复
        self.assertIsNone(self.session)
        self.assertEqual(self.audio["state"], STOPPED)
        self.ctl.tick(10_000)
        self.assertIsNone(self.session)                   # D052：没有显式启动就不播
        self.ctl.start_held()
        self.assertEqual(self.session["kind"], "C")
        self.assertEqual(self.audio["state"], PLAYING)

    def test_x05_preflight_failure_keeps_mode_start_failure_does_not_roll_back(self):
        self.insert("uidC")
        sid = self.session["session_id"]
        self.ctl.select_track("no-such-track")            # 预检失败
        self.assertEqual(self.ctl.last_error, "TRACK_NOT_FOUND")
        self.assertEqual(self.session["session_id"], sid)
        self.ctl.store.tracks["t9"]["start_ok"] = False
        self.ctl.select_track("t9")                       # 预检通过、实际启动失败
        self.assertEqual(self.ctl.last_error, "START_FAILED")
        self.assertIsNone(self.session)                   # 不回滚旧 C
        self.assertEqual(self.audio["state"], STOPPED)

    def test_x06_reader_fault_short_then_long(self):
        self.insert("uidB")
        sid = self.session["session_id"]
        self.ctl.reader_fault()
        self.ctl.tick(1000)
        self.ctl.reader_recovered("uidB")                 # 短故障：模式保留
        self.assertEqual(self.session["session_id"], sid)
        self.ctl.reader_fault()
        self.ctl.tick(self.ctl.fault_threshold_ms)        # 长故障：保护退出
        self.assertIsNone(self.session)
        self.assertEqual(self.ctl.last_error, "READER_FAULT_PROTECTION_EXIT")
        events = [e["event"] for e in self.ctl.log]
        self.assertNotIn("CARD_REMOVED", events)          # 不伪造取走
        self.ctl.reader_recovered("uidB")                 # 恢复见同 UID：不自启
        self.assertIsNone(self.session)
        self.remove()
        self.insert("uidB")                               # 真实重新取放才激活
        self.assertEqual(self.session["kind"], "B")

    def test_x07_saved_changes_do_not_touch_active_snapshot(self):
        self.insert("uidB")
        before = (list(self.session["tracks"]), self.session["snapshot_revision"])
        self.ctl.save_playlist("r1", "P", ["t9", "t8"])
        self.ctl.save_binding("r2", "uidB", "B", {"track": "t5"})
        self.assertEqual((self.session["tracks"], self.session["snapshot_revision"]), before)
        self.eof(1)
        self.assertEqual(self.audio["track_id"], "t2")    # 仍按旧快照循环
        self.remove()
        self.insert("uidB")                               # 下一次真实放入才用新绑定
        self.assertEqual(self.session["tracks"], ["t5"])

    def test_x08_delete_protection_for_tracks_and_playlists(self):
        self.insert("uidCS")                              # 活动会话引用 SMALL
        r = self.ctl.delete_track("d1", "t8")
        self.assertFalse(r["ok"])
        self.assertIn("now_playing", r["error"])
        self.assertIn("playlist:SMALL", r["error"])
        self.assertIn("session:", r["error"])
        r = self.ctl.delete_playlist("d2", "SMALL")
        self.assertFalse(r["ok"])
        self.assertIn("binding:uidCS", r["error"])
        r = self.ctl.delete_playlist("d3", "BDAY")
        self.assertIn("birthday", r["error"])
        # 无引用的歌单可以删，且不删除歌曲
        self.ctl.save_playlist("s1", "TMP", ["t4"])
        r = self.ctl.delete_playlist("d4", "TMP")
        self.assertTrue(r["ok"])
        self.assertIn("t4", self.ctl.store.tracks)

    def test_x09_bad_track_skip_and_repair(self):
        self.insert("uidB")
        self.ctl.media_corrupted("t3")
        self.eof(2)                                       # t1 → t2 → t3 坏 → t4
        self.assertEqual(self.audio["track_id"], "t4")
        self.assertIn("t3", self.session["bad"])
        self.eof(6)                                       # t5 t6 t7 t1 t2 → 跳过 t3 → t4
        self.assertEqual(self.audio["track_id"], "t4")
        self.ctl.media_published("t3", verified=False)    # 修复未通过校验：不解锁
        self.assertIn("t3", self.session["bad"])
        self.ctl.media_published("t3", verified=True)     # 成功发布：解锁但不插播
        self.assertNotIn("t3", self.session["bad"])
        self.assertEqual(self.audio["track_id"], "t4")
        self.eof(6)                                       # 下一次轮到 t3 才播
        self.assertEqual(self.audio["track_id"], "t3")
        self.ctl.media_corrupted("t3")                    # 再坏一次：下次轮到时重新标记并跳过
        self.eof(7)                                       # t4 … t2，再从 t3 跳到 t4
        self.assertEqual(self.audio["track_id"], "t4")
        self.assertIn("t3", self.session["bad"])

    def test_x10_all_unplayable_then_repair_needs_explicit_play(self):
        self.ctl.media_corrupted("t8")
        self.ctl.media_corrupted("t9")
        self.insert("uidCS")
        self.assertEqual(self.session["kind"], "C")       # 模式保持
        self.assertEqual(self.audio["state"], STOP_ERROR)
        self.ctl.media_published("t8", verified=True)
        self.assertEqual(self.audio["state"], STOP_ERROR) # 不自动发声
        self.ctl.mode_play()
        self.assertEqual(self.audio["state"], PLAYING)
        self.assertEqual(self.audio["track_id"], "t8")

    def test_x11_last_successful_save_wins_and_late_receipt_does_not_rewind(self):
        r_a = self.ctl.save_binding("body-1", "uid9", "A", {"track": "t1"})
        r_b = self.ctl.save_binding("web-1", "uid9", "A", {"track": "t2"})
        self.assertTrue(r_a["ok"] and r_b["ok"])
        self.assertGreater(r_b["commit_seq"], r_a["commit_seq"])
        # 旧 A 回执最后才到页面：页面以设备权威状态刷新
        ui_view = self.ctl.device_state()
        self.assertEqual(ui_view["bindings"]["uid9"]["target"], {"track": "t2"})

    def test_x12_retry_with_same_request_id_only_replays(self):
        first = self.ctl.save_binding("web-A", "uid9", "A", {"track": "t1"})
        self.ctl.save_binding("body-B", "uid9", "A", {"track": "t2"})
        retry = self.ctl.save_binding("web-A", "uid9", "A", {"track": "t1"})
        self.assertTrue(retry["replayed"])
        self.assertEqual(retry["commit_seq"], first["commit_seq"])
        self.assertEqual(self.ctl.store.bindings["uid9"]["target"], {"track": "t2"})
        r = self.ctl.delete_track("del-1", "t2")          # 删除保护仍正常
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
