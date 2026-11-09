"""Summarise E11b. Primary split: held-out targets 21-100 (threshold and
phrasing were chosen on targets 1-20)."""
import json
import sys
from math import comb

import numpy as np

rows = [json.loads(line) for line in open(sys.argv[1] if len(sys.argv) > 1 else "results/e11b_flagged_blockade_nq_k10.jsonl")]
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
held_out_ids = set(order[20:])
rng = np.random.default_rng(0)
conds = ["clean", "attack", "oracle", "flagged_block"]


def rate(v):
    v = np.array(v, dtype=float)
    b = rng.choice(v, size=(5000, len(v))).mean(axis=1)
    return f"{v.mean():.2f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]"


def mcnemar(a, b):
    x = sum(p and not q for p, q in zip(a, b))
    y = sum(q and not p for p, q in zip(a, b))
    m = x + y
    return 1.0 if m == 0 else min(1.0, 2 * sum(comb(m, i) for i in range(min(x, y) + 1)) / 2 ** m)


for name, sub in [("HELD-OUT targets 21-100", [r for r in rows if r["id"] in held_out_ids]),
                  ("all targets", rows)]:
    if not sub:
        continue
    print(f"\n== {name}: n={len(sub)}; mean true flags {np.mean([r['n_true_flags'] for r in sub]):.2f}, "
          f"mean false flags {np.mean([r['n_false_flags'] for r in sub]):.2f}, "
          f"mean poisons in top-10 {np.mean([len(r['poison_idx']) for r in sub]):.2f}")
    print(f"  {'condition':16s}{'endorsed [95% CI]':24s}{'correct [95% CI]':24s}")
    for c in conds:
        print(f"  {c:16s}{rate([r[c]['endorsed'] for r in sub]):24s}{rate([r[c]['correct'] for r in sub]):24s}")
    for a, b in [("attack", "flagged_block"), ("oracle", "flagged_block"), ("clean", "flagged_block")]:
        for m in ("endorsed", "correct"):
            print(f"  McNemar {a:>7s} vs {b:<14s} {m:9s} p={mcnemar([r[a][m] for r in sub], [r[b][m] for r in sub]):.2g}")
    ff = [r for r in sub if r["n_false_flags"] > 0]
    if ff:
        print(f"  targets with >=1 false flag: {len(ff)}; correct oracle->flagged: "
              f"{sum(r['oracle']['correct'] for r in ff)} -> {sum(r['flagged_block']['correct'] for r in ff)}")
