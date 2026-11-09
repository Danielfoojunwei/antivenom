"""E32 (M3 placebo): NQ dev 21-100, attacked top-10, frozen v1 OR flags
(E11a entailment tau=0.01 OR E11c layer-21 attention z>=0). Arms:
delete + true backfill (next-ranked clean passages for this question),
delete + placebo backfill (same count of clean passages from the NEXT target's
pool, i.e. off-topic but real), delete only. Same reader/prompt/decoder."""
import json
from pathlib import Path
import numpy as np
from antivenom.llm import LocalLLM
from antivenom.masked import generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

targets, corpus = load("nq"); by = {t.id: t for t in targets}
rel = json.load(open("data/external/poisonedrag/nq-contriever.json"))
e11 = [json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
att = {json.loads(l)["id"]: json.loads(l) for l in open("results/e11c_attention_scores_nq_k10.jsonl")}
dev = [r["id"] for r in e11[20:]]; ent = {r["id"]: r for r in e11}
R = Contriever(); llm = LocalLLM(); hf = llm.tok._tokenizer


def answer(t, pieces):
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}], add_generation_prompt=True, tokenize=False)
    ids, spans = token_spans(hf, text, pieces)
    resp = generate_masked(llm.model, llm.tok, ids, [], 0.0, from_row=0).strip()
    return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)}


def pool_of(t):
    q = R.encode([t.question])[0]
    p = [(corpus[i]["title"] + " " + corpus[i]["text"], rel[t.id][i], "clean") for i in t.clean_ids]
    p += [(x, float(v @ q), "poison") for x, v in zip(t.poison, R.encode(t.poison))]
    return sorted(p, key=lambda x: -x[1])


out = Path("results/e32_backfill_placebo_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for n, tid in enumerate(dev):
        if tid in done:
            continue
        t = by[tid]; pool = pool_of(t); top, rest = pool[:10], pool[10:]
        a = np.array(att[tid]["attn"]["21"]["per_token"]); z = (a - a.mean()) / (a.std() + 1e-9)
        flags = sorted({i for i, s in enumerate(ent[tid]["entail_qa"]) if s >= 0.01} | {i for i, v in enumerate(z) if v >= 0})
        kept = [c[0] for i, c in enumerate(top) if i not in set(flags)]
        other = by[dev[(n + 1) % len(dev)]]
        placebo = [c[0] for c in pool_of(other) if c[2] == "clean"][10:10 + len(flags)]
        row = {"id": tid, "n_flags": len(flags), "placebo_from": other.id,
               "delete_true_backfill": answer(t, kept + [c[0] for c in rest[:len(flags)]]),
               "delete_placebo_backfill": answer(t, kept + placebo),
               "delete_only": answer(t, kept)}
        f.write(json.dumps(row) + "\n"); f.flush(); print(tid, flush=True)
