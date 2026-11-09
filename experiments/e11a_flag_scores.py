"""E11a: score every passage in each attacked top-k context for entailment of
the false claim extracted from ONE captured poison passage (poison[0]).

The extracted claim is reused from E02, where the immunologist produced it
from poison[0] alone. Output: one row per target with per-passage scores and
ground-truth labels, for threshold calibration and flag evaluation.
"""
import json
from pathlib import Path

from sentence_transformers import CrossEncoder

from antivenom.poisonedrag import load
from antivenom.retriever import Contriever

K = 10
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
claims = {json.loads(l)["id"]: json.loads(l)["analysis"]
          for l in open("results/e02_nq_Qwen2.5-7B-Instruct-4bit_k5.jsonl")}
R = Contriever()
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")
ENTAIL = 1  # id2label {0: contradiction, 1: entailment, 2: neutral}

out = Path("results/e11a_flag_scores_nq_k10.jsonl")
with out.open("w") as f:
    for t in targets:
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], "clean") for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), "captured" if j == 0 else "poison")
                 for j, (p, v) in enumerate(zip(t.poison, R.encode(t.poison)))]
        ctx = sorted(pool, key=lambda x: -x[1])[:K]
        an = claims[t.id]  # extracted from poison[0] only; never the dataset question
        claim, q_ext = an["false_claim"], an["question"]
        hyps = {"claim": claim,
                "qa": f'The answer to the question "{q_ext}" is {claim}.',
                "q_claim": f"{q_ext} {claim}"}
        row = {"id": t.id, "claim": claim, "question_extracted": q_ext, "labels": [c[2] for c in ctx]}
        for name, h in hyps.items():
            s = nli.predict([(c[0], h) for c in ctx], apply_softmax=True)[:, ENTAIL]
            row[f"entail_{name}"] = [round(float(x), 5) for x in s]
        f.write(json.dumps(row) + "\n")
print("wrote", out)
