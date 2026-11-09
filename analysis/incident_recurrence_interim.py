"""Completed recurrence scope: two sessions per incident, never independent trials."""
import hashlib
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

from antivenom.continuation import freeze, read_rows, save
from antivenom.poisonedrag import load
from incident_summary import summarize


def main():
    rows = read_rows("results/incident_recurrence_contriever.jsonl")
    order = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][20:]
    expected = {f"{tid}:s{s}" for tid in order for s in (0, 1)}
    assert len(rows) == len({r["id"] for r in rows}) == 160
    assert {r["id"] for r in rows} == expected
    paths = [f"results/checkpoints/incident_cases/recurrence_contriever/{hashlib.sha256(r['id'].encode()).hexdigest()}.json" for r in rows]
    freeze("results/incident_recurrence_interim_manifest.json", [__file__, "analysis/incident_summary.py",
        "analysis/continuation_stats.py", "tests/incident_integrity.py", "src/antivenom/qa.py",
        "results/incident_recurrence_contriever.jsonl", "results/incident_recurrence_contriever_manifest.json",
        "results/incident_recurrence_contriever_evaluation_manifest.json", "results/e18_recurrence_nq_k10.jsonl", *paths],
        {"scope": "complete recurrence only, two sessions clustered within 80 incidents; full suite pending"})
    for name in ("incident_queue_manifest.json", "extraction_resilience_manifest.json",
                 "performance_runtime_manifest.json", "performance_validation_manifest.json",
                 "performance_choice_frozen.json", "swarm_track4_manifest.json",
                 "incident_recurrence_contriever_manifest.json", "incident_recurrence_contriever_evaluation_manifest.json"):
        for filename, digest in json.load(open("results/" + name))["inputs"].items():
            assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, (name, filename)
    spec = importlib.util.spec_from_file_location("original_incident_integrity", "tests/incident_integrity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    targets = {t.id: t for t in load("nq")[0]}
    historical = {r["id"]: r for r in read_rows("results/e18_recurrence_nq_k10.jsonl")}
    checks, grouped = 0, defaultdict(list)
    for row, path in zip(rows, paths):
        tid = row["target_id"]
        checkpoint = json.load(open(path))
        assert checkpoint["answers"] == row["answers"] and len(row["answers"]) == 14
        assert row["question"] == historical[tid]["sessions"][row["session"]]["question"]
        target = targets[tid]
        assert row["artifact"]["sample_sha256"] == hashlib.sha256(target.poison[0].encode()).hexdigest()
        for arm, answer in row["answers"].items():
            condition = arm.split(":")[0]
            pool = checkpoint[condition + "_context"]
            module.check_answer(answer, target, pool)
            assert row[condition + "_hashes"] == [hashlib.sha256(p["text"].encode()).hexdigest() for p in pool[:10]]
            checks += 1
        grouped[tid].append(row)
    assert set(grouped) == set(order)
    for cases in grouped.values():
        assert {r["session"] for r in cases} == {0, 1}
        assert len({(r["artifact"]["question"], r["artifact"]["claim"]) for r in cases}) == 1
    valid_ids = {tid for tid, cases in grouped.items() if all(r["artifact"]["question"].strip()
                and r["artifact"]["claim"].strip() for r in cases)}
    valid = [r for r in rows if r["target_id"] in valid_ids]
    result = {"scope": "Completed used-question recurrence, actual reretrieval, captured passage excluded",
        "integrity": {"passed": True, "independent_incidents": 80, "sessions": 160,
                      "checked_answers": checks, "full_suite": "pending"},
        "capture_counts": {"nonblank_incidents": len(valid_ids), "blank_incidents": 80-len(valid_ids)},
        "all_targets": summarize(rows, repeated=True),
        "nonblank_secondary": summarize(valid, repeated=True) if len(valid_ids) >= 2 else None,
        "limitations": ["used questions and stored paraphrases, not fresh confirmation",
            "two sessions are correlated within incident", "no swarm receiver outcomes",
            "automated scoring and nonblank semantics not independently human validated",
            "historical E18 stored-context results are a separate evaluation"]}
    save("results/incident_recurrence_interim_summary.json", result)
    lines = [f"Recurrence complete: 80 independent incidents, 160 sessions, {checks} answer checks; full suite pending",
             f"Nonblank signatures: {len(valid_ids)}/80 incidents"]
    for method in ("none", "attention", "OR", "cosine", "coordguard_gate", "trustrag", "gated_OR"):
        a = result["all_targets"]["rates"]["attacked:" + method]
        c = result["all_targets"]["rates"]["clean:" + method]
        lines.append(f"{method}: attacked endorsed={a['endorsed']['mean']:.4f}, correct={a['correct']['mean']:.4f}; clean correct={c['correct']['mean']:.4f}")
    Path("results/rescored/summaries/incident_recurrence_interim_summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
