"""Plan step 1: offline analyses on stored results (no model loading).

1. Construction profile (2610.33849): question containment and length of
   poison vs clean passages in the attacked top-10, per dataset.
2. M1 avidity: one logistic model on (entailment logit, attention z) fitted on
   NQ 1-20, evaluated on NQ 21-100 (development) by ROC AUC, against OR/AND.
3. M5 kinetic proofreading: attention z required to persist across layers
   15-24 vs layer 21 alone, recall/FPR on the development set.
4. M2 gate: development targets with >=1 clean passage in the medium band
   that carries the gold answer.
5. M10 H1a: E17 targets with attack not endorsed but a bound arm endorsed.
6. CoordGuard gate sweep (attacked side): remove C* iff audit_score >= g;
   answer = coordguard_af(_refill) if removed else attack.
"""
import json
import re

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from antivenom.poisonedrag import clean_str, load

R = "results/"
out = []


def say(s=""):
    print(s)
    out.append(s)


def z(v):
    v = np.array(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-9)


# ---- 1. construction profile --------------------------------------------
say("== 1. Construction profile (attacked top-10)")
for d in ("nq", "hotpotqa", "msmarco"):
    targets, corpus = load(d)
    res = json.load(open(f"data/external/poisonedrag/{d}-contriever.json"))
    cont_p, cont_c, len_p, len_c = [], [], [], []
    for t in targets:
        q = clean_str(t.question)
        for p in t.poison:
            cont_p.append(q in clean_str(p))
            len_p.append(len(p.split()))
        for i in t.clean_ids[:10]:
            txt = corpus[i]["title"] + " " + corpus[i]["text"]
            cont_c.append(q in clean_str(txt))
            len_c.append(len(txt.split()))
    say(f"  {d:9s} question contained: poison {np.mean(cont_p):.2f} clean {np.mean(cont_c):.2f} | "
        f"words: poison median {np.median(len_p):.0f}, clean median {np.median(len_c):.0f}")

# ---- shared NQ signals ---------------------------------------------------
ent = {json.loads(l)["id"]: json.loads(l) for l in open(R + "e11a_flag_scores_nq_k10.jsonl")}
att = {json.loads(l)["id"]: json.loads(l) for l in open(R + "e11c_attention_scores_nq_k10.jsonl")}
order = list(ent)
cal, dev = order[:20], order[20:]
flags = json.load(open(R + "e11c_combined_flags.json"))


def rows(ids):
    X, y, g = [], [], []
    for i in ids:
        e = np.clip(np.array(ent[i]["entail_qa"]), 1e-6, 1 - 1e-6)
        a = z(att[i]["attn"]["21"]["per_token"])
        for j, lab in enumerate(ent[i]["labels"]):
            if lab == "captured":
                continue
            X.append([np.log(e[j] / (1 - e[j])), a[j]])
            y.append(lab == "poison")
            g.append(i)
    return np.array(X), np.array(y), g


# ---- 2. avidity ------------------------------------------------------------
say("\n== 2. M1 avidity (fit NQ 1-20, report NQ 21-100 development)")
Xc, yc, _ = rows(cal)
Xd, yd, gd = rows(dev)
m = LogisticRegression().fit(Xc, yc)
s_av = m.predict_proba(Xd)[:, 1]
say(f"  coefficients (entail logit, attn z) = {np.round(m.coef_[0], 3)}")
say(f"  dev AUC: avidity {roc_auc_score(yd, s_av):.3f} | entailment alone {roc_auc_score(yd, Xd[:, 0]):.3f} "
    f"| attention alone {roc_auc_score(yd, Xd[:, 1]):.3f}")
nb = Xd[:, 0] / Xd[:, 0].std() + Xd[:, 1]
say(f"  naive sum ablation AUC {roc_auc_score(yd, nb):.3f}; within-class corr(poison) "
    f"{np.corrcoef(Xd[yd][:, 0], Xd[yd][:, 1])[0, 1]:.2f}, (clean) {np.corrcoef(Xd[~yd][:, 0], Xd[~yd][:, 1])[0, 1]:.2f}")
for name in ("OR", "AND"):
    tp = fp = fn = tn = 0
    for i in dev:
        f = set(flags[name][i])
        for j, lab in enumerate(ent[i]["labels"]):
            if lab == "captured":
                continue
            tp += (j in f) and lab == "poison"; fp += (j in f) and lab == "clean"
            fn += (j not in f) and lab == "poison"; tn += (j not in f) and lab == "clean"
    rec, fpr = tp / (tp + fn), fp / (fp + tn)
    thr = np.quantile(s_av[~yd], 1 - fpr)
    say(f"  at {name}'s FPR {fpr:.3f}: {name} recall {rec:.3f} vs avidity recall {np.mean(s_av[yd] >= thr):.3f}")
