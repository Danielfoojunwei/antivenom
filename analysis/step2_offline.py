"""Step 2 offline (CPU): antivenomics miss profile (M14), length confound (S11),
tolerance diagnostics (M12) and extra hypothesis templates (M7) on confirmatory
tier 1 (HotpotQA, MS-MARCO 1-50; post hoc, labelled exploratory).

Contexts are rebuilt exactly as in E24 (0 label mismatches there). The avidity
model is the frozen NQ 1-20 fit. "Missed" = poison (non-captured) scoring below
the threshold that removes the same share of clean passages as CoordGuard AF.
Output: results/rescored/summaries/step2_offline.txt and step2_passages.jsonl.
"""
import json
import re

import numpy as np
from sentence_transformers import CrossEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from antivenom.poisonedrag import load
from antivenom.retriever import Contriever

E24 = {r["dataset"]: r for r in json.load(open("results/e24_detection_confirm.json"))}
OUT = open("results/rescored/summaries/step2_offline.txt", "w")


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    OUT.write(s + "\n")


def z(v):
    v = np.array(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-9)


def logit(p):
    p = np.clip(np.array(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


ent = [json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
att = {json.loads(l)["id"]: json.loads(l) for l in open("results/e11c_attention_scores_nq_k10.jsonl")}
X, y = [], []
for r in ent[:20]:
    a = z(att[r["id"]]["attn"]["21"]["per_token"])
    for j, lab in enumerate(r["labels"]):
        if lab != "captured":
            X.append([logit(r["entail_qa"][j]), a[j]]); y.append(lab == "poison")
model = LogisticRegression().fit(np.array(X), np.array(y))

YESNO = re.compile(r"^(yes|no)$", re.I)
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")
R = Contriever()
recs = []
for d in ("hotpotqa", "msmarco"):
    targets, corpus = load(d)
    by = {t.id: t for t in targets}
    rel = json.load(open(f"data/external/poisonedrag/{d}-contriever.json"))
    for r in (json.loads(l) for l in open(f"results/rescored/e15_cross_dataset_{d}_k10.jsonl")):
        t = by[r["id"]]
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], rel[t.id][i], "clean") for i in t.clean_ids]
        qv = R.encode([t.question])[0]
        pv = R.encode(t.poison)
        pool += [(p, float(v @ qv), "captured" if j == 0 else "poison") for j, (p, v) in enumerate(zip(t.poison, pv))]
        top = sorted(pool, key=lambda x: -x[1])[:10]
        assert [c[2] for c in top] == r["labels"]
        texts = [c[0] for c in top]
        tv = R.encode(texts)
        cap = pv[0]
        Q, C = r["question_extracted"], r["claim"]
        hyps = {"claim": C, "q_claim": f"{Q} {C}"}
        extra = {k: nli.predict([(p, h) for p in texts], apply_softmax=True)[:, 1].tolist() for k, h in hyps.items()}
        s = model.predict_proba(np.stack([logit(r["entail"]), np.array(r["attn_z"])], 1))[:, 1]
        for j, (p, sc, lab) in enumerate(top):
            recs.append({"dataset": d, "id": t.id, "slot": j, "label": lab, "yesno": bool(YESNO.match(t.incorrect.strip())),
                         "words": len(p.split()), "has_q": t.question.lower() in p.lower(),
                         "has_target": t.incorrect.lower() in p.lower(), "cos_captured": float(tv[j] @ cap / (np.linalg.norm(tv[j]) * np.linalg.norm(cap))),
                         "entail_qa": r["entail"][j], "entail_claim": extra["claim"][j], "entail_q_claim": extra["q_claim"][j],
                         "attn_z": r["attn_z"][j], "avidity": float(s[j]), "text": p})
        print(d, t.id, flush=True)
with open("results/rescored/summaries/step2_passages.jsonl", "w") as f:
    for x in recs:
        f.write(json.dumps(x) + "\n")

