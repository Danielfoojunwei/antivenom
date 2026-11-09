"""Completed E42 audit and E42-only estimates; E45 and joint decision stay pending."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

from antivenom.continuation import freeze, read_rows, save
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses
from continuation_stats import holm, interval
from incident_summary import summarize as suite_summary
from swarm_track4_summary import bounded_comparison, harm_estimate, verify_manifest

METHODS = ("isolated_attention", "shared_record_ids", "shared_sample_cosine",
           "shared_claim_entail", "shared_claim_OR", "coordguard_gate")
LAYOUTS = ("distinct_ids", "shared_ids")


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def focused(rows, layout, focal="shared_claim_OR"):
    def outcomes(row, method, condition, metric):
        return np.array([float(row["receivers"][f"{layout}:agent{a}"]["answers"]
                               [f"{condition}:{method}"][metric]) for a in (1, 2, 3)])

    rates = {}
    for method in METHODS:
        rates[method] = {}
        for condition in ("clean", "attacked"):
            rates[method][condition] = {}
            for metric in ("correct", "endorsed"):
                values = [outcomes(r, method, condition, metric).mean() for r in rows]
                rates[method][condition][metric] = {"mean": float(np.mean(values)), "ci95": interval(values)}
    comparisons, harms = {}, {}
    for baseline in ("shared_record_ids", "shared_sample_cosine"):
        benefit = [(outcomes(r, baseline, "attacked", "endorsed")
                    - outcomes(r, focal, "attacked", "endorsed")).mean() for r in rows]
        comparisons["attack_benefit_vs:" + baseline] = bounded_comparison(benefit, family_size=5)
        differences = [outcomes(r, focal, "clean", "correct")
                       - outcomes(r, baseline, "clean", "correct") for r in rows]
        comparisons["clean_benefit_vs:" + baseline] = bounded_comparison([x.mean() for x in differences], family_size=5)
        harms[baseline] = harm_estimate([bool((x < 0).any()) for x in differences])
    # Retain the frozen five-test family conservatively while E45 is unavailable.
    pending = "clean_benefit_vs:untreated_PENDING"
    adjusted = holm({**{k: v["one_sided_p"] for k, v in comparisons.items()}, pending: 1.})
    for key, value in comparisons.items():
        value["holm_p_conservative_pending_fifth"] = adjusted[key]
    return {"independent_incidents": len(rows), "receivers_per_incident": 3,
            "focal_method": focal, "rates": rates, "comparisons": comparisons,
            "clean_receiver_loss": harms, "joint_claim": "pending actual untreated clean E45 reference",
            "multiplicity_note": "Frozen five-comparison family retained; missing E45 endpoint reserves a p=1 slot solely for conservative interim Holm adjustment. No untreated result is imputed. Full five-test analysis will be rerun unchanged after E45."}


def main():
    rows = read_rows("results/incident_swarm.jsonl")
    expected = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][20:]
    assert len(rows) == len({r["id"] for r in rows}) == 80
    assert {r["id"] for r in rows} == set(expected)
    paths = [f"results/checkpoints/incident_swarm/{sha(r['id'])}.json" for r in rows]
    manifests = sorted(set(Path("results").glob("incident_*manifest.json"))
                       | set(Path("results").glob("incident_*frozen.json")))
    for path in manifests:
        verify_manifest(path)
    for name in ("remaining_queue_manifest_v2.json", "performance_runtime_manifest.json",
                 "performance_validation_manifest.json", "performance_choice_frozen.json",
                 "extraction_resilience_manifest.json", "swarm_track4_manifest.json"):
        verify_manifest("results/" + name)
    freeze("results/incident_swarm_interim_manifest.json", [__file__,
           "analysis/incident_summary.py", "analysis/swarm_track4_summary.py",
           "analysis/continuation_stats.py", "tests/incident_integrity.py",
           "src/antivenom/qa.py", "results/incident_swarm.jsonl",
           "results/incident_swarm_manifest.json", "results/swarm_track4_manifest.json", *paths],
           {"scope": "Completed E42 only; E45, MemForm and whole-suite integrity pending",
            "statistics": "Existing frozen functions; conservative five-test accounting with unavailable E45 slot p=1; no imputed untreated outcome"})
    spec = importlib.util.spec_from_file_location("original_integrity", "tests/incident_integrity.py")
    integrity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(integrity)
    targets = {t.id: t for t in load("nq")[0]}
    checks = 0
    for row, path in zip(rows, paths):
        full = json.loads(Path(path).read_text())
        target = targets[row["target_id"]]
        assert row["id"] == row["target_id"] == full["id"]
        assert row["publisher"] == {k: v for k, v in full["publisher"].items() if k != "context"}
        publisher = full["publisher"]
        assert publisher["captured"] is True and publisher["artifact"]["sample_sha256"] == sha(target.poison[0])
        assert publisher["record_blocklist"] == [publisher["context"][i]["doc_id"] for i in publisher["attacked"]["flags"]]
        integrity.check_answer(publisher["attacked"], target, publisher["context"])
        for answer in (publisher["attacked"], publisher["clean"]):
            assert answer["correct"] == bool(correct(answer["resp"], target.correct))
            assert answer["endorsed"] == bool(endorses(answer["resp"], target.incorrect))
        claim = json.loads(full["messages"]["claim"]["wire"])["payload"]
        assert set(claim) == {"schema", "incident_id", "question", "claim", "sample_sha256"}
        for kind, message in full["messages"].items():
            assert message["sha256"] == sha(message["wire"]) and message["bytes"] == len(message["wire"].encode())
            assert row["messages"][kind] == ({k: v for k, v in message.items() if k != "wire"} if kind == "sample" else message)
        assert set(full["receivers"]) == {f"{layout}:agent{a}" for layout in LAYOUTS for a in (1, 2, 3)}
        for rid, receiver in full["receivers"].items():
            assert receiver["captured"] is False and len(receiver["answers"]) == 12
            assert len(receiver["clean_record_ids"]) >= 10
            public = row["receivers"][rid]
            for condition in ("clean", "attacked"):
                metadata = [{k: v for k, v in p.items() if k != "text"} | {"sha256": sha(p["text"])}
                            for p in receiver[condition + "_context"]]
                assert public[condition + "_context_metadata"] == metadata
            for arm, answer in receiver["answers"].items():
                condition, method = arm.split(":", 1)
                integrity.check_answer(answer, target, receiver[condition + "_context"])
                normalized = copy.deepcopy(answer)
                if "sample" in normalized["receiver_state"]["registry"]:
                    normalized["receiver_state"]["registry"]["sample"].pop("text")
                assert public["answers"][arm] == normalized
                state = answer["receiver_state"]
                kind = {"shared_claim_entail": "claim", "shared_claim_OR": "claim",
                        "shared_sample_cosine": "sample", "shared_record_ids": "blocklist"}.get(method)
                assert state["captured"] is False
                if kind:
                    message = full["messages"][kind]
                    assert state["messages_received"] == [message["sha256"]]
                    assert state["registry"] == {kind: json.loads(message["wire"])["payload"]}
                else:
                    assert state["messages_received"] == [] and state["registry"] == {}
                checks += 1
    valid = [r for r in rows if r["publisher"]["artifact"]["question"].strip()
             and r["publisher"]["artifact"]["claim"].strip()]
    result = {"scope": "Completed used-question E42; prospective exploratory shared protection, E45 pending",
              "integrity": {"passed": True, "receiver_answer_checks": checks,
                  "publisher_attacked_context_checks": 80, "publisher_clean_score_checks_only": 80,
                  "total_saved_answers": 5920, "full_original_suite": "pending", "reader_weights_after": "pending"},
              "capture_counts": {"all": 80, "nonblank": len(valid), "blank": 80 - len(valid)},
              "primary_distinct_ids": focused(rows, "distinct_ids"),
              "secondary_shared_ids": focused(rows, "shared_ids"),
              "secondary_nonblank_distinct_ids": focused(valid, "distinct_ids") if len(valid) >= 2 else None,
              "original_suite_analysis": {layout: suite_summary(
                  [{"target_id": r["target_id"], "answers": v["answers"]}
                   for r in rows for v in r["receivers"].values() if v["layout"] == layout], repeated=True)
                  for layout in LAYOUTS},
              "limitations": ["E45 untreated clean endpoint unavailable; joint no-harm conclusion pending",
                  "human scoring/semantic review deferred; nonblank is not semantic validation",
                  "80 used incidents; receivers and layouts are not independent incidents",
                  "homogeneous serial local agents, limited released variants; no authenticated publication or autonomous contagion",
                  "R2 explicitly post-start extraction policy; all targets retained"]}
    save("results/incident_swarm_interim_summary.json", result)
    print(json.dumps({"integrity": result["integrity"], "capture_counts": result["capture_counts"],
                      "primary": result["primary_distinct_ids"]["comparisons"]}, indent=2))


if __name__ == "__main__":
    main()