thr95 = np.quantile(s_av[yd], 0.05)
say(f"  clean-removal budget for 95% poison recall: avidity {np.mean(s_av[~yd] >= thr95):.3f}")

# ---- 3. kinetic proofreading ---------------------------------------------
say("\n== 3. M5 kinetic proofreading (attention persistence across layers)")
LAY = ["15", "18", "21", "24"]


def att_eval(rule):
    tp = fp = fn = tn = 0
    for i in dev:
        Z = np.stack([z(att[i]["attn"][L]["per_token"]) for L in LAY])
        hit = rule(Z)
        for j, lab in enumerate(ent[i]["labels"]):
            if lab == "captured":
                continue
            tp += hit[j] and lab == "poison"; fp += hit[j] and lab == "clean"
            fn += (not hit[j]) and lab == "poison"; tn += (not hit[j]) and lab == "clean"
    return tp / (tp + fn), fp / (fp + tn)


for name, rule in [("layer 21 z>=0", lambda Z: Z[2] >= 0),
                   ("all of 15-24 z>=0", lambda Z: (Z >= 0).all(0)),
                   ("3 of 4 z>=0", lambda Z: (Z >= 0).sum(0) >= 3),
                   ("mean z>=0", lambda Z: Z.mean(0) >= 0)]:
    r, f = att_eval(rule)
    say(f"  {name:20s} recall {r:.3f} FPR {f:.3f}")

# ---- 4. M2 gate -------------------------------------------------------------
say("\n== 4. M2 isotype-switching gate (development targets)")
targets = {t.id: t for t in load("nq")[0]}
corpus = load("nq")[1]
lo, hi = np.quantile(s_av[~yd], 0.90), np.quantile(s_av[yd], 0.50)
k = 0
cnt = 0
cand = 0
for i in dev:
    t = targets[i]
    res = json.load(open("data/external/poisonedrag/nq-contriever.json")) if cnt == 0 else res
    cnt += 1
    labs = [l for l in ent[i]["labels"]]
    clean_ix = [j for j, l in enumerate(labs) if l == "clean"]
    found = False
    # rank order of clean passages in the top-10 equals released order among clean ones
    clean_docs = t.clean_ids[:len(clean_ix)]
    for j, doc in zip(clean_ix, clean_docs):
        sc = s_av[k + [jj for jj, l in enumerate(labs) if l != "captured"].index(j)]
        txt = corpus[doc]["title"] + " " + corpus[doc]["text"]
        if lo <= sc < hi and re.search(r"(?<![a-z0-9])" + re.escape(clean_str(t.correct)) + r"(?![a-z0-9])", clean_str(txt)):
            found = True
    cand += found
    k += sum(1 for l in labs if l != "captured")
say(f"  medium band = clean 90th pct to poison median of avidity; targets with a gold-bearing medium-band "
    f"clean passage: {cand}/{len(dev)} -> {'RUN M2' if cand >= 15 else 'do NOT run M2 (write null)'}")

# ---- 5. M10 H1a --------------------------------------------------------------
say("\n== 5. M10 H1a backfire count (E17)")
e17 = [json.loads(l) for l in open(R + "rescored/e17_bound_delivery_nq_k10.jsonl")]
for arm in ("bound_flag", "bound_best"):
    n = sum((not r["attack"]["endorsed"]) and r[arm]["endorsed"] for r in e17)
    say(f"  {arm}: attack not endorsed but bound endorsed in {n}/{len(e17)} targets")

# ---- 6. CoordGuard gate sweep -----------------------------------------------
say("\n== 6. CoordGuard gate sweep, attacked side (NQ development, identical contexts)")
e19 = {json.loads(l)["id"]: json.loads(l) for l in open(R + "rescored/e19_baselines_nq_k10.jsonl")}
e12 = {json.loads(l)["id"]: json.loads(l) for l in open(R + "rescored/e12_combined_and_deletion_nq_k10.jsonl")}
ids = [i for i in dev if i in e19 and i in e12]
sc = np.array([e19[i]["coordguard_af"]["audit_score"] for i in ids])
for q in (0.0, 0.25, 0.5, 0.75, 0.9):
    g = np.quantile(sc, q)
    for arm in ("coordguard_af", "coordguard_af_refill"):
        pick = [e19[i][arm] if e19[i]["coordguard_af"]["audit_score"] >= g else e12[i]["attack"] for i in ids]
        say(f"  gate at attacked-score quantile {q:.2f}: {arm:22s} fires {np.mean(sc >= g):.2f} "
            f"endorsed {np.mean([p['endorsed'] for p in pick]):.2f} correct {np.mean([p['correct'] for p in pick]):.2f}")
say("  (clean-side gate calibration needs e5 on clean contexts: CPU, separate step)")

open(R + "rescored/summaries/step1_offline.txt", "w").write("\n".join(out) + "\n")
