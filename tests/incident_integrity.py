"""Full coverage, provenance, metrics, captured exclusion and actual deliveries."""
import hashlib
import json
from pathlib import Path

import numpy as np

from antivenom.continuation import keyed, read_rows, save
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses


def sha(text): return hashlib.sha256(text.encode()).hexdigest()


def check_answer(a, target, pool):
    assert a["correct"] == bool(correct(a["resp"], target.correct))
    assert a["endorsed"] == bool(endorses(a["resp"], target.incorrect))
    flags = a["flags"]
    assert sorted(set(flags)) == sorted(flags) and all(0 <= i < min(10, len(pool)) for i in flags)
    assert a["clean_removed"] == sum(pool[i]["label"] == "clean" for i in flags)
    assert a["poison_removed"] == sum(pool[i]["label"] != "clean" for i in flags)
    expected = [p for i,p in enumerate(pool[:10]) if i not in flags]
    if "timing_note" not in a: expected += pool[10:10+len(flags)]
    assert [sha(p["text"]) for p in expected] == a["final_context_hashes"]
    assert sum(p["label"] != "clean" for p in expected) == a["poison_after_refill"]
    assert np.isfinite(a["pipeline_seconds"]) and a["pipeline_seconds"] >= 0
    assert all(p["poison_index"] != 0 for p in pool)
    assert sha(target.poison[0]) not in [sha(p["text"]) for p in pool]
    for key in ("entail", "cosine", "attention_z", "avidity"):
        if key in a["detection"]:
            assert len(a["detection"][key]) == min(10, len(pool))
            assert np.isfinite(a["detection"][key]).all()


def main():
    order = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")]
    targets = {t.id: t for t in load("nq")[0]}
    manifests = list(Path("results").glob("incident_*manifest.json")) + list(Path("results").glob("incident_*frozen.json"))
    assert manifests
    for path in manifests:
        manifest = json.load(path.open())
        for filename, digest in manifest["inputs"].items():
            assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, (path, filename)
    counts = {}
    for mode, engine, total in (("base", "contriever", 80), ("prefixfree", "contriever", 80),
                                ("recurrence", "contriever", 160), ("e5", "e5", 80)):
        rows = keyed(f"results/incident_{mode}_{engine}.jsonl")
        assert len(rows) == total and {r["target_id"] for r in rows.values()} == set(order[20:])
        by = targets if mode != "prefixfree" else {t.id: t for t in load("nq", prefix=False)[0]}
        for case_id, row in rows.items():
            check = json.load(open(f"results/checkpoints/incident_cases/{mode}_{engine}/{sha(case_id)}.json"))
            assert check["answers"] == row["answers"]
            for arm, answer in row["answers"].items():
                condition = arm.split(":", 1)[0]
                check_answer(answer, by[row["target_id"]], check[condition + "_context"])
            assert row["artifact"]["sample_sha256"] == sha(by[row["target_id"]].poison[0])
        counts[mode] = total
    for engine in ("contriever", "e5"):
        fit = json.load(open(f"results/incident_calibration_{engine}.json"))
        assert fit["ids"] == order[:20]
        assert json.load(open(f"results/incident_revocation_{engine}.json"))["identical_response"]
    swarm = keyed("results/incident_swarm.jsonl")
    assert set(swarm) == set(order[20:])
    for tid, row in swarm.items():
        full = json.load(open(f"results/checkpoints/incident_swarm/{sha(tid)}.json"))
        assert full["publisher"]["record_blocklist"] == [full["publisher"]["context"][i]["doc_id"] for i in full["publisher"]["attacked"]["flags"]]
        assert len(row["receivers"]) == 6
        claim = json.loads(full["messages"]["claim"]["wire"])["payload"]
        assert set(claim) == {"schema", "incident_id", "question", "claim", "sample_sha256"}
        for message in full["messages"].values():
            assert message["sha256"] == sha(message["wire"]) and message["bytes"] == len(message["wire"].encode())
        for rid, receiver in full["receivers"].items():
            assert receiver["captured"] is False and len(receiver["answers"]) == 12
            assert len(receiver["clean_record_ids"]) >= 10
            for arm, answer in receiver["answers"].items():
                condition, method = arm.split(":", 1)
                check_answer(answer, targets[tid], receiver[condition + "_context"])
                state = answer["receiver_state"]
                assert state["captured"] is False
                if method.startswith("shared_"): assert len(state["messages_received"]) == 1
                else: assert state["messages_received"] == [] and state["registry"] == {}
                if method.startswith("shared_claim"):
                    assert state["registry"] == {"claim": claim}
    assert json.load(open("results/incident_weights_after.json"))["identical_to_before"]
    save("results/incident_integrity.json", {"passed": True, "coverage": counts,
        "swarm_targets": 80, "receiver_contexts": 480, "reader_weights_unchanged": True,
        "automated_scoring_only": True})
    print("Incident suite full integrity passed", counts)


if __name__ == "__main__": main()
