"""RC-08C-01：最后成功保存覆盖、request_id 幂等、写入失败与重启恢复（D085）。"""

import unittest
from unittest.mock import patch

from helpers import SimTestCase
from rc_sim import Store


class TestCommitProtocol(SimTestCase):
    def test_same_request_id_different_payload_is_rejected(self):
        self.ctl.save_binding("r1", "uid9", "A", {"track": "t1"})
        r = self.ctl.save_binding("r1", "uid9", "A", {"track": "t2"})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "REQUEST_ID_PAYLOAD_MISMATCH")
        self.assertEqual(self.ctl.store.bindings["uid9"]["target"], {"track": "t1"})

    def test_write_failure_changes_nothing_and_can_be_retried(self):
        seq = self.ctl.store.commit_seq
        self.ctl.store.fail_next_write = True
        r = self.ctl.save_binding("r1", "uid9", "A", {"track": "t1"})
        self.assertEqual(r["error"], "WRITE_FAILED")
        self.assertNotIn("uid9", self.ctl.store.bindings)
        self.assertEqual(self.ctl.store.commit_seq, seq)
        self.assertNotIn("r1", self.ctl.store.receipts)
        r = self.ctl.save_binding("r1", "uid9", "A", {"track": "t1"})
        self.assertTrue(r["ok"])
        self.assertFalse(r["replayed"])

    def test_receipts_survive_restart(self):
        first = self.ctl.save_binding("web-A", "uid9", "A", {"track": "t1"})
        self.ctl.save_binding("body-B", "uid9", "A", {"track": "t2"})
        self.restart()
        retry = self.ctl.save_binding("web-A", "uid9", "A", {"track": "t1"})
        self.assertTrue(retry["replayed"])
        self.assertEqual(retry["commit_seq"], first["commit_seq"])
        self.assertEqual(self.ctl.store.bindings["uid9"]["target"], {"track": "t2"})

    def test_os_write_errors_roll_back_and_retry_without_false_receipt(self):
        for operation in ("builtins.open", "rc_sim.store.os.replace"):
            with self.subTest(operation=operation):
                request_id = "write-error-" + operation
                uid = "new-card-" + operation
                seq = self.ctl.store.commit_seq
                with patch(operation, side_effect=OSError("file write failed")):
                    result = self.ctl.save_binding(request_id, uid, "A", {"track": "t1"})
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "WRITE_FAILED")
                self.assertEqual(self.ctl.store.commit_seq, seq)
                self.assertNotIn(uid, self.ctl.store.bindings)
                self.assertNotIn(request_id, self.ctl.store.receipts)
                self.assertNotIn(uid, Store.load(self.path).bindings)
                retry = self.ctl.save_binding(request_id, uid, "A", {"track": "t1"})
                self.assertTrue(retry["ok"])
                self.assertFalse(retry["replayed"])
                disk = Store.load(self.path)
                self.assertEqual(disk.bindings[uid]["target"], {"track": "t1"})
                self.assertEqual(disk.receipts[request_id]["commit_seq"], seq + 1)

    def test_rejected_commit_is_also_idempotent(self):
        self.insert("uidB")
        r1 = self.ctl.delete_track("del", "t1")
        r2 = self.ctl.delete_track("del", "t1")
        self.assertFalse(r1["ok"])
        self.assertTrue(r2["replayed"])
        self.assertEqual(r1["error"], r2["error"])

    def test_c02_a_binding_rejects_playlist(self):
        r = self.ctl.save_binding("r1", "uid9", "A", {"playlist": "P"})
        self.assertEqual(r["error"], "A_REQUIRES_SINGLE_TRACK")

    def test_e21_delete_rechecks_latest_references(self):
        self.ctl.save_playlist("s1", "NEW", ["t9"])       # 另一入口刚建立引用
        r = self.ctl.delete_track("d1", "t9")
        self.assertFalse(r["ok"])
        self.assertIn("playlist:NEW", r["error"])

    def test_log_has_required_fields(self):
        self.insert("uidB")
        required = {"event_seq", "placement_id", "session_id", "mode_kind", "audio_state",
                    "selected_track_id", "playlist_snapshot_revision", "media_revision",
                    "saved_binding_revision", "successful_commit_seq", "last_error"}
        self.assertTrue(required.issubset(self.ctl.log[-1].keys()))


if __name__ == "__main__":
    unittest.main()
