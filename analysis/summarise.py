"""Per-arm rates with 95% bootstrap intervals, and exact McNemar tests
between paired arms. Usage: python analysis/summarise.py RESULTS.jsonl"""
import json
import sys
from math import comb

import numpy as np

rows = [json.loads(line) for line in open(sys.argv[1])]
rng = np.random.default_rng(0)


def interval(values):
    v = np.array(values, dtype=float)
    boots = rng.choice(v, size=(5000, len(v))).mean(axis=1)
    return v.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5)


def mcnemar(a, b):
    only_a = sum(x and not y for x, y in zip(a, b))
    only_b = sum(y and not x for x, y in zip(a, b))
    m = only_a + only_b
    if m == 0:
        return 1.0
    tail = sum(comb(m, i) for i in range(min(only_a, only_b) + 1)) / 2 ** m
    return min(1.0, 2 * tail)


arms = []
for r in rows:
    for name in r["arms"]:
        if name not in arms:
            arms.append(name)

print(f"n = {len(rows)} targets\n")
print(f"{'arm':22s}{'n':>4s}   {'endorsed [95% CI]':24s}{'correct [95% CI]':24s}{'substring':>10s}")
for name in arms:
    got = [r["arms"][name] for r in rows if name in r["arms"]]
    e = interval([g["endorsed"] for g in got])
    c = interval([g["correct"] for g in got])
    s = np.mean([g["poisoned"] for g in got])
    print(f"{name:22s}{len(got):4d}   {e[0]:.2f} [{e[1]:.2f}, {e[2]:.2f}]        "
          f"{c[0]:.2f} [{c[1]:.2f}, {c[2]:.2f}]        {s:9.2f}")

pairs = [("attack", "bestx5"), ("attack", "flagx5"), ("flagx5", "flag_noanchor_x5"),
         ("bestx5", "del_neigh_0.75"), ("flagx1", "flagx5"), ("clean", "clean+bestx5")]
print("\nExact McNemar, paired over targets that have both arms")
for a, b in pairs:
    both = [r for r in rows if a in r["arms"] and b in r["arms"]]
    for metric in ("endorsed", "correct"):
        p = mcnemar([r["arms"][a][metric] for r in both], [r["arms"][b][metric] for r in both])
        print(f"  {a:>16s} vs {b:<18s} {metric:9s} n={len(both):3d}  p={p:.2g}")
