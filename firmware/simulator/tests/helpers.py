"""测试夹具：在临时目录建立虚拟曲库与绑定。"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rc_sim import Controller, Store  # noqa: E402

TRACKS = {f"t{i}": {} for i in range(1, 10)}
PLAYLISTS = {
    "P": ["t1", "t2", "t3", "t4", "t5", "t6", "t7"],   # 7 首，便于测“第 6 首”
    "SMALL": ["t8", "t9"],
    "BDAY": ["t1"],
}
BINDINGS = {
    "uidA": {"kind": "A", "target": {"track": "t1"}},
    "uidA2": {"kind": "A", "target": {"track": "t2"}},
    "uidB": {"kind": "B", "target": {"playlist": "P"}},
    "uidB2": {"kind": "B", "target": {"track": "t3"}},
    "uidC": {"kind": "C", "target": {"playlist": "P"}},
    "uidCS": {"kind": "C", "target": {"playlist": "SMALL"}},
}


class SimTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "store.json")
        store = Store.load(self.path)
        store.seed(tracks=TRACKS, playlists=PLAYLISTS, bindings=BINDINGS,
                   birthday={"playlist": "BDAY"})
        self.ctl = Controller(store)

    def tearDown(self):
        self._tmp.cleanup()

    # ---- 小工具 ----
    def insert(self, uid):
        self.ctl.card_inserted(uid)
        return self.ctl.placement["placement_id"]

    def remove(self):
        self.ctl.card_removed(self.ctl.placement["placement_id"])

    def eof(self, times=1):
        for _ in range(times):
            self.ctl.audio_eof(self.ctl.gen)

    def restart(self, present_uid=None):
        """模拟关机重启：只保留持久化存储。"""
        self.ctl = Controller(Store.load(self.path), present_uid=present_uid)

    @property
    def audio(self):
        return self.ctl.audio

    @property
    def session(self):
        return self.ctl.session
