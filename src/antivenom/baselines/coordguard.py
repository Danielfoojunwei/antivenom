"""CoordGuard (Li, Guo, Xu; arXiv 2610.24834), implemented from the paper.

No code is released. Implements Section 3.2 / Algorithm 1 in always-filter
(AF) mode: auditor = mean-pooled, l2-normalised e5-large-v2; W = S * min(s_q);
robust z-normalisation of off-diagonal W by median and MAD; link pairs with
Z > tau_c (tau_c = 1.0, as in the paper); connected components with >= 2
passages are candidates; remove the component maximising
Phi = D(C) * R(C, q) * log(1 + |C|).

Assumption not stated in the paper: e5 inputs use the model's documented
"query: " / "passage: " prefixes.
"""
from __future__ import annotations

import functools

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

E5 = "intfloat/e5-large-v2"
TAU_C, EPS = 1.0, 1e-8


@functools.lru_cache(maxsize=1)
def _e5():
    return AutoTokenizer.from_pretrained(E5), AutoModel.from_pretrained(E5).eval()


def _embed(texts):
    tok, model = _e5()
    with torch.no_grad():
        enc = tok(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
        h = model(**enc).last_hidden_state
        m = enc["attention_mask"].unsqueeze(-1).float()
        v = (h * m).sum(1) / m.sum(1)
    return torch.nn.functional.normalize(v, dim=-1).numpy()


def _components(adj):
    n, seen, comps = len(adj), set(), []
    for s in range(n):
        if s in seen:
            continue
        stack, comp = [s], []
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            comp.append(u)
            stack += [v for v in range(n) if adj[u][v] and v not in seen]
        comps.append(sorted(comp))
    return comps


def audit(question, docs):
    """Return (indices of C*, A(q)); ([], None) when no candidate exists."""
    q = _embed(["query: " + question])[0]
    P = _embed(["passage: " + d for d in docs])
    s_q, S = P @ q, P @ P.T
    W = S * np.minimum.outer(s_q, s_q)
    off = W[~np.eye(len(docs), dtype=bool)]
    med = np.median(off)
    mad = np.median(np.abs(off - med))
    Z = (W - med) / (mad + EPS)
    adj = (Z > TAU_C) & ~np.eye(len(docs), dtype=bool)
    cands = [c for c in _components(adj) if len(c) >= 2]
    if not cands:
        return [], None

    def phi(c):
        pairs = [S[i, j] for a, i in enumerate(c) for j in c[a + 1:]]
        return float(np.mean(pairs) * np.mean(s_q[c]) * np.log(1 + len(c)))

    best = max(cands, key=phi)
    return best, phi(best)
