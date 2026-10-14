"""Independent behavioral expectations from product/validation.md."""

from controller import (AudioToken, Binding, CardIdentity, Controller, FakeAudio,
                        FakeCatalogStore, FakeNFC, PlaylistSnapshot, VirtualClock)


A = CardIdentity("ISO14443A", bytes.fromhex("01020304"))
B = CardIdentity("ISO14443A", bytes.fromhex("01020304050607"))
C = CardIdentity("ISO14443A", bytes.fromhex("a1b2c3d4"))
C2 = CardIdentity("ISO14443A", bytes.fromhex("a2b2c3d4"))
UNBOUND = CardIdentity("ISO14443A", bytes.fromhex("f1f2f3f4"))
MISSING = CardIdentity("ISO14443A", bytes.fromhex("e1e2e3e4"))


class Rig:
    def __init__(self):
        self.catalog = FakeCatalogStore(
            {A: Binding("A", "TRACK", "t1"), B: Binding("B", "PLAYLIST", "mix"),
             C: Binding("C", "PLAYLIST", "mix"), C2: Binding("C", "TRACK", "t4"),
             MISSING: Binding("A", "TRACK", "missing")},
            {"mix": PlaylistSnapshot("mix", 1, ("t1", "t2", "t3", "t4", "t5", "t6", "t7"))},
            ("t1", "t2", "t3", "t4", "t5", "t6", "t7"))
        self.audio, self.clock = FakeAudio(), VirtualClock()
        self.ctrl = Controller(self.catalog, self.audio, self.clock, fault_limit_ms=1000)
        self.nfc = FakeNFC(self.ctrl)
        self.checks = []

    @property
    def s(self):
        return self.ctrl.state

    def check(self, label, actual, expected):
        self.checks.append({"label": label, "actual": actual, "expected": expected})
        if actual != expected:
            raise AssertionError(f"{label}: expected {expected!r}, actual {actual!r}")

    def command(self, kind, **payload):
        return self.ctrl.dispatch(kind, **payload)

    def started(self, card):
        self.nfc.insert(card)
        self.ack()
        return self.s.mode.session_id if self.s.mode else None

    def ack(self):
        token = self.s.audio.token
        self.command("AUDIO_STARTED", token=token)
        self.check("actual start callback accepted", self.s.audio.status, "PLAYING")
        return token

    def advance(self, ms):
        self.command("TICK", ms=ms)

    def tracks_started(self):
        return [c["token"]["track_id"] for c in self.audio.starts]


def x01(r):
    r.started(A)
    placement = r.s.presence.placement_id
    r.advance(1234)
    r.nfc.observe(A)
    r.command("CARD_INSERTED", card=A, placement_id=placement)
    r.nfc.remove()
    r.nfc.observe(A)  # Late raw read after removal is not a new trusted placement.
    r.check("A has no persistent mode", r.s.mode, None)
    r.check("one point-play request", r.tracks_started(), ["t1"])
    r.check("removal preserves playback", (r.s.audio.status, r.s.audio.position_ms), ("PLAYING", 1234))
    r.check("trusted empty retained", r.s.presence.state, "EMPTY")


def x02(r):
    sid = r.started(B)
    r.advance(100)
    r.command("PAUSE", session_id=sid)
    r.command("STOP", session_id=sid)
    r.check("STOP keeps B", (r.s.mode.session_id, r.s.audio.status), (sid, "STOPPED_USER"))
    r.nfc.remove()
    r.check("B removal clears mode and selection", (r.s.mode, r.s.selection, r.s.audio.status),
            (None, None, "STOPPED"))


def x03(r):
    sid = r.started(C)
    old = r.s.audio.token
    r.command("EOF", token=old)
    r.ack()
    r.advance(2000)
    r.nfc.remove()
    r.nfc.insert(C)
    r.check("same C preserves session and progress", (r.s.mode.session_id, r.s.audio.position_ms), (sid, 2000))
    r.check("same C no new start", r.tracks_started(), ["t1", "t2"])
    r.command("STOP", session_id=sid)
    r.command("NEXT", session_id=sid)
    r.check("NEXT stays silent", (r.s.selection.track_id, r.s.audio.status, len(r.audio.starts)),
            ("t3", "STOPPED_USER", 2))
    r.command("PLAY", session_id=sid)
    r.check("PLAY latest selected at zero", (r.s.audio.token.track_id, r.audio.starts[-1]["offset_ms"]), ("t3", 0))
    r.ack()
    r.check("mode retained", r.s.mode.session_id, sid)


