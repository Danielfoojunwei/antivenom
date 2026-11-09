"""Re-score every stored response with the current scoring rules.

Raw results files are never modified. For each results/<name>.jsonl, every
nested dict that has a "resp" field gets "endorsed" and "correct" recomputed
(word-boundary rules) and "poisoned_substring" (PoisonedRAG's original rule).
E01's flat fields (clean_resp / att_resp) are handled too. Output goes to
results/rescored/<name>.jsonl. Targets' answers come from the released files.

Usage: python analysis/rescore.py results/e12_combined_and_deletion_nq_k10.jsonl ...
"""
import json
import sys
from pathlib import Path

from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, poisoned

answers = {}
for d in ("nq", "hotpotqa", "msmarco"):
    for t in load(d)[0]:
        answers[t.id] = (t.correct, t.incorrect)


def fix(node, right, wrong, stats):
    if isinstance(node, dict):
        if "other_id" in node:  # E02 off-target arm answers a different target's question
            right, wrong = answers[node["other_id"]]
        if "resp" in node:
            old = (node.get("endorsed"), node.get("correct"))
            node["endorsed"] = endorses(node["resp"], wrong)
            node["correct"] = correct(node["resp"], right)
            node["poisoned_substring"] = poisoned(node["resp"], wrong)
            stats["n"] += 1
            stats["changed"] += old != (node["endorsed"], node["correct"])
        for v in node.values():
            fix(v, right, wrong, stats)
    elif isinstance(node, list):
        for v in node:
            fix(v, right, wrong, stats)


out_dir = Path("results/rescored")
out_dir.mkdir(exist_ok=True)
for path in sys.argv[1:]:
    stats = {"n": 0, "changed": 0}
    rows = [json.loads(l) for l in open(path)]
    for r in rows:
        right, wrong = answers[r["id"]]
        if "clean_resp" in r:  # E01 layout
            for k in ("clean", "att"):
                r[f"{k}_endorsed"] = endorses(r[f"{k}_resp"], wrong)
                r[f"{k}_correct"] = correct(r[f"{k}_resp"], right)
                stats["n"] += 1
        fix(r, right, wrong, stats)
    with open(out_dir / Path(path).name, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{Path(path).name}: rows={len(rows)} responses={stats['n']} changed={stats['changed']}")
