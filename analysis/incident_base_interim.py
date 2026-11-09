"""Audit and summarize the completed base scope without waiting for later phases."""
import hashlib
import importlib.util
import json
from pathlib import Path

from antivenom.continuation import freeze, read_rows, save
from antivenom.poisonedrag import load
from incident_summary import summarize


def main():
    rows = read_rows("results/incident_base_contriever.jsonl")
    expected = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][20:]
    assert len(rows) == len({r["id"] for r in rows}) == 80
    assert {r["id"] for r in rows} == set(expected)
    checkpoints = [f"results/checkpoints/incident_cases/base_contriever/{hashlib.sha256(r['id'].encode()).hexdigest()}.json" for r in rows]
    freeze("results/incident_base_interim_manifest.json", [__file__, "analysis/incident_summary.py",
        "analysis/continuation_stats.py", "tests/incident_integrity.py", "src/antivenom/qa.py",
        "results/incident_base_contriever.jsonl", "results/incident_base_contriever_manifest.json",
        "results/incident_base_contriever_evaluation_manifest.json", "results/incident_power.json", *checkpoints],
        {"scope": "complete base only; later incident phases and full suite integrity remain pending"})
    for name in ("incident_queue_manifest.json", "remaining_queue_manifest_v2.json",
                 "performance_runtime_manifest.json", "extraction_resilience_manifest.json",
                 "performance_validation_manifest.json", "performance_choice_frozen.json",
                 "swarm_track4_manifest.json", "incident_base_contriever_manifest.json",
                 "incident_base_contriever_evaluation_manifest.json"):
        manifest = json.load(open("results/" + name))
        for path, digest in manifest["inputs"].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, (name, path)
    spec = importlib.util.spec_from_file_location("original_incident_integrity", "tests/incident_integrity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    targets = {t.id: t for t in load("nq")[0]}
    checks = 0
    for row, filename in zip(rows, checkpoints):
        saved = json.load(open(filename))
        assert saved["answers"] == row["answers"] and len(row["answers"]) == 24
        assert row["artifact"]["sample_sha256"] == hashlib.sha256(targets[row["id"]].poison[0].encode()).hexdigest()
        assert row["mistaken_artifact"]["sample_sha256"] == hashlib.sha256(saved["clean_context"][0]["text"].encode()).hexdigest()
        for arm, answer in row["answers"].items():
            condition = arm.split(":")[0]
            pool = saved[condition + "_context"]
            module.check_answer(answer, targets[row["id"]], pool)
            assert row[condition + "_hashes"] == [hashlib.sha256(p["text"].encode()).hexdigest() for p in pool[:10]]
            checks += 1
    valid = [r for r in rows if r["artifact"]["question"].strip() and r["artifact"]["claim"].strip()]
    result = {"scope": "Completed used-question base evaluation only, not swarm or fresh confirmation",
        "base_integrity": {"passed": True, "independent_targets": 80, "checked_answers": checks,
                           "full_suite_integrity": "pending"},
        "capture_counts": {"nonblank": len(valid), "blank": len(rows) - len(valid),
                           "mistaken_nonblank": sum(bool(r["mistaken_artifact"]["question"].strip()
                                                      and r["mistaken_artifact"]["claim"].strip()) for r in rows)},
        "all_targets": summarize(rows),
        "nonblank_secondary": summarize(valid) if len(valid) >= 2 else None,
        "correct_and_endorsed_overlap": {arm: sum(bool(r["answers"][arm]["correct"] and r["answers"][arm]["endorsed"]) for r in rows)
                                         for arm in rows[0]["answers"]},
        "limitations": ["automated rules, blind scoring deferred", "used NQ questions",
                        "nonblank capture is not human-validated semantics", "no swarm claim from this scope",
                        "deployed thresholds are not matched-recall operating points"]}
    save("results/incident_base_interim_summary.json", result)
    lines = ["Completed incident base scope only (80 used NQ questions); not swarm evidence",
             f"Base-only integrity: {checks} answers checked; full suite integrity pending",
             f"Nonblank captured signatures: {len(valid)}/80"]
    for method in ("none", "attention", "entail", "OR", "avidity", "cosine", "exact_hash",
                   "coordguard_af", "coordguard_gate", "trustrag", "gated_OR", "mistaken_capture_OR"):
        a = result["all_targets"]["rates"]["attacked:" + method]
        c = result["all_targets"]["rates"]["clean:" + method]
        lines.append(f"{method}: attacked endorsed={a['endorsed']['mean']:.4f}, correct={a['correct']['mean']:.4f}; clean correct={c['correct']['mean']:.4f}")
    Path("results/rescored/summaries/incident_base_interim_summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
