"""RC-08 PC reference controller; virtual adapters, optional real file content store."""

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Optional


VERSION = "0.2.2-batch2"
BASELINE = "5262430cb385316403daadc68f4142c04d6f2259"


@dataclass(frozen=True)
class CardIdentity:
    technology: str
    uid: bytes

    def wire(self):
        return {"technology": self.technology, "uid_hex": self.uid.hex(),
                "uid_length": len(self.uid)}


@dataclass(frozen=True)
class MediaVersion:
    track_id: str
    version: int


@dataclass(frozen=True)
class PlaylistSnapshot:
    playlist_id: Optional[str]
    revision: int
    tracks: tuple[str, ...]


@dataclass(frozen=True)
class Binding:
    kind: str
    target_kind: str
    target_id: str
    revision: int = 1


@dataclass
class TagPresence:
    state: str = "EMPTY"
    card: Optional[CardIdentity] = None
    placement_id: Optional[str] = None
    consumed: bool = False
    requires_replacement: bool = False
    reader_health: str = "HEALTHY"
    fault_since_ms: Optional[int] = None
    boot_held: bool = False


@dataclass(frozen=True)
class ModeSession:
    session_id: str
    kind: str
    origin_card: CardIdentity
    owner_placement: str
    binding_revision: int
    snapshot: PlaylistSnapshot


@dataclass
class TrackSelection:
    snapshot: PlaylistSnapshot
    index: int = 0

    @property
    def track_id(self):
        return self.snapshot.tracks[self.index]


@dataclass(frozen=True)
class AudioToken:
    session_id: Optional[str]
    operation_seq: int
    track_id: str
    media_version: int


@dataclass
class AudioState:
    status: str = "STOPPED"
    position_ms: int = 0
    token: Optional[AudioToken] = None


@dataclass
class DeviceState:
    presence: TagPresence = field(default_factory=TagPresence)
    mode: Optional[ModeSession] = None
    selection: Optional[TrackSelection] = None
    audio: AudioState = field(default_factory=AudioState)
    state_revision: int = 0
    last_error: Optional[str] = None
    # None for RAM fixtures; durable stores supply their actual committed sequence.
    commit_seq: Optional[int] = None
    failed_tracks: dict[str, int] = field(default_factory=dict)
    mode_music_started: bool = False


class VirtualClock:
    def __init__(self):
        self.now_ms = 0

    def advance(self, ms):
        if ms < 0:
            raise ValueError("Virtual time must be monotonic")
        self.now_ms += ms


class FakeCatalogStore:
    """Read-only RAM fixtures. No save/retry/power-loss claims."""

    def __init__(self, bindings, playlists, tracks):
        self.bindings = dict(bindings)
        self.playlists = dict(playlists)
        self.tracks = {track: MediaVersion(track, 1) for track in tracks}
        self.resources_ready = True

    def preflight(self, binding):
        if not self.resources_ready:
            raise ValueError("PRECHECK_RESOURCE_UNAVAILABLE")
        if binding.kind not in {"A", "B", "C"}:
            raise ValueError("PRECHECK_INVALID_KIND")
        if binding.kind == "A" and binding.target_kind != "TRACK":
            raise ValueError("PRECHECK_A_REQUIRES_TRACK")
        if binding.target_kind == "TRACK":
            if binding.target_id not in self.tracks:
                raise ValueError("PRECHECK_TRACK_MISSING")
            return PlaylistSnapshot(None, 0, (binding.target_id,))
        if binding.target_kind == "PLAYLIST":
            snapshot = self.playlists.get(binding.target_id)
            if not snapshot or not snapshot.tracks:
                raise ValueError("PRECHECK_PLAYLIST_MISSING_OR_EMPTY")
            if snapshot.tracks[0] not in self.tracks:
                raise ValueError("PRECHECK_TRACK_MISSING")
            return snapshot
        # Special-only bindings require a defined special-action adapter, outside this batch.
        raise ValueError("PRECHECK_UNSUPPORTED_TARGET")


class FakeAudio:
    def __init__(self):
        self.commands = []

    def send(self, command):
        self.commands.append(command)

    @property
    def starts(self):
        return [c for c in self.commands if c["kind"] in {"AUDIO_START", "AUDIO_RESUME"}]


