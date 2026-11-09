"""Completed-reader operational and identically paired nonblank sensitivity."""
import ast
import json
from pathlib import Path

import numpy as np

from antivenom.continuation import freeze, read_rows, save
from continuation_stats import arm_rates, compare


def main():
    tags = ["Meta-Llama-3-8B-Instruct-4bit", "Mistral-7B-Instruct-v0.3-4bit"]
    files = [f"results/e36_{t}_{d}_k10.jsonl" for t in tags for d in ("hotpotqa", "msmarco")]
    freeze("results/e36_capture_sensitivity_manifest.json", [
        __file__, "analysis/remaining_summary.py", "analysis/continuation_stats.py",
        "docs/EXTRACTION_RESILIENCE_AMENDMENT.md", "results/e36_geometry_gate_calibration.json", *files])
    tree = ast.parse(Path("analysis/remaining_summary.py").read_text())
    nodes = [n for n in tree.body if
             isinstance(n, ast.FunctionDef) and n.name in {"gated", "scope"} or
             isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id in {"ARMS", "GATE_ARMS"}]
    namespace = {"np": np, "arm_rates": arm_rates, "compare": compare}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "frozen_remaining_functions", "exec"), namespace)
    threshold = json.load(open("results/e36_geometry_gate_calibration.json"))["threshold"]
    result = {"scope": "Completed E36 readers; all-target operational results remain primary",
              "subset_rule": "Nonblank selected question_extracted AND claim; identical records for every comparator",
              "limitations": ["Nonblank is not human semantic verification", "Llama subset has only five targets",
                              "Reader subsets are separate; no pooled independent-incident claim"], "readers": {}}
    for tag in tags:
        rows = [namespace["gated"](r, threshold) for d in ("hotpotqa", "msmarco")
                for r in read_rows(f"results/e36_{tag}_{d}_k10.jsonl")]
        assert len(rows) == 100
        subset = [r for r in rows if r["question_extracted"].strip() and r["claim"].strip()]
        result["readers"][tag] = {"all_targets": namespace["scope"](rows),
            "nonblank_targets": namespace["scope"](subset), "nonblank_ids": [r["id"] for r in subset],
            "all_count": len(rows), "nonblank_count": len(subset)}
    save("results/e36_capture_sensitivity.json", result)
    print({t: r["nonblank_count"] for t, r in result["readers"].items()})


if __name__ == "__main__":
    main()
