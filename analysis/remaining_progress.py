"""Read the queue and per-arm checkpoints without loading any model."""
import json
import os
from pathlib import Path

from antivenom.continuation import read_rows, save

state = json.load(open("results/remaining_queue_status.json"))
alive = {}
for name in ("queue_pid", "child_pid"):
    pid = state.get(name)
    try:
        if pid is None:
            alive[name] = False
        else:
            os.kill(pid, 0)
            alive[name] = True
    except ProcessLookupError:
        alive[name] = False
counts = {}
for tag in ("Meta-Llama-3-8B-Instruct-4bit", "Mistral-7B-Instruct-v0.3-4bit"):
    counts[tag] = {"calibration": len(read_rows(f"results/e36_{tag}_calibration_rows.jsonl"))}
    for dataset in ("hotpotqa", "msmarco"):
        path = Path(f"results/checkpoints/e36/{tag}/{dataset}")
        checkpoints = [json.load(p.open()) for p in path.glob("*.json")] if path.exists() else []
        counts[tag][dataset] = {"complete_targets": len(read_rows(f"results/e36_{tag}_{dataset}_k10.jsonl")),
            "target_total": 50, "checkpointed_targets": len(checkpoints),
            "saved_answer_arms": sum(sum(isinstance(v, dict) and "resp" in v for v in r.values()) for r in checkpoints)}
counts["composite_complete_targets"] = len(read_rows("results/e37_composite_nq_k10.jsonl"))
counts["gate_cache_complete_targets"] = len(read_rows("results/e38_gate_cache.jsonl"))
result = {"queue": state, "process_alive": alive, "counts": counts,
          "human_validation": json.load(open("results/human_validation_status.json"))}
save("results/remaining_progress.json", result)
print(json.dumps(result, indent=2))
