"""Freeze the supplemental plan before any E42 receiver outcomes; no model calls."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from antivenom.continuation import freeze, read_rows, save

PATH = Path("results/swarm_track4_manifest.json")
SOURCES = ["docs/SWARM_TRACK4_PROTOCOL.md", __file__,
    "experiments/run_swarm_track4.py", "experiments/swarm_clean_reference.py",
    "analysis/swarm_track4_summary.py", "analysis/continuation_stats.py",
    "tests/swarm_track4_preflight.py", "experiments/incident_swarm.py",
    "src/antivenom/incident.py", "src/antivenom/continuation.py", "src/antivenom/qa.py",
    "src/antivenom/masked.py", "src/antivenom/llm.py", "src/antivenom/poisonedrag.py",
    "results/incident_queue_manifest.json", "results/remaining_queue_manifest_v2.json",
    "results/extraction_resilience_manifest.json", "results/performance_runtime_manifest.json",
    "results/performance_validation_manifest.json", "results/performance_choice_frozen.json",
    "results/incident_calibration_contriever_frozen.json", "results/incident_contriever_fidelity.json",
    "results/incident_calibration_contriever.json", "results/e11a_flag_scores_nq_k10.jsonl", "uv.lock"]


def main():
    if PATH.exists():
        manifest = json.load(PATH.open())
        for filename, digest in manifest["inputs"].items():
            assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, filename
        print("Existing Track 4 freeze verified")
        return
    assert not read_rows("results/incident_swarm.jsonl")
    assert not list(Path("results/checkpoints/incident_swarm").glob("*.json"))
    status = json.load(open("results/incident_queue_status.json"))
    assert "swarm" not in status["completed_phases"] and status["phase"] != "swarm"
    ids = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][20:]
    assert len(ids) == len(set(ids)) == 80
    settings = {"frozen_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Track 4 prospective exploratory extension; preexisting hackathon work",
        "ids": ids, "receiver_outcomes_at_freeze": 0, "focal_method": "shared_claim_OR",
        "primary_layout": "distinct_ids", "clean_reference_actual_calls": 480,
        "clean_accuracy_loss_margin": 0., "future_fresh_endorsement_NI_margin": .05,
        "human_scoring": "deferred; not passed", "current_mac_only": True,
        "original_scientific_queue": "unchanged", "supplement_waits_for_original_integrity": True}
    freeze(PATH, SOURCES, settings)
    save("results/swarm_track4_freeze_status.json", {"frozen": True, **settings})
    print("Track 4 protocol frozen before E42 outcomes; original queue unchanged")


if __name__ == "__main__":
    main()
