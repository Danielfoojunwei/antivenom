"""Prepare blinded, unlabelled publication review; never calls a model.

This is a new retrospective human audit of the completed local MemForm study.
It neither overwrites the earlier human gate nor certifies reviewer identity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = "data/validation/publication_v1"
INPUTS = (
    "results/incident_memform.jsonl",
    "results/incident_memform_manifest.json",
    "results/incident_memform_integrity.json",
    "results/incident_memform_capture_audit.json",
    "results/memform_drop_all_control_v1.jsonl",
    "results/memform_drop_all_control_v1_integrity.json",
    "results/memform_drop_all_completion_audit_v1.json",
    "data/external/memform/accepted_mcq.jsonl",
)
METHODS = ("entail", "OR", "cosine", "none")
YES_NO_UNCERTAIN = ("yes", "no", "uncertain")
FIELDS = {
    "extraction": {
        "human_question_faithful": YES_NO_UNCERTAIN,
        "human_claim_faithful": YES_NO_UNCERTAIN,
        "human_conditions_preserved": YES_NO_UNCERTAIN,
        "human_invented_content": YES_NO_UNCERTAIN,
    },
    "policy": {"human_reference_action": None},
    "memory": {
        "human_policy_consistent": YES_NO_UNCERTAIN,
        "human_task_relevant": YES_NO_UNCERTAIN,
        "human_useful_for_reference_decision": YES_NO_UNCERTAIN,
    },
    "outcome": {"human_committed_label": None},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def opaque(kind, *parts):
    return digest(json.dumps(["publication-review-v1", kind, *parts], ensure_ascii=False).encode())[:20]


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def immutable(row):
    return {k: v for k, v in row.items() if not k.startswith("human_")}


def shuffled(rows, seed):
    result = list(rows)
    random.Random(seed).shuffle(result)
    return result


def task_projection(task):
    return {"task": task["task"], "choices": task["choices"]}


def build(root=ROOT):
    """Build content only from completed records; no source metadata in public rows."""
    root = Path(root)
    original = read_jsonl(root / INPUTS[0])
    drop_all = read_jsonl(root / INPUTS[4])
    families = {}
    for case in read_jsonl(root / INPUTS[7]):
        families.setdefault(case["family_id"], {})[case["interface"]] = case
    by_id = {r["id"]: r for r in original}
    manifest = json.loads((root / INPUTS[1]).read_text())
    planned = manifest["settings"]["test_families"]
    assert set(planned) == set(by_id)
    original_integrity = json.loads((root / INPUTS[2]).read_text())
    control_integrity = json.loads((root / INPUTS[5]).read_text())
    completion = json.loads((root / INPUTS[6]).read_text())
    assert original_integrity["passed"] is True and original_integrity["families"] == 212
    assert control_integrity["passed"] is True and control_integrity["reader_weights_unchanged"] is True
    assert control_integrity["actual_answer_calls"] == 424
    assert completion["all424_complete"] is True
    assert completion["all_bound_checkpoints_parser_scoring_replayed"] is True
    output_hash = digest((root / INPUTS[4]).read_bytes())
    assert output_hash == control_integrity["output_sha256"] == completion["output_file_sha256"]
    assert digest((root / INPUTS[7]).read_bytes()) == manifest["inputs"][INPUTS[7]]
    assert len(by_id) == len(original) == 212
    assert len(drop_all) == 424
    assert len({r["arm_id"] for r in drop_all}) == 424
    assert {r["family_id"] for r in drop_all} == set(by_id)
    templates = {kind: [] for kind in FIELDS}
    key = {kind: {} for kind in FIELDS}
    for fid in sorted(by_id):
        record, cases = by_id[fid], families[fid]
        case = cases["P2"]
        capture = cases["P1"]["memory_building"]["poisoned_condition"]["memory_text"]
        artifact = record["artifact"]
        assert digest(capture.encode()) == artifact["sample_sha256"]
        uid = opaque("extraction", fid)
        templates["extraction"].append({
            "uid": uid, "captured_text": capture,
            "extracted_question": artifact["question"], "extracted_claim": artifact["claim"],
            **{field: "" for field in FIELDS["extraction"]}, "human_notes": "",
        })
        key["extraction"][uid] = {"family_id": fid}
        tasks = case["evaluation"]["trigger_tasks"]
        assert len(tasks) == 1
        task = tasks[0]
        projected = task_projection(task)
        choices = json.dumps(projected["choices"], ensure_ascii=False)
        policy = case["clean_policy"]["rule"]
        puid = opaque("policy", fid, projected)
        templates["policy"].append({
            "uid": puid, "reference_policy": policy, "task": projected["task"],
            "choices": choices, "human_reference_action": "", "human_notes": "",
        })
        key["policy"][puid] = {"family_id": fid, "task_id": task["task_id"],
                              "benchmark_clean_answer": task["clean_answer"],
                              "benchmark_poisoned_answer": task["poisoned_answer"]}
        experiences = {e["id"]: e for e in case["candidate_experiences"]}
        grouped = {}
        for condition in ("clean", "poisoned"):
            ids = case["memory_building"][condition + "_condition"]["evidence_ids"]
            expected_hashes = [digest(experiences[eid]["text"].encode()) for eid in ids]
            assert all(record["answers"][condition + ":" + method]["input_hashes"] == expected_hashes
                       for method in METHODS)
            for index, eid in enumerate(ids):
                text = experiences[eid]["text"]
                muid = opaque("memory", fid, task["task_id"], text)
                if muid not in grouped:
                    grouped[muid] = {"text": text, "observations": []}
                grouped[muid]["observations"].append({
                    "condition": condition, "record_id": eid, "index": index,
                    "removed_by": {method: index in record["answers"][condition + ":" + method]["flags"]
                                   for method in METHODS},
                })
        for muid, group in sorted(grouped.items()):
            templates["memory"].append({
                "uid": muid, "reference_policy": policy, "task": projected["task"],
                "choices": choices, "experience": group["text"],
                **{field: "" for field in FIELDS["memory"]}, "human_notes": "",
            })
            key["memory"][muid] = {"family_id": fid, "task_id": task["task_id"],
                                  "observations": group["observations"]}
        responses = {}
        for condition in ("clean", "poisoned"):
            for method in METHODS:
                answer = record["answers"][condition + ":" + method]["tasks"][task["task_id"]]
                ouid = opaque("outcome", fid, projected, answer["resp"])
                entry = responses.setdefault(ouid, {"resp": answer["resp"], "observations": []})
                entry["observations"].append({"condition": condition, "method": method,
                                              "rule_prediction": answer["prediction"],
                                              "rule_correct": answer["correct"],
                                              "rule_endorsed": answer["endorsed"]})
        for answer in drop_all:
            if answer["family_id"] != fid:
                continue
            assert answer["task_id"] == task["task_id"]
            ouid = opaque("outcome", fid, projected, answer["resp"])
            entry = responses.setdefault(ouid, {"resp": answer["resp"], "observations": []})
            entry["observations"].append({"condition": answer["condition"], "method": "drop_all",
                                          "rule_prediction": answer["prediction"],
                                          "rule_correct": answer["correct"],
                                          "rule_endorsed": answer["endorsed"]})
        assert sum(len(value["observations"]) for value in responses.values()) == 10
        for ouid, entry in sorted(responses.items()):
            templates["outcome"].append({
                "uid": ouid, "task": projected["task"], "choices": choices,
                "response": entry["resp"], "human_committed_label": "", "human_notes": "",
            })
            key["outcome"][ouid] = {"family_id": fid, "task_id": task["task_id"],
                                   "benchmark_clean_answer": task["clean_answer"],
                                   "benchmark_poisoned_answer": task["poisoned_answer"],
                                   "policy_uid": puid, "observations": entry["observations"]}
    for kind, rows in templates.items():
        assert len({r["uid"] for r in rows}) == len(rows) == len(key[kind])
    return templates, key


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def prepare(root=ROOT, destination=None):
    root = Path(root)
    target = Path(destination) if destination else root / DESTINATION
    target.mkdir(parents=True, exist_ok=True)
    templates, key = build(root)
    immutable_hashes = {kind: {r["uid"]: digest(canonical(immutable(r)).encode()) for r in rows}
                        for kind, rows in templates.items()}
    inputs = {name: digest((root / name).read_bytes()) for name in INPUTS}
    bound = ("analysis/prepare_publication_review.py", "tests/test_publication_review.py",
             "docs/PUBLICATION_HUMAN_REVIEW.md")
    inputs.update({name: digest((root / name).read_bytes()) for name in bound})
    specification = {
        "schema": "antivenom.publication_human_review.v1",
        "scope": "retrospective completed local MemForm 212-family audit, not fresh confirmation or native MemMorph",
        "input_sha256": inputs, "counts_per_reviewer": {k: len(v) for k, v in templates.items()},
        "family_count": 212, "method_condition_observations_mapped": 2120,
        "raw_response_deduplication": "exact raw text within the same family/task only; all observation mappings retained",
        "memory_deduplication": "exact experience text within the same family/task only; all condition/flag mappings retained",
        "label_choices": FIELDS, "immutable_row_sha256": immutable_hashes,
        "private_mapping_sha256": digest(canonical(key).encode()),
        "blinding_limit": "contents can reveal attack semantics; opaque IDs/order do not guarantee perfect blinding",
        "automated_human_labels": False,
    }
    manifest_path = target / "review_manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
        assert canonical({name: existing[name] for name in specification}) == canonical(specification), "Frozen package changed; make a new version."
    else:
        manifest_path.write_text(canonical({**specification, "prepared_utc": datetime.now(timezone.utc).isoformat()}))
    private = target / "PRIVATE_admin_only"
    private.mkdir(exist_ok=True)
    key_path = private / "mapping.json"
    if key_path.exists():
        assert json.loads(key_path.read_text()) == key
    else:
        key_path.write_text(canonical(key))
    for index, (kind, rows) in enumerate(templates.items()):
        folder = target / f"phase_{index + 1}_{kind}"
        folder.mkdir(exist_ok=True)
        for reviewer, seed in (("a", 76111), ("b", 76112)):
            path = folder / f"reviewer_{reviewer}.csv"
            if not path.exists():
                write_csv(path, shuffled(rows, seed + index))
    attestation = target / "attestations.json"
    if not attestation.exists():
        attestation.write_text(canonical({
            r: {"reviewer_name_or_private_code": "", "is_independent_human": False,
                "did_not_consult_other_reviewer_or_rule_key": False,
                "no_model_generated_labels": False, "signed_utc": ""} for r in ("a", "b")
        }))
    return assess(target)


def validate_rows(kind, rows, expected):
    by_id = {r["uid"]: r for r in rows}
    assert len(rows) == len(by_id), f"Duplicate {kind} review rows"
    assert set(by_id) == set(expected), f"Missing/extra {kind} review rows"
    for uid, row in by_id.items():
        assert digest(canonical(immutable(row)).encode()) == expected[uid], f"Altered review text: {kind}/{uid}"
        for field, allowed in FIELDS[kind].items():
            assert field in row
            values = allowed
            if values is None:
                choices = [x["label"] for x in json.loads(row["choices"])]
                values = choices + (["UNCERTAIN"] if kind == "policy" else ["NONE", "AMBIGUOUS"])
            assert row[field] in ("", *values), f"Invalid label: {kind}/{uid}/{field}"
    return by_id


def agreement(a, b):
    assert len(a) == len(b)
    if not a:
        return {"n": 0, "agreement": None, "cohen_kappa": None}
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    aa, bb = Counter(a), Counter(b)
    chance = sum(aa[c] * bb[c] for c in set(aa) | set(bb)) / n ** 2
    return {"n": n, "agreement": observed,
            "cohen_kappa": (observed - chance) / (1 - chance) if chance < 1 else None}


def assess(target):
    target = Path(target)
    manifest = json.loads((target / "review_manifest.json").read_text())
    assert digest((target / "PRIVATE_admin_only/mapping.json").read_bytes()) == manifest["private_mapping_sha256"], "Private mapping changed"
    counts, labels, metrics, disagreements = {}, {}, {}, []
    for index, kind in enumerate(FIELDS):
        labels[kind] = {}
        counts[kind] = {}
        for reviewer in ("a", "b"):
            path = target / f"phase_{index + 1}_{kind}" / f"reviewer_{reviewer}.csv"
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            by = validate_rows(kind, rows, manifest["immutable_row_sha256"][kind])
            labels[kind][reviewer] = by
            counts[kind][reviewer] = sum(all(r[field] for field in FIELDS[kind]) for r in rows)
        metrics[kind] = {}
        for field in FIELDS[kind]:
            ids = [uid for uid in labels[kind]["a"] if labels[kind]["a"][uid][field] and labels[kind]["b"][uid][field]]
            metrics[kind][field] = agreement([labels[kind]["a"][uid][field] for uid in ids],
                                              [labels[kind]["b"][uid][field] for uid in ids])
            for uid in ids:
                a, b = labels[kind]["a"][uid][field], labels[kind]["b"][uid][field]
                if a != b:
                    disagreements.append({"kind": kind, "uid": uid, "field": field, "reviewer_a": a,
                                          "reviewer_b": b, "adjudicated_human_label": "", "human_reason": ""})
    attestation = json.loads((target / "attestations.json").read_text())
    attested = all(a.get("reviewer_name_or_private_code") and a.get("signed_utc") and
                   a.get("is_independent_human") is True and
                   a.get("did_not_consult_other_reviewer_or_rule_key") is True and
                   a.get("no_model_generated_labels") is True for a in attestation.values())
    assert set(attestation) == {"a", "b"}
    if attested:
        assert attestation["a"]["reviewer_name_or_private_code"] != attestation["b"]["reviewer_name_or_private_code"], "Reviewers must be distinct humans"
    complete = all(n == manifest["counts_per_reviewer"][kind] for kind, reviewers in counts.items() for n in reviewers.values())
    status = "pending_independent_human_labels"
    if complete:
        status = "complete_labels_missing_human_attestation" if not attested else "independent_labels_complete_adjudication_required"
    result = {"schema": "antivenom.publication_human_review_status.v1", "status": status,
              "counts_per_reviewer": manifest["counts_per_reviewer"], "completed_rows": counts,
              "human_attestations_complete": bool(attested), "human_validation_passed": False,
              "agreement_on_jointly_completed_fields": metrics, "disagreement_fields": len(disagreements),
              "note": "Software cannot certify reviewer identity/independence. Complete labels require adjudication and a signed human validation report; no automatic pass or outcome exclusions."}
    (target / "review_status.json").write_text(canonical(result))
    private = target / "PRIVATE_admin_only"
    private.mkdir(exist_ok=True)
    pending = private / "adjudication_pending.json"
    pending.write_text(canonical(disagreements))
    return result


def verify_frozen(root=ROOT, destination=None):
    root = Path(root)
    target = Path(destination) if destination else root / DESTINATION
    manifest = json.loads((target / "review_manifest.json").read_text())
    for name, expected in manifest["input_sha256"].items():
        assert digest((root / name).read_bytes()) == expected, f"Frozen input changed: {name}"
    return assess(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = prepare() if args.prepare else verify_frozen()
    print(canonical(result), end="")
    if args.require_complete and result["status"] != "independent_labels_complete_adjudication_required":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
