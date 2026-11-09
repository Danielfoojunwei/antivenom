"""Fidelity of the mechanism-level code in src/antivenom/masked.py.

1. forward_logits with only the causal mask equals the model's own forward.
2. generate_masked with no bias equals mlx_lm greedy generation, on 10 real
   attacked PoisonedRAG prompts.
3. attention_rows returns causal probability distributions (rows sum to 1,
   zero mass on future positions) at every layer.
Writes results/fidelity/masked.txt.
"""
import sys
from pathlib import Path

import mlx.core as mx
import numpy as np

from antivenom.llm import LocalLLM
from antivenom.masked import attention_rows, causal_mask, forward_logits, generate_masked
from antivenom.poisonedrag import load
from antivenom.qa import wrap_prompt

MODEL = sys.argv[1] if len(sys.argv) > 1 else None
llm = LocalLLM(MODEL) if MODEL else LocalLLM()
TAG = MODEL.split('/')[-1] if MODEL else 'qwen'
m, tok = llm.model, llm.tok
targets, corpus = load("nq")
lines = []

# 1. forward equivalence on 5 real prompts
worst = 0.0
for t in targets[:5]:
    msgs = [{"role": "user", "content": wrap_prompt(t.question, t.poison[:3])}]
    ids = tok.encode(tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False), add_special_tokens=False)
    ref = m(mx.array([ids]))[0]
    ours = forward_logits(m, ids, causal_mask(len(ids)))
    worst = max(worst, float(mx.abs(ref - ours).max()))
lines.append(f"forward_logits vs model forward, 5 prompts: max_abs_logit_diff={worst:.3e}")

# 2. greedy equivalence on 10 real attacked prompts
same = 0
for t in targets[:10]:
    ctx = t.poison[:3] + [corpus[i]["title"] + " " + corpus[i]["text"] for i in t.clean_ids[:2]]
    msgs = [{"role": "user", "content": wrap_prompt(t.question, ctx)}]
    ref = llm.generate(msgs, temp=0.0, max_tokens=48).strip()
    ids = tok.encode(tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False), add_special_tokens=False)
    same += ref == generate_masked(m, tok, ids, [], 0.0, 0, 48).strip()
lines.append(f"generate_masked (no bias) vs mlx_lm greedy, 10 prompts: identical={same}/10")

# 3. attention rows at all layers
t = targets[0]
msgs = [{"role": "user", "content": wrap_prompt(t.question, t.poison[:2])}]
ids = tok.encode(tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False), add_special_tokens=False)
rows = [len(ids) - 1, 10]
A = attention_rows(m, ids, rows, list(range(len(m.model.layers))))
sums = np.concatenate([a.sum(-1).ravel() for a in A.values()])
future = max(float(a[:, 1, 11:].sum()) for a in A.values())
lines.append(f"attention_rows, {len(A)} layers: row_sum min={sums.min():.6f} max={sums.max():.6f}; "
             f"max mass on future positions={future:.2e}")

Path("results/fidelity").mkdir(parents=True, exist_ok=True)
Path("results/fidelity/masked.txt" if TAG == "qwen" else f"results/fidelity/masked_{TAG}.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
