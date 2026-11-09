"""Full coverage, identity, manifest and scoring checks for E36–E38; no model inference."""
import hashlib
import json
from pathlib import Path

import numpy as np

from antivenom.continuation import keyed, passage_hashes, read_rows
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses

ARMS36 = ["clean", "attack", "v1_block", "v1_delete_backfill", "v2_delete_backfill", "random_delete_backfill",
          "lowrel_delete_backfill", "coordguard_af", "coordguard_af_refill", "trustrag", "defclean_v1", "defclean_v2", "defclean_coordguard"]
ARMS37 = ["clean", "attack", "delete_OR_backfill", "delete_entail_backfill", "coordguard_af_refill", "trustrag", "defclean_OR", "defclean_coordguard"]
checked = 0
for manifest_path in ["results/e36_prepare_manifest.json", "results/e37_manifest.json", "results/e38_manifest.json"] + [
    f"results/e36_{tag}{suffix}" for tag in ("Meta-Llama-3-8B-Instruct-4bit", "Mistral-7B-Instruct-v0.3-4bit")
    for suffix in ("_manifest.json", "_evaluation_manifest.json")]:
    for path, digest in json.load(open(manifest_path))["inputs"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, (manifest_path, path)
for tag in ("Meta-Llama-3-8B-Instruct-4bit", "Mistral-7B-Instruct-v0.3-4bit"):
    cal = json.load(open(f"results/e36_{tag}_calibration.json"))
    ids = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][:20]
    assert cal["ids"] == ids and set(keyed(f"results/e36_{tag}_calibration_rows.jsonl")) == set(ids)
    for d in ("hotpotqa", "msmarco"):
        targets = {t.id: t for t in load(d)[0][50:100]}
        rows = keyed(f"results/e36_{tag}_{d}_k10.jsonl")
        context = keyed(f"data/cache/e36_contexts_{d}.jsonl")
        assert set(rows) == set(targets) and len(rows) == 50
        for tid, r in rows.items():
            assert r["context_hashes"] == passage_hashes(context[tid]["pool"][:10])
            assert r["labels"] == [c["label"] for c in context[tid]["pool"][:10]]
            assert r["flags_v1"] == np.flatnonzero((np.array(r["entail_v1"]) >= .01) |
                                                        (np.array(r["attn_z"]) >= cal["zmin"])).tolist()
            for a in ARMS36:
                t = targets[tid]
                assert r[a]["correct"] == bool(correct(r[a]["resp"], t.correct)), (tid, a)
                assert r[a]["endorsed"] == bool(endorses(r[a]["resp"], t.incorrect)), (tid, a)
                checked += 1
targets = {t.id: t for t in load("nq", prefix=False)[0]}
expected = {r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")[20:]}
rows = keyed("results/e37_composite_nq_k10.jsonl")
assert set(rows) == expected and len(rows) == 80
for tid, r in rows.items():
    assert r["capture_index"] != r["poison_index"]
    assert set(r["variants"]) == {"1", "2", "3", "4"}
    state = json.load(open(f"results/checkpoints/e37/{tid}.json"))
    candidates = []
    for j, v in r["variants"].items():
        pool = state["variants"][j]["pool"]
        assert passage_hashes(pool[:10]) == v["context_hashes"]
        assert sum(c["label"] != "clean" for c in pool[:10]) <= 1
        assert all(c["poison_index"] in (-1, int(j)) for c in pool)
        for c in v["candidates"]:
            assert c["capture_index"] != int(j)
            assert c["flags_OR"] == np.flatnonzero((np.array(c["entail"]) >= .01) | (np.array(v["attn_z"]) >= 0)).tolist()
            if v["poison_slots"]:
                candidates.append(c)
    if candidates:
        best = min(candidates, key=lambda c: (c["poison_recall"], -c["clean_flag_count"], c["poison_index"], c["capture_index"]))
        assert (best["capture_index"], best["poison_index"]) == (r["capture_index"], r["poison_index"])
    for a in ARMS37:
        t = targets[tid]
        assert r[a]["correct"] == bool(correct(r[a]["resp"], t.correct)), (tid, a)
        assert r[a]["endorsed"] == bool(endorses(r[a]["resp"], t.incorrect)), (tid, a)
        checked += 1
assert len(keyed("results/e38_gate_cache.jsonl")) == 100
assert json.load(open("results/remaining_runs_summary.json"))["gate_replay"]["historical_printed_rates_reproduced"]
print(f"PASS: 200 reader-transfer targets, 80 composite targets, 100 cached gate targets; {checked} raw response scores; frozen manifests and identity/selection checks.")
