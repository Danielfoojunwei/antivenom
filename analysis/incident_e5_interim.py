"""Audit the completed E5 candidate-pool transfer scope with the unchanged suite analysis."""
import hashlib
import importlib.util
import json
from pathlib import Path

from antivenom.continuation import freeze, read_rows, save
from antivenom.poisonedrag import load
from incident_summary import summarize


def main():
    rows = read_rows("results/incident_e5_e5.jsonl")
    expected = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][20:]
    assert len(rows) == len({r["id"] for r in rows}) == 80
    assert {r["id"] for r in rows} == set(expected)
    paths = [f"results/checkpoints/incident_cases/e5_e5/{hashlib.sha256(r['id'].encode()).hexdigest()}.json" for r in rows]
    freeze("results/incident_e5_interim_manifest.json", [__file__, "analysis/incident_summary.py",
        "analysis/continuation_stats.py", "tests/incident_integrity.py", "src/antivenom/qa.py",
        "results/incident_e5_e5.jsonl", "results/incident_e5_e5_manifest.json",
        "results/incident_e5_e5_evaluation_manifest.json", *paths],
        {"scope": "complete E5 candidate-pool transfer scope only; later phases and full suite integrity pending; invokes unchanged predeclared analysis"})
    for name in ("incident_queue_manifest.json", "extraction_resilience_manifest.json",
                 "performance_runtime_manifest.json", "performance_validation_manifest.json",
                 "performance_choice_frozen.json", "swarm_track4_manifest.json",
                 "incident_e5_e5_manifest.json", "incident_e5_e5_evaluation_manifest.json"):
        for filename, digest in json.load(open("results/" + name))["inputs"].items():
            assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, (name, filename)
    spec = importlib.util.spec_from_file_location("original_incident_integrity", "tests/incident_integrity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    targets = {t.id: t for t in load("nq")[0]}
    checks = 0
    for row, path in zip(rows, paths):
        checkpoint = json.load(open(path))
        assert checkpoint["answers"] == row["answers"] and len(row["answers"]) == 22
        target = targets[row["target_id"]]
        assert row["artifact"]["sample_sha256"] == hashlib.sha256(target.poison[0].encode()).hexdigest()
        for arm, answer in row["answers"].items():
            condition = arm.split(":")[0]
            pool = checkpoint[condition + "_context"]
            module.check_answer(answer, target, pool)
            assert row[condition + "_hashes"] == [hashlib.sha256(p["text"].encode()).hexdigest() for p in pool[:10]]
            checks += 1
    valid = [r for r in rows if r["artifact"]["question"].strip() and r["artifact"]["claim"].strip()]
    result = {"scope": "Completed used-question E5 candidate-pool transfer context shift; captured passage excluded; E5 calibration frozen on 20 development calibration cases",
        "integrity": {"passed": True, "independent_targets": 80, "checked_answers": checks, "full_suite": "pending"},
        "capture_counts": {"nonblank": len(valid), "blank": 80-len(valid)},
        "all_targets": summarize(rows), "nonblank_secondary": summarize(valid) if len(valid) >= 2 else None,
        "limitations": ["used questions; not fresh confirmation", "automated scoring, human review deferred",
            "swarm scope incomplete", "candidate pool originally selected by Contriever; not independent full-corpus retrieval", "nonblank capture is not validated semantics", "limited released poison diversity"]}
    save("results/incident_e5_interim_summary.json", result)
    lines = [f"E5 incident scope complete: 80 targets, {checks} answer checks; full suite integrity pending",
             f"Nonblank selected captures: {len(valid)}/80"]
    for method in ("none", "attention", "entail", "OR", "avidity", "cosine", "coordguard_gate", "trustrag", "gated_OR"):
        a = result["all_targets"]["rates"]["attacked:" + method]
        c = result["all_targets"]["rates"]["clean:" + method]
        lines.append(f"{method}: attacked endorsed={a['endorsed']['mean']:.4f}, correct={a['correct']['mean']:.4f}; clean correct={c['correct']['mean']:.4f}")
    Path("results/rescored/summaries/incident_e5_interim_summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
