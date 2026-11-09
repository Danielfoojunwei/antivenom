"""Pre-registered confirmatory analysis of E29 (tier 2), per dataset and pooled.
Primary family (Holm): (1) clean passages removed at matched poison recall,
ours (v2 avidity score, threshold moved to CoordGuard's recall) vs CoordGuard AF;
(2) defended-clean accuracy, ours primary (v1) vs CoordGuard AF+refill.
(3) endorsement vs CoordGuard AF+refill and TrustRAG: paired CIs, no NI claim.
Secondary: correct under attack, v2 arms, GOLD/HIJACK/DRIFT/ABSTAIN.
Unit = target; exact McNemar; target bootstrap B=2000."""
import json
import sys

import numpy as np
from scipy.stats import binomtest

from antivenom.qa import _ABSTAIN

B = 2000
rng = np.random.default_rng(0)
sets = {d: [json.loads(l) for l in open(f"results/e29_tier2_{d}_k10.jsonl")] for d in sys.argv[1:] or ("hotpotqa", "msmarco")}
sets["pooled"] = [r for v in list(sets.values()) for r in v] if len(sets) > 1 else None
sets = {k: v for k, v in sets.items() if v}
ARMS = ["clean", "attack", "v1_block", "v1_delete_backfill", "v2_delete_backfill", "random_delete_backfill",
        "lowrel_delete_backfill", "coordguard_af", "coordguard_af_refill", "trustrag", "defclean_v1", "defclean_v2", "defclean_coordguard"]


def boot(f, R):
    idx = rng.integers(0, len(R), (B, len(R)))
    return np.array([f([R[i] for i in b]) for b in idx])


def ci(v):
    return f"[{np.percentile(v, 2.5):.3f}, {np.percentile(v, 97.5):.3f}]"


def mcn(R, a, b, k):
    x = sum(r[a][k] and not r[b][k] for r in R); y = sum(r[b][k] and not r[a][k] for r in R)
    return x, y, (binomtest(x, x + y).pvalue if x + y else 1.0)


def passages(R):
    out = []
    for r in R:
        cg = set(r["coordguard_removed"])
        for i, l in enumerate(r["labels"]):
            if l != "captured":
                out.append((l == "poison", r["avidity_v2"][i], i in cg, i in set(r["flags_v1"])))
    return out


def claim1(R):
    P = passages(R)
    lab = np.array([p[0] for p in P]); s = np.array([p[1] for p in P]); cg = np.array([p[2] for p in P])
    rec_cg = cg[lab].mean()
    thr = np.quantile(s[lab], 1 - rec_cg)
    ours = s >= thr
    return cg[~lab].mean() - ours[~lab].mean(), rec_cg, cg[~lab].mean(), ours[lab].mean(), ours[~lab].mean()


def decomp(R, a):
    g = h = ab = dr = 0
    for r in R:
        x = r[a]
        if x["endorsed"]: h += 1
        elif x["correct"]: g += 1
        elif _ABSTAIN.search(x["resp"]): ab += 1
        else: dr += 1
    n = len(R); return f"GOLD {g/n:.2f} HIJACK {h/n:.2f} ABSTAIN {ab/n:.2f} DRIFT {dr/n:.2f}"


for name, R in sets.items():
    print(f"\n==================== {name}  n={len(R)} targets")
    print("  arm                       endorsed [95% CI]          correct [95% CI]")
    for a in ARMS:
        e = boot(lambda S: np.mean([r[a]["endorsed"] for r in S]), R); c = boot(lambda S: np.mean([r[a]["correct"] for r in S]), R)
        print(f"  {a:24s} {np.mean([r[a]['endorsed'] for r in R]):.2f} {ci(e)}   {np.mean([r[a]['correct'] for r in R]):.2f} {ci(c)}")
    d, rc, cgc, orc, occ = claim1(R)
    bd = boot(lambda S: claim1(S)[0], R)
    p1 = min(1.0, 2 * min((bd <= 0).mean(), (bd >= 0).mean()))
    print(f"\n  CLAIM 1 clean removed at matched recall: CoordGuard recall {rc:.3f} clean removed {cgc:.3f} | ours recall {orc:.3f} clean removed {occ:.3f}")
    print(f"          difference (CG - ours) {d:.3f} {ci(bd)}  bootstrap p={p1:.4f}")
    x, y, p2 = mcn(R, "defclean_v1", "defclean_coordguard", "correct")
    print(f"  CLAIM 2 defended-clean correct: ours v1 {np.mean([r['defclean_v1']['correct'] for r in R]):.2f} vs CG {np.mean([r['defclean_coordguard']['correct'] for r in R]):.2f} (discordant {x}/{y}) McNemar p={p2:.4f}")
    ps = sorted([(p1, "claim1"), (p2, "claim2")])
    holm = {ps[0][1]: min(1, ps[0][0] * 2), ps[1][1]: min(1, max(ps[0][0] * 2, ps[1][0]))}
    print(f"          Holm-adjusted: claim1 p={holm['claim1']:.4f}  claim2 p={holm['claim2']:.4f}")
    for b in ("coordguard_af_refill", "trustrag"):
        diff = boot(lambda S: np.mean([r["v1_delete_backfill"]["endorsed"] - r[b]["endorsed"] for r in S]), R)
        x, y, p = mcn(R, "v1_delete_backfill", b, "endorsed")
        print(f"  CLAIM 3 endorsed ours v1 - {b}: {np.mean([r['v1_delete_backfill']['endorsed'] - r[b]['endorsed'] for r in R]):+.3f} {ci(diff)} (McNemar {x}/{y} p={p:.3f})")
    print("\n  secondary (no multiplicity control):")
    for a, b in (("v1_delete_backfill", "coordguard_af_refill"), ("v2_delete_backfill", "coordguard_af_refill"), ("v1_delete_backfill", "trustrag"),
                 ("v2_delete_backfill", "trustrag"), ("v2_delete_backfill", "v1_delete_backfill"), ("defclean_v2", "defclean_coordguard")):
        for k in ("endorsed", "correct"):
            x, y, p = mcn(R, a, b, k)
            print(f"    {a} vs {b} {k}: {x}/{y} p={p:.3f}")
    P = passages(R); lab = np.array([p[0] for p in P])
    v1 = np.array([p[3] for p in P]); v2 = np.array([p[1] >= json.load(open('results/v2_calibration.json'))['threshold'] for p in P])
    print(f"    detection at deployed points: v1 recall {v1[lab].mean():.3f} clean removed {v1[~lab].mean():.3f} | v2 recall {v2[lab].mean():.3f} clean removed {v2[~lab].mean():.3f}")
    for a in ("attack", "v1_delete_backfill", "v2_delete_backfill", "coordguard_af_refill", "trustrag", "defclean_v1", "defclean_coordguard"):
        print(f"    {a:22s} {decomp(R, a)}")
