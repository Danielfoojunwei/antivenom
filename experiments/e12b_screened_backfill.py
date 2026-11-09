"""E12b: delete OR-flagged passages and backfill with screening ("immune
surveillance"). Each backfill candidate, taken in rank order, is admitted only
if it does not entail the stored claim signature (same NLI model and
phrasing, tau=0.01, frozen v1). NQ development targets present in E12.
Compared with E12's unscreened delete_OR_backfill on the same targets.
"""
import json
from pathlib import Path

from sentence_transformers import CrossEncoder

from antivenom.llm import LocalLLM
from antivenom.masked import generate_masked
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

K, TAU = 10, 0.01
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
or_flags = json.load(open("results/e11c_combined_flags.json"))["OR"]
claims = {json.loads(l)["id"]: json.loads(l)["analysis"] for l in open("results/e02_nq_Qwen2.5-7B-Instruct-4bit_k5.jsonl")}
prior = {json.loads(l)["id"]: json.loads(l) for l in open("results/e12_combined_and_deletion_nq_k10.jsonl")}
R = Contriever()
llm = LocalLLM()
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")

out = Path("results/e12b_screened_backfill_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id not in prior or t.id in done:
            continue
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], False) for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), True) for p, v in zip(t.poison, R.encode(t.poison))]
        pool.sort(key=lambda x: -x[1])
        flags = set(or_flags[t.id])
        kept = [c for i, c in enumerate(pool[:K]) if i not in flags]
        an = claims[t.id]
        hyp = f'The answer to the question "{an["question"]}" is {an["false_claim"]}.'
        refill, rejected = [], 0
        for c in pool[K:]:
            if len(refill) == len(flags):
                break
            if float(nli.predict([(c[0], hyp)], apply_softmax=True)[0, 1]) >= TAU:
                rejected += 1
                continue
            refill.append(c)
        ctx = kept + refill
        text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, [c[0] for c in ctx])}],
                                           add_generation_prompt=True, tokenize=False)
        ids = llm.tok._tokenizer(text, add_special_tokens=False)["input_ids"]
        resp = generate_masked(llm.model, llm.tok, ids, [], 0.0, from_row=0).strip()
        row = {"id": t.id, "attack": prior[t.id]["attack"], "clean": prior[t.id]["clean"],
               "delete_OR_backfill": prior[t.id]["delete_OR_backfill"],
               "delete_OR_screened_backfill": {"resp": resp, "endorsed": endorses(resp, t.incorrect),
                                               "correct": correct(resp, t.correct),
                                               "n_poison_in_ctx": sum(c[2] for c in ctx),
                                               "backfill_rejected": rejected}}
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, row["delete_OR_screened_backfill"]["n_poison_in_ctx"], int(row["delete_OR_screened_backfill"]["endorsed"]), flush=True)
