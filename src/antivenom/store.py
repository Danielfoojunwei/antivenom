"""Retrieval memory store with an explicit record lifecycle.

Every record has an ``origin`` (who wrote it) and a ``status``. Defences in
this project only ever *append* records or change ``status`` through the
store's own update path; nothing reaches in and edits text.

``enforce_revocation`` exists because "Revoked but Still Authoritative"
(arXiv 2609.08258) found that real memory systems keep returning revoked
facts. We keep the switch so that failure mode can be measured, not assumed.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

ORIGINS = {"corpus", "poison", "antibody", "agent"}


@dataclass
class Record:
    id: str
    text: str
    origin: str
    status: str = "active"          # active | retired
    meta: dict = field(default_factory=dict)


class MemoryStore:
    def __init__(self, retriever, enforce_revocation: bool = True):
        self.retriever = retriever
        self.enforce_revocation = enforce_revocation
        self.records: list[Record] = []
        self._vecs: list[np.ndarray] = []
        self._ids = itertools.count()

    def add(self, texts: list[str], origin: str, vecs: np.ndarray | None = None,
            meta: list[dict] | None = None, ids: list[str] | None = None) -> list[Record]:
        assert origin in ORIGINS, origin
        if vecs is None:
            vecs = self.retriever.encode(texts)
        new = []
        for i, t in enumerate(texts):
            rid = ids[i] if ids else f"{origin}-{next(self._ids)}"
            r = Record(rid, t, origin, meta=(meta[i] if meta else {}))
            self.records.append(r)
            self._vecs.append(np.asarray(vecs[i], dtype=np.float32))
            new.append(r)
        return new

    def retire(self, rid: str, reason: str) -> None:
        for r in self.records:
            if r.id == rid:
                r.status = "retired"
                r.meta["retired_reason"] = reason

    def search(self, query: str, k: int, qvec: np.ndarray | None = None) -> list[tuple[Record, float]]:
        if qvec is None:
            qvec = self.retriever.encode([query])[0]
        M = np.stack(self._vecs)
        if self.retriever.score == "cos":
            M = M / np.linalg.norm(M, axis=1, keepdims=True)
            qvec = qvec / np.linalg.norm(qvec)
        scores = M @ qvec
        order = np.argsort(-scores)
        out = []
        for j in order:
            r = self.records[j]
            if self.enforce_revocation and r.status != "active":
                continue
            out.append((r, float(scores[j])))
            if len(out) == k:
                break
        return out
