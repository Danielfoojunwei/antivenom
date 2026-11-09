"""Completed-reader interim report; use frozen analysis functions verbatim.

Does not inspect partial Mistral outcomes or alter frozen experimental code.
The additional control comparison family is exploratory and labelled as such.
"""
import ast
import json
from pathlib import Path

import numpy as np

from antivenom.continuation import read_rows, save
from continuation_stats import arm_rates, compare


def main():
    tree = ast.parse(Path("analysis/remaining_summary.py").read_text())
    namespace = {"np": np, "arm_rates": arm_rates, "compare": compare}
    nodes = [n for n in tree.body if
             isinstance(n, ast.FunctionDef) and n.name in {"gated", "scope"} or
             isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in {"ARMS", "GATE_ARMS"}]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "frozen_remaining_analysis_functions", "exec"), namespace)
    threshold = json.load(open("results/e36_geometry_gate_calibration.json"))["threshold"]
    scopes = {d: [namespace["gated"](r, threshold) for r in read_rows(
        f"results/e36_Meta-Llama-3-8B-Instruct-4bit_{d}_k10.jsonl")] for d in ("hotpotqa", "msmarco")}
    assert all(len(rows) == 50 for rows in scopes.values())
    scopes["pooled"] = scopes["hotpotqa"] + scopes["msmarco"]
    result = {"scope": "Completed Llama reader only; used-question exploratory transfer. Mistral/composite/final pooled analyses pending. Frozen analysis functions/families reused without recipe changes.",
        "reader": "Meta-Llama-3-8B-Instruct-4bit", "n_targets": 100,
        "scopes": {name: namespace["scope"](rows) for name, rows in scopes.items()},
        "exploratory_controls_family": compare(scopes["pooled"], [("v1_delete_backfill", "attack"),
            ("v1_delete_backfill", "random_delete_backfill"), ("v1_delete_backfill", "lowrel_delete_backfill")]),
        "empty_claims": sum(not r["claim"].strip() for r in scopes["pooled"]),
        "rule_metric_overlap_counts": {a: sum(r[a]["correct"] and r[a]["endorsed"] for r in scopes["pooled"])
                                       for a in namespace["ARMS"]}}
    save("results/e36_llama_interim_summary.json", result)
    print("Llama interim summary saved; targets:", result["n_targets"], "blank claims:", result["empty_claims"])


if __name__ == "__main__":
    main()
