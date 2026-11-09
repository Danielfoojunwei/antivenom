"""E19 vs our arms on identical NQ development targets and contexts.

Joins re-scored E19 (TrustRAG, RobustRAG keyword, CoordGuard AF / AF+refill)
with re-scored E12 (attack, clean, block_OR, delete_OR, delete_OR_backfill).
Reports endorsed / correct with bootstrap CIs, exact McNemar vs our arms, and
a passage-level detection comparison: CoordGuard's removed component vs our
OR flags (true poisons removed, clean passages removed)."""
import json
from math import comb

import numpy as np

e19 = {json.loads(l)["id"]: json.loads(l) for l in open("results/rescored/e19_baselines_nq_k10.jsonl")}
e12 = {json.loads(l)["id"]: json.loads(l) for l in open("results/rescored/e12_combined_and_deletion_nq_k10.jsonl")}
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
labels = {json.loads(l)["id"]: json.loads(l)["labels"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")}
or_flags = json.load(open("results/e11c_combined_flags.json"))["OR"]
ids = [i for i in order[20:] if i in e19 and i in e12]
rng = np.random.default_rng(0)

rows = []
for i in ids:
    r = {k: e12[i][k] for k in ("clean", "attack", "block_OR", "delete_OR", "delete_OR_backfill")}
    r.update({k: e19[i][k] for k in ("trustrag", "robustrag_keyword", "coordguard_af", "coordguard_af_refill")})
    rows.append(r)


def rate(v):
    v = np.array(v, dtype=float)
    b = rng.choice(v, size=(5000, len(v))).mean(axis=1)
    return f"{v.mean():.2f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]"


def mcnemar(a, b):
    x = sum(p and not q for p, q in zip(a, b))
    y = sum(q and not p for p, q in zip(a, b))
    m = x + y
    return 1.0 if m == 0 else min(1.0, 2 * sum(comb(m, k) for k in range(min(x, y) + 1)) / 2 ** m)


print(f"E19 vs ours, NQ DEVELOPMENT set, identical contexts, n={len(rows)}")
print(f"  {'arm':22s}{'endorsed [95% CI]':24s}{'correct [95% CI]':24s}")
for a in rows[0]:
    print(f"  {a:22s}{rate([r[a]['endorsed'] for r in rows]):24s}{rate([r[a]['correct'] for r in rows]):24s}")
for ours in ("delete_OR_backfill", "block_OR"):
    for base in ("trustrag", "robustrag_keyword", "coordguard_af", "coordguard_af_refill"):
        pe = mcnemar([r[ours]["endorsed"] for r in rows], [r[base]["endorsed"] for r in rows])
        pc = mcnemar([r[ours]["correct"] for r in rows], [r[base]["correct"] for r in rows])
        print(f"  McNemar {ours} vs {base}: endorsed p={pe:.2g}  correct p={pc:.2g}")

tp_cg = fp_cg = tp_or = fp_or = n_poison = n_clean = 0
for i in ids:
    lab = labels[i]
    pois = {k for k, l in enumerate(lab) if l != "clean"}
    clean = set(range(len(lab))) - pois
    cg = set(e19[i]["coordguard_af"]["removed"])
    ours = set(or_flags[i])
    n_poison += len(pois)
    n_clean += len(clean)
    tp_cg += len(cg & pois)
    fp_cg += len(cg & clean)
    tp_or += len(ours & pois)
    fp_or += len(ours & clean)
print(f"\nDetection on the same contexts (all poisons incl. captured; n_poison={n_poison}, n_clean={n_clean}):")
print(f"  CoordGuard AF removed: poison recall={tp_cg / n_poison:.3f} clean removed={fp_cg / n_clean:.3f}")
print(f"  ours (OR flags)      : poison recall={tp_or / n_poison:.3f} clean removed={fp_or / n_clean:.3f}")
