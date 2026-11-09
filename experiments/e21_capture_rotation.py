"""E21: does detection depend on which poison was captured?

For each NQ development target (21-100) and each released poison j in 1..4,
the defender captures poison[j] instead of poison[0]: the immunologist (same
reader, same prompt) extracts its claim, and every passage of the same
attacked top-10 context is scored for entailment of that claim (same NLI
model, phrasing and frozen tau as E11a). j=0 is taken from E11a/E02.
Detection only; no answers are generated.
"""
import json
from pathlib import Path

from sentence_transformers import CrossEncoder

from antivenom.antibody import Immunologist
from antivenom.llm import LocalLLM
from antivenom.poisonedrag import load
from antivenom.retriever import Contriever

K = 10
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
dev = set(order[20:])
R = Contriever()
imm = Immunologist(LocalLLM())
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")

out = Path("results/e21_capture_rotation_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id not in dev or t.id in done:
            continue
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], -1) for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), j) for j, (p, v) in enumerate(zip(t.poison, R.encode(t.poison)))]
        top = sorted(pool, key=lambda x: -x[1])[:K]
        row = {"id": t.id, "poison_index": [c[2] for c in top], "captures": {}}
        for j in range(1, len(t.poison)):
            an = imm.analyse(t.poison[j])
            hyp = f'The answer to the question "{an.question}" is {an.false_claim}.'
            scores = nli.predict([(c[0], hyp) for c in top], apply_softmax=True)[:, 1]
            row["captures"][str(j)] = {"claim": an.false_claim, "question_extracted": an.question,
                                       "entail": [round(float(s), 5) for s in scores]}
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, flush=True)
