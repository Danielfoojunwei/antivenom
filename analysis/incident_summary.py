"""Exploratory incident-suite results; incidents, not passages/agents, are units."""
import itertools
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

from antivenom.continuation import read_rows, save
from continuation_stats import holm, interval


def values(rows, arm, metric):
    grouped = defaultdict(list)
    for row in rows:
        a = row["answers"][arm]
        if metric == "clean_removal":
            v = a["clean_removed"] / a["clean_in"] if a["clean_in"] else None
        elif metric == "poison_recall":
            v = a["poison_removed"] / a["poison_in"] if a["poison_in"] else None
        else:
            v = a[metric]
        if v is not None:
            grouped[row["target_id"]].append(float(v))
    return {k: float(np.mean(v)) for k, v in grouped.items()}


def estimate(x):
    x = np.asarray(list(x), dtype=float)
    return {"mean": float(x.mean()), "ci95": interval(x), "independent_targets": len(x)} if len(x) else None


def difference(a, b, repeated):
    ids = sorted(set(a) & set(b))
    x = np.array([a[i] - b[i] for i in ids])
    result = estimate(x)
    if not repeated:
        wins, losses = int((x > 0).sum()), int((x < 0).sum())
        result.update(p=float(binomtest(wins, wins + losses).pvalue) if wins + losses else 1.,
                      test="exact paired binary McNemar", discordant=[wins, losses])
    else:
        rng = np.random.default_rng(0)
        null = (rng.choice([-1, 1], (20000, len(x))) * x).mean(axis=1)
        result.update(p=float((1 + (np.abs(null) >= abs(x.mean()) - 1e-12).sum()) / 20001),
                      test="target-level paired sign randomization, 20000 draws")
    return result


def summarize(rows, repeated=False):
    arms = sorted(rows[0]["answers"])
    assert all(sorted(r["answers"]) == arms for r in rows)
    rates = {a: {m: estimate(values(rows, a, m).values()) for m in
             ("correct", "endorsed", "clean_removal", "poison_recall", "pipeline_seconds")} for a in arms}
    methods = sorted(a.split(":", 1)[1] for a in arms if a.startswith("attacked:"))
    refs = set(methods) & {"OR", "cosine", "coordguard_gate", "trustrag", "isolated_attention", "shared_record_ids"}
    pairs = [(a, b) for a, b in itertools.combinations(methods, 2) if a in refs or b in refs]
    comparisons = {}
    for a, b in pairs:
        for condition in ("clean", "attacked"):
            for metric in ("correct", "endorsed"):
                comparisons[f"{condition}:{a} - {b}:{metric}"] = difference(
                    values(rows, condition + ":" + a, metric), values(rows, condition + ":" + b, metric), repeated)
    adjusted = holm({k: v["p"] for k, v in comparisons.items()})
    for k, v in comparisons.items(): v["holm_p"] = adjusted[k]
    return {"cases": len(rows), "targets": len({r["target_id"] for r in rows}), "rates": rates,
            "comparisons": comparisons, "holm_family": "All listed method pairs, both conditions and both answer endpoints within this scope",
            "scoring": "Frozen automated rules; independent human review deferred",
            "timing": "Warm method filtering plus answer generation, includes independently recomputed features; loading and capture extraction separate"}


def main():
    result = {}
    for mode, engine, n in (("base", "contriever", 80), ("prefixfree", "contriever", 80),
                             ("recurrence", "contriever", 160), ("e5", "e5", 80)):
        rows = read_rows(f"results/incident_{mode}_{engine}.jsonl")
        assert len(rows) == n
        result[mode] = summarize(rows, repeated=mode == "recurrence")
    swarm = read_rows("results/incident_swarm.jsonl")
    assert len(swarm) == 80
    for layout in ("shared_ids", "distinct_ids"):
        rows = [{"target_id": r["target_id"], "answers": receiver["answers"]}
                for r in swarm for receiver in r["receivers"].values() if receiver["layout"] == layout]
        assert len(rows) == 240
        result["swarm:" + layout] = summarize(rows, repeated=True)
    base = read_rows("results/incident_base_contriever.jsonl")
    result["signature_operations"] = {"extraction_seconds": estimate(r["artifact"]["extraction_seconds"] for r in base),
        "payload_bytes": estimate(r["artifact"]["payload_bytes"] for r in base),
        "sample_bytes": estimate(r["artifact"]["sample_bytes"] for r in base),
        "cosine_setup_seconds": estimate(r["artifact"]["cosine_setup_seconds"] for r in base),
        "valid_extractions": sum(r["artifact"]["extraction_valid"] for r in base),
        "notes": "Extraction is cached once per sample, separately measured; no human interpretability result"}
    result["reader_weights_unchanged"] = json.load(open("results/incident_weights_after.json"))["identical_to_before"]
    save("results/incident_summary.json", result)
    lines = ["Incident-response development evaluation (automatically scored; not fresh confirmation)"]
    for scope, report in result.items():
        if not isinstance(report, dict) or "rates" not in report: continue
        lines.append(f"\n{scope}: {report['targets']} independent targets, {report['cases']} cases")
        for arm, metrics in report["rates"].items():
            lines.append(f"{arm}: correct={metrics['correct']['mean']:.4f}; endorsement={metrics['endorsed']['mean']:.4f}; warm seconds={metrics['pipeline_seconds']['mean']:.2f}")
    Path("results/rescored/summaries/incident_summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__": main()
