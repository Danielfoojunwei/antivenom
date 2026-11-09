"""Data-only preflight; never loads a reader or produces experimental outcomes."""
import hashlib
import json
from pathlib import Path

from antivenom.continuation import read_rows, save
from antivenom.poisonedrag import load
from antivenom.memform_port import family_split, native_functions


def main():
    order = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")]
    assert len(order) == len(set(order)) == 100
    minimum = 100
    for prefix in (True, False):
        targets, corpus = load("nq", prefix=prefix)
        assert set(t.id for t in targets) == set(order)
        for t in targets:
            assert len(t.clean_ids) == 100 and len(set(t.clean_ids)) == 100
            assert all(i in corpus for i in t.clean_ids)
            assert t.poison[0] not in t.poison[1:]
            for a in range(4):
                size = sum(int(hashlib.sha256(("17:" + str(i)).encode()).hexdigest(), 16) % 4 == a for i in t.clean_ids)
                minimum = min(minimum, size)
    assert minimum >= 10
    recurrence = {r["id"]: r for r in read_rows("results/e18_recurrence_nq_k10.jsonl")}
    assert set(recurrence) == set(order[20:]) and all(len(r["sessions"]) == 2 for r in recurrence.values())
    assert Path("data/cache/nq_clean_vecs.npz").exists()
    data = [json.loads(x) for x in open("data/external/memform/accepted_mcq.jsonl")]
    families, cal, test = family_split(data)
    assert len(cal) == 20 and len(test) == 212 and not set(cal) & set(test)
    native = native_functions()
    assert native["parse_final_label_details"]("reasoning mentions B.\nFINAL_ANSWER: A", ["A", "B"])[0] == "A"
    assert native["parse_final_label_details"]("I cannot decide.", ["A", "B"])[0] is None
    for fid in cal + test:
        case = families[fid]["P2"]
        for condition in ("clean", "poisoned"):
            ids = case["memory_building"][condition + "_condition"]["evidence_ids"]
            mapping = native["exp_texts"](case)
            texts = [mapping[i] for i in ids]
            assert len(texts) == len(set(texts)) == 4
    save("results/incident_memform_split.json", {"calibration":cal,"held_out":test,"excluded_schema_family_prefix":"F0001_","model_outcomes_generated":False})
    save("results/incident_preflight.json", {"passed": True, "calibration_targets": 20, "development_targets": 80,
        "recurrence_questions": 160, "minimum_agent_clean_records": minimum,
        "captured_text_differs_from_every_evaluated_poison": True,
        "reader_experiments_run": False, "human_review_deferred_by_user": True, "fresh_NI_margin_absolute": .05})
    print("Incident data preflight passed; no model outcomes generated")


if __name__ == "__main__": main()
