"""E16: titration, dose-to-effect per threat.

For each held-out NQ target and its OR-flagged passages, a fork of the reader
scores the extracted false claim (from poison[0], E02) as an answer
continuation. The dose is the smallest blockade strength on the ladder at which
log P(claim) falls to its value with the flagged passages removed (+ margin).
The answer is then generated at that dose. Compared with the fixed s=-5
(block_OR in E12). Uses only defender-side information.
"""
import json
from pathlib import Path

import mlx.core as mx
import numpy as np

from antivenom.llm import LocalLLM
from antivenom.masked import causal_mask, forward_logits, generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

K, LADDER, MARGIN, CLAIM_TOKENS = 10, [-1.0, -2.0, -3.0, -4.0, -5.0, -8.0], 0.5, 8
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
held_out = set(order[20:])
or_flags = json.load(open("results/e11c_combined_flags.json"))["OR"]
claims = {json.loads(l)["id"]: json.loads(l)["analysis"]["false_claim"]
          for l in open("results/e02_nq_Qwen2.5-7B-Instruct-4bit_k5.jsonl")}
prior = {json.loads(l)["id"]: json.loads(l) for l in open("results/e12_combined_and_deletion_nq_k10.jsonl")}
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer


def build(question, pieces):
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    return token_spans(hf, text, pieces)


def claim_logprob(ids, blocked, strength, from_row, claim_ids):
    n = len(ids) + len(claim_ids)
    mask = np.array(causal_mask(n))
    for a, b in blocked:
        mask[from_row:, a:b] += strength
    logits = forward_logits(llm.model, ids + claim_ids, mx.array(mask))
    logp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
    pos = mx.arange(len(ids) - 1, n - 1)
    return float(logp[pos, mx.array(claim_ids)].sum().item())


out = Path("results/e16_titration_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id not in held_out or t.id in done or t.id not in prior:
            continue
        flags = or_flags[t.id]
        if not flags:
            continue
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i]) for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q)) for p, v in zip(t.poison, R.encode(t.poison))]
        top = [p for p, _ in sorted(pool, key=lambda x: -x[1])[:K]]
        claim_ids = hf(" " + claims[t.id], add_special_tokens=False)["input_ids"][:CLAIM_TOKENS]

        ids, spans = build(t.question, top)
        blocked, from_row = [spans[i] for i in flags], spans[-1][1]
        kept = [p for i, p in enumerate(top) if i not in set(flags)]
        k_ids, k_spans = build(t.question, kept) if kept else build(t.question, [])
        target_lp = claim_logprob(k_ids, [], 0.0, 0, claim_ids)  # reference: flagged removed

        ladder = []
        dose = LADDER[-1]
        for s in LADDER:
            lp = claim_logprob(ids, blocked, s, from_row, claim_ids)
            ladder.append([s, round(lp, 3)])
            if lp <= target_lp + MARGIN:
                dose = s
                break
        resp = generate_masked(llm.model, llm.tok, ids, blocked, dose, from_row=from_row).strip()
        row = {"id": t.id, "flags": flags, "dose": dose, "ladder": ladder, "reference_lp": round(target_lp, 3),
               "titrated": {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)},
               **{k: prior[t.id][k] for k in ("attack", "block_OR", "delete_OR", "delete_OR_backfill", "clean")}}
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, "dose", dose, int(row["titrated"]["endorsed"]), int(row["titrated"]["correct"]), flush=True)
