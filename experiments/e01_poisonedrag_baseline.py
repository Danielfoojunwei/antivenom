"""E01: reproduce the PoisonedRAG attack baseline on a local model.

Protocol follows PoisonedRAG main.py: clean top-k from the released
Contriever results, published poison passages scored with Contriever (dot),
merged by score, top-k given to the LLM with the authors' prompt.
Writes one JSON line per target to results/e01_<dataset>_<model>.jsonl.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from antivenom.llm import LocalLLM
from antivenom.poisonedrag import load
from antivenom.qa import answer, correct, poisoned
from antivenom.retriever import Contriever

ap = argparse.ArgumentParser()
ap.add_argument("--dataset", default="nq")
ap.add_argument("--model", default="mlx-community/Qwen2.5-7B-Instruct-4bit")
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--limit", type=int, default=100)
args = ap.parse_args()

targets, corpus = load(args.dataset)
targets = targets[: args.limit]
released = json.load(open(f"data/external/poisonedrag/{args.dataset}-contriever.json"))
R = Contriever()
llm = LocalLLM(args.model)
out = Path("results") / f"e01_{args.dataset}_{args.model.split('/')[-1]}_k{args.k}.jsonl"
out.parent.mkdir(exist_ok=True)

done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id in done:
            continue
        clean = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], "corpus")
                 for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pois = [(p, float(v @ q), "poison") for p, v in zip(t.poison, R.encode(t.poison))]
        clean_top = [c[0] for c in clean[: args.k]]
        merged = sorted(clean + pois, key=lambda x: -x[1])[: args.k]
        t0 = time.time()
        r_clean = answer(llm, t.question, clean_top)
        r_att = answer(llm, t.question, [m[0] for m in merged])
        f.write(json.dumps({
            "id": t.id, "question": t.question, "correct": t.correct, "incorrect": t.incorrect,
            "clean_resp": r_clean, "clean_correct": correct(r_clean, t.correct),
            "clean_poisoned": poisoned(r_clean, t.incorrect),
            "att_resp": r_att, "att_correct": correct(r_att, t.correct),
            "att_poisoned": poisoned(r_att, t.incorrect),
            "poison_in_topk": sum(m[2] == "poison" for m in merged),
            "secs": round(time.time() - t0, 2)}) + "\n")
        f.flush()

rows = [json.loads(l) for l in out.open()]
n = len(rows)
summary = {k: round(sum(r[k] for r in rows) / n, 3) for k in
           ["clean_correct", "clean_poisoned", "att_correct", "att_poisoned"]}
summary["mean_poison_in_topk"] = round(sum(r["poison_in_topk"] for r in rows) / n, 2)
summary["n"] = n
print(json.dumps(summary))
json.dump(summary, open(str(out).replace(".jsonl", "_summary.json"), "w"), indent=1)
