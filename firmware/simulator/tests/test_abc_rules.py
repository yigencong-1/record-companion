"""validation.md 中 L/C/E 系列里已确认、可纯逻辑验证的 ABC 规则。"""

import unittest

from helpers import SimTestCase
from rc_sim import PAUSED, PLAYING, STOPPED, STOPPED_USER, STOP_ERROR


class TestABCRules(SimTestCase):
    def test_l03_real_reinsert_of_a_triggers_again(self):
        self.insert("uidA")
        self.remove()
        gen = self.ctl.gen
        self.insert("uidA")
        self.assertGreater(self.ctl.gen, gen)
        self.assertEqual(self.audio["track_id"], "t1")

    def test_l05_b_reinsert_starts_from_beginning(self):
        self.insert("uidB")
        self.eof(3)
        self.remove()
        self.insert("uidB")
        self.assertEqual(self.audio["track_id"], "t1")

    def test_l06_manual_exit_does_not_revive_until_real_reseat(self):
        self.insert("uidB")
        self.ctl.mode_exit()
        self.ctl.card_inserted("uidB")                    # 重复读到同 UID
        self.assertIsNone(self.session)
        self.remove()
        self.insert("uidB")
        self.assertEqual(self.session["kind"], "B")

    def test_l08_c_keeps_looping_after_removal(self):
        self.insert("uidC")
        self.remove()
        self.eof(1)
        self.assertEqual(self.session["kind"], "C")
        self.assertEqual(self.audio["track_id"], "t2")

    def test_l10_new_a_exits_c(self):
        self.insert("uidC")
        self.remove()
        self.insert("uidA2")
        self.assertIsNone(self.session)
        self.assertEqual(self.audio["track_id"], "t2")

    def test_l12_in_mode_controls_do_not_exit(self):
        self.insert("uidC")
        sid = self.session["session_id"]
        self.ctl.mode_next()
        self.ctl.pause_audio()
        self.ctl.resume_audio()
        self.assertEqual(self.session["session_id"], sid)
        self.assertEqual(self.audio["state"], PLAYING)

    def test_l13_invalid_new_card_keeps_c(self):
        self.insert("uidC")
        self.remove()
        self.insert("uid-unbound")
        self.assertEqual(self.ctl.last_error, "UNBOUND")
        self.assertEqual(self.session["kind"], "C")

    def test_l14_l25_b_removed_then_unbound_card_does_not_revive_b(self):
        self.insert("uidB")
        self.remove()
        self.insert("uid-unbound")
        self.assertIsNone(self.session)
        self.assertEqual(self.audio["state"], STOPPED)

    def test_l15_late_b_removal_after_web_select_has_no_effect(self):
        pid = self.insert("uidB")
        self.ctl.select_track("t5")                       # 网页点歌接管
        self.assertIsNone(self.session)
        self.ctl.card_removed(pid)                        # 迟到的旧 B 取走
        self.assertEqual(self.audio["state"], PLAYING)
        self.assertEqual(self.audio["track_id"], "t5")

    def test_l20_stale_eof_is_ignored(self):
        self.insert("uidB")
        old_gen = self.ctl.gen
        self.ctl.pause_audio()
        self.ctl.audio_eof(old_gen)
        self.assertEqual(self.audio["state"], PAUSED)
        self.assertEqual(self.audio["track_id"], "t1")

    def test_l21_rebind_in_place_does_not_fake_insert(self):
        self.insert("uidC")
        sid = self.session["session_id"]
        self.ctl.save_binding("r1", "uidC", "C", {"track": "t9"})
        self.assertEqual(self.session["session_id"], sid)
        self.ctl.execute_binding()                        # 用户明确执行新绑定
        self.assertEqual(self.session["tracks"], ["t9"])

    def test_l22_c15_stop_at_6th_replays_6th_from_zero_pause_resumes(self):
        self.insert("uidB")
        self.eof(5)
        self.assertEqual(self.audio["track_id"], "t6")
        self.ctl.advance(120_000)                         # 第 6 首 2:00
        self.ctl.pause_audio()
        self.ctl.resume_audio()
        self.assertEqual(self.audio["position_ms"], 120_000)   # PAUSE 从原位置继续
        stale = self.ctl.gen
        self.ctl.stop_audio()
        self.ctl.audio_eof(stale)                         # 旧 EOF 不循环
        self.assertEqual(self.audio["state"], STOPPED_USER)
        self.ctl.mode_play()
        self.assertEqual(self.audio["track_id"], "t6")    # 不是第 1 首
        self.assertEqual(self.audio["position_ms"], 0)
        self.eof(1)
        self.assertEqual(self.audio["track_id"], "t7")

    def test_l23_power_cycle_does_not_resume_c(self):
        self.insert("uidC")
        self.remove()
        self.restart()
        self.assertIsNone(self.session)
        self.assertEqual(self.audio["state"], STOPPED)

    def test_l27_e03_c_reinsert_keeps_stop_lock(self):
        self.insert("uidC")
        self.ctl.stop_audio()
        self.remove()
        self.insert("uidC")
        self.assertEqual(self.audio["state"], STOPPED_USER)
        self.assertIsNone(self.ctl.last_error)

    def test_l29_pause_stop_then_exit(self):
        self.insert("uidC")
        self.ctl.pause_audio()
        self.ctl.stop_audio()
        self.assertEqual(self.session["kind"], "C")
        self.ctl.mode_exit()
        self.assertIsNone(self.session)

    def test_e15_double_next_while_stopped_with_late_eof(self):
        self.insert("uidB")
        stale = self.ctl.gen
        self.ctl.stop_audio()
        self.ctl.mode_next()
        self.ctl.mode_next()
        self.ctl.audio_eof(stale)
        self.assertEqual(self.audio["state"], STOPPED_USER)
        self.assertEqual(self.ctl._selected_track(), "t3")

    def test_e08_c22_all_unplayable_mode_stays_until_exit(self):
        for t in ("t8", "t9"):
            self.ctl.media_corrupted(t)
        self.insert("uidCS")
        self.assertEqual(self.session["kind"], "C")
        self.ctl.mode_exit()
        self.assertIsNone(self.session)

    def _assert_c_replaced_by(self, uid, kind, first_track):
        self.insert("uidC")
        sid = self.session["session_id"]
        stale_gen = self.ctl.gen
        self.remove()
        self.insert(uid)
        self.assertEqual(self.session["kind"], kind)
        self.assertEqual(self.session["origin_uid"], uid)
        self.assertGreater(self.session["session_id"], sid)
        self.assertIsNone(self.ctl.last_error)
        self.assertEqual(self.audio["track_id"], first_track)
        self.ctl.audio_eof(stale_gen)
        self.assertEqual(self.audio["track_id"], first_track)
        if kind == "B":
            self.remove()
        else:
            self.ctl.mode_exit()
        self.assertIsNone(self.session)                  # 新模式结束不恢复旧 C
        self.assertEqual(self.audio["state"], STOPPED)

    def test_d089_new_b_replaces_removed_c_without_restoration(self):
        self._assert_c_replaced_by("uidB2", "B", "t3")

    def test_d089_new_c_replaces_removed_c_without_restoration(self):
        self._assert_c_replaced_by("uidCS", "C", "t8")

    def test_d089_invalid_new_target_keeps_old_c(self):
        self.insert("uidC")
        sid = self.session["session_id"]
        self.remove()
        del self.ctl.store.tracks["t3"]                 # 新片已绑定的目标丢失
        self.insert("uidB2")
        self.assertEqual(self.ctl.last_error, "TARGET_INVALID")
        self.assertEqual(self.session["session_id"], sid)
        self.assertEqual(self.audio["track_id"], "t1")

    def test_d089_new_start_failure_does_not_restore_old_c(self):
        self.insert("uidC")
        sid = self.session["session_id"]
        self.remove()
        self.ctl.store.tracks["t3"]["start_ok"] = False
        self.insert("uidB2")
        self.assertGreater(self.session["session_id"], sid)
        self.assertEqual(self.session["origin_uid"], "uidB2")
        self.assertEqual(self.audio["state"], STOP_ERROR)
        self.assertEqual(self.ctl.last_error, "START_FAILED")
        self.remove()
        self.assertIsNone(self.session)

    def test_d072_repeated_fault_reports_keep_first_fault_deadline(self):
        self.insert("uidB")
        self.ctl.reader_fault()
        self.ctl.tick(1000)
        self.ctl.reader_fault()
        self.ctl.tick(1000)
        self.ctl.reader_fault()
        self.ctl.tick(999)
        self.assertIsNotNone(self.session)
        self.ctl.tick(1)                                # 距首次故障共 3000 ms
        self.assertIsNone(self.session)
        self.assertEqual(self.ctl.last_error, "READER_FAULT_PROTECTION_EXIT")
        self.ctl.reader_recovered("uidB")
        self.assertIsNone(self.session)                 # 恢复同片仍不得自启

    def test_d090_explicit_play_searches_original_snapshot_from_selection(self):
        self.insert("uidC")
        self.eof(5)                                     # 当前选曲为第 6 首
        for tid in self.session["tracks"]:
            self.ctl.media_corrupted(tid)
        self.eof()
        self.assertEqual(self.audio["state"], STOP_ERROR)
        self.assertEqual(self.ctl._selected_track(), "t6")
        self.ctl.save_playlist("new-order", "P", ["t2", "t7"])
        self.ctl.media_published("t2", verified=True)
        self.ctl.media_published("t7", verified=True)
        self.assertEqual(self.audio["state"], STOP_ERROR)
        self.ctl.mode_play()
        self.assertEqual(self.audio["track_id"], "t7")   # 原快照 t6 后先到 t7
        self.assertEqual(self.audio["position_ms"], 0)


if __name__ == "__main__":
    unittest.main()
