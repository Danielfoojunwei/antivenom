"""Fidelity: our Contriever reproduces PoisonedRAG's released retrieval scores.

For every dataset and every one of its 100 targets, encode the question and
its released clean top-3 passages (title + " " + text) and compare our dot
products with the released scores. Writes results/fidelity/retriever.txt.
CPU only.
"""
import json
from pathlib import Path

import numpy as np

from antivenom.poisonedrag import load
from antivenom.retriever import Contriever

R = Contriever()
lines = []
for d in ("nq", "hotpotqa", "msmarco"):
    targets, corpus = load(d)
    released = json.load(open(f"data/external/poisonedrag/{d}-contriever.json"))
    diffs = []
    for t in targets:
        ids = t.clean_ids[:3]
        q = R.encode([t.question])[0]
        ours = R.encode([corpus[i]["title"] + " " + corpus[i]["text"] for i in ids]) @ q
        diffs += list(np.abs(ours - np.array([released[t.id][i] for i in ids])))
    diffs = np.array(diffs)
    lines.append(f"{d}: n_pairs={len(diffs)} max_abs_diff={diffs.max():.2e} mean_abs_diff={diffs.mean():.2e} "
                 f"share_within_1e-3={np.mean(diffs < 1e-3):.3f}")
    print(lines[-1], flush=True)
Path("results/fidelity").mkdir(parents=True, exist_ok=True)
Path("results/fidelity/retriever.txt").write_text("\n".join(lines) + "\n")
