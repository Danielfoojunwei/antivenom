"""Exploratory stored-context score-aware selection. Never estimates ASR."""
import json

import numpy as np
from sklearn.linear_model import LogisticRegression

from continuation_stats import interval, read_rows, save_report


def zf(v):
    v = np.asarray(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-9)


def logit(v):
    v = np.clip(v, 1e-6, 1 - 1e-6)
    return np.log(v / (1 - v))


ent = read_rows("results/e11a_flag_scores_nq_k10.jsonl")
att = {r["id"]: r for r in read_rows("results/e11c_attention_scores_nq_k10.jsonl")}
cg = {r["id"]: r for r in read_rows("results/e19_baselines_nq_k10.jsonl")}
rotation = {r["id"]: r for r in read_rows("results/e21_capture_rotation_nq_k10.jsonl")}
X, y = [], []
for r in ent[:20]:
    a = zf(att[r["id"]]["attn"]["21"]["per_token"])
    for i, label in enumerate(r["labels"]):
        if label != "captured":
            X.append([logit(r["entail_qa"][i]), a[i]])
            y.append(label == "poison")
model = LogisticRegression().fit(np.array(X), np.array(y))
scores = model.predict_proba(np.array(X))[:, 1]
threshold = float(np.quantile(scores[~np.array(y)], .95))
records = []
for r in ent[20:]:
    tid = r["id"]
    a = zf(att[tid]["attn"]["21"]["per_token"])
    e = np.array(r["entail_qa"])
    av = model.predict_proba(np.stack([logit(e), a], axis=1))[:, 1]
    assert r["labels"] == att[tid]["labels"]
    pidx = rotation[tid]["poison_index"]
    assert ["clean" if p < 0 else "captured" if p == 0 else "poison" for p in pidx] == r["labels"]
    flags = {"entailment": e >= .01, "attention": a >= 0,
             "OR": (e >= .01) | (a >= 0), "avidity": av >= threshold,
             "coordguard": np.isin(np.arange(10), cg[tid]["coordguard_af"]["removed"])}
    score = {"entailment": e, "attention": a, "OR": flags["OR"].astype(float),
             "avidity": av, "coordguard": flags["coordguard"].astype(float)}
    poison = [i for i, l in enumerate(r["labels"]) if l == "poison"]
    clean = [i for i, l in enumerate(r["labels"]) if l == "clean"]
    record = {"id": tid, "n_unseen_poison": len(poison), "detectors": {}, "worst_capture": {}}
    for name, f in flags.items():
        ordered = sorted(poison, key=lambda i: (score[name][i], i))
        record["detectors"][name] = {"original_recall": float(f[poison].mean()),
            "clean_removed": float(f[clean].mean()), "selected": {
                str(m): {"slots": ordered[:m], "recall": float(f[ordered[:m]].mean()),
                         "any_missed": bool(not f[ordered[:m]].all())}
                for m in range(1, 5) if len(poison) >= m}}
    captures = {0: e, **{int(j): np.array(c["entail"]) for j, c in rotation[tid]["captures"].items()}}
    assert set(captures) == set(range(5))
    for name in ("entailment", "OR"):
        record["worst_capture"][name] = {}
        for m in range(1, 5):
            candidates = []
            for j, ej in captures.items():
                eligible = [i for i, p in enumerate(pidx) if p >= 0 and p != j]
                if len(eligible) < m:
                    continue
                f = (ej >= .01) if name == "entailment" else (ej >= .01) | (a >= 0)
                ordered = sorted(eligible, key=lambda i: (bool(f[i]), i))[:m]
                candidates.append({"capture": j, "slots": ordered,
                                   "recall": float(f[ordered].mean()), "any_missed": bool(not f[ordered].all())})
            if candidates:
                record["worst_capture"][name][str(m)] = min(candidates, key=lambda x: (x["recall"], x["capture"]))
    records.append(record)

result = {"split": "NQ development", "n_targets": len(records),
          "scope": "Stored full-context detection only; no recontextualized detection or reader ASR",
          "avidity_calibration": {"coef": model.coef_[0].tolist(), "intercept": float(model.intercept_[0]), "threshold": threshold},
          "detectors": {}, "worst_capture": {}}
lines = ["E33 score-aware released-poison selection (exploratory)",
         "NQ development; scores remain those of original full contexts. Unit = target.",
         "Do not interpret as attack success or as detection after context reconstruction."]
for name in flags:
    result["detectors"][name] = {"original_recall": float(np.mean([r["detectors"][name]["original_recall"] for r in records])),
        "clean_removed": float(np.mean([r["detectors"][name]["clean_removed"] for r in records])), "selection": {}}
    lines.append(f"\n{name}: original target-mean recall {result['detectors'][name]['original_recall']:.3f}, clean removal {result['detectors'][name]['clean_removed']:.3f}")
    for m in range(1, 5):
        selected = [r["detectors"][name]["selected"][str(m)] for r in records if str(m) in r["detectors"][name]["selected"]]
        v = [r["recall"] for r in selected]
        res = {"n_targets": len(v), "recall": float(np.mean(v)), "recall_ci": interval(v),
               "targets_with_miss": sum(r["any_missed"] for r in selected)}
        result["detectors"][name]["selection"][str(m)] = res
        lines.append(f"  m={m}, n={len(v)}: selected recall {res['recall']:.3f} {res['recall_ci']}; targets with miss {res['targets_with_miss']}")
for name in ("entailment", "OR"):
    result["worst_capture"][name] = {}
    lines.append(f"\nWorst of all 5 captures plus missed-first selection: {name}")
    for m in range(1, 5):
        selected = [r["worst_capture"][name][str(m)] for r in records if str(m) in r["worst_capture"][name]]
        v = [r["recall"] for r in selected]
        res = {"n_targets": len(v), "recall": float(np.mean(v)), "recall_ci": interval(v),
               "targets_with_miss": sum(r["any_missed"] for r in selected)}
        result["worst_capture"][name][str(m)] = res
        lines.append(f"  m={m}, n={len(v)}: selected recall {res['recall']:.3f} {res['recall_ci']}; targets with miss {res['targets_with_miss']}")
with open("results/e33_score_aware_targets.jsonl", "w") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")
save_report("e33_score_aware", result, lines)
