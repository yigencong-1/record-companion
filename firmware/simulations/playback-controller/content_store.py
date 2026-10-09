"""PC-only file-backed content authority. SQLite and synthetic PCM WAV, stdlib only."""

import errno
import json
import os
import shutil
import sqlite3
import uuid
import wave
from dataclasses import asdict
from pathlib import Path

from controller import Binding, CardIdentity, FakeCatalogStore, MediaVersion, PlaylistSnapshot


def card_key(card):
    return card.technology + ":" + card.uid.hex()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class Rejected(Exception):
    def __init__(self, code, references=()):
        self.code, self.references = code, list(references)


class DurableCatalog(FakeCatalogStore):
    """One controller owns runtime references; DB serializes saved data and receipts."""

    def __init__(self, root, seed=None, hook=None):
        self.root = Path(root)
        self.db = self.root / "catalog.sqlite3"
        self.hook = hook or (lambda stage: None)
        self.resources_ready = True
        if not self.db.exists():
            if seed is None:
                raise FileNotFoundError("Catalog missing; explicit seed required, no silent reset")
            self.root.mkdir(parents=True, exist_ok=True)
            conn = self.connect()
            try:
                conn.execute("CREATE TABLE config (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)")
                conn.execute("CREATE TABLE receipts (request_id TEXT PRIMARY KEY, payload TEXT NOT NULL, body TEXT NOT NULL)")
                conn.execute("INSERT INTO config VALUES (1, ?)", (encode(seed),))
            finally:
                conn.close()
        self.refresh()

    def connect(self):
        conn = sqlite3.connect(self.db, timeout=8, isolation_level=None)
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA busy_timeout=8000")
        return conn

    @staticmethod
    def read_config(conn):
        return json.loads(conn.execute("SELECT body FROM config WHERE id=1").fetchone()[0])

    def refresh(self):
        conn = self.connect()
        try:
            self.config = self.read_config(conn)
        finally:
            conn.close()
        self.commit_seq = self.config["commit_seq"]
        self.bindings = {}
        for key, value in self.config["bindings"].items():
            technology, uid_hex = key.split(":", 1)
            self.bindings[CardIdentity(technology, bytes.fromhex(uid_hex))] = Binding(**value)
        self.playlists = {
            key: PlaylistSnapshot(key, value["revision"], tuple(value["tracks"]))
            for key, value in self.config["playlists"].items()}
        self.tracks = {key: MediaVersion(key, value["version"])
                       for key, value in self.config["tracks"].items()}

    def durable_snapshot(self):
        conn = self.connect()
        try:
            config = self.read_config(conn)
            receipts = {key: json.loads(body) for key, body in
                        conn.execute("SELECT request_id, body FROM receipts ORDER BY request_id")}
            referenced = {value["file"] for value in config["tracks"].values() if value.get("file")}
            # Retained old versions are expected, not safe-to-delete garbage.
            unreferenced = [p.relative_to(self.root).as_posix()
                            for p in sorted((self.root / "media").glob("*.wav"))
                            if p.relative_to(self.root).as_posix() not in referenced]
            staged = [p.name for p in sorted((self.root / "uploads").glob("*.part"))]
            return {"config": config, "receipts": receipts,
                    "unreferenced_version_files": unreferenced, "staged_files": staged,
                    "sqlite_integrity": conn.execute("PRAGMA integrity_check").fetchone()[0]}
        finally:
            conn.close()

    @staticmethod
    def references(config, target_kind, target_id, runtime=()):
        result = []

        def uses(kind, target):
            if kind == target_kind and target == target_id:
                return True
            return (target_kind == "TRACK" and kind == "PLAYLIST" and
                    target_id in config["playlists"].get(target, {}).get("tracks", []))

        for key, binding in config["bindings"].items():
            if uses(binding["target_kind"], binding["target_id"]):
                result.append({"source": "card", "id": key})
        birthday = config.get("birthday")
        if birthday and uses(birthday["target_kind"], birthday["target_id"]):
            result.append({"source": "birthday", "id": "birthday-single-content"})
        if target_kind == "TRACK":
            for key, playlist in config["playlists"].items():
                if target_id in playlist["tracks"]:
                    result.append({"source": "saved-playlist", "id": key})
        for ref in runtime:
            if ref["target_kind"] == target_kind and ref["target_id"] == target_id:
                item = {"source": ref["source"], "id": ref["id"]}
                if item not in result:
                    result.append(item)
        return result

    @staticmethod
    def validate_target(config, kind, target):
        if kind not in {"TRACK", "PLAYLIST"}:
            raise Rejected("UNSUPPORTED_CONTENT_TARGET")
        table = "tracks" if kind == "TRACK" else "playlists"
        if target not in config[table]:
            raise Rejected("TARGET_MISSING")

    def stage_media(self, data, expected_bytes):
        """Upload is invisible until validated publication commits the directory pointer."""
        upload_id = uuid.uuid4().hex
        directory = self.root / "uploads"
        directory.mkdir(exist_ok=True)
        path = directory / (upload_id + ".part")
        with path.open("wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        (directory / (upload_id + ".json")).write_text(
            encode({"expected_bytes": expected_bytes}), encoding="utf-8")
        return upload_id

    def prepare_media(self, upload_id):
        if (not isinstance(upload_id, str) or len(upload_id) != 32 or
                any(c not in "0123456789abcdef" for c in upload_id)):
            raise Rejected("INVALID_UPLOAD_ID")
        path = self.root / "uploads" / (upload_id + ".part")
        try:
            manifest = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            if path.stat().st_size != manifest["expected_bytes"]:
                raise Rejected("MEDIA_INCOMPLETE")
            with wave.open(str(path), "rb") as wav:
                width, channels, frames = wav.getsampwidth(), wav.getnchannels(), wav.getnframes()
                if (wav.getcomptype() != "NONE" or width not in {1, 2, 3, 4} or
                        channels not in {1, 2} or wav.getframerate() <= 0 or frames <= 0):
                    raise Rejected("MEDIA_VALIDATION_FAILED")
                if len(wav.readframes(frames)) != frames * width * channels:
                    raise Rejected("MEDIA_VALIDATION_FAILED")
        except (FileNotFoundError, wave.Error, EOFError, KeyError, ValueError):
            raise Rejected("MEDIA_VALIDATION_FAILED")
        self.hook("media_before_write")
        directory = self.root / "media"
        directory.mkdir(exist_ok=True)
        target = directory / (uuid.uuid4().hex + ".wav")
        with path.open("rb") as source, target.open("xb") as dest:
            shutil.copyfileobj(source, dest)
            dest.flush()
            os.fsync(dest.fileno())
        self.hook("media_file_ready")
        return target.relative_to(self.root).as_posix()

    def mutate(self, config, kind, payload, runtime):
        if kind == "SAVE_BINDING":
            key = payload["card_key"]
            binding = payload["binding"]
            if binding is None:
                config["bindings"].pop(key, None)
                return {"object_revision": None}
            if binding["kind"] not in {"A", "B", "C"}:
                raise Rejected("PRECHECK_INVALID_KIND")
            if binding["kind"] == "A" and binding["target_kind"] != "TRACK":
                raise Rejected("PRECHECK_A_REQUIRES_TRACK")
            self.validate_target(config, binding["target_kind"], binding["target_id"])
            revision = config["bindings"].get(key, {}).get("revision", 0) + 1
            config["bindings"][key] = {**binding, "revision": revision}
            return {"object_revision": revision}
        if kind == "SAVE_PLAYLIST":
            tracks = payload["tracks"]
            if len(set(tracks)) != len(tracks):
                raise Rejected("UNRESOLVED_DUPLICATE_PLAYLIST_ENTRIES")
            for track in tracks:
                self.validate_target(config, "TRACK", track)
            key = payload["playlist_id"]
            revision = config["playlists"].get(key, {}).get("revision", 0) + 1
            config["playlists"][key] = {"tracks": list(tracks), "revision": revision}
            return {"object_revision": revision}
        if kind == "SAVE_BIRTHDAY":
            target = payload["target"]
            if target:
                self.validate_target(config, target["target_kind"], target["target_id"])
            config["birthday"] = target
            return {}
        if kind in {"DELETE_TRACK", "DELETE_PLAYLIST"}:
            target_kind = "TRACK" if kind == "DELETE_TRACK" else "PLAYLIST"
            target = payload["target_id"]
            self.validate_target(config, target_kind, target)
            refs = self.references(config, target_kind, target, runtime)
            if refs:
                raise Rejected("DELETE_BLOCKED_REFERENCED", refs)
            del config["tracks" if target_kind == "TRACK" else "playlists"][target]
            return {"deleted": {"target_kind": target_kind, "target_id": target}}
        if kind == "PUBLISH_MEDIA":
            track = payload["track_id"]
            self.validate_target(config, "TRACK", track)
            file = self.prepare_media(payload["upload_id"])
            version = config["tracks"][track]["version"] + 1
            config["tracks"][track] = {"version": version, "file": file, "validated": True}
            return {"track_id": track, "media_version": version}
        raise Rejected("UNKNOWN_CONTENT_COMMAND")

    def apply(self, request_id, kind, payload, runtime=()):
        if not isinstance(request_id, str) or not request_id:
            return {"outcome": "FAILED", "reason": "REQUEST_ID_REQUIRED"}
        serialized = encode({"kind": kind, "payload": payload})
        conn = self.connect()
        committed = False
        try:
            conn.execute("BEGIN IMMEDIATE")
            old = conn.execute("SELECT payload,body FROM receipts WHERE request_id=?", (request_id,)).fetchone()
            if old:
                if old[0] != serialized:
                    raise Rejected("REQUEST_ID_PAYLOAD_MISMATCH")
                receipt = json.loads(old[1])
                config = self.read_config(conn)
                conn.rollback()
                self.refresh()
                return {"outcome": "SAVED", "replayed": True, "receipt": receipt,
                        "latest_config": config}
            config = self.read_config(conn)
            result = self.mutate(config, kind, payload, runtime)
            config["commit_seq"] += 1
            receipt = {"request_id": request_id, "kind": kind,
                       "commit_seq": config["commit_seq"], **result}
            self.hook("before_config")
            conn.execute("UPDATE config SET body=? WHERE id=1", (encode(config),))
            self.hook("config_written")
            conn.execute("INSERT INTO receipts VALUES (?,?,?)", (request_id, serialized, encode(receipt)))
            self.hook("receipt_written")
            self.hook("before_commit")
            conn.commit()
            committed = True
        except Rejected as error:
            conn.rollback()
            return {"outcome": "FAILED", "reason": error.code, "references": error.references}
        except (OSError, sqlite3.Error) as error:
            conn.rollback()
            code = "NO_SPACE" if getattr(error, "errno", None) == errno.ENOSPC else "STORAGE_FAILURE"
            return {"outcome": "FAILED", "reason": code}
        finally:
            conn.close()
        if committed:
            # A crash here loses delivery, not the atomic config/receipt commit.
            self.hook("after_commit")
            self.refresh()
            return {"outcome": "SAVED", "replayed": False, "receipt": receipt,
                    "latest_config": self.config}

    def publication_is_committed(self, track, version):
        value = self.config["tracks"].get(track, {})
        return (value.get("version") == version and value.get("validated") is True
                and (self.root / value["file"]).is_file())


def fixture_seed():
    """Valid references only; initial media v1 are virtual until a test publishes WAV."""
    cards = [CardIdentity("ISO14443A", bytes.fromhex(uid))
             for uid in ("01020304", "01020304050607", "a1b2c3d4")]
    bindings = [Binding("A", "TRACK", "t1"), Binding("B", "PLAYLIST", "mix"),
                Binding("C", "PLAYLIST", "mix")]
    return {"commit_seq": 0, "bindings": {card_key(c): asdict(b) for c, b in zip(cards, bindings)},
            "playlists": {"mix": {"revision": 1, "tracks": ["t1", "t2", "t3"]},
                          "spare": {"revision": 1, "tracks": ["t4"]}},
            "tracks": {"t" + str(n): {"version": 1, "file": None, "validated": False}
                       for n in range(1, 6)}, "birthday": None}


class ClientView:
    """Abstract UI only: original receipt and latest device configuration are separate."""

    def __init__(self):
        self.commit_seq, self.config = -1, None

    def observe(self, config):
        if config["commit_seq"] < self.commit_seq:
            return "IGNORED_OLD_NOTIFICATION"
        self.commit_seq, self.config = config["commit_seq"], config
        return "LATEST_SHOWN"
