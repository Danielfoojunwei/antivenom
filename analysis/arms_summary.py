"""Generic summary for experiments whose rows hold one dict per arm with
"endorsed" / "correct" (use the re-scored files in results/rescored/).

Rates with 95% percentile-bootstrap intervals (5000 resamples, seed 0) and
exact two-sided McNemar tests on paired targets.

Usage:
  python analysis/arms_summary.py FILE --label development|confirmatory \
      [--pairs a:b c:d ...] [--subset dev]
--subset dev keeps only NQ targets 21-100 (order from the E11a file).
"""
import argparse
import json
from math import comb

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("file")
ap.add_argument("--label", required=True, choices=["development", "confirmatory"])
ap.add_argument("--pairs", nargs="*", default=[])
ap.add_argument("--subset", choices=["dev"], default=None)
args = ap.parse_args()

rows = [json.loads(l) for l in open(args.file)]
if args.subset == "dev":
    order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
    dev = set(order[20:])
    rows = [r for r in rows if r["id"] in dev]
arms = [k for k, v in rows[0].items() if isinstance(v, dict) and "endorsed" in v]
rng = np.random.default_rng(0)


def rate(v):
    v = np.array(v, dtype=float)
    b = rng.choice(v, size=(5000, len(v))).mean(axis=1)
    return f"{v.mean():.2f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]"


def mcnemar(a, b):
    x = sum(p and not q for p, q in zip(a, b))
    y = sum(q and not p for p, q in zip(a, b))
    m = x + y
    return 1.0 if m == 0 else min(1.0, 2 * sum(comb(m, i) for i in range(min(x, y) + 1)) / 2 ** m)


print(f"{args.file}  [{args.label.upper()}]  n={len(rows)}")
print(f"  {'arm':26s}{'endorsed [95% CI]':24s}{'correct [95% CI]':24s}")
for a in arms:
    print(f"  {a:26s}{rate([r[a]['endorsed'] for r in rows]):24s}{rate([r[a]['correct'] for r in rows]):24s}")
for pair in args.pairs:
    a, b = pair.split(":")
    for m in ("endorsed", "correct"):
        print(f"  McNemar {a} vs {b} {m}: p={mcnemar([r[a][m] for r in rows], [r[b][m] for r in rows]):.2g}")
