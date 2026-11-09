"""Three structural defences, all operating on a retrieved passage set.

1. ``neff_answer``   -- co-stimulation: pick the answer with the largest
   effective number of independent supporting passages,
   n_eff = (sum s)^2 / sum_ij s_i s_j rho_ij.
2. ``complement``    -- personalised PageRank from a captured sample over the
   passage similarity graph; down-weights retrieval scores (no deletion).
3. ``danger``        -- Herfindahl concentration of cluster-level
   leave-out influence on the model's answer.
"""
from __future__ import annotations

import numpy as np

from .poisonedrag import clean_str
from .qa import wrap_prompt


def sim_matrix(vecs: np.ndarray) -> np.ndarray:
    v = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    return np.clip(v @ v.T, 0.0, 1.0)


def excess(rho: np.ndarray, rho0: float) -> np.ndarray:
    """Similarity beyond the topical baseline rho0; diagonal stays 1."""
    r = np.clip((rho - rho0) / (1 - rho0), 0.0, 1.0)
    np.fill_diagonal(r, 1.0)
    return r


def neff(s: np.ndarray, rho: np.ndarray) -> float:
    den = float(s @ rho @ s)
    return float(s.sum() ** 2 / den) if den > 0 else 0.0


def _ask(llm, q, ctx, max_tokens=32):
    return llm.generate([{"role": "user", "content": wrap_prompt(q, ctx)}], temp=0.0,
                        max_tokens=max_tokens).strip()


def _key(ans: str) -> str:
    a = clean_str(ans)
    return "" if a.startswith("i don") or not a else a


def neff_answer(llm, q, passages, rho):
    """Isolate each passage, group identical answers, rank groups by n_eff
    (and, for the ablation, by raw count)."""
    answers = [_ask(llm, q, [p]) for p in passages]
    groups: dict[str, list[int]] = {}
    for i, a in enumerate(answers):
        k = _key(a)
        if k:
            groups.setdefault(k, []).append(i)
    stats = {}
    for k, idx in groups.items():
        s = np.zeros(len(passages)); s[idx] = 1.0
        stats[k] = {"count": len(idx), "neff": neff(s, rho), "text": answers[idx[0]]}
    by_neff = max(stats.values(), key=lambda d: (d["neff"], d["count"]))["text"] if stats else "I don't know."
    by_count = max(stats.values(), key=lambda d: (d["count"], d["neff"]))["text"] if stats else "I don't know."
    return {"by_neff": by_neff, "by_count": by_count, "answers": answers,
            "groups": {k: {"count": v["count"], "neff": round(v["neff"], 3)} for k, v in stats.items()}}


def complement(rho: np.ndarray, seed: int, beta: float = 0.85) -> np.ndarray:
    W = rho.copy(); np.fill_diagonal(W, 0.0)
    W = W / np.maximum(W.sum(1, keepdims=True), 1e-9)
    e = np.zeros(len(rho)); e[seed] = 1.0
    return (1 - beta) * np.linalg.solve(np.eye(len(rho)) - beta * W.T, e)


def clusters(rho: np.ndarray, tau: float) -> list[list[int]]:
    n, lab = len(rho), list(range(len(rho)))
    def find(x):
        while lab[x] != x:
            lab[x] = lab[lab[x]]; x = lab[x]
        return x
    for i in range(n):
        for j in range(i + 1, n):
            if rho[i, j] >= tau:
                lab[find(i)] = find(j)
    out: dict[int, list[int]] = {}
    for i in range(n):
        out.setdefault(find(i), []).append(i)
    return list(out.values())


def danger(llm, q, passages, rho, tau: float = 0.8):
    """Cluster-level leave-out influence on the base answer's log-prob."""
    base = _ask(llm, q, passages)
    msgs = lambda ctx: [{"role": "user", "content": wrap_prompt(q, ctx)}]
    lp0 = llm.option_logprobs(msgs(passages), [base])[base]
    cl = clusters(rho, tau)
    deltas = []
    for c in cl:
        rest = [p for i, p in enumerate(passages) if i not in c]
        lp = llm.option_logprobs(msgs(rest or ["(no context)"]), [base])[base]
        deltas.append(max(0.0, lp0 - lp))
    tot = sum(deltas)
    D = float(sum(d * d for d in deltas) / tot ** 2) if tot > 0 else 0.0
    top = int(np.argmax(deltas)) if deltas else -1
    return {"base": base, "D": D, "deltas": [round(d, 3) for d in deltas],
            "clusters": cl, "top_cluster": cl[top] if top >= 0 else []}
