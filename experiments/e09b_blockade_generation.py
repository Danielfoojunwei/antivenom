"""E09b: oracle attention blockade scored on generated answers, k=10.

With k=10 the five poison passages sit alongside clean evidence. For each
target we generate answers for: clean context, attacked context, the poison
spans blocked (answer side), and a count-matched control that blocks the same
number of randomly chosen clean passages in the attacked context instead.
"""
import argparse
import json
import random
from pathlib import Path

from antivenom.llm import LocalLLM
from antivenom.masked import generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=100)
ap.add_argument("--k", type=int, default=10)
ap.add_argument("--strengths", type=float, nargs="+", default=[-5.0, -1e4])
args = ap.parse_args()

targets, corpus = load("nq")
targets = targets[: args.limit]
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer


def contexts(t, poison: bool):
    pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], False) for i in t.clean_ids]
    if poison:
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), True) for p, v in zip(t.poison, R.encode(t.poison))]
    return sorted(pool, key=lambda x: -x[1])[: args.k]


def answer(t, ctx, block=(), strength=0.0):
    pieces = [c[0] for c in ctx]
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    ids, spans = token_spans(hf, text, pieces)
    resp = generate_masked(llm.model, llm.tok, ids, [spans[i] for i in block], strength,
                           from_row=spans[-1][1]).strip()
    return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)}


out = Path(f"results/e09b_blockade_generation_nq_k{args.k}.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id in done:
            continue
        clean_ctx, att_ctx = contexts(t, False), contexts(t, True)
        poison_idx = [i for i, c in enumerate(att_ctx) if c[2]]
        clean_idx = [i for i, c in enumerate(att_ctx) if not c[2]]
        rng = random.Random(t.id)
        control_idx = rng.sample(clean_idx, min(len(poison_idx), len(clean_idx)))
        row = {"id": t.id, "n_poison": len(poison_idx), "n_control_blocked": len(control_idx),
               "clean": answer(t, clean_ctx), "attack": answer(t, att_ctx)}
        for s in args.strengths:
            row[f"block_poison_{s:g}"] = answer(t, att_ctx, poison_idx, s)
            row[f"block_random_clean_{s:g}"] = answer(t, att_ctx, control_idx, s)
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, row["n_poison"], {k: (int(v["endorsed"]), int(v["correct"]))
                                      for k, v in row.items() if isinstance(v, dict)}, flush=True)