def x04(r):
    for card in (A, B, C):
        r.command("BOOT_RESET")
        r.nfc.observe(card)  # Discovery after a delayed scan cannot play.
        r.nfc.insert(card, boot=True)
        r.nfc.observe(card)
        r.check("boot waits", (r.s.mode, r.s.audio.status, len(r.audio.starts)), (None, "STOPPED", 0))
        r.check("boot-held status", r.s.presence.state, "BOOT_HELD")
    r.command("PLAY")
    r.ack()
    r.check("explicit boot PLAY can start C", r.s.mode.kind, "C")
    old = r.s.audio.token
    r.command("BOOT_RESET")
    r.nfc.insert(C, boot=True)
    r.command("AUDIO_STARTED", token=old)
    r.check("C not restored after reboot", (r.s.mode, r.s.audio.status), (None, "STOPPED"))


def x05(r):
    sid = r.started(C)
    old = r.s.audio.token
    r.advance(2000)
    r.check("missing independent target rejected", r.command("SELECT_TRACK", track_id="absent"), "REJECTED")
    r.check("precheck preserves C/progress", (r.s.mode.session_id, r.s.audio.token, r.s.audio.position_ms),
            (sid, old, 2000))
    r.command("SELECT_TRACK", track_id="t4")
    new = r.s.audio.token
    r.check("old C exited before async start", (r.s.mode, r.s.audio.status), (None, "STARTING"))
    r.command("AUDIO_START_FAILED", token=new, reason="decoder-open-failure")
    r.command("EOF", token=old)
    r.nfc.observe(C)
    r.advance(20000)
    r.check("no rollback/retry", (r.s.mode, r.s.audio.status, len(r.audio.starts)), (None, "STOPPED_ERROR", 2))
    r.command("PLAY")
    r.check("explicit retry allowed", r.s.audio.status, "STARTING")
    r.ack()


def x06(r):
    r.started(B)
    r.command("READER_FAULT")
    r.advance(999)
    r.check("short fault retains B", (r.s.mode.kind, r.s.audio.status), ("B", "PLAYING"))
    r.command("READER_RECOVERED", card=B)
    r.advance(5000)
    r.check("old fault interval cannot exit recovered B", r.s.mode.kind, "B")
    r.command("READER_FAULT")
    r.advance(1000)
    r.check("at threshold still holds", r.s.mode.kind, "B")
    r.advance(1)
    r.check("over threshold clears B", (r.s.mode, r.s.selection, r.s.audio.status), (None, None, "STOPPED"))
    r.check("fault is not trusted removal", r.s.presence.card, B)
    r.check("distinct error", r.s.last_error, "READER_FAULT_PROTECTION")
    r.command("READER_RECOVERED", card=B)
    r.nfc.observe(B)
    r.check("explicit start cannot bypass real replacement after fault", r.command("START_CURRENT_CARD"),
            "REPLACEMENT_REQUIRED")
    r.check("recovery no start", len(r.audio.starts), 1)
    r.nfc.remove()
    r.nfc.insert(B)
    r.ack()
    r.check("true re-placement starts from zero", (len(r.audio.starts), r.s.audio.position_ms), (2, 0))
    endings = [a["reason"] for a in r.ctrl.actions if a["kind"] == "MODE_ENDED"]
    r.check("protection reason not removal", endings, ["READER_FAULT_PROTECTION"])


def restart_b(r):
    sid = r.started(B)
    r.advance(2000)
    r.nfc.remove()
    r.nfc.insert(B)
    r.ack()
    r.check("B new session from zero", (r.s.mode.session_id != sid, r.s.audio.position_ms), (True, 0))
    r.check("two real starts", r.tracks_started(), ["t1", "t1"])


def manual_exit(r):
    r.started(C)
    placement = r.s.presence.placement_id
    r.command("MODE_EXIT")
    r.nfc.observe(C)
    r.command("CARD_INSERTED", card=C, placement_id=placement)
    r.check("same placement stays consumed", (r.s.mode, len(r.audio.starts)), (None, 1))
    r.nfc.remove()
    r.nfc.insert(C)
    r.ack()
    r.check("new placement starts", len(r.audio.starts), 2)


def c_stop_reinsert(r):
    sid = r.started(C)
    r.command("STOP")
    r.nfc.remove()
    r.nfc.insert(C)
    r.nfc.observe(C)
    r.check("same C retains stopped selection", (r.s.mode.session_id, r.s.audio.status, r.s.selection.track_id,
                                                len(r.audio.starts)), (sid, "STOPPED_USER", "t1", 1))


