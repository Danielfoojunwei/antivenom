"""Residual-stream access for MLX transformer models: read and edit.

``LayerTap`` wraps one decoder block. In record mode it stores the block's
output hidden states; in steer mode it applies h <- h - alpha * (h.v) v
(projection removal along unit vector v), or any callable edit.
"""
from __future__ import annotations

import mlx.core as mx
import mlx.nn as nn


class LayerTap(nn.Module):
    def __init__(self, block):
        super().__init__()
        self.block = block
        self.record = False
        self.saved = None
        self.edit = None            # callable(h) -> h, or None

    def __call__(self, x, *args, **kwargs):
        h = self.block(x, *args, **kwargs)
        if self.record:
            self.saved = h
        if self.edit is not None:
            h = self.edit(h)
        return h


def install(model, layers: list[int]) -> dict[int, LayerTap]:
    inner = model.model
    taps = {}
    for i in layers:
        if not isinstance(inner.layers[i], LayerTap):
            inner.layers[i] = LayerTap(inner.layers[i])
        taps[i] = inner.layers[i]
    return taps


def hidden(model, tok, prompt: str, taps: dict[int, LayerTap]) -> dict[int, mx.array]:
    """Last-token hidden state at each tapped layer for ``prompt``."""
    for t in taps.values():
        t.record, t.saved = True, None
    model(mx.array([tok.encode(prompt, add_special_tokens=False)]))
    out = {i: t.saved[0, -1].astype(mx.float32) for i, t in taps.items()}
    for t in taps.values():
        t.record, t.saved = False, None
    return out


def project_out(v: mx.array, alpha: float = 1.0):
    """Edit removing alpha * component along unit v from every position."""
    v = (v / mx.linalg.norm(v)).astype(mx.float16)

    def f(h):
        coef = (h * v).sum(-1, keepdims=True)
        return h - alpha * coef * v
    return f
