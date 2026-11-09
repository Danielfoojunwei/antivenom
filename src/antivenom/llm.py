"""Local LLM backend (MLX). Real model weights, real inference; no stubs.

Two entry points:
  * ``generate``      -- free-text generation (ReAct decisions, record writing).
  * ``option_logprobs`` -- exact log-probability of each candidate continuation
    after a fixed assistant prefix. Used to read the agent's full tool
    distribution pi(t | s, M) instead of a single sampled choice.
"""
from __future__ import annotations

import functools
import math
from dataclasses import dataclass

import mlx.core as mx
from mlx_lm import generate as _mlx_generate
from mlx_lm import load as _mlx_load
from mlx_lm.sample_utils import make_sampler

DEFAULT_MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"


@functools.lru_cache(maxsize=2)
def _load(model_id: str):
    return _mlx_load(model_id)


@dataclass
class LocalLLM:
    model_id: str = DEFAULT_MODEL

    def __post_init__(self):
        self.model, self.tok = _load(self.model_id)

    def _prompt(self, messages: list[dict], assistant_prefix: str = "") -> str:
        p = self.tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        return p + assistant_prefix

    def generate(self, messages: list[dict], *, temp: float = 0.0, top_p: float = 0.0,
                 max_tokens: int = 256, seed: int | None = None,
                 assistant_prefix: str = "") -> str:
        if seed is not None:
            mx.random.seed(seed)
        sampler = make_sampler(temp=temp, top_p=top_p)
        return _mlx_generate(self.model, self.tok, prompt=self._prompt(messages, assistant_prefix),
                             max_tokens=max_tokens, sampler=sampler)

    def option_logprobs(self, messages: list[dict], options: list[str],
                        assistant_prefix: str = "") -> dict[str, float]:
        """Sum of token log-probs for each option appended after the prefix.

        The shared context is encoded once; each option is scored with a
        single forward pass over context+option.
        """
        ctx = self.tok.encode(self._prompt(messages, assistant_prefix), add_special_tokens=False)
        out: dict[str, float] = {}
        for opt in options:
            opt_ids = self.tok.encode(opt, add_special_tokens=False)
            ids = mx.array([ctx + opt_ids])
            logits = self.model(ids)[0]  # (T, V)
            logp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
            # token at position i is predicted by logits at i-1
            pos = mx.arange(len(ctx) - 1, len(ctx) + len(opt_ids) - 1)
            tgt = mx.array(opt_ids)
            out[opt] = float(logp[pos, tgt].sum().item())
        return out


def normalise(logps: dict[str, float]) -> dict[str, float]:
    m = max(logps.values())
    z = sum(math.exp(v - m) for v in logps.values())
    return {k: math.exp(v - m) / z for k, v in logps.items()}
