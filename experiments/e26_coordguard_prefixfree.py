"""E26 (CPU): CoordGuard AF on the E25 prefix-free contexts (NQ dev), rebuilt
deterministically; labels checked against E25. Compares to our OR flags and
the frozen avidity score at matched clean-removal rate / matched recall."""
import json
import numpy as np
from antivenom.baselines.coordguard import audit
from antivenom.poisonedrag import load
from antivenom.retriever import Contriever

targets, corpus = load("nq", prefix=False)
by = {t.id: t for t in targets}
rel = json.load(open("data/external/poisonedrag/nq-contriever.json"))
R = Contriever()
S, OR, CG, LAB, mism = [], [], [], [], 0
for r in (json.loads(l) for l in open("results/e25_prefixfree_nq_k10.jsonl")):
    t = by[r["id"]]
    pool = [(corpus[i]["title"] + " " + corpus[i]["text"], rel[t.id][i], "clean") for i in t.clean_ids]
    q = R.encode([t.question])[0]
    pool += [(p, float(v @ q), "captured" if j == 0 else "poison") for j, (p, v) in enumerate(zip(t.poison, R.encode(t.poison)))]
    top = sorted(pool, key=lambda x: -x[1])[:10]
    if [c[2] for c in top] != r["labels"]:
        mism += 1; continue
    comp, _ = audit(t.question, [c[0] for c in top])
    for j, lab in enumerate(r["labels"]):
        if lab == "captured":
            continue
        S.append(r["avidity"][j]); OR.append(j in set(r["flags_OR"])); CG.append(j in set(comp)); LAB.append(lab == "poison")
S, OR, CG, LAB = map(np.array, (S, OR, CG, LAB))
rec = lambda f: f[LAB].mean(); fpr = lambda f: f[~LAB].mean()
a1 = S >= np.quantile(S[~LAB], 1 - fpr(CG)); a2 = S >= np.quantile(S[LAB], 1 - rec(CG))
res = {"mismatch": mism, "coordguard": [rec(CG), fpr(CG)], "ours_OR": [rec(OR), fpr(OR)],
       "avidity_at_CG_clean_rate": [rec(a1), fpr(a1)], "avidity_at_CG_recall": [rec(a2), fpr(a2)]}
print(json.dumps(res, indent=1)); json.dump(res, open("results/e26_coordguard_prefixfree.json", "w"), indent=1)
