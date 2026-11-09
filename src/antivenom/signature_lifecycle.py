"""Local publication/revocation contracts for capture-derived signatures.

This is a separately versioned, model-free addition.  A logical ID is bound to
one capture; positive revisions may replace its signature while that ID is
active.  Revocation permanently tombstones the ID, including when received
before publication.  A new capture requires a new logical ID.

Portable snapshots preserve delivery history and validate it by deterministic
replay.  Hashes detect inconsistent local records; they do not authenticate a
publisher.  Two manually driven registry objects are local receiver replicas,
not evidence of a network, authenticated publication, fleet behavior or
distributed revocation latency.

Filtering always starts from the caller's original immutable memory tuple.
Revocation can restore that filtering input, but cannot undo previous agent
actions or memories written as a result of them.  No model or tool is loaded.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from numbers import Real
from typing import Mapping, Sequence

from antivenom.tool_policy_signature import (
    MAX_MEMORY_CHARS, CaptureView, ExtractionResult, ScoreCallback,
    build_nli_hypothesis, parse_extraction,
)

SCHEMA_VERSION = "antivenom.signature-lifecycle.v1"
MAX_REVISION = 2 ** 53 - 1  # Portable exact integer in common JSON readers.


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def _hash(value: object) -> str:
    return _sha(_canonical(value))


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError("logical ID must be a nonblank string of at most 512 characters")
    return value


def _revision(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_REVISION:
        raise ValueError("revision must be a positive JSON-safe integer")
    return value


def _digest(value: object) -> str:
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)):
        raise ValueError("digest must be lowercase SHA256")
    return value


def _validated_extraction(record: Mapping[str, object]) -> ExtractionResult:
    """Validate exact saved decoder evidence without retrying a decoder."""
    expected = {"schema", "capture_id", "raw_memory_sha256", "stored_memory_sha256",
                "raw_output", "raw_output_sha256", "status", "errors", "signature", "valid"}
    if not isinstance(record, Mapping) or set(record) != expected:
        raise ValueError("publication needs the exact extraction evidence schema")
    if (type(record["schema"]) is not int or record["schema"] != 1
            or record["valid"] is not True or record["status"] != "valid"
            or not isinstance(record["errors"], (list, tuple)) or record["errors"]):
        raise ValueError("invalid or malformed extraction cannot be published")
    capture_id = record["capture_id"]
    if not isinstance(capture_id, str) or not capture_id.strip():
        raise ValueError("capture ID must be a nonblank string")
    raw_hash = _digest(record["raw_memory_sha256"])
    stored_hash = record["stored_memory_sha256"]
    if stored_hash is not None:
        _digest(stored_hash)
    output = record["raw_output"]
    if not isinstance(output, str) or _digest(record["raw_output_sha256"]) != _sha(output):
        raise ValueError("raw decoder output hash mismatch")
    # The placeholder is used only to revalidate saved output syntax/signature;
    # its source hash is discarded.  Declared original source hashes remain
    # explicit bindings, not authentication or independent source verification.
    parsed = parse_extraction(CaptureView(capture_id, "saved-output syntax validation only"), output)
    if not parsed.valid or parsed.signature is None:
        raise ValueError("invalid or malformed extraction cannot be published")
    if not isinstance(record["signature"], Mapping) or asdict(parsed.signature) != record["signature"]:
        raise ValueError("published signature disagrees with exact decoder output")
    return ExtractionResult(capture_id=capture_id, raw_memory_sha256=raw_hash,
        stored_memory_sha256=stored_hash, raw_output=output,
        raw_output_sha256=_sha(output), status="valid", errors=(), signature=parsed.signature)


def _extraction_record(extraction: ExtractionResult) -> dict:
    if not isinstance(extraction, ExtractionResult):
        raise ValueError("publication requires an ExtractionResult")
    checked = _validated_extraction(extraction.as_dict())
    # Normalize tuple/list representation to portable JSON primitives.
    return json.loads(_canonical(checked.as_dict()))


def _capture_binding(record: Mapping[str, object]) -> tuple:
    return (record["capture_id"], record["raw_memory_sha256"], record["stored_memory_sha256"])


def _memories(memories: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(memories, Sequence) or isinstance(memories, (str, bytes)):
        raise ValueError("memories must be an ordered sequence of actual stored-memory strings")
    texts = tuple(memories)
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("each stored memory must be a nonblank string")
    if any(len(text) > MAX_MEMORY_CHARS for text in texts):
        raise ValueError("stored memory exceeds the recorded size limit")
    return texts


def _probability(value: object) -> float:
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not 0 <= value <= 1 or not math.isfinite(value)):
        raise ValueError("threshold and scores must be finite numbers in [0, 1]")
    return float(value)


def _scores(values: Sequence[float], count: int) -> tuple[float, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError("callback scores must be a numeric sequence")
    try:
        scores = tuple(values)
    except TypeError as exc:
        raise ValueError("callback scores must be a numeric sequence") from exc
    if len(scores) != count:
        raise ValueError("score count does not match all active-signature/memory pairs")
    return tuple(_probability(score) for score in scores)


@dataclass(frozen=True)
class SignatureScore:
    logical_id: str
    revision: int
    publication_sha256: str
    capture_id: str
    raw_memory_sha256: str
    stored_memory_sha256: str | None
    hypothesis: str
    hypothesis_sha256: str
    scores: tuple[float, ...]
    flags: tuple[int, ...]


@dataclass(frozen=True)
class LifecycleFilterDecision:
    schema: str
    status: str
    registry_content_sha256: str
    entailment_threshold: float
    active_signature_ids: tuple[str, ...]
    per_signature: tuple[SignatureScore, ...]
    callback_calls: int
    scored_pairs: int
    input_hashes: tuple[str, ...]
    flags: tuple[int, ...]
    kept_memories: tuple[str, ...]
    kept_hashes: tuple[str, ...]

    def as_dict(self) -> dict:
        return asdict(self)


class SignatureRegistry:
    """Deterministic local registry with permanent logical-ID tombstones."""

    def __init__(self) -> None:
        self._active: dict[str, dict] = {}
        self._tombstones: set[str] = set()
        self._history: list[dict] = []

    @property
    def active_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._active))

    @property
    def tombstone_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._tombstones))

    def _content(self) -> dict:
        return {"schema": SCHEMA_VERSION,
                "active": [copy.deepcopy(self._active[key]) for key in self.active_ids],
                "tombstones": list(self.tombstone_ids)}

    @property
    def content_sha256(self) -> str:
        return _hash(self._content())

    def publish(self, logical_id: str, revision: int, extraction: ExtractionResult) -> str:
        """Publish/update, ignore stale/duplicate, or honor a prior tombstone.

        Conflicting same-version content and changing the capture bound to an
        active logical ID are errors and leave the registry/history unchanged.
        Every accepted or ignored valid delivery is recorded for local replay.
        """
        logical_id, revision = _identifier(logical_id), _revision(revision)
        record = _extraction_record(extraction)
        payload_hash = _hash(record)
        entry = {"logical_id": logical_id, "revision": revision,
                 "extraction": record, "publication_sha256": payload_hash}
        if logical_id in self._tombstones:
            outcome = "tombstoned"
        elif logical_id not in self._active:
            self._active[logical_id] = entry
            outcome = "published"
        else:
            current = self._active[logical_id]
            if _capture_binding(current["extraction"]) != _capture_binding(record):
                raise ValueError("different capture requires a new logical ID")
            if revision < current["revision"]:
                outcome = "stale"
            elif revision == current["revision"]:
                if payload_hash != current["publication_sha256"]:
                    raise ValueError("conflicting publication for the same revision")
                outcome = "duplicate"
            else:
                self._active[logical_id] = entry
                outcome = "updated"
        self._history.append({"operation": "publish", **copy.deepcopy(entry), "outcome": outcome})
        return outcome

    def revoke(self, logical_id: str) -> str:
        """Permanently tombstone an ID, even before any publication arrives."""
        logical_id = _identifier(logical_id)
        outcome = "already_revoked" if logical_id in self._tombstones else "revoked"
        self._tombstones.add(logical_id)
        self._active.pop(logical_id, None)
        self._history.append({"operation": "revoke", "logical_id": logical_id, "outcome": outcome})
        return outcome

    def snapshot(self) -> dict:
        """Return independent JSON primitives, including delivery history."""
        content = self._content()
        payload = {**content, "history": copy.deepcopy(self._history),
                   "content_sha256": _hash(content), "history_sha256": _hash(self._history)}
        return {**payload, "snapshot_sha256": _hash(payload)}

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, object]) -> "SignatureRegistry":
        """Validate hashes, replay history, and match the declared final state.

        Self-consistent local hashes are not publisher authentication.  A
        caller requiring authentic messages must supply an external reviewed
        trust/transport mechanism; none is implemented or inferred here.
        """
        keys = {"schema", "active", "tombstones", "history", "content_sha256",
                "history_sha256", "snapshot_sha256"}
        if not isinstance(snapshot, Mapping) or set(snapshot) != keys or snapshot["schema"] != SCHEMA_VERSION:
            raise ValueError("unsupported lifecycle snapshot schema")
        for key in ("active", "tombstones", "history"):
            if not isinstance(snapshot[key], list):
                raise ValueError("snapshot state/history fields must be lists")
        for key in ("content_sha256", "history_sha256", "snapshot_sha256"):
            _digest(snapshot[key])
        payload = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
        if _hash(payload) != snapshot["snapshot_sha256"]:
            raise ValueError("snapshot hash mismatch")
        restored = cls()
        for event in snapshot["history"]:
            if not isinstance(event, Mapping):
                raise ValueError("history event must be an object")
            operation = event.get("operation")
            if operation == "publish":
                expected = {"operation", "logical_id", "revision", "extraction",
                            "publication_sha256", "outcome"}
                if set(event) != expected:
                    raise ValueError("publication history has undeclared/missing fields")
                extraction = _validated_extraction(event["extraction"])
                if _hash(_extraction_record(extraction)) != event["publication_sha256"]:
                    raise ValueError("publication history binding mismatch")
                outcome = restored.publish(event["logical_id"], event["revision"], extraction)
            elif operation == "revoke":
                if set(event) != {"operation", "logical_id", "outcome"}:
                    raise ValueError("revocation history has undeclared/missing fields")
                outcome = restored.revoke(event["logical_id"])
            else:
                raise ValueError("unknown history operation")
            if event["outcome"] != outcome:
                raise ValueError("history outcome disagrees with deterministic replay")
        if restored.snapshot() != dict(snapshot):
            raise ValueError("declared snapshot state/hash disagrees with deterministic history replay")
        return restored

    def filter(
        self, memories: Sequence[str], score_callback: ScoreCallback | None = None,
        *, entailment_threshold: float,
    ) -> LifecycleFilterDecision:
        """Union active-signature flags against original evidence every time.

        Active signatures are snapshotted at call entry; a publication or
        revocation during scoring affects the next call, not an in-flight
        decision.  The callback receives all pairs once, ordered by sorted
        logical ID then original memory position.  ``callback_calls`` counts Python
        callback invocations, not underlying model calls.  Original texts are
        retained byte-for-byte; no in-place store mutation or refill occurs.
        """
        texts = _memories(memories)
        threshold = _probability(entailment_threshold)
        content = self._content()
        content_hash = _hash(content)
        entries = content["active"]
        ids = tuple(entry["logical_id"] for entry in entries)
        hypotheses = []
        for entry in entries:
            extraction = _validated_extraction(entry["extraction"])
            assert extraction.signature is not None
            hypotheses.append(build_nli_hypothesis(extraction.signature))
        pairs = [(text, hypothesis) for hypothesis in hypotheses for text in texts]
        if pairs and not callable(score_callback):
            raise ValueError("active filtering needs a callable score_callback")
        values = _scores(score_callback(pairs), len(pairs)) if pairs else ()
        per_signature = []
        union = set()
        width = len(texts)
        for i, entry in enumerate(entries):
            scores = tuple(values[i * width:(i + 1) * width])
            flags = tuple(j for j, score in enumerate(scores) if score >= threshold)
            union.update(flags)
            extraction = entry["extraction"]
            per_signature.append(SignatureScore(logical_id=entry["logical_id"], revision=entry["revision"],
                publication_sha256=entry["publication_sha256"], capture_id=extraction["capture_id"],
                raw_memory_sha256=extraction["raw_memory_sha256"],
                stored_memory_sha256=extraction["stored_memory_sha256"],
                hypothesis=hypotheses[i], hypothesis_sha256=_sha(hypotheses[i]),
                scores=scores, flags=flags))
        flags = tuple(sorted(union))
        kept = tuple(text for i, text in enumerate(texts) if i not in union)
        return LifecycleFilterDecision(schema=SCHEMA_VERSION,
            status="filtered" if ids else "no_active_signatures_passthrough",
            registry_content_sha256=content_hash, entailment_threshold=threshold,
            active_signature_ids=ids, per_signature=tuple(per_signature),
            callback_calls=int(bool(pairs)), scored_pairs=len(pairs),
            input_hashes=tuple(map(_sha, texts)), flags=flags, kept_memories=kept,
            kept_hashes=tuple(map(_sha, kept)))
