"""Preplanned fixed-gate replay on completed E37 answers; no new inference."""
import json

import numpy as np

from antivenom.continuation import freeze, read_rows, save
from continuation_stats import arm_rates, compare


def main():
    rows = read_rows("results/e37_composite_nq_k10.jsonl")
    assert len(rows) == 80 and len({r["id"] for r in rows}) == 80
    g = json.load(open("results/e30_attack_gate.json"))["g"]
    geometry = json.load(open("results/e36_geometry_gate_calibration.json"))["threshold"]
    freeze("results/e37_gate_replay_manifest.json", [__file__, "docs/REMAINING_RUNS_PROTOCOL.md",
        "docs/EXTRACTION_RESILIENCE_AMENDMENT.md", "results/e37_composite_nq_k10.jsonl",
        "results/e30_attack_gate.json", "results/e36_geometry_gate_calibration.json",
        "analysis/continuation_stats.py"],
        {"scope":"Planned fixed E30 gate replay; extra exploratory comparison family, not fresh confirmation",
         "nli_threshold":g,"geometry_threshold":geometry,"no_threshold_refit":True})
    current = []
    for r in rows:
        assert r["gate_attacked"] == bool(max(r["entail"]) >= g)
        assert r["gate_clean"] == bool(max(r["clean_entail"]) >= g)
        x = dict(r)
        x["gated_OR"] = r["delete_OR_backfill"] if r["gate_attacked"] else r["attack"]
        x["gated_clean_OR"] = r["defclean_OR"] if r["gate_clean"] else r["clean"]
        x["gated_cg"] = r["coordguard_af_refill"] if r["gate_attacked"] else r["attack"]
        x["gated_clean_cg"] = r["defclean_coordguard"] if r["gate_clean"] else r["clean"]
        x["geometry_cg"] = r["coordguard_af_refill"] if r["coordguard_score"] is not None and r["coordguard_score"] > geometry else r["attack"]
        x["geometry_clean_cg"] = r["defclean_coordguard"] if r["clean_coordguard_score"] is not None and r["clean_coordguard_score"] > geometry else r["clean"]
        current.append(x)
    arms = ["clean","attack","delete_OR_backfill","coordguard_af_refill","trustrag","defclean_OR","defclean_coordguard",
            "gated_OR","gated_clean_OR","gated_cg","gated_clean_cg","geometry_cg","geometry_clean_cg"]
    pairs = [("gated_OR","delete_OR_backfill"),("gated_clean_OR","defclean_OR"),
             ("gated_OR","geometry_cg"),("gated_clean_OR","geometry_clean_cg"),
             ("gated_cg","geometry_cg"),("gated_clean_cg","geometry_clean_cg")]
    result = {"scope":"Used-question E37 replay. Gate fixed before E37 outcomes; additional comparison family is exploratory. R2 invalid capture retained.",
        "thresholds":{"NLI":g,"geometry":geometry},"scopes":{},
        "limitation":"Nonblank capture sensitivity is secondary and does not establish semantic extraction validity or fresh NI confirmation."}
    nonblank = [r for r in current if r["question_extracted"].strip() and r["claim"].strip()]
    for name,scope in [("all80",current),("nonblank_selected",nonblank)]:
        result["scopes"][name] = {"n_targets":len(scope),"arms":arm_rates(scope,arms),
            "comparison_family":compare(scope,pairs),
            "holm_family":"Six listed arm pairs, two answer endpoints, 12 tests within scope",
            "gate_fires_clean":float(np.mean([r["gate_clean"] for r in scope])),
            "gate_fires_attacked":float(np.mean([r["gate_attacked"] for r in scope])),
            "exposed_targets":sum(r["exposed"] for r in scope),
            "gate_fires_among_exposed":sum(r["exposed"] and r["gate_attacked"] for r in scope)}
    save("results/e37_gate_replay.json",result)
    s=result["scopes"]["all80"]
    print("E37 fixed-gate replay:",s["n_targets"],"targets; fires clean",s["gate_fires_clean"],"attacked",s["gate_fires_attacked"])
    for a in arms:
        print(a,"correct",s["arms"][a]["correct"]["rate"],"endorsed",s["arms"][a]["endorsed"]["rate"])
    for k,v in s["comparison_family"].items():
        print(k,"difference",v["difference"],"CI",v["ci"],"Holm p",v["holm_p"])


if __name__ == "__main__": main()
