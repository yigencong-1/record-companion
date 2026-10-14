"""Independent process for durable writes, interruption barriers and restart inspection."""

import argparse
import json
import os
import sys
from pathlib import Path

from content_store import DurableCatalog
from controller import CardIdentity, Controller, FakeAudio, FakeNFC, VirtualClock


def emit(kind, **payload):
    print(json.dumps({"type": kind, "pid": os.getpid(), **payload}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--job", required=True)
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))

    def hook(stage):
        if stage == job.get("barrier"):
            emit("checkpoint", stage=stage)
            if sys.stdin.readline().strip() != "continue":
                os._exit(97)

    catalog = DurableCatalog(args.root, hook=hook)
    emit("ready", commit_seq=catalog.commit_seq)
    if "command" in job:
        result = catalog.apply(job["request_id"], job["command"], job["payload"])
        emit("result", result=result)
    if job.get("exercise_c") or job.get("boot_card"):
        audio = FakeAudio()
        ctrl = Controller(catalog, audio, VirtualClock())
        nfc = FakeNFC(ctrl)
        card = CardIdentity("ISO14443A", bytes.fromhex("a1b2c3d4"))
        initial = ctrl.snapshot()
        if job.get("exercise_c"):
            nfc.insert(card)
            ctrl.dispatch("AUDIO_STARTED", token=ctrl.state.audio.token)
            ctrl.dispatch("TICK", ms=1234)
            emit("live", state=ctrl.snapshot(), starts=len(audio.starts))
            hook("running_c")
        else:
            nfc.insert(card, boot=True)
            held = ctrl.snapshot()
            before_starts = len(audio.starts)
            if job.get("explicit_play"):
                ctrl.dispatch("PLAY")
            emit("boot", initial=initial, held=held, before_starts=before_starts,
                 after=ctrl.snapshot(), starts=len(audio.starts))
    emit("snapshot", snapshot=catalog.durable_snapshot())


if __name__ == "__main__":
    main()
