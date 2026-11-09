"""R2-prespecified nonblank-capture sensitivity; retains all-target main result."""
import hashlib
import json
from pathlib import Path

from antivenom.continuation import freeze, keyed, read_rows, save
from continuation_stats import arm_rates, compare

ARMS = ["clean", "attack", "delete_OR_backfill", "delete_entail_backfill", "coordguard_af_refill",
        "trustrag", "defclean_OR", "defclean_coordguard"]
PAIRS = [("delete_OR_backfill", "coordguard_af_refill"), ("delete_OR_backfill", "trustrag"),
         ("delete_OR_backfill", "delete_entail_backfill")]


def nonblank(question, claim):
    return isinstance(question,str) and isinstance(claim,str) and bool(question.strip() and claim.strip())


def main():
    rows = read_rows("results/e37_composite_nq_k10.jsonl")
    ids = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][20:]
    assert len(rows) == 80 and {r["id"] for r in rows} == set(ids)
    events = [r for r in read_rows("results/extraction_failure_events.jsonl")
              if any(Path(a).name == "e37_composite.py" for a in r["script_arguments"])]
    save("results/provenance/e37_extraction_failures_at_completion.json", events)
    freeze("results/e37_capture_sensitivity_manifest.json", [__file__, "docs/EXTRACTION_RESILIENCE_AMENDMENT.md",
        "results/e37_composite_nq_k10.jsonl", "results/e11a_flag_scores_nq_k10.jsonl",
        "analysis/continuation_stats.py", "analysis/remaining_summary.py",
        "results/provenance/e37_original_first70_hash.json", "results/provenance/e37_extraction_failures_at_completion.json"],
        {"rule": "Secondary same-subset comparison using nonblank selected question AND claim; semantic correctness unverified",
         "all_target_main_retained": 80})
    raw = Path("results/e37_composite_nq_k10.jsonl").read_bytes()
    reference = json.load(open("results/provenance/e37_original_first70_hash.json"))
    assert hashlib.sha256(b"".join(raw.splitlines(keepends=True)[:70])).hexdigest() == reference["sha256"]
    selected = [r for r in rows if nonblank(r["question_extracted"],r["claim"])]
    failed = []
    for row in rows:
        state = json.load(open(f"results/checkpoints/e37/{row['id']}.json"))
        assert len(state["captures"]) == 5
        for index,c in state["captures"].items():
            if not nonblank(c["question_extracted"],c["claim"]):
                failed.append({"id":row["id"],"capture_index":int(index),"selected":int(index)==row["capture_index"]})
    result = {"scope":"R2 secondary syntactic nonblank-capture sensitivity; no case removed from main report",
        "all_planned_targets":80,"capture_attempts":400,"invalid_or_blank_captures":failed,
        "selected_nonblank_targets":len(selected),"selected_blank_target_ids":[r["id"] for r in rows if r not in selected],
        "recorded_E37_malformed_output_events":len(events),"original_first70_unchanged":True,
        "limitations":["R2 was a post-start amendment after a strict-parser failure at target 71",
                        "Nonblank fields do not establish semantic extraction validity",
                        "The conditional subset is secondary; operational main report includes every failed capture",
                        "Used development questions; not fresh confirmation, equivalence or human-validated scoring"],
        "scopes":{}}
    for label,subset in [("all80",rows),("nonblank_selected",selected),
                          ("exposed_nonblank_selected",[r for r in selected if r["exposed"]])]:
        result["scopes"][label] = {"n_targets":len(subset),"arms":arm_rates(subset,ARMS),
            "comparison_family":compare(subset,PAIRS)} if subset else {"n_targets":0}
    result["exploratory_mitigation_control_family"] = compare(rows,[("delete_OR_backfill","attack")])
    original=json.load(open("results/remaining_runs_summary.json"))["composite"]["all"]
    assert result["scopes"]["all80"]["arms"] == original["arms"]
    assert result["scopes"]["all80"]["comparison_family"] == original["comparison_family"]
    save("results/e37_capture_sensitivity.json",result)
    print("E37 R2 audit: 80 retained; nonblank selected",len(selected),"blank capture attempts",len(failed),"original70 unchanged")
    print("Exploratory mitigation controls:",json.dumps(result["exploratory_mitigation_control_family"]))


if __name__ == "__main__": main()
