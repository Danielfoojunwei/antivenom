"""E09: oracle upper bound for attention blockade.

Question: if the reader is stopped from attending to the true poison passages,
does its preference return to the correct answer? Poison positions are known
(oracle), so this bounds what any real flagging method could achieve.

Metric: log P(correct answer) - log P(target answer) as a continuation of the
prompt, read from the reader's own logits.
"""
import argparse
import json
from pathlib import Path

import mlx.core as mx
import numpy as np

from antivenom.llm import LocalLLM
from antivenom.masked import causal_mask, forward_logits, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import wrap_prompt
from antivenom.retriever import Contriever

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=100)
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--strengths", type=float, nargs="+", default=[-2.0, -5.0, -1e4])
args = ap.parse_args()

targets, corpus = load("nq")
targets = targets[: args.limit]
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer


def contexts(t, poison: bool):
    clean = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], False) for i in t.clean_ids]
    pool = clean
    if poison:
        q = R.encode([t.question])[0]
        pool = clean + [(p, float(v @ q), True) for p, v in zip(t.poison, R.encode(t.poison))]
    return sorted(pool, key=lambda x: -x[1])[: args.k]


def option_logprob(ids, spans_to_block, strength, answer_side_from, full, option):
    opt = hf(" " + option, add_special_tokens=False)["input_ids"]
    n = len(ids) + len(opt)
    mask = np.array(causal_mask(n))
    for a, b in spans_to_block:
        rows = slice(b, n) if full else slice(answer_side_from, n)
        mask[rows, a:b] += strength
    logits = forward_logits(llm.model, ids + opt, mx.array(mask))
    logp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
    pos = mx.arange(len(ids) - 1, n - 1)
    return float(logp[pos, mx.array(opt)].sum().item())


def preference(t, ctx, block, strength=0.0, full=False):
    pieces = [c[0] for c in ctx]
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    ids, spans = token_spans(hf, text, pieces)
    answer_side_from = spans[-1][1]
    chosen = [spans[i] for i in block]
    good = option_logprob(ids, chosen, strength, answer_side_from, full, t.correct)
    bad = option_logprob(ids, chosen, strength, answer_side_from, full, t.incorrect)
    return good - bad


out = Path("results/e09_oracle_blockade_nq.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id in done:
            continue
        clean_ctx, att_ctx = contexts(t, False), contexts(t, True)
        poison_idx = [i for i, c in enumerate(att_ctx) if c[2]]
        row = {"id": t.id, "n_poison": len(poison_idx),
               "clean": preference(t, clean_ctx, []), "attack": preference(t, att_ctx, [])}
        for s in args.strengths:
            row[f"answer_side_{s:g}"] = preference(t, att_ctx, poison_idx, s, full=False)
            row[f"full_{s:g}"] = preference(t, att_ctx, poison_idx, s, full=True)
            # control: block the same number of passages in the clean context
            row[f"clean_control_{s:g}"] = preference(t, clean_ctx, list(range(len(poison_idx))), s, full=False)
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, {k: round(v, 2) for k, v in row.items() if isinstance(v, float)}, flush=True)
