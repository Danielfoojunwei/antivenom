"""E24 (CPU only): passage-level detection on confirmatory tier 1 (HotpotQA,
MS-MARCO 1-50), ours vs CoordGuard on identical contexts.

Ours: the avidity logistic model (entailment logit, attention z), fitted on NQ
1-20 only and frozen, applied to the stored E15 signals. Also the frozen v1 OR
flags. CoordGuard: AF audit (e5-large-v2, CPU) on the same rebuilt top-10.
Contexts are rebuilt deterministically (released clean scores + Contriever
poison scores); labels are checked against E15's stored labels.
Recall counts all poisons; comparisons are at matched clean-removal rate.
"""
import json

import numpy as np
from sklearn.linear_model import LogisticRegression

from antivenom.baselines.coordguard import audit
from antivenom.poisonedrag import load
from antivenom.retriever import Contriever


def z(v):
    v = np.array(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-9)


def feats(entail, attz):
    e = np.clip(np.array(entail), 1e-6, 1 - 1e-6)
    return np.stack([np.log(e / (1 - e)), np.array(attz)], 1)


# frozen avidity model, NQ 1-20
ent = [json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
att = {json.loads(l)["id"]: json.loads(l) for l in open("results/e11c_attention_scores_nq_k10.jsonl")}
X, y = [], []
for r in ent[:20]:
    F = feats(r["entail_qa"], z(att[r["id"]]["attn"]["21"]["per_token"]))
    for j, lab in enumerate(r["labels"]):
        if lab != "captured":
            X.append(F[j]); y.append(lab == "poison")
model = LogisticRegression().fit(np.array(X), np.array(y))
print("frozen avidity coefficients", np.round(model.coef_[0], 3), flush=True)

R = Contriever()
out = []
for d in ("hotpotqa", "msmarco"):
    targets, corpus = load(d)
    by = {t.id: t for t in targets}
    rel = json.load(open(f"data/external/poisonedrag/{d}-contriever.json"))
    rows = [json.loads(l) for l in open(f"results/rescored/e15_cross_dataset_{d}_k10.jsonl")]
    S_ours, S_or, CG, LAB, mism = [], [], [], [], 0
    for r in rows:
        t = by[r["id"]]
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], rel[t.id][i], "clean") for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), "captured" if j == 0 else "poison") for j, (p, v) in enumerate(zip(t.poison, R.encode(t.poison)))]
        top = sorted(pool, key=lambda x: -x[1])[:10]
        if [c[2] for c in top] != r["labels"]:
            mism += 1
            continue
        comp, _ = audit(t.question, [c[0] for c in top])
        s = model.predict_proba(feats(r["entail"], r["attn_z"]))[:, 1]
        for j, lab in enumerate(r["labels"]):
            S_ours.append(s[j]); S_or.append(j in set(r["flags_OR"])); CG.append(j in set(comp)); LAB.append(lab != "clean")
        print(d, r["id"], flush=True)
    S_ours, S_or, CG, LAB = map(np.array, (S_ours, S_or, CG, LAB))
    rec = lambda f: f[LAB].mean()
    fpr = lambda f: f[~LAB].mean()
    thr = np.quantile(S_ours[~LAB], 1 - fpr(CG))
    av_at_cg = S_ours >= thr
    thr_r = np.quantile(S_ours[LAB], 1 - rec(CG))
    av_at_cgrec = S_ours >= thr_r
    res = {"dataset": d, "n_targets": len(rows) - mism, "context_mismatch": mism,
           "coordguard": {"recall": rec(CG), "clean_removed": fpr(CG)},
           "ours_OR_v1": {"recall": rec(S_or), "clean_removed": fpr(S_or)},
           "ours_avidity_at_CG_clean_rate": {"recall": rec(av_at_cg), "clean_removed": fpr(av_at_cg)},
           "ours_avidity_at_CG_recall": {"recall": rec(av_at_cgrec), "clean_removed": fpr(av_at_cgrec)}}
    out.append(res)
    print(json.dumps(res, indent=1), flush=True)
json.dump(out, open("results/e24_detection_confirm.json", "w"), indent=1)
