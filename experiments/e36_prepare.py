"""Prepare canonical contexts and reader-independent CoordGuard scores."""
import json
from pathlib import Path

import numpy as np

from antivenom.baselines.coordguard import audit
from antivenom.continuation import append, build_pool, clean_pool, keyed, passage_hashes, read_rows, save
from antivenom.poisonedrag import load
from antivenom.retriever import Contriever

order = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][:20]
retriever = Contriever()
for dataset in ("nq", "hotpotqa", "msmarco"):
    targets, corpus = load(dataset)
    by = {t.id: t for t in targets}
    selected = [by[i] for i in order] if dataset == "nq" else targets[50:100]
    rel = json.load(open(f"data/external/poisonedrag/{dataset}-contriever.json"))
    path = f"data/cache/e36_contexts_{dataset}.jsonl"
    done = keyed(path)
    old = keyed(f"results/e29_tier2_{dataset}_k10.jsonl") if dataset != "nq" else {}
    for n, t in enumerate(selected):
        if t.id in done:
            continue
        pool = build_pool(t, corpus, rel, retriever)
        clean = clean_pool(t, corpus, rel)
        texts = [c["text"] for c in pool[:10]]
        if dataset != "nq":
            assert [c["label"] for c in pool[:10]] == old[t.id]["labels"]
            comp, score = old[t.id]["coordguard_removed"], old[t.id]["coordguard_score"]
            # Validate cache use against the algorithm on the first 3 contexts.
            if n < 3:
                actual, actual_score = audit(t.question, texts)
                assert sorted(actual) == sorted(comp), t.id
                assert np.isclose(actual_score, score, rtol=1e-5, atol=1e-6), t.id
        else:
            comp, score = audit(t.question, texts)
        clean_comp, clean_score = audit(t.question, [c["text"] for c in clean[:10]])
        if dataset != "nq":
            assert sorted(clean_comp) == old[t.id]["defclean_coordguard_removed"], t.id
        append(path, {"id": t.id, "dataset": dataset, "pool": pool, "clean_pool": clean,
            "context_hashes": passage_hashes(pool[:10]), "coordguard_removed": sorted(comp),
            "coordguard_score": score, "clean_coordguard_removed": sorted(clean_comp),
            "clean_coordguard_score": clean_score})
        print("prepare", dataset, t.id, f"{n + 1}/{len(selected)}", flush=True)
    actual = keyed(path)
    assert set(actual) == {t.id for t in selected}
cal = read_rows("data/cache/e36_contexts_nq.jsonl")
scores = [r["clean_coordguard_score"] if r["clean_coordguard_score"] is not None else -1e9 for r in cal]
save("results/e36_geometry_gate_calibration.json", {"quantile": .90, "threshold": float(np.quantile(scores, .90)),
    "calibration_ids": order, "clean_scores": scores})
print("canonical contexts and geometry gate calibration complete", flush=True)
