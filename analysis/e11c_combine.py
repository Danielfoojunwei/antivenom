"""Combine the attention-concentration signal (E11c) with claim entailment
(E11a). Every choice (layer, normalisation, threshold) is made on targets 1-20;
results are reported on held-out targets 21-100. Recall excludes the captured
sample, as in E11a."""
import json

import numpy as np

ent = {json.loads(l)["id"]: json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")}
att = {json.loads(l)["id"]: json.loads(l) for l in open("results/e11c_attention_scores_nq_k10.jsonl")}
chosen = json.load(open("results/e11a_chosen_flags.json"))
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
ids = [i for i in order if i in att]
cal, test = [i for i in ids if i in order[:20]], [i for i in ids if i in order[20:]]
ent_flag = {i: set(chosen["flags"][i]) for i in ids}


def zscore(v):
    v = np.array(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-9)


def att_flags(i, layer, norm, tau):
    return set(np.where(zscore(att[i]["attn"][layer][norm]) >= tau)[0].tolist())


def quality(id_list, flagger):
    tp = fp = fn = tn = 0
    for i in id_list:
        flags = flagger(i)
        for j, lab in enumerate(att[i]["labels"]):
            if lab == "captured":
                continue
            hit = j in flags
            if lab == "poison":
                tp += hit
                fn += not hit
            else:
                fp += hit
                tn += not hit
    p, r = tp / max(1, tp + fp), tp / max(1, tp + fn)
    return {"P": p, "R": r, "F1": 2 * p * r / max(1e-9, p + r), "FPR": fp / max(1, fp + tn), "FP": fp, "FN": fn}


layers = list(att[ids[0]]["attn"].keys())
best = None
for layer in layers:
    for norm in ("mass", "per_token"):
        for tau in np.arange(-1.0, 2.6, 0.25):
            q = quality(cal, lambda i: att_flags(i, layer, norm, tau))
            if q["FPR"] <= 0.05 and (best is None or q["F1"] > best[3]["F1"]):
                best = (layer, norm, float(tau), q)
layer, norm, tau, qcal = best
print(f"attention signal chosen on targets 1-20: layer={layer} norm={norm} z>={tau:.2f}  "
      f"(cal P={qcal['P']:.3f} R={qcal['R']:.3f} FPR={qcal['FPR']:.3f})")

flaggers = {
    "entailment": lambda i: ent_flag[i],
    "attention": lambda i: att_flags(i, layer, norm, tau),
    "OR": lambda i: ent_flag[i] | att_flags(i, layer, norm, tau),
    "AND": lambda i: ent_flag[i] & att_flags(i, layer, norm, tau),
}
print(f"\nHELD-OUT targets 21-100 (n={len(test)})")
for name, fl in flaggers.items():
    q = quality(test, fl)
    print(f"  {name:11s} precision={q['P']:.3f} recall={q['R']:.3f} clean-FPR={q['FPR']:.4f}  FP={q['FP']} FN={q['FN']}")

json.dump({"attention": {"layer": layer, "norm": norm, "tau": tau},
           "OR": {i: sorted(flaggers["OR"](i)) for i in ids},
           "AND": {i: sorted(flaggers["AND"](i)) for i in ids}},
          open("results/e11c_combined_flags.json", "w"))
print("saved results/e11c_combined_flags.json")
print("\nattention sensitivity (chosen layer/norm), calibration vs held-out:")
for t2 in np.arange(-1.0, 1.01, 0.25):
    c = quality(cal, lambda i: att_flags(i, layer, norm, t2)); h = quality(test, lambda i: att_flags(i, layer, norm, t2))
    print(f"  z>={t2:+.2f}  cal P={c['P']:.3f} R={c['R']:.3f} FPR={c['FPR']:.3f} | held-out P={h['P']:.3f} R={h['R']:.3f} FPR={h['FPR']:.3f}")
