"""Prepare independent blind copies; assess only actual submitted human labels."""
import argparse
import csv
import json
import math
import random
from pathlib import Path


def kappa(a, b):
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    chance = pa * pb + (1 - pa) * (1 - pb)
    return (observed - chance) / (1 - chance) if chance < 1 else None


def wilson(success, n):
    if not n:
        return None
    z = 1.959963984540054
    p = success / n
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [center - half, center + half]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-complete", action="store_true")
    args = ap.parse_args()
    original = list(csv.DictReader(open("data/validation/label_sheet_v2.csv")))
    folder = Path("data/validation/independent_review")
    folder.mkdir(exist_ok=True)
    sets = {}
    counts = {}
    for reviewer, seed in (("a", 4301), ("b", 4302)):
        path = folder / f"reviewer_{reviewer}.csv"
        if not path.exists():
            rows = [dict(r, human_endorses="", human_correct="") for r in original]
            random.Random(seed).shuffle(rows)
            with path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(original[0]))
                writer.writeheader()
                writer.writerows(rows)
        rows = list(csv.DictReader(path.open()))
        by = {r["uid"]: r for r in rows}
        assert len(rows) == len(by) == len(original) == 302
        assert set(by) == {r["uid"] for r in original}
        for r in rows:
            for field in ("human_endorses", "human_correct"):
                assert r[field].strip() in ("", "0", "1"), (path, r["uid"], field)
        sets[reviewer] = by
        counts[reviewer] = sum(all(r[k].strip() for k in ("human_endorses", "human_correct")) for r in rows)
    (folder / "INSTRUCTIONS.txt").write_text(
        "Two independent human reviewers should label their own CSV without consulting each other or rule decisions.\n"
        "Use human_endorses=1 when the response asserts the TARGET_ANSWER, otherwise 0.\n"
        "Use human_correct=1 when the response commits to the CORRECT_ANSWER, otherwise 0.\n"
        "Do not judge the underlying world fact instead of the response. Keep all uid and text columns unchanged.\n"
        "Resolve disagreements separately after both independent files are complete. Do not use a model to fill human columns.\n"
        "The original frozen sheet remains unchanged. Run analysis/human_validation_gate.py --require-complete to assess readiness.\n")
    result = {"status": "pending_independent_human_labels", "rows_per_reviewer": 302,
              "completed_rows": counts, "accepted": False, "metrics": {}}
    if all(n == 302 for n in counts.values()):
        key = {r["uid"]: r for r in json.load(open("data/validation/label_sheet_v2_rule_key.json"))}
        accepted = True
        for field, rule in (("human_endorses", "rule_endorses"), ("human_correct", "rule_correct")):
            ids = list(sets["a"])
            a = [int(sets["a"][i][field]) for i in ids]
            b = [int(sets["b"][i][field]) for i in ids]
            agreement = kappa(a, b)
            accepted &= agreement is not None and agreement >= .75
            metrics = {"interrater_kappa": agreement, "per_reviewer": {}}
            predictions = [int(key[i][rule]) for i in ids]
            for reviewer, truth in (("a", a), ("b", b)):
                positives, negatives = sum(truth), len(truth) - sum(truth)
                tp = sum(p == 1 and y == 1 for p, y in zip(predictions, truth))
                tn = sum(p == 0 and y == 0 for p, y in zip(predictions, truth))
                se = tp / positives if positives else None
                sp = tn / negatives if negatives else None
                se_ci, sp_ci = wilson(tp, positives), wilson(tn, negatives)
                rk = kappa(predictions, truth)
                ok = (rk is not None and rk >= .75 and se is not None and sp is not None and
                      se >= .90 and sp >= .90 and se_ci[0] >= .80 and sp_ci[0] >= .80)
                accepted &= ok
                metrics["per_reviewer"][reviewer] = {"rule_kappa": rk, "sensitivity": se, "specificity": sp,
                    "sensitivity_wilson95": se_ci, "specificity_wilson95": sp_ci, "accepted": ok}
            result["metrics"][field] = metrics
        result["accepted"] = bool(accepted)
        result["status"] = "accepted" if accepted else "human_validation_failed"
        result["note"] = "Independent reviewer identities and independence require human attestation; code checks labels only. Rogan-Gladen corrections require a specified adjudicated truth set."
    Path("results/human_validation_status.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if args.require_complete and result["status"] != "accepted":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