def pause_resume(r):
    sid = r.started(B)
    old = r.s.audio.token
    r.advance(120000)
    r.command("PAUSE")
    r.advance(30000)
    r.command("EOF", token=old)
    r.check("paused position frozen", (r.s.audio.status, r.s.audio.position_ms), ("PAUSED", 120000))
    r.command("PLAY")
    r.command("EOF", token=old)
    r.check("resume at old position", r.audio.starts[-1]["offset_ms"], 120000)
    r.ack()
    r.check("resume same mode", r.s.mode.session_id, sid)


def stop_selected_sixth(r):
    sid = r.started(C)
    for _ in range(5):
        r.command("NEXT")
        r.ack()
    r.advance(120000)
    old = r.s.audio.token
    r.command("STOP")
    r.command("EOF", token=old)
    r.command("PLAY")
    r.check("sixth not first from zero", (r.s.audio.token.track_id, r.audio.starts[-1]["offset_ms"]), ("t6", 0))
    r.ack()
    r.command("EOF", token=r.s.audio.token)
    r.ack()
    r.check("then seventh in original sequence", (r.s.mode.session_id, r.s.selection.track_id), (sid, "t7"))


def stopped_next_twice(r):
    r.started(C)
    token = r.s.audio.token
    r.command("STOP")
    r.command("NEXT")
    r.command("NEXT")
    r.command("EOF", token=token)
    r.command("AUDIO_STARTED", token=token)
    r.check("two silent selections", (r.s.audio.status, r.s.selection.track_id, len(r.audio.starts)),
            ("STOPPED_USER", "t3", 1))


def stale_callbacks(r):
    sid = r.started(B)
    old = r.s.audio.token
    place = r.s.presence.placement_id
    r.command("SELECT_TRACK", track_id="t4")
    new = r.ack()
    r.nfc.remove(place)
    for event in ("EOF", "AUDIO_STARTED", "AUDIO_START_FAILED", "AUDIO_STOPPED"):
        r.check("old " + event + " discarded", r.command(event, token=old), "IGNORED_STALE_AUDIO")
    r.command("STOP", session_id=sid)
    r.check("new playback unaffected", (r.s.audio.token, r.s.audio.status, len(r.audio.starts)), (new, "PLAYING", 2))


def same_session_old_eof(r):
    sid = r.started(C)
    old = r.s.audio.token
    r.command("NEXT")
    current = r.ack()
    r.check("session same, operation distinct", (current.session_id, current.operation_seq != old.operation_seq),
            (sid, True))
    r.command("EOF", token=old)
    r.check("old track EOF does not skip current", (r.s.selection.track_id, len(r.audio.starts)), ("t2", 2))


def stop_during_start(r):
    r.nfc.insert(B)
    old = r.s.audio.token
    r.command("STOP")
    r.command("AUDIO_STARTED", token=old)
    r.command("AUDIO_START_FAILED", token=old)
    r.check("late start cannot defeat STOP", (r.s.mode.kind, r.s.audio.status, r.s.last_error),
            ("B", "STOPPED_USER", None))


def invalid_new_card(r):
    sid = r.started(C)
    r.nfc.remove()
    r.nfc.insert(MISSING)
    r.check("invalid card keeps C", (r.s.mode.session_id, r.s.audio.status, len(r.audio.starts)), (sid, "PLAYING", 1))
    r.nfc.remove()
    r.nfc.insert(UNBOUND)
    r.check("unbound also preserves C", r.s.mode.session_id, sid)


def b_removed_invalid(r):
    r.started(B)
    r.nfc.remove()
    r.nfc.insert(UNBOUND)
    r.check("invalid new card cannot resurrect physically removed B", (r.s.mode, r.s.selection, r.s.audio.status),
            (None, None, "STOPPED"))


def valid_a_takeover(r):
    r.started(C)
    r.nfc.remove()
    r.nfc.insert(A)
    r.ack()
    r.check("A takes over C as normal playback", (r.s.mode, r.s.selection.track_id), (None, "t1"))
    endings = [a for a in r.ctrl.actions if a["kind"] == "MODE_ENDED"]
    r.check("old C completely ended", len(endings), 1)


def same_placement_start_failure(r):
    r.nfc.insert(A)
    p, token = r.s.presence.placement_id, r.s.audio.token
    r.command("AUDIO_START_FAILED", token=token)
    r.nfc.observe(A)
    r.command("CARD_INSERTED", card=A, placement_id=p)
    r.advance(5000)
    r.check("failed A no automatic retry", (r.s.audio.status, len(r.audio.starts)), ("STOPPED_ERROR", 1))
    r.nfc.remove()
    r.nfc.insert(A)
    r.ack()
    r.check("real re-placement retries", len(r.audio.starts), 2)


