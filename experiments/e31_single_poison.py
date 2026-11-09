"""E31 (CPU): single non-captured poison. Context = clean top passages plus ONE
released poison (poison[j], j=1..4 in turn), retrieved by Contriever into a
top-10. Defender holds poison[0]'s claim (stored E11a extraction). Detection:
our entailment flag (tau=0.01, v1 hypothesis) vs CoordGuard AF (which removes
only components of >= 2 passages). NQ dev 21-100."""
import json
import numpy as np
from sentence_transformers import CrossEncoder
from antivenom.baselines.coordguard import audit
from antivenom.poisonedrag import load
from antivenom.retriever import Contriever

nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")
targets, corpus = load("nq"); by = {t.id: t for t in targets}
rel = json.load(open("data/external/poisonedrag/nq-contriever.json"))
e11 = [json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")][20:]
R = Contriever()
st = {"ours": [0, 0, 0], "cg": [0, 0, 0]}  # caught, n_poison_in_ctx, clean removed
nclean = ncontexts = 0
for r in e11:
    t = by[r["id"]]; q = R.encode([t.question])[0]; pv = R.encode(t.poison)
    clean = [(corpus[i]["title"] + " " + corpus[i]["text"], rel[t.id][i], False) for i in t.clean_ids]
    h = f'The answer to the question "{r["question_extracted"]}" is {r["claim"]}.'
    for j in range(1, 5):
        top = sorted(clean + [(t.poison[j], float(pv[j] @ q), True)], key=lambda x: -x[1])[:10]
        if not any(c[2] for c in top):
            continue
        ncontexts += 1
        texts = [c[0] for c in top]; pi = [c[2] for c in top].index(True)
        ent = nli.predict([(p, h) for p in texts], apply_softmax=True)[:, 1]
        ours = {i for i, s in enumerate(ent) if s >= 0.01}
        comp, _ = audit(t.question, texts); comp = set(comp)
        for k, f in (("ours", ours), ("cg", comp)):
            st[k][0] += pi in f; st[k][1] += 1; st[k][2] += len(f - {pi})
        nclean += 9
    print(r["id"], flush=True)
res = {k: {"recall": v[0] / v[1], "clean_removed": v[2] / nclean} for k, v in st.items()}
res["n_contexts"] = ncontexts
print(json.dumps(res, indent=1)); json.dump(res, open("results/e31_single_poison.json", "w"), indent=1)
