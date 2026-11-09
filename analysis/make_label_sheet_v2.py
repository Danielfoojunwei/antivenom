"""Label sheet v2: keeps the 152 v1 rows unchanged and adds rows from sources
v1 did not cover: E15 HotpotQA / MS-MARCO (incl. yes/no answers), E19
baselines (verbose TrustRAG / RobustRAG / CoordGuard answers), E16b and E17.
Stratified by source and rule decision, seed 1. Opaque ids; rule decisions in
a separate key file. Output: data/validation/label_sheet_v2.csv + key."""
import csv
import hashlib
import json
import random

from antivenom.poisonedrag import load

NEW = {"e15h": "results/rescored/e15_cross_dataset_hotpotqa_k10.jsonl",
       "e15m": "results/rescored/e15_cross_dataset_msmarco_k10.jsonl",
       "e19": "results/rescored/e19_baselines_nq_k10.jsonl",
       "e16b": "results/rescored/e16b_clinical_titration_nq_k10.jsonl",
       "e17": "results/rescored/e17_bound_delivery_nq_k10.jsonl"}
PER_CELL = 15  # 5 sources x 2 rule outcomes x 15 = up to 150 new rows

answers = {}
for d in ("nq", "hotpotqa", "msmarco"):
    for t in load(d)[0]:
        answers[t.id] = t
rng = random.Random(1)

v1 = list(csv.DictReader(open("data/validation/label_sheet.csv")))
key = json.load(open("data/validation/label_sheet_rule_key.json"))
seen = {k["source"] for k in key}

pool = {}
for src, path in NEW.items():
    for line in open(path):
        r = json.loads(line)
        for arm, v in r.items():
            if isinstance(v, dict) and "resp" in v and f"{src}:{r['id']}:{arm}" not in seen:
                pool.setdefault((src, bool(v["endorsed"])), []).append((src, r["id"], arm, v))

rows = [{k: r[k] for k in ("uid", "question", "TARGET_ANSWER", "CORRECT_ANSWER", "response",
                           "human_endorses", "human_correct")} for r in v1]
for cell in sorted(pool):
    for src, qid, arm, v in rng.sample(pool[cell], min(PER_CELL, len(pool[cell]))):
        t = answers[qid]
        source = f"{src}:{qid}:{arm}"
        uid = hashlib.sha1(source.encode()).hexdigest()[:10]
        rows.append({"uid": uid, "question": t.question, "TARGET_ANSWER": t.incorrect,
                     "CORRECT_ANSWER": t.correct, "response": v["resp"], "human_endorses": "", "human_correct": ""})
        key.append({"uid": uid, "source": source, "rule_endorses": int(v["endorsed"]), "rule_correct": int(v["correct"])})
rng.shuffle(rows)
with open("data/validation/label_sheet_v2.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
json.dump(key, open("data/validation/label_sheet_v2_rule_key.json", "w"))
print(f"label_sheet_v2: {len(rows)} rows ({len(v1)} from v1, {len(rows) - len(v1)} new)")
