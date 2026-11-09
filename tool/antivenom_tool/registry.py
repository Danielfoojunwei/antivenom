"""Sharing signatures between agents, safely.

A forged signature could make agents delete good evidence, so shared
signatures are signed. ``SignatureRegistry`` is a small, transport-agnostic
store: publish signed signatures, and subscribers accept only those whose
HMAC verifies with the shared key and that have not expired or been revoked.

Transport is up to you: the registry is a JSON file by default, and
``export``/``ingest`` move signed messages over any channel (HTTP, a queue,
a shared memory store, an agent-to-agent protocol).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path

from .signature import Signature


class SignatureRejected(ValueError):
    pass


def _mac(key: bytes, payload: str) -> str:
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def sign(sig: Signature, key: bytes) -> dict:
    payload = sig.to_json()
    return {"signature": json.loads(payload), "mac": _mac(key, payload)}


def verify(message: dict, key: bytes) -> Signature:
    sig = Signature.from_dict(message["signature"])
    if not hmac.compare_digest(_mac(key, sig.to_json()), str(message.get("mac", ""))):
        raise SignatureRejected("bad MAC: message was not signed with the shared key or was altered")
    if sig.expired():
        raise SignatureRejected("signature expired")
    return sig


class SignatureRegistry:
    """Signed, revocable store of active signatures.

    Args:
        key: shared secret bytes; defaults to the ``ANTIVENOM_KEY`` environment variable.
        path: optional JSON file for persistence (shared between local agents).
    """

    def __init__(self, key: bytes | None = None, path: str | os.PathLike | None = None):
        k = key if key is not None else os.environ.get("ANTIVENOM_KEY", "").encode()
        if not k:
            raise ValueError("a shared key is required (pass key= or set ANTIVENOM_KEY)")
        self.key, self.path = k, Path(path) if path else None
        self._lock = threading.Lock()
        self._msgs: dict[str, dict] = {}
        self._revoked: set[str] = set()
        if self.path and self.path.exists():
            d = json.loads(self.path.read_text())
            self._msgs, self._revoked = d.get("messages", {}), set(d.get("revoked", []))

    def _save(self):
        if self.path:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"messages": self._msgs, "revoked": sorted(self._revoked)}))
            tmp.replace(self.path)

    def publish(self, sig: Signature) -> dict:
        msg = sign(sig, self.key)
        with self._lock:
            self._msgs[sig.id] = msg
            self._save()
        return msg

    def ingest(self, message: dict) -> Signature:
        """Accept a signed message received over any transport."""
        sig = verify(message, self.key)
        if sig.id in self._revoked:
            raise SignatureRejected("signature was revoked")
        with self._lock:
            self._msgs[sig.id] = message
            self._save()
        return sig

    def revoke(self, sig_id: str) -> None:
        with self._lock:
            self._revoked.add(sig_id)
            self._msgs.pop(sig_id, None)
            self._save()

    def active(self) -> list[Signature]:
        out = []
        for sid, msg in list(self._msgs.items()):
            if sid in self._revoked:
                continue
            try:
                out.append(verify(msg, self.key))
            except SignatureRejected:
                continue
        return out

    def export(self) -> list[dict]:
        return [m for sid, m in self._msgs.items() if sid not in self._revoked]

    def refresh(self) -> list[Signature]:
        """Reload from the shared file (to pick up other agents' publications)."""
        if self.path and self.path.exists():
            with self._lock:
                d = json.loads(self.path.read_text())
                self._msgs, self._revoked = d.get("messages", {}), set(d.get("revoked", []))
        return self.active()
