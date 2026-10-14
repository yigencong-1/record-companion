"""Batch 2 expectations: product rules first, actual file/process observations second."""

import errno
import io
import json
import os
import queue
import subprocess
import sys
import threading
import wave
from dataclasses import asdict
from pathlib import Path

from content_store import ClientView, DurableCatalog, card_key, fixture_seed
from controller import Binding, Controller, FakeAudio, FakeNFC, VirtualClock
from scenarios import A, B, C, Rig


def wav_bytes(sample=0):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(sample.to_bytes(2, "little", signed=True) * 80)
    return buffer.getvalue()


class Probe:
    """Blocking checkpoints, real process termination, bounded reads; no RAM restart mock."""

    def __init__(self, rig, root, job):
        self.rig, self.lines, self.errors = rig, [], []
        self.messages = queue.Queue()
        self.number = len(rig.processes) + 1
        self.job_path = rig.root / ("process-" + str(self.number) + ".json")
        self.job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).with_name("process_worker.py")),
             "--root", str(root), "--job", str(self.job_path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
        rig.processes.append(self)

        def read_out():
            for line in self.process.stdout:
                value = json.loads(line)
                self.lines.append(value)
                self.messages.put(value)
            self.messages.put({"type": "closed"})

        def read_err():
            self.errors.extend(self.process.stderr.read().splitlines())

        self.out_thread = threading.Thread(target=read_out, daemon=True)
        self.err_thread = threading.Thread(target=read_err, daemon=True)
        self.out_thread.start()
        self.err_thread.start()

    def take(self, expected):
        value = self.messages.get(timeout=8)
        if value["type"] != expected:
            raise AssertionError(f"process {self.number}: expected {expected}, got {value}; {self.errors}")
        return value

    def release(self):
        self.process.stdin.write("continue\n")
        self.process.stdin.flush()

    def finish(self, terminate=False):
        if terminate:
            self.process.kill()
        code = self.process.wait(timeout=8)
        self.out_thread.join(timeout=2)
        self.err_thread.join(timeout=2)
        self.rig.notes.append({"process": self.number, "pid": self.process.pid,
                               "terminated": terminate, "exit_code": code,
                               "output": self.lines, "stderr": self.errors})
        self.rig.check("interrupted child nonzero" if terminate else "child exited successfully",
                       code != 0 if terminate else code, True if terminate else 0)
        self.rig.check("child stderr empty", self.errors, [])
        for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
            pipe.close()
        return code


class BatchRig(Rig):
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.catalog = DurableCatalog(self.root / "store", fixture_seed())
        self.audio, self.clock = FakeAudio(), VirtualClock()
        self.ctrl = Controller(self.catalog, self.audio, self.clock)
        self.nfc = FakeNFC(self.ctrl)
        self.checks, self.notes, self.processes = [], [], []
        self.request_seq = 0

    def save(self, kind, request_id=None, **payload):
        self.request_seq += 1
        return self.command(kind, request_id=request_id or f"request-{self.request_seq}", **payload)

    def bind(self, card, binding, **extras):
        return self.save("SAVE_BINDING", card=card, binding=binding, **extras)

    def playlist(self, tracks, playlist_id="mix"):
        return self.save("SAVE_PLAYLIST", playlist_id=playlist_id, tracks=tracks)

    def publish(self, track, data=None, expected_bytes=None, **extras):
        data = wav_bytes() if data is None else data
        upload = self.catalog.stage_media(data, len(data) if expected_bytes is None else expected_bytes)
        return self.save("PUBLISH_MEDIA", track_id=track, upload_id=upload, **extras)

    def eof(self):
        self.command("EOF", token=self.s.audio.token)
        self.ack()

    def fail(self):
        return self.command("TRACK_READ_ERROR", token=self.s.audio.token, reason="INJECTED_READ_FAILURE")

    def all_bad(self):
        self.started(C)
        self.fail()
        self.ack()
        self.fail()
        self.ack()
        self.fail()
        self.check("all failed mode retained", (self.s.mode.kind, self.s.audio.status,
                                               self.s.selection.track_id), ("C", "STOPPED_ERROR", "t3"))

    def inspect(self, catalog=None):
        snapshot = (catalog or self.catalog).durable_snapshot()
        self.notes.append({"durable": snapshot})
        self.check("SQLite integrity", snapshot["sqlite_integrity"], "ok")
        return snapshot

    def child(self, root, job):
        probe = Probe(self, root, job)
        probe.take("ready")
        return probe

    def cleanup(self):
        for probe in self.processes:
            if probe.process.poll() is None:
                probe.process.kill()
                probe.process.wait(timeout=8)


def x07(r):
    sid = r.started(B)
    r.advance(2500)
    frozen = (r.s.mode, r.s.audio.token, r.s.audio.position_ms, r.s.selection.snapshot)
    r.check("playlist save succeeds", r.playlist(["t3", "t2", "t1"]), "SAVED")
    r.check("in-place rebind succeeds", r.bind(B, Binding("C", "TRACK", "t4")), "SAVED")
    r.nfc.observe(B)
    r.check("save leaves entire active snapshot and audio intact",
            (r.s.mode, r.s.audio.token, r.s.audio.position_ms, r.s.selection.snapshot), frozen)
    r.check("two saves did not start audio", r.tracks_started(), ["t1"])
    r.eof()
    r.check("old order survives new saved order", r.s.selection.track_id, "t2")
    r.nfc.remove()
    r.nfc.insert(B)
    r.ack()
    r.check("trusted B replacement reads saved binding", (r.s.mode.kind, r.s.selection.track_id,
                                                         r.s.mode.binding_revision), ("C", "t4", 2))
    r.check("new activation has new session", r.s.mode.session_id != sid, True)
    r.inspect()


def snapshot_c(r):
    r.started(C)
    original = r.s.mode
    r.playlist(["t3", "t2", "t1"])
    r.bind(C, Binding("B", "PLAYLIST", "mix"))
    r.nfc.remove()
    r.nfc.insert(C)
    r.check("C same real card retains old kind and snapshot", r.s.mode, original)
    r.check("C reinsertion does not add playback", r.tracks_started(), ["t1"])
    r.command("MODE_EXIT")
    r.command("START_CURRENT_CARD")
    r.ack()
    r.check("explicit restart applies both saved revisions",
            (r.s.mode.kind, r.s.mode.snapshot.revision, r.s.selection.track_id), ("B", 2, "t3"))


def snapshot_a(r):
    r.started(A)
    token = r.s.audio.token
    r.bind(A, Binding("A", "TRACK", "t4"))
    r.nfc.observe(A)
    r.check("A in-place save does not retrigger", (r.s.audio.token, r.tracks_started()), (token, ["t1"]))
    r.command("START_CURRENT_CARD")
    r.ack()
    r.check("explicit A applies new target", r.tracks_started(), ["t1", "t4"])
    r.check("A invalid playlist binding rejected", r.bind(A, Binding("A", "PLAYLIST", "mix")),
            "PRECHECK_A_REQUIRES_TRACK")
    r.check("invalid configuration kept last saved binding", r.catalog.bindings[A].target_id, "t4")


def x08(r):
    r.nfc.insert(C)  # STARTING is an occupied resource, before any sound callback.
    r.check("referenced track blocked", r.save("DELETE_TRACK", track_id="t1"), "DELETE_BLOCKED_REFERENCED")
    sources = {ref["source"] for ref in r.ctrl.last_content_result["references"]}
    r.check("specific reference classes include startup", sources,
            {"card", "saved-playlist", "active-snapshot", "audio-starting"})
    r.check("playlist blocked by cards and active session", r.save("DELETE_PLAYLIST", playlist_id="mix"),
            "DELETE_BLOCKED_REFERENCED")
    r.check("playlist reports active source", "active-session" in
            {ref["source"] for ref in r.ctrl.last_content_result["references"]}, True)
    r.publish("t4")
    path = r.catalog.config["tracks"]["t4"]["file"]
    r.save("SAVE_BIRTHDAY", target={"target_kind": "PLAYLIST", "target_id": "spare"})
    r.check("unique birthday reference blocks playlist", r.save("DELETE_PLAYLIST", playlist_id="spare"),
            "DELETE_BLOCKED_REFERENCED")
    r.check("birthday relation displayed", r.ctrl.last_content_result["references"],
            [{"source": "birthday", "id": "birthday-single-content"}])
    r.save("SAVE_BIRTHDAY", target=None)
    r.check("unreferenced playlist deletes", r.save("DELETE_PLAYLIST", playlist_id="spare"), "SAVED")
    r.check("playlist delete leaves track and actual media",
            ("t4" in r.catalog.tracks, (r.catalog.root / path).is_file()), (True, True))
    r.inspect()


def refs_active(r):
    r.publish("t1")
    path = r.catalog.config["tracks"]["t1"]["file"]
    r.started(C)
    for card in (A, B, C):
        r.bind(card, None)
    r.playlist(["t2", "t3"])
    r.command("STOP")
    r.check("old active snapshot still blocks removed track", r.save("DELETE_TRACK", track_id="t1"),
            "DELETE_BLOCKED_REFERENCED")
    r.check("old snapshot explicitly reported", "active-snapshot" in
            {ref["source"] for ref in r.ctrl.last_content_result["references"]}, True)
    r.check("STOP does not free active playlist", r.save("DELETE_PLAYLIST", playlist_id="mix"),
            "DELETE_BLOCKED_REFERENCED")
    r.command("MODE_EXIT")
    r.check("exit frees unbound playlist", r.save("DELETE_PLAYLIST", playlist_id="mix"), "SAVED")
    r.check("exit frees removed track", r.save("DELETE_TRACK", track_id="t1"), "SAVED")
    r.check("track invisible in catalog", "t1" in r.catalog.tracks, False)
    r.check("old media kept for separate file reclamation", (r.catalog.root / path).is_file(), True)


def refs_audio(r):
    r.command("SELECT_TRACK", track_id="t5")
    r.check("ordinary async startup blocks delete", r.save("DELETE_TRACK", track_id="t5"),
            "DELETE_BLOCKED_REFERENCED")
    r.ack()
    r.command("PAUSE")
    r.check("pause keeps resource", r.save("DELETE_TRACK", track_id="t5"), "DELETE_BLOCKED_REFERENCED")
    r.command("STOP")
    r.check("STOP selection remains occupied", r.save("DELETE_TRACK", track_id="t5"),
            "DELETE_BLOCKED_REFERENCED")
    r.command("MODE_EXIT")
    r.check("complete release permits deletion", r.save("DELETE_TRACK", track_id="t5"), "SAVED")


def refs_race(r):
    old = r.catalog.references(r.catalog.config, "TRACK", "t5")
    r.check("old view had no refs", old, [])
    r.bind(A, Binding("A", "TRACK", "t5"))
    r.check("submit rechecks new binding", r.save("DELETE_TRACK", track_id="t5", view_revision=0),
            "DELETE_BLOCKED_REFERENCED")
    r.check("new reference did not dangle", (r.catalog.bindings[A].target_id, "t5" in r.catalog.tracks),
            ("t5", True))
    r.save("SAVE_BIRTHDAY", target={"target_kind": "PLAYLIST", "target_id": "spare"})
    r.check("stale deletion cannot bypass birthday ref", r.save("DELETE_PLAYLIST", playlist_id="spare",
                                                               view_revision=0), "DELETE_BLOCKED_REFERENCED")
    seq = r.catalog.commit_seq
    r.check("missing playlist track is rejected", r.playlist(["missing"]), "TARGET_MISSING")
    r.check("failed save did not obtain a commit", r.catalog.commit_seq, seq)
    r.inspect()


def x09(r):
    r.started(C)
    old = r.s.audio.token
    r.fail()
    r.ack()
    r.check("bad first track skipped", (r.s.selection.track_id, r.s.failed_tracks), ("t2", {"t1": 1}))
    r.eof()
    r.eof()
    r.check("loop skips blocked first track", r.tracks_started(), ["t1", "t2", "t3", "t2"])
    current, starts = r.s.audio.token, len(r.audio.starts)
    full = wav_bytes()
    r.check("half upload is not publication", r.publish("t1", full[:60], len(full)), "MEDIA_INCOMPLETE")
    r.check("bad format cannot publish", r.publish("t1", b"invalid-wav"), "MEDIA_VALIDATION_FAILED")
    r.check("uncommitted publication event rejected", r.command("MEDIA_PUBLISHED", track_id="t1", media_version=2),
            "IGNORED_UNPUBLISHED_MEDIA")
    r.check("failed repairs keep marker and token", (r.s.failed_tracks, r.s.audio.token), ({"t1": 1}, current))
    r.check("valid complete publication succeeds", r.publish("t1"), "SAVED")
    r.check("only qualification changes", (r.s.failed_tracks, r.s.audio.token, len(r.audio.starts)),
            ({}, current, starts))
    r.eof()
    r.eof()
    r.check("normal turn opens repaired version", (r.s.selection.track_id, r.s.audio.token.media_version), ("t1", 2))
    r.fail()
    r.ack()
    r.check("second failure blocks repaired version", r.s.failed_tracks, {"t1": 2})
    r.eof()
    r.eof()
    r.check("second bad version is not retried", r.tracks_started()[-3:], ["t2", "t3", "t2"])
    r.check("old IO callback cannot poison current", r.command("TRACK_READ_ERROR", token=old), "IGNORED_STALE_AUDIO")
    r.inspect()


def media_old(r):
    r.started(C)
    old = r.s.audio.token
    r.publish("t1")
    r.check("new version publication preserves old active token", r.s.audio.token, old)
    r.command("TRACK_READ_ERROR", token=old)
    r.ack()
    r.check("old stream error does not mark new version bad", r.s.failed_tracks, {})
    r.eof()
    r.eof()
    r.check("new version remains eligible next turn", (r.s.selection.track_id, r.s.audio.token.media_version), ("t1", 2))


def media_failure(r):
    r.started(C)
    r.fail()
    r.ack()
    current = r.s.audio.token

    def no_space(stage):
        if stage == "media_before_write":
            raise OSError(errno.ENOSPC, "Injected no space")

    r.catalog.hook = no_space
    r.check("media no-space reported", r.publish("t1"), "NO_SPACE")

    def failed_commit(stage):
        if stage == "before_commit":
            raise OSError(errno.EIO, "Injected commit failure")

    r.catalog.hook = failed_commit
    r.check("media prepared but transaction fails", r.publish("t1"), "STORAGE_FAILURE")
    r.check("no false publication or unlock", (r.catalog.tracks["t1"].version, r.s.failed_tracks,
                                              r.s.audio.token), (1, {"t1": 1}, current))
    r.check("failure emitted no successful notice", [a for a in r.ctrl.actions if a["kind"] == "CONFIG_COMMITTED"], [])
    snapshot = r.inspect()
    r.check("unpublished file is observable", len(snapshot["unreferenced_version_files"]), 1)
    r.catalog.hook = lambda stage: None
    r.check("subsequent valid repair succeeds", r.publish("t1"), "SAVED")
    r.check("recovery did not interrupt audio", r.s.audio.token, current)


def x10(r):
    r.all_bad()
    mode, starts = r.s.mode, len(r.audio.starts)
    r.publish("t3")
    r.check("repair does not release all-bad STOP", (r.s.mode, r.s.audio.status, len(r.audio.starts)),
            (mode, "STOPPED_ERROR", starts))
    r.check("only repaired track requalified", r.s.failed_tracks, {"t1": 1, "t2": 1})
    r.command("PLAY")
    r.ack()
    r.check("explicit PLAY repaired current selection at zero",
            (r.s.selection.track_id, r.s.audio.token.media_version, r.s.audio.position_ms), ("t3", 2, 0))
    r.eof()
    r.check("only good track loops boundedly", r.tracks_started(), ["t1", "t2", "t3", "t3", "t3"])
    r.command("MODE_EXIT")
    r.check("mode exit releases failure map", (r.s.mode, r.s.failed_tracks), (None, {}))


def recovered_play(r):
    r.all_bad()
    stopped = (r.s.mode, r.s.selection.track_id, r.s.audio.status, len(r.audio.starts))
    r.check("PLAY with no playable versions keeps bounded STOP",
            r.command("PLAY"), "ALL_TRACKS_UNPLAYABLE_MODE_RETAINED")
    r.check("all bad PLAY cannot restart failed media",
            (r.s.mode, r.s.selection.track_id, r.s.audio.status, len(r.audio.starts)), stopped)
    r.publish("t1")
    r.check("repair of nonselected track does not start playback",
            (r.s.mode, r.s.selection.track_id, r.s.audio.status, len(r.audio.starts)), stopped)
    r.check("explicit PLAY searches current then original order", r.command("PLAY"), "STARTING")
    r.ack()
    r.check("repaired nonselected track starts at zero",
            (r.s.selection.track_id, r.s.audio.token.media_version, r.s.audio.position_ms), ("t1", 2, 0))
    r.fail()
    r.check("repaired version fails again and cannot spin", (r.s.audio.status, r.s.failed_tracks),
            ("STOPPED_ERROR", {"t1": 2, "t2": 1, "t3": 1}))
    r.check("repeated PLAY with all bad still makes no audio start",
            r.command("PLAY"), "ALL_TRACKS_UNPLAYABLE_MODE_RETAINED")
    r.check("start count bounded by explicit valid attempts", r.tracks_started(), ["t1", "t2", "t3", "t1"])


def recovered_order(r):
    r.all_bad()
    r.publish("t1")
    r.publish("t2")
    r.playlist(["t2", "t1", "t3"])
    r.command("PLAY")
    r.ack()
    r.check("recovery uses frozen order, not newly saved order", r.s.selection.track_id, "t1")
    r.eof()
    r.check("recovered second track follows original snapshot", r.s.selection.track_id, "t2")


def x11(r):
    r.started(C)
    frozen = (r.s.mode, r.s.audio.token)
    r.bind(C, Binding("B", "TRACK", "t4"), request_id="body-A", view_revision=1)
    reply_a = r.ctrl.last_content_result
    r.bind(C, Binding("C", "TRACK", "t5"), request_id="web-B", view_revision=1)
    reply_b = r.ctrl.last_content_result
    r.check("old page new save is accepted and last successful", (r.catalog.commit_seq,
                                                                r.catalog.bindings[C].target_id), (2, "t5"))
    r.check("both saves preserve old active session", (r.s.mode, r.s.audio.token), frozen)
    body, web = ClientView(), ClientView()
    for view in (body, web):
        view.observe(reply_b["latest_config"])
        r.check("late A receipt cannot regress latest display", view.observe(reply_a["latest_config"]),
                "IGNORED_OLD_NOTIFICATION")
        r.check("both show latest device binding", view.config["bindings"][card_key(C)]["target_id"], "t5")

    def fail(stage):
        if stage == "config_written":
            raise OSError(errno.EIO, "Injected save failure")

    r.catalog.hook = fail
    r.check("failed later save has no authority", r.bind(C, Binding("B", "TRACK", "t1")), "STORAGE_FAILURE")
    r.check("failed save does not change durable config or count", (r.catalog.commit_seq,
                                                                 r.catalog.bindings[C].target_id), (2, "t5"))
    r.catalog.hook = lambda stage: None
    r.inspect()


def x12(r):
    r.bind(A, Binding("A", "TRACK", "t4"), request_id="lost-A")
    original = r.ctrl.last_content_result["receipt"]
    r.bind(A, Binding("A", "TRACK", "t5"), request_id="body-B")
    r.check("retry lost A replays receipt", r.bind(A, Binding("A", "TRACK", "t4"), request_id="lost-A"),
            "REPLAYED")
    reply = r.ctrl.last_content_result
    r.check("original receipt retained", reply["receipt"], original)
    r.check("retry includes latest state but does not commit", (reply["latest_config"]["commit_seq"],
                                                             r.catalog.bindings[A].target_id), (2, "t5"))
    r.check("same ID different payload diagnosed", r.bind(A, Binding("A", "TRACK", "t2"), request_id="lost-A"),
            "REQUEST_ID_PAYLOAD_MISMATCH")
    r.check("ID misuse did not write", r.catalog.commit_seq, 2)
    r.check("replayed ID cannot bypass delete protection", r.save("DELETE_TRACK", track_id="t5"),
            "DELETE_BLOCKED_REFERENCED")
    r.inspect()


def save_job(request="process-A", target="t4", barrier=None):
    job = {"request_id": request, "command": "SAVE_BINDING",
           "payload": {"card_key": card_key(A), "binding": asdict(Binding("A", "TRACK", target))}}
    if barrier:
        job["barrier"] = barrier
    return job


def restart_snapshot(r, root):
    probe = r.child(root, {})
    snapshot = probe.take("snapshot")["snapshot"]
    probe.finish()
    r.check("restarted process integrity", snapshot["sqlite_integrity"], "ok")
    return snapshot


def process_transactions(r):
    stages = ("before_config", "config_written", "receipt_written", "before_commit", "after_commit")
    for stage in stages:
        root = r.root / stage
        DurableCatalog(root, fixture_seed())
        probe = r.child(root, save_job(barrier=stage))
        r.check("interrupt at exact barrier", probe.take("checkpoint")["stage"], stage)
        probe.finish(terminate=True)
        snapshot = restart_snapshot(r, root)
        after_commit = stage == "after_commit"
        config = snapshot["config"]
        r.check("atomic sequence after process interruption", config["commit_seq"], 1 if after_commit else 0)
        r.check("atomic config after process interruption", config["bindings"][card_key(A)]["target_id"],
                "t4" if after_commit else "t1")
        r.check("receipt matches config durability", "process-A" in snapshot["receipts"], after_commit)
        if after_commit:
            newer = r.child(root, save_job(request="process-B", target="t5"))
            newer.take("result")
            newer.take("snapshot")
            newer.finish()
        retry = r.child(root, save_job())
        result = retry.take("result")["result"]
        latest = retry.take("snapshot")["snapshot"]
        retry.finish()
        r.check("retry replays exactly when original committed", result["replayed"], after_commit)
        r.check("retry original commit number", result["receipt"]["commit_seq"], 1)
        r.check("retry does not overwrite later B", latest["config"]["bindings"][card_key(A)]["target_id"],
                "t5" if after_commit else "t4")
        r.check("exactly successful submissions counted", latest["config"]["commit_seq"], 2 if after_commit else 1)


def process_duplicate(r):
    root = r.root / "duplicate"
    DurableCatalog(root, fixture_seed())
    first = r.child(root, save_job(barrier="config_written"))
    first.take("checkpoint")
    duplicate = r.child(root, save_job())
    try:
        premature = duplicate.messages.get(timeout=0.25)
        raise AssertionError(f"duplicate should await single writer: {premature}")
    except queue.Empty:
        r.check("in-flight duplicate waits for writer", duplicate.process.poll(), None)
    first.release()
    one = first.take("result")["result"]
    first.take("snapshot")
    first.finish()
    two = duplicate.take("result")["result"]
    snapshot = duplicate.take("snapshot")["snapshot"]
    duplicate.finish()
    r.check("concurrent duplicate one original one replay", (one["replayed"], two["replayed"]), (False, True))
    r.check("same original receipt", one["receipt"], two["receipt"])
    r.check("one durable commit and receipt", (snapshot["config"]["commit_seq"], len(snapshot["receipts"])), (1, 1))
    other = save_job(target="t2")
    probe = r.child(root, other)
    mismatch = probe.take("result")["result"]
    probe.take("snapshot")
    probe.finish()
    r.check("restarted ID misuse rejected", mismatch["reason"], "REQUEST_ID_PAYLOAD_MISMATCH")


def process_media(r):
    for stage in ("media_file_ready", "config_written", "after_commit"):
        root = r.root / stage
        catalog = DurableCatalog(root, fixture_seed())
        old_bytes, new_bytes = wav_bytes(10), wav_bytes(20)
        old_upload = catalog.stage_media(old_bytes, len(old_bytes))
        catalog.apply("old-media", "PUBLISH_MEDIA", {"track_id": "t1", "upload_id": old_upload})
        old_path = root / catalog.config["tracks"]["t1"]["file"]
        handle = old_path.open("rb")
        try:
            upload = catalog.stage_media(new_bytes, len(new_bytes))
            payload = {"track_id": "t1", "upload_id": upload}
            probe = r.child(root, {"request_id": "new-media", "command": "PUBLISH_MEDIA",
                                   "payload": payload, "barrier": stage})
            probe.take("checkpoint")
            probe.finish(terminate=True)
            recovered = restart_snapshot(r, root)
            config = recovered["config"]
            published = stage == "after_commit"
            r.check("media pointer only changes on committed publication", config["tracks"]["t1"]["version"],
                    3 if published else 2)
            r.check("publication and receipt atomic", "new-media" in recovered["receipts"], published)
            r.check("old live handle reads original bytes", handle.read(), old_bytes)
            actual_file = root / config["tracks"]["t1"]["file"]
            r.check("authoritative file complete after restart", actual_file.read_bytes(),
                    new_bytes if published else old_bytes)
            if not published:
                r.check("orphan version observable after interrupted publication",
                        len(recovered["unreferenced_version_files"]), 1)
            retry = r.child(root, {"request_id": "new-media", "command": "PUBLISH_MEDIA", "payload": payload})
            response = retry.take("result")["result"]
            snapshot = retry.take("snapshot")["snapshot"]
            retry.finish()
            r.check("publication retry preserves version", (snapshot["config"]["tracks"]["t1"]["version"],
                                                            response["replayed"]), (3, published))
        finally:
            handle.close()


def process_boot(r):
    r.bind(C, Binding("C", "TRACK", "t4"))
    probe = r.child(r.catalog.root, {"exercise_c": True, "barrier": "running_c"})
    live = probe.take("live")
    r.check("child had real live C controller", (live["state"]["mode"]["kind"], live["state"]["audio_state"]),
            ("C", "PLAYING"))
    probe.take("checkpoint")
    probe.finish(terminate=True)
    fresh = r.child(r.catalog.root, {"boot_card": True, "explicit_play": True})
    boot = fresh.take("boot")
    fresh.take("snapshot")
    fresh.finish()
    r.check("fresh process did not restore RAM C/audio", (boot["initial"]["mode"], boot["initial"]["audio_state"]),
            (None, "STOPPED"))
    r.check("boot-held has zero automatic starts", (boot["held"]["audio_state"], boot["before_starts"]), ("STOPPED", 0))
    r.check("saved binding survives process death", (boot["after"]["selected_track_id"], boot["starts"],
                                                    boot["after"]["commit_seq"]), ("t4", 1, 1))


def partial_upload_restart(r):
    full = wav_bytes()
    upload = r.catalog.stage_media(full[:60], len(full))
    probe = r.child(r.catalog.root, {"command": "PUBLISH_MEDIA", "request_id": "partial",
                                    "payload": {"track_id": "t1", "upload_id": upload}})
    response = probe.take("result")["result"]
    snapshot = probe.take("snapshot")["snapshot"]
    probe.finish()
    r.check("partial real file still rejected after independent restart", response["reason"], "MEDIA_INCOMPLETE")
    r.check("partial invisible and receipt absent", (snapshot["config"]["tracks"]["t1"]["version"],
                                                    snapshot["config"]["commit_seq"], snapshot["receipts"]), (1, 0, {}))
    r.check("recovery inventories staged candidate", upload + ".part" in snapshot["staged_files"], True)


def runtime_open_failure(r):
    r.started(C)
    r.command("EOF", token=r.s.audio.token)
    second = r.s.audio.token
    r.command("AUDIO_START_FAILED", token=second, reason="OPEN_FAILED_AFTER_FIRST_TRACK")
    r.ack()
    r.check("later open failure skips within established session", (r.s.selection.track_id, r.s.failed_tracks),
            ("t3", {"t2": 1}))
    r.eof()
    r.eof()
    r.check("failed next-open track remains boundedly skipped", r.tracks_started(),
            ["t1", "t2", "t3", "t1", "t3"])
    r.command("MODE_EXIT")
    r.command("START_CURRENT_CARD")
    r.check("new session failure map cleared", r.s.failed_tracks, {})
    r.command("AUDIO_START_FAILED", token=r.s.audio.token, reason="INITIAL_OPEN_FAILED")
    r.check("initial request still uses D074 no automatic skip", (r.s.audio.status, r.s.selection.track_id),
            ("STOPPED_ERROR", "t1"))


CASES = [
    ("X07", "saved playlist/binding preserve B active snapshot", "D077,D078;C06,C07,E13", x07),
    ("SNAP-C", "C re-placement retains old binding until explicit restart", "D071,D077,D078", snapshot_c),
    ("SNAP-A", "A in-place rebind and explicit apply", "D078;C02,C06", snapshot_a),
    ("X08", "reference protection with birthday and starting occupation", "D076,D083;C08,C09,E06", x08),
    ("REF-ACTIVE", "saved removal cannot free active STOP snapshot", "D076,D077,D083;C23,E05", refs_active),
    ("REF-AUDIO", "ordinary STARTING/PAUSE/STOP resource protection", "D076;C09", refs_audio),
    ("REF-RACE", "delete rechecks newly committed references", "D076,D083,D085;E04,E21", refs_race),
    ("X09", "bad track repair validates/publishes and retries next normal turn", "D080,D084;C21,E07,E16,E17", x09),
    ("MEDIA-OLD", "old active version failure cannot poison new version", "D084;RC-08C-02", media_old),
    ("MEDIA-FAIL", "no-space and failed publication keep old audio and marker", "D084;C10,E12", media_failure),
    ("RUNTIME-OPEN", "later song open failure skips; initial failure does not", "D074,D080", runtime_open_failure),
    ("X10", "all-bad STOP then repair current selection and explicit PLAY", "D080,D084;C22,E08,E18", x10),
    ("X11", "last successful save and late notifications", "D085;C05,E09,E19", x11),
    ("X12", "lost reply retry returns original receipt and latest config", "D085;C19,E10,E20", x12),
    ("PROC-TXN", "kill process before/after config/receipt/commit then restart", "D085;C20,RC-08C-01", process_transactions),
    ("PROC-DUP", "in-flight duplicate processes serialize to one commit", "D085;RC-08C-01", process_duplicate),
    ("PROC-MEDIA", "media pointer/receipt interruption and old live file handle", "D084;C11,RC-08C-02", process_media),
    ("PROC-BOOT", "live C process death retains config but no mode/audio", "D052,D073", process_boot),
    ("PROC-PARTIAL", "real partial upload remains unpublished after restart", "D084;C10,C11,E16", partial_upload_restart),
    ("RC-08B2-01", "PLAY searches frozen order after nonselected repair", "User confirmed 2026-10-10;D080,D084", recovered_play),
    ("RECOVERY-ORDER", "PLAY repair search keeps original active snapshot order", "User confirmed 2026-10-10;D077", recovered_order),
]

DEFERRED = {
    "SD-POWER": "Physical SD/FAT power loss and ESP32 recovery require actual storage/electrical bench",
    "REAL-ADAPTERS": "03/04 real audio/NFC callbacks, thresholds, UI/HTTP and concurrency timing",
    "CODEC-MP3": "Real MP3 validation/decoding; PC publisher only validates synthetic PCM WAV",
}
