"""Post-hoc component audit of COMPLETED saved outputs; never invokes a model.

This is a reproducibility freeze after exploratory inspection, not a new
preregistration. Original scientific source, answers and thresholds stay intact.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
EMPTY_HISTORY_MEMORY = "No reusable decision rule has been learned yet."
INPUTS = (
    "results/incident_memform.jsonl",
    "results/incident_memform_manifest.json",
    "results/incident_memform_integrity.json",
    "results/incident_memform_capture_audit.json",
    "results/incident_swarm.jsonl",
    "results/swarm_clean_reference.jsonl",
    "results/swarm_clean_reference_integrity.json",
    "results/swarm_track4_evaluation_manifest.json",
    "results/incident_queue_status.json",
    "results/swarm_track4_status.json",
    "src/antivenom/incident.py",
    "experiments/incident_memform.py",
    "data/external/memform/reference/memform/eval/core.py",
)


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest_text(value):
    return digest_bytes(value.encode())


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def read_json(name):
    return json.loads((ROOT / name).read_text())


def read_rows(name):
    rows = [json.loads(line) for line in (ROOT / name).read_text().splitlines() if line.strip()]
    assert len({row["id"] for row in rows}) == len(rows), name
    return rows


def freeze(prefix):
    paths = [*INPUTS, str(Path(__file__).relative_to(ROOT))]
    hashes = {name: digest_bytes((ROOT / name).read_bytes()) for name in paths}
    scientific_spec = {
        "schema": "antivenom.component_utility_audit.v1",
        "classification": "posthoc descriptive completed-record audit; not fresh confirmation",
        "specification_note": "Frozen after exploratory inspection; this is not a prospective preregistration.",
        "source_and_inputs": hashes,
        "replayed_original_rules": {"entailment_threshold": .01, "attention_z_threshold": 0.},
        "comparison": "OR minus entailment at their original frozen operating points",
        "scopes": ["MemForm212 families", "swarm80 incidents separately by layout"],
        "subsets": ["all targets", "identically paired nonblank selected capture"],
        "statistics": "descriptive counts and incident/family-averaged point effects only; no new significance or tuned threshold",
        "no_inference": True,
    }
    path = Path(str(prefix) + "_manifest.json")
    if path.exists():
        manifest = json.loads(path.read_text())
        assert {key: manifest[key] for key in scientific_spec} == scientific_spec, "Audit source/input changed; use a new version."
    else:
        manifest = {**scientific_spec, "frozen_utc": datetime.now(timezone.utc).isoformat()}
        path.write_text(canonical(manifest))
    return path, manifest


def flags(answer, length):
    values = answer["flags"]
    assert values == sorted(set(values))
    assert all(type(index) is int and 0 <= index < length for index in values)
    return set(values)


def validate_vectors(entail, combined):
    e = entail["detection"]["entail"]
    assert e == combined["detection"]["entail"], "NLI component changed between saved arms"
    z = combined["detection"]["attention_z"]
    assert len(e) == len(z) and len(e) > 0
    assert all(math.isfinite(value) for value in [*e, *z])
    ef, cf = flags(entail, len(e)), flags(combined, len(e))
    af = {index for index, value in enumerate(z) if value >= 0.}
    assert ef == {index for index, value in enumerate(e) if value >= .01}
    assert cf == ef | af, "Saved OR flags do not equal original component union"
    return ef, cf, af, len(e)


def decisions(answer):
    return answer["tasks"] if "tasks" in answer else {"answer": answer}


def metric(answer, name):
    return mean(float(value[name]) for value in decisions(answer).values())


def same_predictions(a, b):
    aa, bb = decisions(a), decisions(b)
    assert set(aa) == set(bb)
    # QA lacks an explicit prediction label, so compare the actual saved response.
    return all(aa[key].get("prediction", aa[key]["resp"]) == bb[key].get("prediction", bb[key]["resp"]) for key in aa)


def describe_pair(scope, condition, identity, receiver, nonblank, entail, combined,
                  untreated, input_hashes, expected_context, labels=None, no_memory=None):
    ef, cf, af, length = validate_vectors(entail, combined)
    assert len(input_hashes) == length
    for answer in (entail, combined):
        expected = expected_context(answer["flags"])
        actual = answer.get("kept_hashes", answer.get("final_context_hashes"))
        assert actual == expected, "Saved resulting context disagrees with original filtering/refill recipe"
    extra = cf - ef
    item = {
        "scope": scope, "condition": condition, "id": identity,
        "receiver": receiver, "nonblank_capture": nonblank,
        "input_passages": length, "distinct_input_passage_hashes": len(set(input_hashes)),
        "entail_flags": sorted(ef), "attention_flags": sorted(af), "OR_flags": sorted(cf),
        "OR_only_flags": sorted(extra), "entail_only_flags": sorted(ef - cf),
        "overlap_flags": sorted(ef & af), "OR_only_removal_fraction": len(extra) / length,
        "entail_removal_fraction": len(ef) / length, "OR_removal_fraction": len(cf) / length,
        "entail_removed_all": len(ef) == length, "OR_removed_all": len(cf) == length,
        "OR_adds_flags_to_empty_entail": not ef and bool(cf),
        "same_resulting_context": entail.get("kept_hashes", entail.get("final_context_hashes")) == combined.get("kept_hashes", combined.get("final_context_hashes")),
        "same_predictions": same_predictions(entail, combined),
        "answers": {}, "review_status": "unreviewed; this inventory is unblinded audit metadata, not a human-validation result",
    }
    if labels is not None:
        assert len(labels) == length
        item["OR_only_label_counts"] = dict(Counter("clean" if labels[i] == "clean" else "poison" for i in extra))
    methods = {"entail": entail, "OR": combined, "untreated_same_condition": untreated}
    if no_memory is not None:
        methods["actual_no_memory_prompt"] = {"tasks": no_memory}
    for method, answer in methods.items():
        item["answers"][method] = {
            "correct": metric(answer, "correct"), "endorsed": metric(answer, "endorsed"),
            "task_count": len(decisions(answer)),
            "response_hashes": {key: digest_text(value["resp"]) for key, value in decisions(answer).items()},
            "prediction_labels": {key: value.get("prediction") for key, value in decisions(answer).items()},
            "parse_failures": sum(value.get("prediction", "QA_not_applicable") is None for value in decisions(answer).values()),
        }
        if "memory" in answer:
            item["answers"][method]["compiled_memory_sha256"] = digest_text(answer["memory"])
            item["answers"][method]["native_empty_history_fallback"] = answer["memory"] == EMPTY_HISTORY_MEMORY
    item["clean_or_correctness_loss_vs_entail"] = item["answers"]["entail"]["correct"] > item["answers"]["OR"]["correct"]
    item["clean_or_correctness_gain_vs_entail"] = item["answers"]["entail"]["correct"] < item["answers"]["OR"]["correct"]
    if "gold_token_clean_after" in entail:
        item["gold_token_proxy_lost_vs_entail"] = entail["gold_token_clean_after"] > 0 and combined["gold_token_clean_after"] == 0
    return item


def family_mean(cases, key):
    grouped = defaultdict(list)
    for case in cases:
        grouped[case["id"]].append(key(case))
    return mean(mean(values) for values in grouped.values())


def summarize(cases):
    if not cases:
        return {"independent_units": 0, "status": "empty selected subset"}
    ids = {case["id"] for case in cases}
    methods = sorted(cases[0]["answers"])
    assert all(sorted(case["answers"]) == methods for case in cases)
    rates = {method: {name: family_mean(cases, lambda case: case["answers"][method][name]) for name in ("correct", "endorsed")} for method in methods}
    values = {
        "independent_units": len(ids), "context_observations": len(cases),
        "unit": "family or incident, never receiver/task as independent incident",
        "actual_task_observations_per_method": sum(case["answers"]["OR"]["task_count"] for case in cases),
        "all_vectors_and_contexts_validated": True,
        "contexts_with_OR_only_removals": sum(bool(case["OR_only_flags"]) for case in cases),
        "contexts_with_repeated_input_hashes": sum(case["distinct_input_passage_hashes"] < case["input_passages"] for case in cases),
        "extra_removed_passages": sum(len(case["OR_only_flags"]) for case in cases),
        "total_initial_passages": sum(case["input_passages"] for case in cases),
        "entail_removed_all_contexts": sum(case["entail_removed_all"] for case in cases),
        "OR_removed_all_contexts": sum(case["OR_removed_all"] for case in cases),
        "OR_adds_flags_to_empty_entail_contexts": sum(case["OR_adds_flags_to_empty_entail"] for case in cases),
        "same_resulting_contexts": sum(case["same_resulting_context"] for case in cases),
        "same_predictions": sum(case["same_predictions"] for case in cases),
        "mean_removal_fraction": {name: family_mean(cases, lambda case: case[name + "_removal_fraction"]) for name in ("entail", "OR", "OR_only")},
        "rates": rates,
        "OR_minus_entail": {name: rates["OR"][name] - rates["entail"][name] for name in ("correct", "endorsed")},
        "contexts_correct_under_entail_wrong_under_OR": sum(case["clean_or_correctness_loss_vs_entail"] for case in cases),
        "contexts_wrong_under_entail_correct_under_OR": sum(case["clean_or_correctness_gain_vs_entail"] for case in cases),
        "independent_units_with_any_correctness_loss_vs_entail": len({case["id"] for case in cases if case["clean_or_correctness_loss_vs_entail"]}),
        "independent_units_with_any_correctness_gain_vs_entail": len({case["id"] for case in cases if case["clean_or_correctness_gain_vs_entail"]}),
        "correctness_changes_without_context_change": sum(case["clean_or_correctness_loss_vs_entail"] or case["clean_or_correctness_gain_vs_entail"] for case in cases if case["same_resulting_context"]),
    }
    if "actual_no_memory_prompt" in methods:
        values["OR_minus_actual_no_memory_prompt"] = {name: rates["OR"][name] - rates["actual_no_memory_prompt"][name] for name in ("correct", "endorsed")}
        values["OR_native_empty_history_fallback_contexts"] = sum(case["answers"]["OR"]["native_empty_history_fallback"] for case in cases)
        values["entail_native_empty_history_fallback_contexts"] = sum(case["answers"]["entail"]["native_empty_history_fallback"] for case in cases)
    if "OR_only_label_counts" in cases[0]:
        values["OR_only_passage_labels"] = dict(sum((Counter(case["OR_only_label_counts"]) for case in cases), Counter()))
        values["contexts_losing_all_gold_token_proxy_relative_entail"] = sum(case["gold_token_proxy_lost_vs_entail"] for case in cases)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-prefix", default="results/component_utility_audit_v1")
    args = parser.parse_args()
    prefix = ROOT / args.output_prefix
    assert prefix.parent.resolve() == (ROOT / "results").resolve(), "Audit outputs belong under results/"
    manifest_path, manifest = freeze(prefix)  # Must precede result generation.
    assert read_json("results/incident_queue_status.json")["status"] == "automated_incident_suite_complete"
    assert read_json("results/swarm_track4_status.json")["status"] == "automated_swarm_extension_complete"
    assert read_json("results/incident_memform_integrity.json")["passed"]
    assert read_json("results/swarm_clean_reference_integrity.json")["passed"]
    for original_manifest in ("results/incident_memform_manifest.json", "results/swarm_track4_evaluation_manifest.json"):
        for name, expected_hash in read_json(original_manifest)["inputs"].items():
            assert digest_bytes((ROOT / name).read_bytes()) == expected_hash, (original_manifest, name)
    mf = read_rows("results/incident_memform.jsonl")
    swarm = read_rows("results/incident_swarm.jsonl")
    refs = {row["id"]: row for row in read_rows("results/swarm_clean_reference.jsonl")}
    assert len(mf) == 212 and len(swarm) == len(refs) == 80
    assert set(refs) == {row["id"] for row in swarm}
    inventory = []
    for row in mf:
        nonblank = bool(row["artifact"]["question"].strip() and row["artifact"]["claim"].strip())
        for condition in ("clean", "poisoned"):
            entail, combined, untreated = (row["answers"][condition + ":" + method] for method in ("entail", "OR", "none"))
            assert entail["input_hashes"] == combined["input_hashes"] == untreated["input_hashes"]
            assert set(entail["tasks"]) == set(combined["tasks"]) == set(untreated["tasks"]) == set(row["no_memory"])
            inputs = entail["input_hashes"]
            for answer in (entail, combined):
                if not answer["kept_hashes"]:
                    assert answer["memory"] == EMPTY_HISTORY_MEMORY
            expected = lambda flagged: [value for index, value in enumerate(inputs) if index not in flagged]
            inventory.append(describe_pair("memform", condition, row["id"], None, nonblank, entail, combined,
                                           untreated, inputs, expected, no_memory=row["no_memory"]))
    for row in swarm:
        nonblank = bool(row["publisher"]["artifact"]["question"].strip() and row["publisher"]["artifact"]["claim"].strip())
        assert set(row["receivers"]) == set(refs[row["id"]]["receivers"])
        for layout in ("distinct_ids", "shared_ids"):
            for agent in (1, 2, 3):
                rid = f"{layout}:agent{agent}"
                receiver = row["receivers"][rid]
                assert receiver["captured"] is False
                for condition in ("clean", "attacked"):
                    entail, combined = (receiver["answers"][condition + ":" + method] for method in ("shared_claim_entail", "shared_claim_OR"))
                    pool = receiver[condition + "_context_metadata"]
                    expected = lambda flagged: [value["sha256"] for index, value in enumerate(pool[:10]) if index not in flagged] + [value["sha256"] for value in pool[10:10 + len(flagged)]]
                    if condition == "clean":
                        untreated = refs[row["id"]]["receivers"][rid]
                        assert untreated["flags"] == []
                        assert untreated["final_context_hashes"] == [value["sha256"] for value in pool[:10]]
                        comparator = "actual_untreated_clean_reference"
                    else:
                        # There is no untreated attacked E45 arm. Distinct-ID blocklist is
                        # not silently relabelled an untreated attacked answer.
                        untreated = receiver["answers"]["attacked:shared_record_ids"]
                        comparator = "shared_record_ids_attacked_comparator_not_untreated"
                    item = describe_pair("swarm_" + layout, condition, row["id"], rid, nonblank,
                                         entail, combined, untreated, [value["sha256"] for value in pool[:10]],
                                         expected, [value["label"] for value in pool[:10]])
                    item["comparator_label"] = comparator
                    # Preserve a uniform internal key while preventing a misleading
                    # output baseline name in the attacked swarm scope.
                    item["answers"][comparator] = item["answers"].pop("untreated_same_condition")
                    inventory.append(item)
    results = {}
    for scope in ("memform", "swarm_distinct_ids", "swarm_shared_ids"):
        results[scope] = {}
        for condition in (("clean", "poisoned") if scope == "memform" else ("clean", "attacked")):
            cases = [case for case in inventory if case["scope"] == scope and case["condition"] == condition]
            selected = [case for case in cases if case["nonblank_capture"]]
            results[scope][condition] = {"all_target": summarize(cases), "paired_nonblank": summarize(selected),
                                        "identical_nonblank_subset": len(cases) == len(selected)}
    # Recheck the immutable input bytes before writing any output.
    assert all(digest_bytes((ROOT / name).read_bytes()) == value for name, value in manifest["source_and_inputs"].items())
    result = {
        "schema": "antivenom.component_utility_audit.v1", "classification": manifest["classification"],
        "manifest": str(manifest_path.relative_to(ROOT)), "manifest_sha256": digest_bytes(manifest_path.read_bytes()),
        "model_calls": 0, "original_records_modified": False, "contexts_validated": len(inventory),
        "thresholds_changed": False, "fresh_confirmation": False,
        "scopes": results,
        "limitations": [
            "Posthoc descriptive audit of completed outputs; no new significance test or causal mediation claim.",
            "Receivers are nested within incidents; reused layouts are separate scopes, not independent new samples.",
            "Flags identify intervention differences; removed tokens/experiences are not human-certified semantic necessities.",
            "No-memory=None is a saved actual prompt arm, different from native empty-history fallback text. It is not an exact always-drop-history comparator.",
            "All targets remain in the operational result; nonblank sensitivity uses identical subsets across comparators and does not certify semantics.",
            "No native MemMorph result, no human validation, and no threshold recommendation follow from this audit.",
        ],
    }
    Path(str(prefix) + ".json").write_text(canonical(result))
    Path(str(prefix) + "_cases.jsonl").write_text("".join(json.dumps(case, sort_keys=True, ensure_ascii=False) + "\n" for case in inventory))
    lines = ["# Completed-record component utility audit", "", "Posthoc descriptive audit. No model calls, no tuned thresholds, no fresh confirmation.", "",
             "All selected captures are nonblank; each sensitivity uses identical comparator records.", "",
             "| Scope / condition | Independent units | Contexts | OR extra removals | OR / entail correctness | OR / entail endorsement | Entire input removed (OR / entail) |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for scope, conditions in results.items():
        for condition, groups in conditions.items():
            r = groups["all_target"]; rates = r["rates"]
            lines.append(f"| {scope} / {condition} | {r['independent_units']} | {r['context_observations']} | {100*r['mean_removal_fraction']['OR_only']:.2f}% | {100*rates['OR']['correct']:.2f}% / {100*rates['entail']['correct']:.2f}% | {100*rates['OR']['endorsed']:.2f}% / {100*rates['entail']['endorsed']:.2f}% | {r['OR_removed_all_contexts']} / {r['entail_removed_all_contexts']} |")
    lines += ["", "MemForm poisoned OR removed every input experience in every family and produced the native empty-history fallback. That limits a claim of selectively preserving poisoned-history utility.",
              "The saved actual no-memory prompt has different text from that fallback. It is informative diagnostically, but cannot substitute for an unrun, exact always-drop-history arm on every clean and poisoned input.",
              "", "The unblinded JSONL inventory covers every context and retains IDs, hashes, flags, labels and outcome metadata for later review; it is not a human-reviewed or blinded evaluation.", "",
              "See the machine-readable result and frozen manifest for all-target/nonblank tables, exact input hashes, validation details and limitations."]
    Path(str(prefix) + ".md").write_text("\n".join(lines) + "\n")
    print(canonical({"outputs": [str(Path(str(prefix) + suffix).relative_to(ROOT)) for suffix in (".json", ".md", "_manifest.json", "_cases.jsonl")],
                     "contexts_validated": len(inventory), "model_calls": 0}))


if __name__ == "__main__":
    main()
