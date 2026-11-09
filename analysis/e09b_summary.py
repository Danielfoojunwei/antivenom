"""Summarise E09b: endorsed / correct rates per condition with bootstrap
intervals, plus exact McNemar tests between paired conditions."""
import json
import sys
from math import comb

import numpy as np

rows = [json.loads(line) for line in open(sys.argv[1] if len(sys.argv) > 1 else "results/e09b_blockade_generation_nq_k10.jsonl")]
rng = np.random.default_rng(0)
conds = [k for k, v in rows[0].items() if isinstance(v, dict)]


def rate(vals):
    v = np.array(vals, dtype=float)
    b = rng.choice(v, size=(5000, len(v))).mean(axis=1)
    return f"{v.mean():.2f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]"


def mcnemar(a, b):
    only_a = sum(x and not y for x, y in zip(a, b))
    only_b = sum(y and not x for x, y in zip(a, b))
    m = only_a + only_b
    if m == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(m, i) for i in range(min(only_a, only_b) + 1)) / 2 ** m)


print(f"n = {len(rows)}; mean poison passages in top-k = {np.mean([r['n_poison'] for r in rows]):.2f}; "
      f"mean control passages blocked = {np.mean([r['n_control_blocked'] for r in rows]):.2f}\n")
print(f"{'condition':28s}{'endorsed [95% CI]':24s}{'correct [95% CI]':24s}")
for c in conds:
    print(f"{c:28s}{rate([r[c]['endorsed'] for r in rows]):24s}{rate([r[c]['correct'] for r in rows]):24s}")

print("\nExact McNemar (paired over targets)")
for a, b in [("attack", "block_poison_-5"), ("block_random_clean_-5", "block_poison_-5"),
             ("clean", "block_poison_-5"), ("attack", "block_random_clean_-5"),
             ("block_poison_-5", "block_poison_-10000")]:
    for m in ("endorsed", "correct"):
        p = mcnemar([r[a][m] for r in rows], [r[b][m] for r in rows])
        print(f"  {a:>24s} vs {b:<22s} {m:9s} p={p:.2g}")
