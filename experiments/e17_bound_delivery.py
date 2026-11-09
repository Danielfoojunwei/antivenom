"""E17: bound delivery ("immune complex") where backfill is unavailable.

Setting: a fixed memory/context of top-10 records with no pool to refill from.
Held-out NQ targets 21-100, OR flags from E11c. Arms:
  delete_OR          drop flagged records (context shrinks)
  bound_flag         keep every record; place a flag counter-record right after
                     each flagged record (from E02's antibodies, made from poison[0])
  bound_best         as above with E02's "best" antibody (evidence if the
                     immunologist knew the answer, else flag)
  bound_best+block   bound_best plus the attention blockade on flagged records
Clean / attack / block_OR / delete_OR are reused from E12 when present.
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
or_flags = json.load(open("results/e11c_combined_flags.json"))["OR"]
antibodies = {json.loads(l)["id"]: json.loads(l)["antibodies"]
              for l in open("results/e02_nq_Qwen2.5-7B-Instruct-4bit_k5.jsonl")}
prior = {json.loads(l)["id"]: json.loads(l) for l in open("results/e12_combined_and_deletion_nq_k10.jsonl")}
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer


def top_k(t):
    pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i]) for i in t.clean_ids]
    q = R.encode([t.question])[0]
    pool += [(p, float(v @ q)) for p, v in zip(t.poison, R.encode(t.poison))]
    return [p for p, _ in sorted(pool, key=lambda x: -x[1])[:K]]


def answer(t, pieces, block=()):
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    ids, spans = token_spans(hf, text, pieces)
    resp = generate_masked(llm.model, llm.tok, ids, [spans[i] for i in block], S,
                           from_row=spans[-1][1]).strip()
    return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)}


def bind(pieces, flags, ab):
    """Insert one antibody right after each flagged record; return pieces and
    the new indices of the flagged records."""
    out, new_flagged = [], []
    for i, p in enumerate(pieces):
        out.append(p)
        if i in flags:
            new_flagged.append(len(out) - 1)
            out.append(ab[len(new_flagged) - 1] if len(new_flagged) <= len(ab) else ab[-1])
    return out, new_flagged


out = Path("results/e17_bound_delivery_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id not in held_out or t.id in done or t.id not in prior:
            continue
        top, flags = top_k(t), set(or_flags[t.id])
        ab = antibodies[t.id]
        row = {"id": t.id, "flags": sorted(flags),
               **{k: prior[t.id][k] for k in ("clean", "attack", "block_OR", "delete_OR")}}
        for name, kind in (("bound_flag", "flag"), ("bound_best", "best")):
            pieces, new_flagged = bind(top, flags, ab[kind] or ab["flag"])
            row[name] = answer(t, pieces)
            if name == "bound_best":
                row["bound_best+block"] = answer(t, pieces, new_flagged)
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, {k: (int(v["endorsed"]), int(v["correct"])) for k, v in row.items() if isinstance(v, dict)},
              flush=True)
