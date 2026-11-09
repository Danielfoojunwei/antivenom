"""Optional second recogniser: the reader's own attention.

Needs model internals, so it only works with locally hosted open models.
``slot_corrected_z`` turns raw per-passage attention masses into the
slot-corrected z-scores the Defender expects; ``mlx_attention`` builds a
ready-made provider for Apple-silicon MLX models using the research code
(``antivenom.masked``), when it is installed.

For closed models, pass any other per-passage influence score instead
(for example the drop in the false answer's log-probability when a passage
is removed), standardised within the context.
"""
from __future__ import annotations

from typing import Callable, Sequence

# Slot offsets fitted on clean calibration contexts (Qwen2.5-7B, layer 21, top-10).
QWEN_SLOT_OFFSETS = [0.596, -0.097, -0.214, -0.337, 0.235, 0.135, -0.432, -0.323, -0.187, 0.624]


def _z(v: Sequence[float]) -> list[float]:
    n = len(v)
    if n == 0:
        return []
    m = sum(v) / n
    sd = (sum((x - m) ** 2 for x in v) / n) ** 0.5
    return [(x - m) / (sd + 1e-9) for x in v]


def slot_corrected_z(masses: Sequence[float], offsets: Sequence[float] | None = QWEN_SLOT_OFFSETS) -> list[float]:
    z = _z(masses)
    if offsets:
        z = [x - (offsets[i] if i < len(offsets) else 0.0) for i, x in enumerate(z)]
    return _z(z)


def mlx_attention(model_id: str = "mlx-community/Qwen2.5-7B-Instruct-4bit", layer: int = 21, tail: int = 8,
                  prompt_fn: Callable[[str, Sequence[str]], str] | None = None):
    """Provider for ``Defender(attention=...)`` using a local MLX model."""
    from antivenom.llm import LocalLLM          # research package (optional dependency)
    from antivenom.masked import attention_rows, token_spans
    from antivenom.qa import wrap_prompt
    llm = LocalLLM(model_id)
    hf = llm.tok._tokenizer
    build = prompt_fn or wrap_prompt

    def fn(query: str, passages: Sequence[str]) -> list[float]:
        text = llm.tok.apply_chat_template([{"role": "user", "content": build(query, list(passages))}],
                                           add_generation_prompt=True, tokenize=False)
        ids, spans = token_spans(hf, text, list(passages))
        a = attention_rows(llm.model, ids, list(range(len(ids) - tail, len(ids))), [layer])[layer].mean(axis=(0, 1))
        return slot_corrected_z([float(a[s:e].mean()) for s, e in spans])
    return fn
