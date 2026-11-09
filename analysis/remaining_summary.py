"""Final E36–E38 analyses, with target-cluster reader pooling."""
import json

import numpy as np

from antivenom.continuation import keyed, read_rows
from continuation_stats import arm_rates, compare, interval, save_report

TAGS = ["Meta-Llama-3-8B-Instruct-4bit", "Mistral-7B-Instruct-v0.3-4bit"]
ARMS = ["clean", "attack", "v1_block", "v1_delete_backfill", "v2_delete_backfill", "random_delete_backfill",
        "lowrel_delete_backfill", "coordguard_af", "coordguard_af_refill", "trustrag", "defclean_v1", "defclean_v2", "defclean_coordguard"]
GATE_ARMS = ["gated_v1", "gated_v2", "gated_cg", "gated_clean_v1", "gated_clean_v2", "gated_clean_cg",
             "geometry_gated_cg", "geometry_gated_clean_cg"]


def gated(row, geometry_threshold):
    r = dict(row)
    for name, arm, clean in [("v1", "v1_delete_backfill", "defclean_v1"),
                              ("v2", "v2_delete_backfill", "defclean_v2"),
                              ("cg", "coordguard_af_refill", "defclean_coordguard")]:
        r[f"gated_{name}"] = r[arm] if r["gate_attacked"] else r["attack"]
        r[f"gated_clean_{name}"] = r[clean] if r["gate_clean"] else r["clean"]
    r["geometry_gated_cg"] = r["coordguard_af_refill"] if r["coordguard_score"] is not None and r["coordguard_score"] > geometry_threshold else r["attack"]
    r["geometry_gated_clean_cg"] = r["defclean_coordguard"] if r["clean_coordguard_score"] is not None and r["clean_coordguard_score"] > geometry_threshold else r["clean"]
    return r


def scope(rows):
    return {"n_targets": len(rows), "arms": arm_rates(rows, ARMS + GATE_ARMS),
        "transfer_comparison_family": compare(rows, [("v1_delete_backfill", "coordguard_af_refill"),
            ("v1_delete_backfill", "trustrag"), ("v2_delete_backfill", "coordguard_af_refill"),
            ("v2_delete_backfill", "v1_delete_backfill"), ("defclean_v1", "defclean_coordguard")]),
        "gate_comparison_family": compare(rows, [("gated_v1", "v1_delete_backfill"),
            ("gated_v2", "v2_delete_backfill"), ("gated_clean_v1", "defclean_v1"),
            ("gated_clean_v2", "defclean_v2"), ("gated_cg", "geometry_gated_cg")]),
        "gate_fires_attacked": float(np.mean([r["gate_attacked"] for r in rows])),
        "gate_fires_clean": float(np.mean([r["gate_clean"] for r in rows]))}


geometry_threshold = json.load(open("results/e36_geometry_gate_calibration.json"))["threshold"]
result = {"scope": "Used-question transfer and development analyses; not fresh confirmation or human-validated",
          "reader_transfer": {}, "gate_replay": {}, "pooled_readers": {}, "composite": {}}
lines = ["E36–E38 remaining-runs analysis", result["scope"],
         "Transfer families have 10 exact paired comparisons each; Holm within each listed family.",
         "Bootstrap: 2,000 target resamples, seed 0. No equivalence or non-inferiority claim."]
all_readers = {}
for tag in TAGS:
    datasets = {}
    for d in ("hotpotqa", "msmarco"):
        rows = read_rows(f"results/e36_{tag}_{d}_k10.jsonl")
        assert len(rows) == 50
        datasets[d] = [gated(r, geometry_threshold) for r in rows]
    datasets["pooled"] = datasets["hotpotqa"] + datasets["msmarco"]
    result["reader_transfer"][tag] = {name: scope(rows) for name, rows in datasets.items()}
    result["reader_transfer"][tag]["empty_extracted_claims"] = sum(not r["claim"].strip() for r in datasets["pooled"])
    all_readers[tag] = {r["id"]: r for r in datasets["pooled"]}
    lines.append(f"\n{tag}, n=100")
    for a, rates in result["reader_transfer"][tag]["pooled"]["arms"].items():
        lines.append(f"  {a}: correct {rates['correct']['rate']:.3f}, endorsed {rates['endorsed']['rate']:.3f}")

