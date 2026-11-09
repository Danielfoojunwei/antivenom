"""Agreement between the scoring rules and human labels on
data/validation/label_sheet.csv (filled in by a human labeller).

Reports accuracy, Cohen's kappa and a 95% bootstrap interval for both rules,
overall and per experiment, plus every disagreement for inspection."""
import csv
import json
import sys
from collections import defaultdict

import numpy as np

V2 = len(sys.argv) > 1 and sys.argv[1] == "v2"
SHEET = "data/validation/label_sheet_v2.csv" if V2 else "data/validation/label_sheet.csv"
KEY = "data/validation/label_sheet_v2_rule_key.json" if V2 else "data/validation/label_sheet_rule_key.json"
key = {k["uid"]: k for k in json.load(open(KEY))}
rows = [r for r in csv.DictReader(open(SHEET))
        if r["human_endorses"].strip() != "" and r["human_correct"].strip() != ""]
if not rows:
    raise SystemExit("no labelled rows yet: fill human_endorses / human_correct (0 or 1)")
rng = np.random.default_rng(0)


def kappa(a, b):
    a, b = np.array(a), np.array(b)
    po = np.mean(a == b)
    pe = np.mean(a) * np.mean(b) + (1 - np.mean(a)) * (1 - np.mean(b))
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def report(name, pairs):
    h, r = zip(*pairs)
    agree = np.array(h) == np.array(r)
    b = rng.choice(agree.astype(float), size=(5000, len(agree))).mean(axis=1)
    print(f"  {name:10s} n={len(pairs):3d} accuracy={agree.mean():.3f} "
          f"[{np.percentile(b, 2.5):.3f}, {np.percentile(b, 97.5):.3f}] kappa={kappa(h, r):.3f}")


for field, rule in (("human_endorses", "rule_endorses"), ("human_correct", "rule_correct")):
    print(f"\n== {rule} vs {field}")
    pairs = [(int(r[field]), key[r["uid"]][rule]) for r in rows]
    report("all", pairs)
    by_exp = defaultdict(list)
    for r in rows:
        by_exp[key[r["uid"]]["source"].split(":")[0]].append((int(r[field]), key[r["uid"]][rule]))
    for exp, p in sorted(by_exp.items()):
        report(exp, p)
    print("  disagreements:")
    for r in rows:
        if int(r[field]) != key[r["uid"]][rule]:
            print(f"    {key[r['uid']]['source']}: human={r[field]} rule={key[r['uid']][rule]} | {r['response'][:100]}")
