"""E11c: attention-concentration signal (D-SCAN-style, arXiv 2608.06947).

For each attacked top-k context, measure how much attention the final prompt
positions (the question tail and the assistant header, where the answer is
formed) pay to each passage, averaged over heads, per layer. Needs no captured
sample. Saved per layer so the layer choice can be calibrated on targets 1-20.
"""
import json
from pathlib import Path

import numpy as np

from antivenom.llm import LocalLLM
from antivenom.masked import attention_rows, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import wrap_prompt
from antivenom.retriever import Contriever

K, LAYERS, TAIL = 10, list(range(0, 28, 3)) + [27], 8
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer

out = Path("results/e11c_attention_scores_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id in done:
            continue
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], "clean") for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), "captured" if j == 0 else "poison")
                 for j, (p, v) in enumerate(zip(t.poison, R.encode(t.poison)))]
        ctx = sorted(pool, key=lambda x: -x[1])[:K]
        pieces = [c[0] for c in ctx]
        text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}],
                                           add_generation_prompt=True, tokenize=False)
        ids, spans = token_spans(hf, text, pieces)
        rows = list(range(len(ids) - TAIL, len(ids)))
        A = attention_rows(llm.model, ids, rows, LAYERS)
        per_layer = {}
        for li, a in A.items():
            m = a.mean(axis=(0, 1))  # mean over heads and query rows -> (n,)
            mass = [float(m[s:e].sum()) for s, e in spans]
            per_tok = [float(m[s:e].mean()) for s, e in spans]
            per_layer[str(li)] = {"mass": mass, "per_token": per_tok}
        f.write(json.dumps({"id": t.id, "labels": [c[2] for c in ctx],
                            "lengths": [e - s for s, e in spans], "attn": per_layer}) + "\n")
        f.flush()
print("wrote", out)
