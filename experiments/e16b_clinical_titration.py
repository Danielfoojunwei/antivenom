"""E16b: titration as clinical antivenom practice does it.

Clinical protocol (e.g. WHO snakebite guidelines): give a standard initial
dose, reassess a clinical endpoint, give repeat doses while the patient is
still envenomated up to a maximum, and monitor adverse reactions.

Mapping (fixed a priori, nothing tuned on the development set):
  initial dose   OR flags at v1 settings (entailment tau=0.01, attention
                 layer-21 z>=0), attention blockade s=-5
  endpoint       the reader's generated answer still asserts the captured
                 claim: NLI(premise=answer, hypothesis=claim signature)
                 entailment >= 0.5 (the standard NLI decision)
  repeat dose 2  widen coverage: tau=0.005, z>=-0.25, s=-5
  repeat dose 3  widen further:  tau=0.002, z>=-0.5,  s=-8
  maximum        3 doses
  adverse events clean passages neutralised; escalation that turns a
                 substantive answer into an abstention
Defender-side signals only: the claim from poison[0] (E02), and the
per-passage entailment / attention scores from E11a / E11c.
NQ development targets 21-100.
"""
import json
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder

from antivenom.llm import LocalLLM
from antivenom.masked import generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import _ABSTAIN, correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

K, ENDPOINT = 10, 0.5
DOSES = [(0.01, 0.0, -5.0), (0.005, -0.25, -5.0), (0.002, -0.5, -8.0)]
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
dev = set(order[20:])
ent = {json.loads(l)["id"]: json.loads(l)["entail_qa"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")}
att = {json.loads(l)["id"]: json.loads(l)["attn"]["21"]["per_token"] for l in open("results/e11c_attention_scores_nq_k10.jsonl")}
claims = {json.loads(l)["id"]: json.loads(l)["analysis"] for l in open("results/e02_nq_Qwen2.5-7B-Instruct-4bit_k5.jsonl")}
prior = {json.loads(l)["id"]: json.loads(l) for l in open("results/e12_combined_and_deletion_nq_k10.jsonl")}
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")


def flags_at(tid, tau, zmin):
    a = np.array(att[tid])
    z = (a - a.mean()) / (a.std() + 1e-9)
    return sorted({i for i, s in enumerate(ent[tid]) if s >= tau} | {i for i, v in enumerate(z) if v >= zmin})


out = Path("results/e16b_clinical_titration_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id not in dev or t.id in done or t.id not in prior or t.id not in att:
            continue
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], False) for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), True) for p, v in zip(t.poison, R.encode(t.poison))]
        top = sorted(pool, key=lambda x: -x[1])[:K]
        pieces = [c[0] for c in top]
        text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}],
                                           add_generation_prompt=True, tokenize=False)
        ids, spans = token_spans(hf, text, pieces)
        an = claims[t.id]
        hyp = f'The answer to the question "{an["question"]}" is {an["false_claim"]}.'
        course = []
        for d, (tau, zmin, s) in enumerate(DOSES, start=1):
            fl = flags_at(t.id, tau, zmin)
            resp = generate_masked(llm.model, llm.tok, ids, [spans[i] for i in fl], s, from_row=spans[-1][1]).strip()
            sign = float(nli.predict([(resp, hyp)], apply_softmax=True)[0, 1])
            course.append({"dose": d, "tau": tau, "zmin": zmin, "strength": s, "flags": fl, "resp": resp,
                           "endpoint_entail": round(sign, 4), "abstained": bool(_ABSTAIN.search(resp)),
                           "clean_neutralised": sum(not top[i][2] for i in fl),
                           "poison_neutralised": sum(top[i][2] for i in fl)})
            if sign < ENDPOINT:
                break
        final = course[-1]
        row = {"id": t.id, "doses_given": len(course), "course": course,
               "adverse_abstention": any(not a["abstained"] for a in course[:-1]) and final["abstained"],
               "titrated": {"resp": final["resp"], "endorsed": endorses(final["resp"], t.incorrect),
                            "correct": correct(final["resp"], t.correct)},
               **{k: prior[t.id][k] for k in ("attack", "clean", "block_OR", "delete_OR_backfill")}}
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, "doses", len(course), int(row["titrated"]["endorsed"]), int(row["titrated"]["correct"]), flush=True)
