"""D093–D095及从0.2.2-batch2迁入主控制器的补充回归。"""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

from helpers import SimTestCase
from rc_sim import Controller, Store, PAUSED, PLAYING, STARTING, STOPPED, STOP_ERROR, STOPPED_USER


class TestIntegratedRules(SimTestCase):
    def test_d093_track_restart_silent_then_play_from_zero(self):
        self.ctl.select_track("t4")
        self.ctl.advance(12345)
        self.restart()
        self.assertEqual(self.audio["state"], STOPPED)
        self.assertEqual(self.ctl.device_state()["selected_track_id"], "t4")
        self.assertIsNone(self.session)
        self.ctl.play()
        self.assertEqual((self.audio["state"], self.audio["track_id"], self.audio["position_ms"]),
                         (PLAYING, "t4", 0))

    def test_d093_playlist_remembers_selected_item_without_old_mode(self):
        self.ctl.select_playlist("P", "t6")
        self.insert("uidC")
        self.restart("uidC")
        self.assertIsNone(self.session)
        self.assertEqual(self.ctl.plain_selection, {"playlist_id": "P", "track_id": "t6"})
        self.assertEqual(self.audio["state"], STOPPED)
        self.ctl.play()  # 普通播放明确入口，与待启动唱片分开
        self.assertEqual(self.audio["track_id"], "t6")
        self.assertIsNone(self.session)

    def test_d093_missing_target_reports_without_substituting(self):
        self.ctl.select_track("t4")
        del self.ctl.store.tracks["t4"]
        self.ctl.store._flush()
        self.restart()
        self.ctl.play()
        self.assertEqual(self.ctl.last_error, "SELECTED_TARGET_MISSING")
        self.assertEqual(self.audio["state"], STOPPED)
        self.assertEqual(self.ctl._selected_track(), "t4")

    def test_d093_selection_write_failure_keeps_old_target_and_audio(self):
        self.ctl.select_track("t4")
        token = self.ctl.audio_token()
        self.ctl.store.fail_next_write = True
        self.ctl.select_track("t5")
        self.assertEqual(self.ctl.last_error, "WRITE_FAILED")
        self.assertEqual(self.ctl.audio_token(), token)
        self.restart()
        self.assertEqual(self.ctl._selected_track(), "t4")

    def test_d093_old_json_without_selection_remains_readable(self):
        data = self.ctl.store._snapshot()
        data.pop("ordinary_selection")
        Path(self.path).write_text(json.dumps(data), encoding="utf-8")
        self.restart()
        self.assertIsNone(self.ctl.plain_selection)
        self.assertEqual(self.audio["state"], STOPPED)

    def test_d094_capture_save_and_leave_do_not_trigger(self):
        self.ctl.enter_binding_page()
        placement = self.insert("uidA")
        self.assertEqual(self.audio["state"], STOPPED)
        self.assertTrue(self.ctl.save_captured_binding("bind-1", "B", {"track": "t3"})["ok"])
        self.ctl.leave_binding_page()
        self.ctl.card_inserted("uidA")
        self.assertEqual(self.ctl.placement["placement_id"], placement)
        self.assertEqual(self.audio["state"], STOPPED)
        self.remove()
        self.insert("uidA")
        self.assertEqual(self.audio["track_id"], "t3")

    def test_d094_capture_cancel_preserves_binding_and_silence(self):
        binding = copy.deepcopy(self.ctl.store.bindings["uidA"])
        self.ctl.enter_binding_page()
        self.insert("uidA")
        self.ctl.execute_binding()
        self.assertEqual(self.ctl.last_error, "BINDING_PAGE_ACTIVE")
        self.ctl.leave_binding_page()
        self.ctl.card_inserted("uidA")
        self.assertEqual(self.audio["state"], STOPPED)
        self.assertEqual(self.ctl.store.bindings["uidA"], binding)

    def test_d094_old_b_removal_still_exits_while_binding(self):
        self.insert("uidB")
        self.ctl.enter_binding_page()
        self.remove()
        self.assertIsNone(self.session)
        self.insert("uidA")
        self.assertEqual(self.audio["state"], STOPPED)

    def test_d094_active_c_snapshot_survives_capture_save(self):
        self.insert("uidC")
        snapshot = copy.deepcopy(self.session)
        self.remove()
        self.ctl.enter_binding_page()
        self.insert("uidC")
        self.ctl.save_captured_binding("new-c", "C", {"track": "t9"})
        self.assertEqual(self.session, snapshot)
        self.assertEqual(self.audio["track_id"], "t1")

    def test_d094_existing_card_not_captured_and_removed_capture_rejected(self):
        self.insert("uidA")
        self.ctl.enter_binding_page()
        self.assertFalse(self.ctl.save_captured_binding("r1", "A", {"track": "t2"})["ok"])
        self.remove()
        self.insert("uidA")
        self.remove()
        self.assertFalse(self.ctl.save_captured_binding("r2", "A", {"track": "t2"})["ok"])

    def test_d095_paused_next_twice_and_late_eof_then_play_from_zero(self):
        self.insert("uidB")
        self.ctl.advance(9000)
        stale = self.ctl.audio_token()
        self.ctl.pause_audio()
        self.ctl.mode_next()
        self.ctl.mode_next()
        self.ctl.audio_eof(stale)
        self.assertEqual(self.audio["state"], PAUSED)
        self.assertEqual(self.ctl._selected_track(), "t3")
        self.ctl.play()
        self.assertEqual((self.audio["track_id"], self.audio["position_ms"]), ("t3", 0))

    def test_d095_pause_without_next_resumes_position(self):
        self.insert("uidB")
        self.ctl.advance(9876)
        self.ctl.pause_audio()
        self.ctl.play()
        self.assertEqual((self.audio["state"], self.audio["position_ms"]), (PLAYING, 9876))

    def test_d074_first_song_failure_never_skips_to_playable_second(self):
        self.ctl.store.tracks["t1"]["start_ok"] = False
        self.insert("uidB")
        self.assertTrue(self.ctl.store.tracks["t2"]["start_ok"])
        self.assertEqual(self.audio["state"], STOP_ERROR)
        self.assertEqual(self.ctl._selected_track(), "t1")
        self.assertEqual(self.ctl.last_error, "START_FAILED")
        self.assertFalse(self.session["has_started"])

    def test_d072_recovery_without_uid_does_not_forge_removal(self):
        placement = self.insert("uidB")
        self.ctl.reader_fault()
        self.ctl.reader_recovered(None)
        self.assertEqual(self.ctl.placement["placement_id"], placement)
        self.assertIsNotNone(self.session)
        self.assertNotIn("CARD_REMOVED", [e["event"] for e in self.ctl.log])
        self.ctl.execute_binding()
        self.assertEqual(self.ctl.last_error, "REPLACEMENT_REQUIRED")

    def test_d072_fault_recovery_explicit_start_requires_trusted_reseat(self):
        self.insert("uidB")
        self.ctl.reader_fault()
        self.ctl.execute_binding()
        self.assertEqual(self.ctl.last_error, "READER_UNHEALTHY")
        self.ctl.tick(self.ctl.fault_threshold_ms)
        for observed in (None, "uidC", "uidB"):
            self.ctl.reader_recovered(observed)
            self.ctl.execute_binding()
            self.assertIsNone(self.session)
            self.assertEqual(self.ctl.last_error, "REPLACEMENT_REQUIRED")
        self.ctl.reader_recovered(None, trusted_empty=True)
        self.insert("uidB")
        self.assertEqual(self.session["kind"], "B")

    def test_imported_race02_stop_during_async_start_rejects_late_results(self):
        self.ctl.async_audio = True
        self.insert("uidB")
        token = self.ctl.audio_token()
        self.assertEqual(self.audio["state"], STARTING)
        self.ctl.stop_audio()
        self.ctl.audio_started(token)
        self.ctl.audio_start_failed(token)
        self.ctl.audio_eof(token)
        self.assertEqual(self.audio["state"], STOPPED_USER)
        self.assertEqual(self.ctl._selected_track(), "t1")

    def test_imported_runtime_open_distinguishes_first_and_later_failures(self):
        self.ctl.async_audio = True
        self.insert("uidB")
        self.ctl.audio_start_failed(self.ctl.audio_token())
        self.assertEqual(self.audio["state"], STOP_ERROR)
        self.assertEqual(self.ctl._selected_track(), "t1")
        self.ctl.mode_play()
        self.ctl.audio_started(self.ctl.audio_token())
        self.ctl.audio_eof(self.ctl.audio_token())
        self.assertEqual(self.ctl._selected_track(), "t2")
        self.ctl.audio_start_failed(self.ctl.audio_token())
        self.assertEqual(self.ctl._selected_track(), "t3")
        self.assertEqual(self.audio["state"], STARTING)

    def test_imported_race01_same_session_old_operation_and_old_boot_rejected(self):
        self.insert("uidB")
        stale = self.ctl.audio_token()
        self.eof()
        self.ctl.audio_eof(stale)
        self.assertEqual(self.audio["track_id"], "t2")
        self.restart()
        self.insert("uidB")
        self.ctl.audio_eof(stale)
        self.assertEqual(self.audio["track_id"], "t1")

    def test_imported_media_old_error_cannot_poison_new_version(self):
        self.insert("uidB")
        token = self.ctl.audio_token()
        self.ctl.media_published("t1", verified=True)
        self.assertEqual(self.ctl.audio_token(), token)  # 不插播
        self.ctl.audio_read_error(token)
        self.assertNotIn("t1", self.session["bad"])
        self.assertEqual(self.audio["track_id"], "t2")
        self.eof(6)
        self.assertEqual(self.audio["track_id"], "t1")
        self.assertEqual(self.audio["media_version"], 2)

    def test_imported_media_current_error_is_bounded_and_repair_not_autoplay(self):
        self.insert("uidCS")
        self.ctl.audio_read_error(self.ctl.audio_token())
        self.ctl.audio_read_error(self.ctl.audio_token())
        self.assertEqual(self.audio["state"], STOP_ERROR)
        self.ctl.media_published("t8", verified=True)
        self.assertEqual(self.audio["state"], STOP_ERROR)
        self.ctl.play()
        self.assertEqual(self.audio["track_id"], "t8")

    def test_imported_proc_txn_json_replacement_crash_keeps_config_receipt_together(self):
        # PROC-TXN迁入JSON路线：真实子进程退出，不是物理断电或多写者测试。
        worker = """
import os, sys
from rc_sim import Store, Controller
s = Store.load(sys.argv[1])
def hook(stage):
    if stage == sys.argv[2]:
        os._exit(91)
s.flush_hook = hook
Controller(s).save_binding(sys.argv[3], 'crash-card', 'A', {'track': 't2'})
"""
        root = str(Path(__file__).resolve().parents[1])
        for stage, committed in (("before_replace", False), ("after_replace", True)):
            with self.subTest(stage=stage):
                request = "crash-" + stage
                before = Store.load(self.path).commit_seq
                run = subprocess.run([sys.executable, "-B", "-c", worker, self.path, stage, request],
                                     cwd=root, timeout=15, capture_output=True, text=True)
                self.assertEqual(run.returncode, 91, run.stderr)
                recovered = Store.load(self.path)
                self.assertEqual(request in recovered.receipts, committed)
                self.assertEqual(recovered.commit_seq, before + int(committed))
                if committed:
                    self.assertEqual(recovered.bindings["crash-card"]["target"], {"track": "t2"})
                    retry = Controller(recovered).save_binding(request, "crash-card", "A", {"track": "t2"})
                    self.assertTrue(retry["replayed"])
                    self.assertEqual(recovered.commit_seq, before + 1)
                else:
                    self.assertNotIn("crash-card", recovered.bindings)

    def test_imported_partial_json_is_never_promoted_on_boot(self):
        self.ctl.select_track("t4")
        Path(self.path + ".tmp").write_text('{"ordinary_selection":', encoding="utf-8")
        self.restart()
        self.assertEqual(self.ctl._selected_track(), "t4")
        self.assertEqual(self.audio["state"], STOPPED)

    def test_d095_ordinary_playlist_paused_next_and_restart_preserve_new_selection(self):
        self.ctl.select_playlist("P", "t4")
        self.ctl.advance(2000)
        self.ctl.pause_audio()
        self.ctl.next_track()
        self.assertEqual(self.audio["state"], PAUSED)
        self.assertEqual(self.ctl._selected_track(), "t5")
        self.ctl.play()
        self.assertEqual((self.audio["track_id"], self.audio["position_ms"]), ("t5", 0))
        self.restart()
        self.assertEqual(self.ctl._selected_track(), "t5")
        self.assertEqual(self.audio["state"], STOPPED)

    def test_d072_ambiguous_recovery_keeps_original_fault_deadline(self):
        self.insert("uidB")
        self.ctl.reader_fault()
        self.ctl.tick(2000)
        self.ctl.reader_recovered(None)
        self.ctl.tick(1000)
        self.assertIsNone(self.session)
        self.assertEqual(self.ctl.last_error, "READER_FAULT_PROTECTION_EXIT")

    def test_imported_race03_new_session_ignores_old_callback_and_removal(self):
        first = self.insert("uidB")
        old_token = self.ctl.audio_token()
        self.remove()
        self.insert("uidB2")
        self.ctl.audio_eof(old_token)
        self.ctl.audio_read_error(old_token)
        self.ctl.card_removed(first)
        self.assertEqual(self.audio["track_id"], "t3")
        self.assertEqual(self.session["origin_uid"], "uidB2")

    def test_imported_media_pause_resume_keeps_old_version_and_position(self):
        self.insert("uidB")
        self.ctl.advance(2500)
        self.ctl.pause_audio()
        self.ctl.media_published("t1", verified=True)
        self.ctl.play()
        self.assertEqual((self.audio["media_version"], self.audio["position_ms"]), (1, 2500))

    def test_d093_card_single_track_does_not_inherit_ordinary_playlist(self):
        self.ctl.select_playlist("P", "t1")
        self.insert("uidA")
        self.assertEqual(self.ctl.plain_selection, {"playlist_id": None, "track_id": "t1"})
        self.restart()
        self.assertEqual(self.ctl.plain_selection, {"playlist_id": "P", "track_id": "t1"})
