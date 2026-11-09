"""Dense retriever.

``Contriever`` reproduces PoisonedRAG's retriever (facebook/contriever,
average pooling, dot-product score); passages are encoded as title + " " +
text, which matches the released scores (tests/fidelity_retriever.py).
"""
from __future__ import annotations

import functools

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

# Torch's default CPU thread pool contended with MLX in our runs on Apple
# silicon; a single thread removed the slowdown we observed.
torch.set_num_threads(1)


@functools.lru_cache(maxsize=2)
def _load(name: str):
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModel.from_pretrained(name).eval()
    return tok, model


class Contriever:
    name = "facebook/contriever"
    score = "dot"

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        tok, model = _load(self.name)
        out = []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                enc = tok(texts[i:i + batch_size], padding=True, truncation=True,
                          max_length=512, return_tensors="pt")
                h = model(**enc).last_hidden_state
                mask = enc["attention_mask"].unsqueeze(-1).float()
                out.append(((h * mask).sum(1) / mask.sum(1)).numpy())
        return np.concatenate(out) if out else np.zeros((0, 768), dtype=np.float32)