def raw_uncertain(r):
    r.started(B)
    p = r.s.presence.placement_id
    r.nfc.observe(C)
    r.check("neighbor UID not exit", (r.s.mode.kind, r.s.presence.card), ("B", B))
    r.command("CARD_UNCERTAIN")
    r.advance(200)
    r.command("READER_RECOVERED", card=B)
    r.check("uncertain restored no re-trigger", (r.s.mode.kind, r.s.presence.placement_id, len(r.audio.starts)),
            ("B", p, 1))


def stale_placement(r):
    r.started(B)
    p = r.s.presence.placement_id
    r.nfc.remove()
    r.nfc.insert(B)
    r.ack()
    sid = r.s.mode.session_id
    r.nfc.remove(p)
    r.check("old placement cannot exit new B", (r.s.mode.session_id, r.s.audio.status), (sid, "PLAYING"))


def single_track_loop(r):
    r.catalog.bindings[B] = Binding("B", "TRACK", "t2")
    sid = r.started(B)
    old = r.s.audio.token
    r.command("EOF", token=old)
    r.ack()
    r.check("B single track loops", (r.tracks_started(), r.s.mode.session_id), (["t2", "t2"], sid))


def identifiers(r):
    # UID bytes alone are insufficient: technology AND full UID length must remain part of identity.
    r.nfc.insert(CardIdentity("OTHER", A.uid))
    r.check("technology distinct", (r.s.last_error, len(r.audio.starts)), ("PRECHECK_UNBOUND_CARD", 0))
    r.nfc.remove()
    r.started(B)
    r.check("full UID retained", len(r.s.presence.card.uid), 7)
    r.check("commit not faked", r.s.commit_seq, None)
    r.check("placement/session distinct", r.s.presence.placement_id != r.s.mode.session_id, True)


def boot_recovery(r):
    r.nfc.insert(C, boot=True)
    r.command("READER_FAULT")
    r.advance(1200)
    r.command("READER_RECOVERED", card=C)
    r.check("recovery cannot change boot-held intent", r.s.presence.state, "BOOT_HELD")
    r.check("boot recovery no automatic play", len(r.audio.starts), 0)
    r.command("PLAY")
    r.check("explicit PLAY after recovery still eligible", r.s.audio.status, "STARTING")
    r.ack()


def fault_queued_placement(r):
    r.command("READER_FAULT")
    result = r.nfc.insert(B)
    r.check("queued placement during fault cannot start", result, "REJECTED_READER_UNHEALTHY")
    r.check("reader fault retained", (r.s.presence.reader_health, len(r.audio.starts)), ("READER_FAULT", 0))
    r.command("READER_RECOVERED", card=None)
    r.nfc.insert(B)
    r.ack()
    r.command("READER_FAULT")
    r.nfc.remove()
    r.check("true empty does not magically repair reader", r.s.presence.reader_health, "READER_FAULT")
    r.command("READER_RECOVERED", card=None)
    r.nfc.insert(B)
    r.ack()


def cross_bc(r):
    sid = r.started(C)
    token = r.s.audio.token
    r.nfc.remove()
    r.catalog.resources_ready = False
    r.check("invalid new B preflight preserves old C", r.nfc.insert(B), "REJECTED")
    r.check("preflight cannot end old C", (r.s.mode.session_id, r.s.audio.token), (sid, token))
    r.nfc.remove()
    r.catalog.resources_ready = True
    r.check("valid B fully replaces old C", r.nfc.insert(B), "STARTING")
    r.ack()
    r.check("new B has its own session", (r.s.mode.kind, r.s.mode.session_id != sid), ("B", True))
    r.check("old C EOF cannot change new B", r.command("EOF", token=token), "IGNORED_STALE_AUDIO")
    r.check("old C stop cannot stop new B", r.command("AUDIO_STOPPED", token=token), "IGNORED_STALE_AUDIO")
    r.nfc.remove()
    r.advance(1000)
    r.check("B removal does not resurrect old C", (r.s.mode, r.s.selection, r.s.audio.status,
                                                 len(r.audio.starts)), (None, None, "STOPPED", 2))
    sid = r.started(C)
    token = r.s.audio.token
    r.nfc.remove()
    r.check("different C fully replaces old C", r.nfc.insert(C2), "STARTING")
    r.ack()
    r.check("new C target/session active", (r.s.mode.origin_card, r.s.selection.track_id,
                                          r.s.mode.session_id != sid), (C2, "t4", True))
    r.check("old C command cannot exit new C", r.command("MODE_EXIT", session_id=sid), "IGNORED_STALE_COMMAND")
    r.check("old C IO cannot mark new C bad", r.command("TRACK_READ_ERROR", token=token), "IGNORED_STALE_AUDIO")
    r.nfc.remove()
    r.command("MODE_EXIT")
    r.advance(1000)
    r.check("new C exit does not resurrect old C", (r.s.mode, r.s.selection, r.s.audio.status),
            (None, None, "STOPPED"))
    sid = r.started(C)
    r.nfc.remove()
    r.nfc.insert(B)
    r.command("AUDIO_START_FAILED", token=r.s.audio.token, reason="NEW_B_START_FAILED")
    r.check("new B actual failure does not roll back old C",
            (r.s.mode.kind, r.s.mode.session_id != sid, r.s.audio.status), ("B", True, "STOPPED_ERROR"))
    r.nfc.remove()
    r.check("failed B removal still cannot restore C", r.s.mode, None)


