"""Summarize E32 and (when complete) E34, with target-level paired statistics."""
import json
from pathlib import Path

from antivenom.poisonedrag import load
from antivenom.qa import contains, correct, endorses
from continuation_stats import arm_rates, compare, read_rows, save_report

targets = {t.id: t for t in load("nq")[0]}
_, corpus = load("nq")
rel = json.load(open("data/external/poisonedrag/nq-contriever.json"))
base = read_rows("results/e32_backfill_placebo_nq_k10.jsonl")
assert len(base) == 80
arms32 = ["delete_true_backfill", "delete_placebo_backfill", "delete_only"]


def audit(rows, arms):
    for r in rows:
        t = targets[r["id"]]
        for a in arms:
            assert r[a]["endorsed"] == bool(endorses(r[a]["resp"], t.incorrect)), (r["id"], a, "endorsed")
            assert r[a]["correct"] == bool(correct(r[a]["resp"], t.correct)), (r["id"], a, "correct")


audit(base, arms32)
pairs32 = [(arms32[0], arms32[1]), (arms32[0], arms32[2]), (arms32[1], arms32[2])]
result = {"n_targets": len(base), "split": "NQ development; exploratory; rule-scored", "scoring_mismatches": 0,
          "e32": {"arms": arm_rates(base, arms32), "comparisons": compare(base, pairs32)}}
old = {r["id"]: r for r in read_rows("results/e12_combined_and_deletion_nq_k10.jsonl")}
common = [r for r in base if r["id"] in old]
result["e12_reproduction"] = {"n_shared_targets": len(common), "response_comparisons": 2 * len(common),
    "response_mismatches": sum(r[new]["resp"] != old[r["id"]][prior]["resp"] for r in common
        for new, prior in (("delete_true_backfill", "delete_OR_backfill"), ("delete_only", "delete_OR")))}
assert result["e12_reproduction"]["response_mismatches"] == 0
content_audit = {"n_placebo_with_gold_token": 0, "n_placebo_with_target_token": 0,
                 "n_placebo_with_receiver_top100_doc": 0}
for r in base:
    t, donor = targets[r["id"]], targets[r["placebo_from"]]
    ids = sorted(donor.clean_ids, key=lambda i: -rel[donor.id][i])[10:10 + r["n_flags"]]
    texts = [corpus[i]["title"] + " " + corpus[i]["text"] for i in ids]
    content_audit["n_placebo_with_gold_token"] += any(contains(p, t.correct) for p in texts)
    content_audit["n_placebo_with_target_token"] += any(contains(p, t.incorrect) for p in texts)
    content_audit["n_placebo_with_receiver_top100_doc"] += bool(set(ids) & set(t.clean_ids))
result["placebo_content_audit"] = content_audit
lines = ["E32/E34 M3 backfill controls (NQ development; exploratory)",
         "Exact McNemar; target bootstrap B=2000, seed=0; Holm within each six-comparison family.",
         "Existing responses match frozen scoring rules. Human validation remains pending."]
lines.append(f"E12 reproduction on shared targets: {result['e12_reproduction']}")
lines.append(f"Placebo content audit (token overlap does not establish relevance): {content_audit}")


def append_summary(label, data):
    lines.append("\n" + label)
    for a, metrics in data["arms"].items():
        lines.append(f"  {a}: correct {metrics['correct']['rate']:.4f} {metrics['correct']['ci']}; endorsed {metrics['endorsed']['rate']:.4f} {metrics['endorsed']['ci']}")
    for name, res in data["comparisons"].items():
        lines.append(f"  {name}: diff {res['difference']:+.4f} {res['ci']}; discordant {res['discordant']}, p={res['p']:.6f}, Holm p={res['holm_p']:.6f}")


append_summary("E32 appended backfill, n=80", result["e32"])
path = Path("results/e34_fixed_slots_nq_k10.jsonl")
if path.exists():
    new = read_rows(path)
    result["e34_completed_targets"] = len(new)
    if len(new) == 80:
        assert {r["id"] for r in new} == {r["id"] for r in base}
        audit(new, ["true_inplace", "placebo_inplace"])
        by = {r["id"]: r for r in base}
        joined = [{**by[r["id"]], **r} for r in new]
        arms34 = ["true_inplace", "placebo_inplace", "delete_only"]
        result["e34"] = {"arms": arm_rates(joined, arms34), "comparisons": compare(joined,
            [(arms34[0], arms34[1]), (arms34[0], arms34[2]), (arms34[1], arms34[2])]),
            "secondary_placement_comparisons": compare(joined, [("true_inplace", "delete_true_backfill"),
                                                               ("placebo_inplace", "delete_placebo_backfill")]),
            "true_replacement_poison_count": sum(sum(l != "clean" for l in r["true_inplace"]["replacement_labels"]) for r in new),
            "placebo_replacement_poison_count": sum(sum(l != "clean" for l in r["placebo_inplace"]["replacement_labels"]) for r in new)}
        append_summary("E34 original passage-slot backfill, n=80 (token positions and lengths vary)", result["e34"])
        lines.append(f"  Poison in true/placebo replacements: {result['e34']['true_replacement_poison_count']}/{result['e34']['placebo_replacement_poison_count']}")
        for name, res in result["e34"]["secondary_placement_comparisons"].items():
            lines.append(f"  Secondary placement comparison {name}: {res}")
    else:
        lines.append(f"\nE34 incomplete: {len(new)}/80; no full-set inference produced.")
save_report("e32_e34_summary", result, lines)
