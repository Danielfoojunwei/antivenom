"""Recover E30 per-target clean NLI scores; never calls this fresh confirmation."""
import json

from sentence_transformers import CrossEncoder

from antivenom.continuation import append, freeze, keyed
from antivenom.retriever import Contriever  # one CPU thread

freeze("results/e38_manifest.json", [__file__, "docs/REMAINING_RUNS_PROTOCOL.md", "src/antivenom/continuation.py",
    "results/e30_attack_gate.json", "data/cache/e36_contexts_hotpotqa.jsonl", "data/cache/e36_contexts_msmarco.jsonl",
    "results/e29_tier2_hotpotqa_k10.jsonl", "results/e29_tier2_msmarco_k10.jsonl"], {"scope": "exploratory E30 replay"})
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")
g = json.load(open("results/e30_attack_gate.json"))["g"]
path = "results/e38_gate_cache.jsonl"
done = keyed(path)
for dataset in ("hotpotqa", "msmarco"):
    contexts = keyed(f"data/cache/e36_contexts_{dataset}.jsonl")
    rows = keyed(f"results/e29_tier2_{dataset}_k10.jsonl")
    for n, (tid, r) in enumerate(rows.items()):
        if tid in done:
            continue
        hypothesis = f'The answer to the question "{r["question_extracted"]}" is {r["claim"]}.'
        texts = [c["text"] for c in contexts[tid]["clean_pool"][:10]]
        e = nli.predict([(p, hypothesis) for p in texts], apply_softmax=True)[:, 1]
        append(path, {"id": tid, "dataset": dataset, "threshold": g, "clean_entail": e.astype(float).tolist(),
            "gate_clean": bool(e.max() >= g), "gate_attacked": max(r["entail_v1"]) >= g,
            "gate_attacked_excl": max(x for x, label in zip(r["entail_v1"], r["labels"]) if label != "captured") >= g})
        print("E38", dataset, n + 1, "/50", tid, flush=True)
assert len(keyed(path)) == 100
print("E38 per-target cache complete", flush=True)