# IDs are execution scenarios, not a declaration that the full RC-08/R2 gate passed.
CASES = [
    ("X01", "A once, trusted removal and late raw UID", "D066,D067,D069;L01,L02", x01),
    ("X02", "B pause/STOP/removal", "D066,D075;L26,L29", x02),
    ("X03", "C loop/re-placement/STOP/NEXT/PLAY", "D067,D071,D079,D082;L08,L09,E02", x03),
    ("X04", "boot-held and C reset", "D052,D073;L19,L23", x04),
    ("X05", "precheck failure vs asynchronous start failure", "D074;L13,L24", x05),
    ("X06", "short fault/recovery/timeout/trusted re-placement", "D072;L18,L28", x06),
    ("L05", "B new placement restarts at zero", "D066;L04,L05", restart_b),
    ("L06", "manual exit consumes placement", "D067;L06", manual_exit),
    ("L27", "C same card does not release STOP", "D071,D075;E03,C24-partial", c_stop_reinsert),
    ("L12", "pause freezes time and PLAY resumes", "D068,D079;L12,L20-partial", pause_resume),
    ("E01", "sixth song STOP/PLAY then seventh", "D079;L22,E01", stop_selected_sixth),
    ("E15", "two NEXTs after STOP plus delayed callback", "D082;E15", stopped_next_twice),
    ("L15", "old B/audio callbacks cannot stop new track", "D068;L15", stale_callbacks),
    ("RACE01", "same session old EOF rejected by operation id", "D068,D082", same_session_old_eof),
    ("RACE02", "STOP during async start", "D075,D082", stop_during_start),
    ("L13", "missing/unbound new card preserves C", "D074;L13", invalid_new_card),
    ("L25", "independent removal cannot be rolled back", "D066,D074;L14,L25", b_removed_invalid),
    ("L10", "valid A ends C before start", "D068;L10", valid_a_takeover),
    ("D074-A", "failed A consumed, real re-place can retry", "D074", same_placement_start_failure),
    ("ADAPTER01", "raw UID/uncertain are not removal", "D072;L07-domain-only,L16-suggestion", raw_uncertain),
    ("RACE03", "stale B removal cannot exit new placement", "D068", stale_placement),
    ("LOOP01", "B single track EOF loop", "D067", single_track_loop),
    ("IDENTITY01", "technology/UID length and separate identifiers", "D069;RC-08A-02", identifiers),
    ("BOOT02", "boot-held eligibility survives reader recovery", "D052,D073;L19", boot_recovery),
    ("ADAPTER02", "fault cannot be erased by queued placement/removal", "D072;adapter boundary", fault_queued_placement),
    ("RC-08A-01", "C1->B2/C2 full takeover without old-mode restoration", "User confirmed 2026-10-10;D074", cross_bc),
]

DEFERRED = {
    "X07": "Second batch: configured binding/playlist commits and frozen active snapshots",
    "X08": "Second batch: track/playlist/active/startup references and deletion protection",
    "X09": "Second batch: runtime bad-track skip and validated media publication",
    "X10": "Second batch: all-bad STOP_ERROR and explicit PLAY after repair",
    "X11": "Second batch: last successful save, state notification order and persistence",
    "X12": "Second batch: lost reply/idempotency and durable commit/receipt recovery",
}
