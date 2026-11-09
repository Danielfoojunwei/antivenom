"""Fit the frozen v2 avidity model and operating point on NQ 1-20 only:
features [logit(entailment), debiased attention z] (E27 offsets, re-z-scored),
threshold = 95th percentile of clean-passage scores (5% clean removal)."""
import json, re
import numpy as np
from sklearn.linear_model import LogisticRegression
YN = re.compile(r"^(are|is|was|were|do|does|did|can|could|has|have|had|will|would|should)\b", re.I)
off = np.array(json.load(open("results/e27_position_debias.json"))["offsets"])
def zf(v): v = np.array(v, float); return (v - v.mean()) / (v.std() + 1e-9)
def lg(p): p = np.clip(np.array(p, float), 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
ent = [json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")][:20]
att = {json.loads(l)["id"]: json.loads(l) for l in open("results/e11c_attention_scores_nq_k10.jsonl")}
X, y, yn = [], [], 0
for r in ent:
    yn += bool(YN.match(r["question_extracted"].strip()))
    a = zf(zf(att[r["id"]]["attn"]["21"]["per_token"]) - off[:len(r["labels"])])
    for j, l in enumerate(r["labels"]):
        if l != "captured": X.append([lg(r["entail_qa"][j])[()], a[j]]); y.append(l == "poison")
X, y = np.array(X), np.array(y)
m = LogisticRegression().fit(X, y)
s = m.predict_proba(X)[:, 1]
thr = float(np.quantile(s[~y], 0.95))
res = {"coef": m.coef_[0].tolist(), "intercept": float(m.intercept_[0]), "threshold": thr,
       "cal_recall": float((s[y] >= thr).mean()), "cal_clean_removed": float((s[~y] >= thr).mean()), "yesno_targets_in_cal": yn}
print(json.dumps(res, indent=1)); json.dump(res, open("results/v2_calibration.json", "w"), indent=1)
