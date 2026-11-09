"""Choose the NLI hypothesis phrasing and threshold on targets 1-20 only,
then report held-out flag quality on targets 21-100 and save the flags.

Selection rule (fixed before looking at the test split): maximise F1 on the
non-captured poisons subject to clean false-positive rate <= 5%."""
import json

import numpy as np

rows = [json.loads(line) for line in open("results/e11a_flag_scores_nq_k10.jsonl")]
cal, test = rows[:20], rows[20:]
variants = [k[len("entail_"):] for k in rows[0] if k.startswith("entail_")]
taus = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]


def stats(rs, var, tau):
    tp = fp = fn = tn = cap_hit = cap_n = 0
    for r in rs:
        for lab, s in zip(r["labels"], r[f"entail_{var}"]):
            hit = s >= tau
            if lab == "captured":
                cap_hit += hit
                cap_n += 1
            elif lab == "poison":
                tp += hit
                fn += not hit
            else:
                fp += hit
                tn += not hit
    p = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    return {"precision": p, "recall": rec, "f1": 2 * p * rec / max(1e-9, p + rec),
            "clean_fpr": fp / max(1, fp + tn), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "captured_hit": cap_hit, "captured_n": cap_n}


best = None
print("calibration split (targets 1-20)")
for var in variants:
    for tau in taus:
        s = stats(cal, var, tau)
        if s["clean_fpr"] <= 0.05 and (best is None or s["f1"] > best[2]["f1"]):
            best = (var, tau, s)
    for tau in taus:
        s = stats(cal, var, tau)
        print(f"  {var:8s} tau={tau:<6} P={s['precision']:.3f} R={s['recall']:.3f} F1={s['f1']:.3f} FPR={s['clean_fpr']:.3f}")
var, tau, _ = best
print(f"\nchosen: hypothesis={var} tau={tau}")
s = stats(test, var, tau)
print(f"HELD-OUT (targets 21-100): precision={s['precision']:.3f} recall={s['recall']:.3f} "
      f"clean-FPR={s['clean_fpr']:.4f} TP={s['tp']} FP={s['fp']} FN={s['fn']} TN={s['tn']} "
      f"captured flagged {s['captured_hit']}/{s['captured_n']}")

flags = {r["id"]: [i for i, x in enumerate(r[f"entail_{var}"]) if x >= tau] for r in rows}
json.dump({"hypothesis": var, "tau": tau, "flags": flags}, open("results/e11a_chosen_flags.json", "w"))
print("saved results/e11a_chosen_flags.json")
print("\nsensitivity on HELD-OUT for the chosen phrasing (not used for selection):")
for t2 in taus:
    h = stats(test, var, t2)
    print(f"  tau={t2:<6} P={h['precision']:.3f} R={h['recall']:.3f} FPR={h['clean_fpr']:.4f}")
