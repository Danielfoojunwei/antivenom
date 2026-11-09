"""E11b: attention blockade on passages flagged by claim entailment (E11a),
instead of oracle poison positions. Scored on generated answers.

Clean / attack / oracle answers are reused from E09b where available (greedy
decoding is deterministic, same context construction); otherwise computed.
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
chosen = json.load(open("results/e11a_chosen_flags.json"))
prior = {json.loads(l)["id"]: json.loads(l) for l in open("results/e09b_blockade_generation_nq_k10.jsonl")}
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer


def contexts(t, poison: bool):
    pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], False) for i in t.clean_ids]
    if poison:
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), True) for p, v in zip(t.poison, R.encode(t.poison))]
    return sorted(pool, key=lambda x: -x[1])[:K]


def answer(t, ctx, block=()):
    pieces = [c[0] for c in ctx]
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    ids, spans = token_spans(hf, text, pieces)
    resp = generate_masked(llm.model, llm.tok, ids, [spans[i] for i in block], S,
                           from_row=spans[-1][1]).strip()
    return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)}


out = Path("results/e11b_flagged_blockade_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id in done:
            continue
        att = contexts(t, True)
        flagged = chosen["flags"][t.id]
        poison_idx = [i for i, c in enumerate(att) if c[2]]
        row = {"id": t.id, "flagged": flagged, "poison_idx": poison_idx,
               "n_true_flags": len(set(flagged) & set(poison_idx)),
               "n_false_flags": len(set(flagged) - set(poison_idx))}
        if t.id in prior:
            p = prior[t.id]
            row.update(clean=p["clean"], attack=p["attack"], oracle=p["block_poison_-5"], reused=True)
        else:
            row.update(clean=answer(t, contexts(t, False)), attack=answer(t, att),
                       oracle=answer(t, att, poison_idx), reused=False)
        row["flagged_block"] = answer(t, att, flagged) if flagged else row["attack"]
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, len(flagged), row["n_true_flags"], row["n_false_flags"],
              int(row["attack"]["endorsed"]), int(row["flagged_block"]["endorsed"]), flush=True)
