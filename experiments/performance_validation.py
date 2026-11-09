"""Calibration-only validation of a free allocator-cache cap; no recipe edits."""
import gc
import json
import random
import time
from importlib.metadata import version
from pathlib import Path

import mlx.core as mx
import numpy as np

from antivenom.continuation import freeze, keyed, read_rows, save
from antivenom.incident import IncidentLab

CAP = 256 * 1024 * 1024


def validate():
    source = ["docs/PERFORMANCE_RUNTIME_AMENDMENT.md", "experiments/performance_validation.py",
              "experiments/performance_guard.py", "experiments/run_incident_optimized.py",
              "results/incident_queue_manifest.json", "results/incident_weights_before.json",
              "src/antivenom/incident.py", "src/antivenom/continuation.py", "src/antivenom/llm.py",
              "src/antivenom/masked.py", "src/antivenom/antibody.py", "src/antivenom/retriever.py",
              "src/antivenom/qa.py", "results/e11a_flag_scores_nq_k10.jsonl",
              "data/external/poisonedrag/nq.json", "data/external/poisonedrag/nq-contriever.json",
              "data/external/poisonedrag/nq_target_corpus.json"]
    freeze("results/performance_validation_manifest.json", source,
           {"cap_bytes": CAP, "rounds": 2, "seed": 17,
            "versions": {n: version(n) for n in ("mlx", "mlx-lm", "torch", "transformers")}})
    lab = IncidentLab()
    lab.reader.fast = True
    lab.prewarm()
    ids = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][:20]
    cases = []
    for tid in ids:
        t = lab.by[tid]
        pool = lab.retrieve(t)
        ids_encoded, _ = lab.reader.prompt(t.question, [p["text"] for p in pool[:10]])
        cases.append((len(ids_encoded), tid, pool))
    cases.sort(key=lambda c: (c[0], c[1]))
    chosen = [cases[i] for i in (0, len(cases)//2, len(cases)-1)]
    previous = mx.set_cache_limit(CAP)
    mx.set_cache_limit(previous)

    def one(tid, pool):
        t = lab.by[tid]
        start = time.perf_counter()
        extracted = lab.immunologist.analyse(t.poison[0])
        artifact = {"question": extracted.question, "claim": extracted.false_claim}
        answer = lab.run_method("OR", t, t.question, pool, artifact, t.poison[0], {})
        mx.synchronize()
        return {"signature": artifact, "answer": answer, "seconds": time.perf_counter()-start,
                "active_memory": mx.get_active_memory(), "free_cache_memory": mx.get_cache_memory()}

    # Full pipeline warmup, calibration only, not part of the timing pairs.
    one(chosen[0][1], chosen[0][2])
    records = []
    try:
        for repeat in range(2):
            for tokens, tid, pool in chosen:
                order = ["default", "capped"]
                random.Random(f"17:{repeat}:{tid}").shuffle(order)
                pair = {"id": tid, "round": repeat, "prompt_tokens": tokens, "order": order}
                for setting in order:
                    mx.synchronize(); mx.clear_cache(); gc.collect()
                    mx.set_cache_limit(previous if setting == "default" else CAP)
                    if hasattr(mx, "reset_peak_memory"): mx.reset_peak_memory()
                    pair[setting] = one(tid, pool)
                    pair[setting]["peak_memory"] = mx.get_peak_memory()
                    print("allocator validation", repeat, tid, setting, pair[setting]["seconds"], flush=True)
                a, b = pair["default"], pair["capped"]
                keys = ("resp", "flags", "detection", "final_context_hashes")
                pair["exact_match"] = a["signature"] == b["signature"] and all(a["answer"][k] == b["answer"][k] for k in keys)
                pair["runtime_ratio"] = b["seconds"] / a["seconds"]
                records.append(pair)
                save("results/performance_validation_progress.json", {"records": records})
    finally:
        mx.synchronize(); mx.clear_cache(); mx.set_cache_limit(previous)
    ratios = [r["runtime_ratio"] for r in records]
    total_ratio = sum(r["capped"]["seconds"] for r in records)/sum(r["default"]["seconds"] for r in records)
    exact = all(r["exact_match"] for r in records)
    for tid in {r["id"] for r in records}:
        runs = [r[s] for r in records if r["id"] == tid for s in ("default", "capped")]
        reference = runs[0]
        exact = exact and all(reference["signature"] == r["signature"] and
            all(reference["answer"][k] == r["answer"][k] for k in ("resp", "flags", "detection", "final_context_hashes")) for r in runs)
    valid_signatures = all(r[s]["signature"]["question"].strip() and r[s]["signature"]["claim"].strip()
                           for r in records for s in ("default", "capped"))
    accepted = bool(exact and valid_signatures and np.median(ratios) <= .95 and total_ratio <= 1.)
    result = {"calibration_ids": ids, "selected_cases": [{"id": tid, "prompt_tokens": n} for n,tid,_ in chosen],
        "records": records, "all_exact": exact, "valid_signatures": bool(valid_signatures), "median_paired_runtime_ratio": float(np.median(ratios)),
        "aggregate_runtime_ratio": total_ratio, "accepted": accepted,
        "selected_configuration": "free_allocator_cache_256MiB" if accepted else "original_default",
        "selected_cache_limit_bytes": CAP if accepted else previous, "original_default_cache_limit_bytes": previous,
        "scope": "Calibration-only infrastructure selection. No scientific performance claim, detector retuning, held-out outcomes or cached method timings."}
    save("results/performance_validation.json", result)
    freeze("results/performance_choice_frozen.json", ["results/performance_validation.json", "results/performance_validation_manifest.json"],
           {"configuration": result["selected_configuration"]})
    print("Runtime selected:", result["selected_configuration"], "exact matches:", exact, flush=True)
    return result


if __name__ == "__main__": validate()