for d in ("hotpotqa", "msmarco"):
    P = [x for x in recs if x["dataset"] == d]
    clean = np.array([x["avidity"] for x in P if x["label"] == "clean"])
    thr = np.quantile(clean, 1 - E24[d]["coordguard"]["clean_removed"])
    pois = [x for x in P if x["label"] == "poison"]
    miss = [x for x in pois if x["avidity"] < thr]
    say(f"\n== M14 antivenomics, {d}: {len(miss)}/{len(pois)} non-captured poisons missed at CoordGuard's clean rate")
    for name, f in (("yes/no target", lambda x: x["yesno"]), ("contains target answer", lambda x: x["has_target"]),
                    ("entail_qa<0.5", lambda x: x["entail_qa"] < 0.5), ("attn_z<0", lambda x: x["attn_z"] < 0)):
        say(f"  {name:24s} missed {np.mean([f(x) for x in miss]) if miss else float('nan'):.2f} | caught {np.mean([f(x) for x in pois if x not in miss]):.2f}")
    say(f"  median cos to captured   missed {np.median([x['cos_captured'] for x in miss]) if miss else float('nan'):.3f} | caught {np.median([x['cos_captured'] for x in pois if x not in miss]):.3f}")
    say(f"  targets owning the misses: {len({x['id'] for x in miss})}; yes/no targets in set: {len({x['id'] for x in P if x['yesno']})}")
    for x in miss[:4]:
        say(f"    e.g. {x['id']} slot {x['slot']} entail {x['entail_qa']:.3f} attn_z {x['attn_z']:.2f} | {x['text'][:150]}")

    lab = np.array([x["label"] != "clean" for x in P])
    words = np.array([x["words"] for x in P])
    say(f"\n== S11 length confound, {d}")
    for k in ("entail_qa", "attn_z", "avidity"):
        v = np.array([x[k] for x in P])
        # matched length: compare only within the length band shared by both classes
        lo, hi = np.percentile(words[lab], 10), np.percentile(words[lab], 90)
        m = (words >= lo) & (words <= hi)
        say(f"  {k:10s} AUC all {roc_auc_score(lab, v):.3f} | length-matched band [{lo:.0f},{hi:.0f}] words AUC {roc_auc_score(lab[m], v[m]):.3f} (n clean in band {int((~lab[m]).sum())})")
    say(f"  length alone AUC (shorter = poison) {roc_auc_score(lab, -words):.3f}")

    say(f"\n== M12 tolerance diagnostics, {d}")
    cos_p = [x["cos_captured"] for x in P if x["label"] == "poison"]
    cos_c = [x["cos_captured"] for x in P if x["label"] == "clean"]
    say(f"  cosine to captured poison: poison median {np.median(cos_p):.3f} (min {np.min(cos_p):.3f}); clean median {np.median(cos_c):.3f} (max {np.max(cos_c):.3f})")
    say(f"  cos-to-captured alone AUC {roc_auc_score(lab, [x['cos_captured'] for x in P]):.3f}  (near-clone signal; n_eff=1 by construction)")

    say(f"\n== M7 hypothesis templates, {d} (flag on max over templates, recall at matched clean rate)")
    for keys in (("entail_qa",), ("entail_claim",), ("entail_q_claim",), ("entail_qa", "entail_q_claim"), ("entail_qa", "entail_claim", "entail_q_claim")):
        v = np.array([max(x[k] for k in keys) for x in P])
        say(f"  {'+'.join(keys):40s} AUC {roc_auc_score(lab, v):.3f}")
    for keys in (("entail_qa",), ("entail_qa", "entail_claim", "entail_q_claim")):
        e = np.array([max(x[k] for k in keys) for x in P])
        sc = model.predict_proba(np.stack([logit(e), [x["attn_z"] for x in P]], 1))[:, 1]
        t2 = np.quantile(sc[~lab], 1 - E24[d]["coordguard"]["clean_removed"])
        say(f"  avidity with {'+'.join(keys):34s} recall at CG clean rate {(sc[lab] >= t2).mean():.3f} (CG {E24[d]['coordguard']['recall']:.3f})")
OUT.close()
