"""E12: cure with combined flags (OR / AND of entailment and attention) and
the deletion baselines a reviewer will ask for.

Held-out targets 21-100 only. For each target:
  block_OR, block_AND           attention blockade (s=-5) on flagged passages
  delete_OR, delete_entail      drop flagged passages, context shrinks
  delete_OR_backfill,
  delete_entail_backfill        drop flagged passages and refill top-k with the
                                next-ranked retrieved passages
Clean / attack / oracle / entailment-blockade answers are reused from E11b.
"""
import json
from pathlib import Path

from antivenom.llm import LocalLLM
from antivenom.masked import generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

K, S = 10, -5.0
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
held_out = set(order[20:])
ent_flags = json.load(open("results/e11a_chosen_flags.json"))["flags"]
comb = json.load(open("results/e11c_combined_flags.json"))
prior = {json.loads(l)["id"]: json.loads(l) for l in open("results/e11b_flagged_blockade_nq_k10.jsonl")}
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer


def ranked_pool(t):
    pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], False) for i in t.clean_ids]
    q = R.encode([t.question])[0]
    pool += [(p, float(v @ q), True) for p, v in zip(t.poison, R.encode(t.poison))]
    return sorted(pool, key=lambda x: -x[1])


def answer(t, ctx, block=()):
    pieces = [c[0] for c in ctx]
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    if pieces:
        ids, spans = token_spans(hf, text, pieces)
        blocked, from_row = [spans[i] for i in block], spans[-1][1]
    else:  # every passage deleted: answer with an empty context
        ids, blocked, from_row = hf(text, add_special_tokens=False)["input_ids"], [], 0
    resp = generate_masked(llm.model, llm.tok, ids, blocked, S, from_row=from_row).strip()
    return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct),
            "n_poison_in_ctx": sum(c[2] for c in ctx)}


out = Path("results/e12_combined_and_deletion_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id not in held_out or t.id in done or t.id not in prior or t.id not in comb["OR"]:
            continue
        pool = ranked_pool(t)
        top = pool[:K]
        row = {"id": t.id, **{k: prior[t.id][k] for k in ("clean", "attack", "oracle", "flagged_block")}}
        row["block_entail"] = row.pop("flagged_block")
        for name, flags in (("OR", comb["OR"][t.id]), ("AND", comb["AND"][t.id])):
            row[f"flags_{name}"] = flags
            row[f"block_{name}"] = answer(t, top, flags) if flags else row["attack"]
        for name, flags in (("OR", comb["OR"][t.id]), ("entail", ent_flags[t.id])):
            kept = [c for i, c in enumerate(top) if i not in set(flags)]
            row[f"delete_{name}"] = answer(t, kept) if kept else answer(t, [])
            refill = kept + pool[K:K + len(flags)]
            row[f"delete_{name}_backfill"] = answer(t, refill)
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, {k: int(v["endorsed"]) for k, v in row.items() if isinstance(v, dict)}, flush=True)