cache = keyed("results/e38_gate_cache.jsonl")
assert len(cache) == 100
qwen = []
for d in ("hotpotqa", "msmarco"):
    ctx = keyed(f"data/cache/e36_contexts_{d}.jsonl")
    rows = read_rows(f"results/e29_tier2_{d}_k10.jsonl")
    current = [gated({**r, **cache[r["id"]], "clean_coordguard_score": ctx[r["id"]]["clean_coordguard_score"]}, geometry_threshold) for r in rows]
    qwen += current
    result["gate_replay"][d] = scope(current)
result["gate_replay"]["pooled"] = scope(qwen)
expected = {"hotpotqa": (.86, .00, .18, .18, .16, .54), "msmarco": (.96, .08, .16, .10, .08, .68),
            "pooled": (.91, .04, .17, .14, .12, .61)}
for d, values in expected.items():
    s = result["gate_replay"][d]
    actual = (s["gate_fires_attacked"], s["gate_fires_clean"], s["arms"]["gated_v1"]["endorsed"]["rate"],
              s["arms"]["gated_v2"]["endorsed"]["rate"], s["arms"]["gated_cg"]["endorsed"]["rate"],
              s["arms"]["gated_clean_v1"]["correct"]["rate"])
    assert np.allclose(actual, values, atol=.000001), (d, actual, values)
result["gate_replay"]["historical_printed_rates_reproduced"] = True
all_readers["Qwen"] = {r["id"]: r for r in qwen}
ids = list(all_readers["Qwen"])
assert all(set(rows) == set(ids) for rows in all_readers.values())
reader_order = list(all_readers)
for a, b, metric in [("v1_delete_backfill", "coordguard_af_refill", "endorsed"),
                      ("defclean_v1", "defclean_coordguard", "correct"),
                      ("v2_delete_backfill", "coordguard_af_refill", "endorsed")]:
    values = np.array([[int(all_readers[reader][tid][a][metric]) - int(all_readers[reader][tid][b][metric])
                        for reader in reader_order] for tid in ids], dtype=float)
    rng = np.random.default_rng(0)
    ti = rng.integers(0, len(ids), (2000, len(ids)))
    ri = rng.integers(0, len(reader_order), (2000, len(reader_order)))
    two_level = values[ti[:, :, None], ri[:, None, :]].mean(axis=(1, 2))
    result["pooled_readers"][f"{a} - {b}: {metric}"] = {"difference": float(values.mean()),
        "target_cluster_ci_fixed_readers": interval(values.mean(axis=1)),
        "two_level_target_reader_ci": [float(x) for x in np.quantile(two_level, [.025, .975])],
        "n_targets": 100, "n_readers": 3,
        "limitation": "Only 3 readers; no independent 300-target test or post-hoc NI claim"}
lines.append("\nReader pooling keeps each target's reader results together:")
lines.extend(f"  {k}: {v}" for k, v in result["pooled_readers"].items())

composite = read_rows("results/e37_composite_nq_k10.jsonl")
assert len(composite) == 80
c_arms = ["clean", "attack", "delete_OR_backfill", "delete_entail_backfill", "coordguard_af_refill", "trustrag", "defclean_OR", "defclean_coordguard"]
for label, rows in [("all", composite), ("exposed", [r for r in composite if r["exposed"]])]:
    if not rows:
        result["composite"][label] = {"n_targets": 0}
        continue
    result["composite"][label] = {"n_targets": len(rows), "arms": arm_rates(rows, c_arms),
        "comparison_family": compare(rows, [("delete_OR_backfill", "coordguard_af_refill"),
            ("delete_OR_backfill", "trustrag"), ("delete_OR_backfill", "delete_entail_backfill")]),
        "selected_OR_poison_recall": float(np.mean([r["poison_recall"] for r in rows if r["exposed"]]))}
    lines.append(f"\nE37 composite {label}, n={len(rows)}")
    for arm, rates in result["composite"][label]["arms"].items():
        lines.append(f"  {arm}: correct {rates['correct']['rate']:.3f}, endorsed {rates['endorsed']['rate']:.3f}")
result["composite"]["OR_refill_poison_reintroduced_targets"] = sum(any(l != "clean" for l in r["true_backfill_labels"]) for r in composite)
result["external_dependencies"] = {"human_validation": "pending independent labels",
    "fresh_gate_confirmation": "requires compatible unused released questions; replay does not satisfy it"}
save_report("remaining_runs_summary", result, lines)
