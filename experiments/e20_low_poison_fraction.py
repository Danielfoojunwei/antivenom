"""E20: the full pipeline when only m of the 5 released poisons are present.

For each NQ development target (21-100) and m in {1, 2, 3}, the store holds
the released clean top-100 plus poison[0..m-1] (poison[0] is the captured
sample, so it is always present). Frozen v1 settings: entailment tau=0.01
against the claim extracted from poison[0] (E02), attention layer 21,
per-token, z>=0 within the context, OR combination. Arms per m: attack,
block_OR (s=-5), delete_OR_backfill. Tests whether the within-context
attention threshold over-flags clean passages when poison is sparse.
"""
import json
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder

from antivenom.llm import LocalLLM
from antivenom.masked import attention_rows, generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

K, S, TAU, LAYER, TAIL, MS = 10, -5.0, 0.01, 21, 8, (1, 2, 3)
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
dev = set(order[20:])
claims = {json.loads(l)["id"]: json.loads(l)["analysis"] for l in open("results/e02_nq_Qwen2.5-7B-Instruct-4bit_k5.jsonl")}
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")


def build(question, pieces):
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    return token_spans(hf, text, pieces)


def answer(t, pieces, block=()):
    ids, spans = build(t.question, pieces)
    resp = generate_masked(llm.model, llm.tok, ids, [spans[i] for i in block], S, from_row=spans[-1][1]).strip()
    return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)}


out = Path("results/e20_low_poison_fraction_nq_k10.jsonl")
done = {(json.loads(l)["id"], json.loads(l)["m"]) for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id not in dev:
            continue
        an = claims[t.id]
        hyp = f'The answer to the question "{an["question"]}" is {an["false_claim"]}.'
        q = R.encode([t.question])[0]
        pvec = R.encode(t.poison)
        clean = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], "clean") for i in t.clean_ids]
        for m in MS:
            if (t.id, m) in done:
                continue
            pool = clean + [(t.poison[j], float(pvec[j] @ q), "captured" if j == 0 else "poison") for j in range(m)]
            pool.sort(key=lambda x: -x[1])
            top = pool[:K]
            pieces = [c[0] for c in top]
            ent = {i for i, s in enumerate(nli.predict([(p, hyp) for p in pieces], apply_softmax=True)[:, 1]) if s >= TAU}
            ids, spans = build(t.question, pieces)
            a = attention_rows(llm.model, ids, list(range(len(ids) - TAIL, len(ids))), [LAYER])[LAYER].mean(axis=(0, 1))
            v = np.array([a[s:e].mean() for s, e in spans])
            att = {i for i, z in enumerate((v - v.mean()) / (v.std() + 1e-9)) if z >= 0}
            flags = sorted(ent | att)
            kept = [p for i, p in enumerate(pieces) if i not in set(flags)]
            row = {"id": t.id, "m": m, "labels": [c[2] for c in top],
                   "flags_entail": sorted(ent), "flags_attn": sorted(att), "flags_OR": flags,
                   "attack": answer(t, pieces),
                   "block_OR": answer(t, pieces, flags),
                   "delete_OR_backfill": answer(t, kept + [c[0] for c in pool[K:K + len(flags)]])}
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(t.id, m, len(flags), {k: int(row[k]["endorsed"]) for k in ("attack", "block_OR", "delete_OR_backfill")},
                  flush=True)
