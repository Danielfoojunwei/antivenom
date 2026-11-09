"""Statistical edge cases and pairing integrity; no model calls or real outcomes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from swarm_track4_summary import assemble, bounded_comparison, harm_estimate, summarize, METHODS


def main():
    zero = bounded_comparison([0.] * 80)
    assert zero["paired_ci95"] == [0., 0.]
    assert zero["simultaneous_lower"] < 0 < zero["simultaneous_upper"]
    assert zero["one_sided_p"] == 1.
    harm = harm_estimate([False] * 80)
    assert harm["rate"] == 0 and 0 < harm["exact_one_sided_upper95"] < .05
    benefit = bounded_comparison([1.] * 80)
    damage = bounded_comparison([-1.] * 80)
    assert benefit["simultaneous_lower"] > 0 and damage["simultaneous_upper"] < 0
    swarm, refs = [], []
    for n in range(3):
        receivers, references = {}, {}
        for layout in ("distinct_ids", "shared_ids"):
            for agent in (1, 2, 3):
                rid = f"{layout}:agent{agent}"
                answers = {f"{c}:{m}": {"correct": True, "endorsed": False}
                           for c in ("clean", "attacked") for m in METHODS if m != "untreated"}
                receivers[rid] = {"captured": False, "clean_context_metadata": [{"sha256": "abc"}], "answers": answers}
                references[rid] = {"correct": True, "endorsed": False, "flags": [], "final_context_hashes": ["abc"]}
        swarm.append({"id": str(n), "publisher": {"artifact": {"question": "q", "claim": "c"}}, "receivers": receivers})
        refs.append({"id": str(n), "receivers": references})
    cases = assemble(swarm, refs)
    result = summarize(cases, "distinct_ids")
    assert result["independent_incidents"] == 3  # Not nine receivers or eighteen layout rows.
    assert result["joint_claim"] == "inconclusive"
    refs[0]["receivers"]["distinct_ids:agent1"]["final_context_hashes"] = ["wrong"]
    try:
        assemble(swarm, refs)
    except AssertionError:
        pass
    else:
        raise AssertionError("Mismatched receiver contexts were accepted")
    print("Track 4 preflight passed: clustering, pairing, zero-variance uncertainty and harm bounds")


if __name__ == "__main__":
    main()