class Controller:
    def __init__(self, catalog, audio, clock, fault_limit_ms=1000):
        if fault_limit_ms <= 0:
            raise ValueError("A positive injectable simulation threshold is required")
        self.catalog, self.adapter, self.clock = catalog, audio, clock
        self.fault_limit_ms = fault_limit_ms
        self.state = DeviceState()
        self.state.commit_seq = getattr(catalog, "commit_seq", None)
        self.last_content_result = None
        self.event_seq = self.operation_seq = self.session_seq = 0
        self.actions, self.trace, self.unresolved = [], [], []
        self._seen_placements = set()

    def snapshot(self):
        p, s, a = self.state.presence, self.state, self.state.audio
        return {
            "state_revision": s.state_revision,
            "tag_presence": {**asdict(p), "card": p.card.wire() if p.card else None},
            "mode": ({**asdict(s.mode), "origin_card": s.mode.origin_card.wire()}
                     if s.mode else None),
            "selected_track_id": s.selection.track_id if s.selection else None,
            "selection_index": s.selection.index if s.selection else None,
            "playlist_snapshot": asdict(s.selection.snapshot) if s.selection else None,
            "audio_state": a.status, "position_ms": a.position_ms,
            "audio_token": asdict(a.token) if a.token else None,
            "operation_seq": self.operation_seq, "commit_seq": s.commit_seq,
            "last_error": s.last_error,
            "failed_tracks": dict(s.failed_tracks),
            "mode_music_started": s.mode_music_started,
            "saved_binding_revision": (self.catalog.bindings[p.card].revision
                                       if p.card in self.catalog.bindings else None),
            "saved_playlist_revisions": {k: v.revision for k, v in self.catalog.playlists.items()},
            "media_versions": {k: v.version for k, v in self.catalog.tracks.items()},
        }

    def _action(self, kind, **values):
        action = {"kind": kind, "at_ms": self.clock.now_ms, **values}
        self.actions.append(action)
        if kind.startswith("AUDIO_"):
            self.adapter.send(action)

    def _invalidate(self):
        self.operation_seq += 1
        self.state.audio.token = None

    def _stop(self, clear=False):
        token = self.state.audio.token
        self._invalidate()
        self._action("AUDIO_STOP", token=asdict(token) if token else None,
                     invalidate_through=self.operation_seq)
        self.state.audio.status = "STOPPED" if clear else "STOPPED_USER"
        self.state.audio.position_ms = 0
        if clear:
            self.state.selection = None

    def _exit_mode(self, reason):
        if self.state.mode:
            self._action("MODE_ENDED", session_id=self.state.mode.session_id, reason=reason)
        self.state.mode = None
        self.state.failed_tracks.clear()
        self.state.mode_music_started = False
        self._stop(clear=True)

    def _start_audio(self, position_ms=0, resume=False):
        track = self.state.selection.track_id
        media = self.catalog.tracks.get(track)
        self._invalidate()
        if not media:
            self.state.audio.status = "STOPPED_ERROR"
            self.state.last_error = "START_FAILED_MEDIA_MISSING"
            return
        token = AudioToken(self.state.mode.session_id if self.state.mode else None,
                           self.operation_seq, track, media.version)
        self.state.audio = AudioState("STARTING", position_ms, token)
        self._action("AUDIO_RESUME" if resume else "AUDIO_START",
                     token=asdict(token), offset_ms=position_ms)

    def _advance_playable(self, start_step=1):
        """Bounded search through the frozen order; never retry blocked media versions."""
        s = self.state
        for step in range(start_step, start_step + len(s.selection.snapshot.tracks)):
            index = (s.selection.index + step) % len(s.selection.snapshot.tracks)
            track = s.selection.snapshot.tracks[index]
            media = self.catalog.tracks.get(track)
            if media and s.failed_tracks.get(track) != media.version:
                s.selection.index = index
                self._start_audio(0)
                return "MODE_LOOP_NEXT"
        self._stop()
        s.audio.status, s.last_error = "STOPPED_ERROR", "ALL_TRACKS_UNPLAYABLE"
        self._action("ALL_TRACKS_FAILED", session_id=s.mode.session_id)
        return "ALL_TRACKS_UNPLAYABLE_MODE_RETAINED"

    def _runtime_failure(self, token, reason):
        current = self.catalog.tracks.get(token.track_id)
        if current and current.version == token.media_version:
            self.state.failed_tracks[token.track_id] = token.media_version
        self._action("TRACK_FAILED", token=asdict(token), reason=reason,
                     obsolete_media=bool(current and current.version != token.media_version))
        self._stop()
        return self._advance_playable()

    def _runtime_references(self):
        s, refs = self.state, []
        if s.mode:
            snapshot, sid = s.mode.snapshot, s.mode.session_id
            if snapshot.playlist_id:
                refs.append({"source": "active-session", "id": sid,
                             "target_kind": "PLAYLIST", "target_id": snapshot.playlist_id})
            for track in snapshot.tracks:
                refs.append({"source": "active-snapshot", "id": sid,
                             "target_kind": "TRACK", "target_id": track})
        if s.selection and s.audio.status != "STOPPED":
            refs.append({"source": "audio-" + s.audio.status.lower(),
                         "id": "operation-" + str(self.operation_seq),
                         "target_kind": "TRACK", "target_id": s.selection.track_id})
        return refs

    def _media_published(self, track, version):
        if (not hasattr(self.catalog, "publication_is_committed") or
                not self.catalog.publication_is_committed(track, version)):
            return "IGNORED_UNPUBLISHED_MEDIA"
        failed = self.state.failed_tracks.get(track)
        if failed is not None and version > failed:
            del self.state.failed_tracks[track]
            self._action("TRACK_REQUALIFIED", track_id=track, media_version=version)
        # Qualification never changes selection, token, STOP lock or current audio.
        return "MEDIA_QUALIFIED_NO_AUTOPLAY"

    def _content(self, kind, data):
        if not hasattr(self.catalog, "apply"):
            return "DEFERRED_BATCH2"
        from content_store import card_key
        payload = {k: v for k, v in data.items() if k != "request_id"}
        if kind == "SAVE_BINDING":
            payload["card_key"] = card_key(payload.pop("card"))
            binding = payload["binding"]
            payload["binding"] = asdict(binding) if binding is not None else None
        if kind in {"DELETE_TRACK", "DELETE_PLAYLIST"}:
            payload["target_id"] = payload.pop("track_id" if kind == "DELETE_TRACK" else "playlist_id")
        result = self.catalog.apply(data.get("request_id"), kind, payload,
                                    self._runtime_references())
        self.last_content_result = result
        self.state.commit_seq = self.catalog.commit_seq
        if result["outcome"] == "FAILED":
            self.state.last_error = result["reason"]
            self._action("CONTENT_REJECTED", **result)
            return result["reason"]
        self._action("CONTENT_REPLY", **result)
        if not result["replayed"]:
            self._action("CONFIG_COMMITTED", commit_seq=self.catalog.commit_seq,
                         config=result["latest_config"])
            if kind == "PUBLISH_MEDIA":
                receipt = result["receipt"]
                self._media_published(receipt["track_id"], receipt["media_version"])
        return "REPLAYED" if result["replayed"] else "SAVED"

    def _request(self, binding, card=None, placement_id=None, automatic=False):
        try:
            snapshot = self.catalog.preflight(binding)
        except ValueError as error:
            self.state.last_error = str(error)
            self._action("REQUEST_REJECTED", reason=str(error))
            return "REJECTED"
        # Confirmed RC-08A-01: valid different B/C fully takes over, no old-mode stack.
        self._exit_mode("VALID_REQUEST_TAKEOVER")
        self.state.last_error = None
        self.state.selection = TrackSelection(snapshot)
        if binding.kind in {"B", "C"}:
            self.session_seq += 1
            mode = ModeSession(f"session-{self.session_seq}", binding.kind, card,
                               placement_id, binding.revision, snapshot)
            self.state.mode = mode
            self._action("MODE_STARTED", session_id=mode.session_id, mode_kind=mode.kind)
        self._start_audio()
        return "STARTING"

    def _binding_request(self, automatic):
        p, old = self.state.presence, self.state.mode
        if not p.card or p.state not in {"PRESENT", "BOOT_HELD"}:
            return "NO_TRUSTED_CARD"
        if p.requires_replacement:
            return "REPLACEMENT_REQUIRED"
        if automatic and old and old.kind == "C" and old.origin_card == p.card:
            self._action("C_SAME_CARD_RETAINED", session_id=old.session_id)
            return "RETAINED"
        binding = self.catalog.bindings.get(p.card)
        if binding is None:
            self.state.last_error = "PRECHECK_UNBOUND_CARD"
            self._action("REQUEST_REJECTED", reason=self.state.last_error)
            return "REJECTED"
        result = self._request(binding, p.card, p.placement_id, automatic)
        if result == "STARTING" and p.boot_held:
            p.boot_held, p.state = False, "PRESENT"
        return result

    def dispatch(self, kind, **payload):
        self.event_seq += 1
        before, action_index = self.snapshot(), len(self.actions)
        result = self._handle(kind, payload)
        self.state.state_revision += 1
        serial = {k: (v.wire() if isinstance(v, CardIdentity) else
                      asdict(v) if is_dataclass(v) else v)
                  for k, v in payload.items()}
        self.trace.append({"event_seq": self.event_seq, "at_ms": self.clock.now_ms,
                           "input": {"kind": kind, **serial}, "result": result,
                           "before": before, "actions": self.actions[action_index:],
                           "after": self.snapshot()})
        return result

    def _handle(self, kind, data):
        p, s, a = self.state.presence, self.state, self.state.audio
        if kind == "BOOT_RESET":
            self._exit_mode("BOOT_RESET")
            self.state.presence = TagPresence()
            self.state.last_error = None
            return "RESET_NO_RESTORE"
        if kind in {"CARD_INSERTED", "BOOT_HELD"}:
            placement = data["placement_id"]
            if placement in self._seen_placements:
                return "IGNORED_DUPLICATE_PLACEMENT"
            if p.reader_health != "HEALTHY":
                return "REJECTED_READER_UNHEALTHY"
            if p.card:
                self.state.last_error = "UNTRUSTED_REPLACEMENT"
                return "REJECTED_NO_REMOVAL_EVIDENCE"
            self._seen_placements.add(placement)
            self.state.presence = TagPresence(
                kind if kind == "BOOT_HELD" else "PRESENT", data["card"], placement, True,
                boot_held=kind == "BOOT_HELD")
            if kind == "BOOT_HELD":
                return "WAIT_EXPLICIT_START"
            return self._binding_request(automatic=True)
        if kind == "UID_OBSERVED":
            if p.card and data.get("card") != p.card:
                self.state.last_error = "UID_CONFLICT"
                return "CONFLICT_NOT_REMOVAL"
            return "OBSERVATION_ONLY"
        if kind == "CARD_REMOVED":
            placement = data["placement_id"]
            if placement != p.placement_id:
                return "IGNORED_STALE_REMOVAL"
            if s.mode and s.mode.kind == "B" and s.mode.owner_placement == placement:
                self._exit_mode("TRUSTED_B_REMOVAL")
            self.state.presence = TagPresence(reader_health=p.reader_health,
                                             fault_since_ms=p.fault_since_ms)
            return "TRUSTED_EMPTY"
        if kind in {"CARD_UNCERTAIN", "READER_FAULT"}:
            if p.fault_since_ms is None:
                p.fault_since_ms = self.clock.now_ms
            p.reader_health = kind
            p.state = kind
            self._action("READER_RECOVERY_REQUESTED", reason=kind)
            return "FAULT_NOT_REMOVAL"
        if kind == "READER_RECOVERED":
            if data.get("card") != p.card:
                return "RECOVERY_IDENTITY_NOT_CONFIRMED"
            p.reader_health, p.fault_since_ms = "HEALTHY", None
            p.state = ("BOOT_HELD" if p.boot_held else "PRESENT") if p.card else "EMPTY"
            return "RECOVERED_NO_TRIGGER"
        if kind == "TICK":
            delta = data["ms"]
            self.clock.advance(delta)
            if a.status == "PLAYING":
                a.position_ms += delta
            if (s.mode and s.mode.kind == "B" and p.fault_since_ms is not None
                    and self.clock.now_ms - p.fault_since_ms > self.fault_limit_ms):
                self._exit_mode("READER_FAULT_PROTECTION")
                p.consumed, p.requires_replacement = True, True
                self.state.last_error = "READER_FAULT_PROTECTION"
            return "TIME_ADVANCED"
        if kind == "SELECT_TRACK":
            return self._request(Binding("A", "TRACK", data["track_id"]))
        if kind == "START_CURRENT_CARD":
            return self._binding_request(automatic=False)
        if kind in {"PLAY", "PAUSE", "STOP", "NEXT", "MODE_EXIT"}:
            expected_session = data.get("session_id")
            if expected_session and (not s.mode or s.mode.session_id != expected_session):
                return "IGNORED_STALE_COMMAND"
            if kind == "MODE_EXIT":
                self._exit_mode("EXPLICIT_MODE_EXIT")
                p.consumed = True
                return "MODE_EXITED"
            if kind == "STOP":
                self._stop()
                return "AUDIO_STOPPED_MODE_RETAINED"
            if kind == "PAUSE":
                if a.status != "PLAYING":
                    return "NO_PLAYING_AUDIO"
                token = a.token
                self._invalidate()
                self._action("AUDIO_PAUSE", token=asdict(token))
                a.status = "PAUSED"
                return "AUDIO_PAUSED_MODE_RETAINED"
            if kind == "NEXT":
                if not s.mode or not s.selection:
                    return "NO_MODE_SELECTION"
                if a.status in {"PAUSED", "STARTING", "STOPPED_ERROR"}:
                    return "OUT_OF_BATCH_CONTROL_STATE"
                if a.status == "PLAYING":
                    self._stop()
                    self._advance_playable()
                    return "NEXT_SELECTED"
                s.selection.index = (s.selection.index + 1) % len(s.selection.snapshot.tracks)
                return "NEXT_SELECTED"
            if kind == "PLAY":
                if not s.selection:
                    if p.state == "BOOT_HELD":
                        return self._binding_request(automatic=False)
                    return "NO_SELECTION"
                if a.status in {"PLAYING", "STARTING"}:
                    return "ALREADY_ACTIVE"
                if a.status == "PAUSED":
                    self._start_audio(a.position_ms, resume=True)
                elif s.mode:
                    # Confirmed RC-08B2-01: inspect current selection, then frozen order.
                    result = self._advance_playable(start_step=0)
                    if s.audio.status != "STARTING":
                        return result
                else:
                    self._start_audio(0)
                return "STARTING"
        if kind in {"AUDIO_STARTED", "AUDIO_START_FAILED", "EOF", "AUDIO_STOPPED"}:
            token = data["token"]
            if token != a.token:
                return "IGNORED_STALE_AUDIO"
            if kind == "AUDIO_STARTED" and a.status == "STARTING":
                a.status = "PLAYING"
                if s.mode:
                    s.mode_music_started = True
                return "AUDIO_PLAYING"
            if kind == "AUDIO_START_FAILED" and a.status == "STARTING":
                if s.mode and s.mode_music_started:
                    return self._runtime_failure(token, data.get("reason", "NEXT_OPEN_FAILED"))
                self._invalidate()
                a.status = "STOPPED_ERROR"
                self.state.last_error = "AUDIO_START_FAILED"
                self._action("START_FAILURE_REPORTED", reason=data.get("reason", "FAKE_IO_ERROR"))
                return "START_FAILED_NO_ROLLBACK"
            if kind == "EOF" and a.status == "PLAYING":
                if s.mode:
                    return self._advance_playable()
                self._invalidate()
                a.status, a.position_ms = "STOPPED", 0
                return "NORMAL_TRACK_ENDED"
            return "IGNORED_AUDIO_WRONG_STATE"
        if kind == "TRACK_READ_ERROR":
            token = data["token"]
            if token != a.token:
                return "IGNORED_STALE_AUDIO"
            if a.status != "PLAYING":
                return "IGNORED_AUDIO_WRONG_STATE"
            if not s.mode:
                return "OUT_OF_BATCH_NORMAL_READ_ERROR"
            return self._runtime_failure(token, data.get("reason", "READ_ERROR"))
        if kind == "MEDIA_PUBLISHED":
            return self._media_published(data["track_id"], data["media_version"])
        if kind in {"SAVE_BINDING", "SAVE_PLAYLIST", "SAVE_BIRTHDAY", "PUBLISH_MEDIA",
                    "DELETE_TRACK", "DELETE_PLAYLIST"}:
            return self._content(kind, data)
        raise ValueError(f"Unknown event: {kind}")


class FakeNFC:
    """Only explicit trusted methods create placement/removal evidence."""

    def __init__(self, controller):
        self.controller, self.placement_seq = controller, 0

    def insert(self, card, boot=False):
        self.placement_seq += 1
        return self.controller.dispatch("BOOT_HELD" if boot else "CARD_INSERTED",
                                        card=card, placement_id=f"placement-{self.placement_seq}")

    def remove(self, placement_id=None):
        placement = placement_id or self.controller.state.presence.placement_id
        return self.controller.dispatch("CARD_REMOVED", placement_id=placement)

    def observe(self, card):
        return self.controller.dispatch("UID_OBSERVED", card=card)
