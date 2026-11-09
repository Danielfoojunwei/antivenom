"""E15 confirmatory detection quality: flags frozen at NQ settings, scored on
HotpotQA / MS-MARCO. Recall excludes the captured sample (poison[0]); the
captured hit rate is reported separately.
Usage: python analysis/e15_detection.py results/e15_cross_dataset_hotpotqa_k10.jsonl"""
import json
import sys

for path in sys.argv[1:]:
    rows = [json.loads(l) for l in open(path)]
    print(f"{path}  [CONFIRMATORY]  n={len(rows)}")
    for name in ("flags_entail", "flags_attn", "flags_OR"):
        tp = fp = fn = tn = cap = cap_n = 0
        for r in rows:
            fl = set(r[name])
            for i, lab in enumerate(r["labels"]):
                hit = i in fl
                if lab == "captured":
                    cap += hit
                    cap_n += 1
                elif lab == "poison":
                    tp += hit
                    fn += not hit
                else:
                    fp += hit
                    tn += not hit
        print(f"  {name:13s} precision={tp / max(1, tp + fp):.3f} recall={tp / max(1, tp + fn):.3f} "
              f"clean-FPR={fp / max(1, fp + tn):.4f}  TP={tp} FP={fp} FN={fn} TN={tn}  captured {cap}/{cap_n}")
