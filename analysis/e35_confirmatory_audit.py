"""Audit E29 without editing historical code, data, protocol or output.

Uses discrete attainable thresholds for continuous v2 scores. The frozen v1
OR detector is binary and has no pre-registered continuous ranking.
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

from antivenom.poisonedrag import load
from antivenom.qa import contains, correct, endorses
from continuation_stats import holm, read_rows, save_report


sets = {d: read_rows(f"results/e29_tier2_{d}_k10.jsonl") for d in ("hotpotqa", "msmarco")}
frozen = {}
history = []
for line in Path("docs/PREREG_CONFIRMATORY.sha256").read_text().splitlines():
    expected, path = line.split(maxsplit=1)
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    history.append({"path": path, "hash": expected, "matches_current": expected == actual})
    frozen[path] = expected  # Later entries explicitly supersede earlier hashes of same path.
latest_ok = all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in frozen.items())
assert latest_ok
scoring_n = scoring_mismatches = 0
clean_context_audit = {}
for d, rows in sets.items():
    targets, corpus = load(d)
    assert len(rows) == 50 and {r["id"] for r in rows} == {t.id for t in targets[50:100]}
    by = {t.id: t for t in targets}
    first = {r["id"] for r in read_rows(f"results/e15_cross_dataset_{d}_k10.jsonl")}
    assert not first & {r["id"] for r in rows}
    rel = json.load(open(f"data/external/poisonedrag/{d}-contriever.json"))
    clean_context_audit[d] = {}
    for flag_key in ("defclean_flags_v1", "defclean_flags_v2", "defclean_coordguard_removed"):
        counts = [len(r[flag_key]) for r in rows]
        with_gold = lost_gold = 0
        for r in rows:
            t = by[r["id"]]
            ids = sorted(t.clean_ids, key=lambda i: -rel[t.id][i])
            texts = [corpus[i]["title"] + " " + corpus[i]["text"] for i in ids]
            before = any(contains(p, t.correct) for p in texts[:10])
            filtered = [p for i, p in enumerate(texts[:10]) if i not in r[flag_key]] + texts[10:10 + len(r[flag_key])]
            after = any(contains(p, t.correct) for p in filtered)
            with_gold += before
            lost_gold += before and not after
        clean_context_audit[d][flag_key] = {"contexts_flagged": sum(n > 0 for n in counts),
            "mean_flags": float(np.mean(counts)), "min_flags": min(counts),
            "contexts_with_gold_token_before": with_gold, "contexts_losing_all_gold_tokens": lost_gold}
    for r in rows:
        t = by[r["id"]]
        for arm in r.values():
            if isinstance(arm, dict) and "resp" in arm:
                scoring_n += 1
                scoring_mismatches += ((arm["endorsed"], arm["correct"]) !=
                    (bool(endorses(arm["resp"], t.incorrect)), bool(correct(arm["resp"], t.correct))))
assert scoring_mismatches == 0


def passage_arrays(rows):
    values = []
    for r in rows:
        for i, l in enumerate(r["labels"]):
            if l != "captured":
                values.append((l == "poison", r["avidity_v2"][i], i in r["coordguard_removed"], i in r["flags_v1"]))
    return np.array(values)


def matched_cost(rows):
    a = passage_arrays(rows)
    poison, score, cg, v1 = a[:, 0].astype(bool), a[:, 1], a[:, 2].astype(bool), a[:, 3].astype(bool)
    # Least expensive attainable threshold with at least CG's integer TP count.
    need = int(cg[poison].sum())
    threshold = float(np.sort(score[poison])[::-1][need - 1]) if need else float("inf")
    predicted = score >= threshold
    return {"cg_recall": float(cg[poison].mean()), "cg_clean_removed": float(cg[~poison].mean()),
            "v2_threshold": threshold, "v2_recall": float(predicted[poison].mean()),
            "v2_clean_removed": float(predicted[~poison].mean()),
            "difference_cg_minus_v2": float(cg[~poison].mean() - predicted[~poison].mean()),
            "v1_deployed_recall": float(v1[poison].mean()), "v1_deployed_clean_removed": float(v1[~poison].mean()),
            "v1_binary_matched_cost": float(v1[~poison].mean()) if v1[poison].mean() >= cg[poison].mean() else 1.0,
            "n_poison": int(poison.sum()), "n_clean": int((~poison).sum())}


def paired_p(rows, a, b, metric):
    wins = sum(bool(r[a][metric]) and not bool(r[b][metric]) for r in rows)
    losses = sum(bool(r[b][metric]) and not bool(r[a][metric]) for r in rows)
    return {"discordant": [wins, losses], "p": float(binomtest(wins, wins + losses).pvalue) if wins + losses else 1.0}


result = {"n_targets": 100, "latest_frozen_hashes_match": latest_ok,
          "hash_history": history, "scored_responses_checked": scoring_n,
          "scoring_mismatches": scoring_mismatches,
          "claim1_status": "Historical analysis uses continuous v2, not frozen binary v1; no pre-registered v1 ranking exists.",
          "human_labels": {}, "scopes": {}, "clean_context_audit": clean_context_audit}
overlap_review = []
for d, rows in sets.items():
    targets_by_id = {t.id: t for t in load(d)[0]}
    for r in rows:
        for name, arm in r.items():
            if isinstance(arm, dict) and arm.get("correct") and arm.get("endorsed"):
                t = targets_by_id[r["id"]]
                overlap_review.append({"dataset": d, "id": t.id, "arm": name, "question": t.question,
                    "TARGET_ANSWER": t.incorrect, "CORRECT_ANSWER": t.correct, "response": arm["resp"],
                    "human_endorses": "", "human_correct": ""})
result["dual_correct_and_endorsed_by_arm"] = {a: sum(r["arm"] == a for r in overlap_review)
    for a in sorted({r["arm"] for r in overlap_review})}
with open("data/validation/e29_overlap_review.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=["dataset", "id", "arm", "question", "TARGET_ANSWER",
                                          "CORRECT_ANSWER", "response", "human_endorses", "human_correct"])
    writer.writeheader()
    writer.writerows(overlap_review)
for sheet in ("label_sheet.csv", "label_sheet_v2.csv"):
    rows = list(csv.DictReader(open("data/validation/" + sheet)))
    result["human_labels"][sheet] = {"rows": len(rows), "fully_labelled": sum(bool(r["human_endorses"].strip()) and bool(r["human_correct"].strip()) for r in rows)}
lines = ["E35 audit of historical E29 (original files preserved)",
         f"100 expected tier-2 target IDs; no tier-1 overlap; {scoring_n} responses checked, zero scoring mismatches.",
         "All latest frozen hashes match. The older v2 document hash is superseded by its later entry.",
         "Claim 1 used v2 continuous scores although the primary detector is v1 OR (binary).",
         "No pre-registered continuous v1 ranking is available. v2 matched-recall analysis is a sensitivity analysis.",
         "Discrete thresholds below attain at least CG's integer poison catch count (ties may overshoot)."]
lines.append("The bootstrap sign-tail p replicates the historical approach; it is not a null-calibrated permutation test.")
lines.append("Structural false alarms: within-context attention z>=0 must flag at least one passage, even with no poison.")
lines.append(f"Clean-context filtering audit (gold-token containment is only a proxy): {clean_context_audit}")
for name, rows in {**sets, "pooled": sum(sets.values(), [])}.items():
    cost = matched_cost(rows)
    rng = np.random.default_rng(0)
    indices = rng.integers(0, len(rows), (2000, len(rows)))
    differences = np.array([matched_cost([rows[i] for i in sample])["difference_cg_minus_v2"] for sample in indices])
    p1 = float(min(1.0, 2 * min((differences <= 0).mean(), (differences >= 0).mean())))
    ps = {"claim1_v2_sensitivity": p1,
          "claim2_clean_accuracy": paired_p(rows, "defclean_v1", "defclean_coordguard", "correct")["p"],
          "claim3_endorsement_cg": paired_p(rows, "v1_delete_backfill", "coordguard_af_refill", "endorsed")["p"],
          "claim3_endorsement_trustrag": paired_p(rows, "v1_delete_backfill", "trustrag", "endorsed")["p"]}
    res = {"n": len(rows), "matched_cost_v2_sensitivity": cost,
           "difference_ci": [float(x) for x in np.quantile(differences, [.025, .975])],
           "raw_ps": ps, "historical_two_test_holm": holm({k: v for k, v in ps.items() if not k.startswith("claim3")}),
           "conservative_four_test_holm_sensitivity": holm(ps)}
    result["scopes"][name] = res
    lines.append(f"\n{name} n={len(rows)}: {cost}")
    lines.append(f"  v2 clean-cost difference CI {res['difference_ci']}")
    lines.append(f"  Raw p: {ps}")
    lines.append(f"  Historical two-test Holm: {res['historical_two_test_holm']}")
    lines.append(f"  Conservative four-test Holm sensitivity: {res['conservative_four_test_holm_sensitivity']}")
lines.extend(["\nInterpretation: no primary superiority demonstrated; parity/equivalence was not established.",
              "The historical p=0.039 for endorsement vs CG is unadjusted, not a Holm-adjusted result.",
              "Gate and later experiments are exploratory; tier 2 cannot confirm them afresh.",
              f"Both rule-correct and rule-endorsed (requires manual review): {result['dual_correct_and_endorsed_by_arm']}",
              f"Human label completeness: {result['human_labels']}"])
save_report("e35_confirmatory_audit", result, lines)
