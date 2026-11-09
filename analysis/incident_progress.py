"""Read-only queue/checkpoint coverage; no model loading or outcome analysis."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from antivenom.continuation import read_rows, save


def alive(pid):
    if not pid: return False
    try: os.kill(pid,0); return True
    except ProcessLookupError: return False


def checkpoint_counts(folder, swarm=False):
    files = list(Path(folder).glob("*.json"))
    arms = 0
    for path in files:
        row = json.load(path.open())
        if swarm:
            arms += int("attacked" in row.get("publisher",{})) + int("clean" in row.get("publisher",{}))
            arms += sum(len(r["answers"]) for r in row.get("receivers",{}).values())
        else: arms += len(row.get("answers",{}))
    return {"checkpointed_cases":len(files),"saved_result_arms":arms}


def main():
    state = json.load(open("results/incident_queue_status.json"))
    counts = {}
    for mode,engine,total,per_case in [("base","contriever",80,24),("prefixfree","contriever",80,18),
                                      ("recurrence","contriever",160,14),("e5","e5",80,22)]:
        counts[mode] = {"complete_cases":len(read_rows(f"results/incident_{mode}_{engine}.jsonl")),
            "planned_cases":total,"planned_result_arms_per_case":per_case,
            **checkpoint_counts(f"results/checkpoints/incident_cases/{mode}_{engine}")}
    counts["swarm"] = {"complete_targets":len(read_rows("results/incident_swarm.jsonl")),"planned_targets":80,
        "planned_publisher_and_receiver_arms_per_target":74,
        **checkpoint_counts("results/checkpoints/incident_swarm",swarm=True)}
    counts["memform"] = {"complete_families":len(read_rows("results/incident_memform.jsonl")),"planned_families":212,
        "planned_memory_condition_arms_per_family":14,**checkpoint_counts("results/checkpoints/incident_memform")}
    counts["calibration"] = {engine:len(read_rows(f"results/incident_calibration_{engine}_rows.jsonl")) for engine in ("contriever","e5")}
    report = {"checked_utc":datetime.now(timezone.utc).isoformat(),"queue":state,
        "process_alive":{key:alive(state.get(key)) for key in ("queue_pid","child_pid")},"counts":counts,
        "counting_note":"Saved result arms are not generation-call counts: TrustRAG has multiple internal generations, and MemForm has memory compilation plus decisions."}
    p=Path("results/performance_validation.json")
    if p.exists():
        choice=json.load(p.open());report["runtime_configuration"]={key:choice[key] for key in ("accepted","selected_configuration","all_exact")}
    save("results/incident_progress.json",report)
    print(json.dumps(report,indent=2))


if __name__ == "__main__": main()
