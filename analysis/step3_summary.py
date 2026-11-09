"""Summaries for E20 (low poison count), E22 (other readers), E25 permute,
prefixfree and s4. NQ development targets; all exploratory.
Detection recall excludes the captured passage; FPR is over clean passages."""
import json
from collections import defaultdict

import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import roc_auc_score


def J(p):
    return [json.loads(l) for l in open(p)]


def rate(rows, arm, k):
    return np.mean([r[arm][k] for r in rows])


def ci(v, B=2000):
    v = np.array(v, float); b = np.random.default_rng(0).choice(v, (B, len(v))).mean(1)
    return f"{v.mean():.2f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]"


def mcn(rows, a, b, k):
    x = sum(r[a][k] and not r[b][k] for r in rows); y = sum(r[b][k] and not r[a][k] for r in rows)
    return binomtest(x, x + y).pvalue if x + y else 1.0


def det(rows, key="flags_OR"):
    tp = P = fp = N = 0
    for r in rows:
        f = set(r[key])
        for i, l in enumerate(r["labels"]):
            if l == "poison": P += 1; tp += i in f
            elif l == "clean": N += 1; fp += i in f
    return f"recall {tp / max(P, 1):.3f} (n={P}) FPR {fp / N:.3f}"


def arms(rows, names):
    for a in names:
        print(f"    {a:22s} endorsed {ci([r[a]['endorsed'] for r in rows])}  correct {ci([r[a]['correct'] for r in rows])}")


print("== E20 low poison count (NQ dev)")
e20 = J("results/e20_low_poison_fraction_nq_k10.jsonl")
by = defaultdict(list)
for r in e20: by[r["m"]].append(r)
for m in sorted(by):
    print(f"  m={m} n={len(by[m])} | {det(by[m])} | attention-only FPR {det(by[m], 'flags_attn').split('FPR ')[1]}")
    arms(by[m], ["attack", "block_OR", "delete_OR_backfill"])

print("\n== E22 other readers (NQ dev, per-reader attention layer from NQ 1-20)")
for name in ("Meta-Llama-3-8B-Instruct-4bit", "Mistral-7B-Instruct-v0.3-4bit"):
    rows = J(f"results/e22_{name}_nq_k10.jsonl")
    cal = json.load(open(f"results/e22_{name}_calibration.json"))
    print(f"  {name}: layer {cal['layer']} zmin {cal['zmin']} n={len(rows)} | OR {det(rows)} | attn {det(rows, 'flags_attn')}")
    arms(rows, ["clean", "attack", "block_OR", "delete_OR_backfill"])
    print(f"    McNemar attack vs delete_OR_backfill endorsed p={mcn(rows, 'attack', 'delete_OR_backfill', 'endorsed'):.2g}")

print("\n== E25 permutation (attention z>=0 flags, layer 21)")
pr = J("results/e25_permute_nq_k10.jsonl")
for k in ("z_orig", "z_reversed", "z_shuffle0", "z_shuffle1"):
    rows = [{"labels": r["labels"], "flags_OR": [i for i, v in enumerate(r[k]) if v >= 0]} for r in pr]
    print(f"  {k:12s} {det(rows)}")
flip = np.mean([(a >= 0) != (b >= 0) for r in pr for a, b in zip(r["z_orig"], r["z_reversed"])])
print(f"  share of passages whose flag flips under reversal: {flip:.3f}")
slot0 = np.mean([r["z_clean_twin"][0] for r in pr]); rest = np.mean([np.mean(r["z_clean_twin"][1:]) for r in pr])
print(f"  clean-only twin: mean z slot 0 {slot0:.2f} vs slots 1-9 {rest:.2f}; flagged clean share {np.mean([v >= 0 for r in pr for v in r['z_clean_twin']]):.3f}")
sl = np.array([[v for v in r["z_clean_twin"]] for r in pr]).mean(0)
print("  clean twin mean z by slot:", np.round(sl, 2).tolist())

print("\n== E25 prefix-free control (M0)")
pf = J("results/e25_prefixfree_nq_k10.jsonl")
e11 = {r["id"]: r for r in J("results/e11a_flag_scores_nq_k10.jsonl")}
print(f"  n={len(pf)}; mean poisons retrieved in top-10 {np.mean([r['n_poison_retrieved'] for r in pf]):.2f} (prefixed: {np.mean([sum(l != 'clean' for l in e11[r['id']]['labels']) for r in pf]):.2f})")
print(f"  targets with no poison retrieved: {sum(r['n_poison_retrieved'] == 0 for r in pf)}")
print(f"  OR {det(pf)}")
ent_rows = [{"labels": r["labels"], "flags_OR": [i for i, v in enumerate(r["entail"]) if v >= .01]} for r in pf]
att_rows = [{"labels": r["labels"], "flags_OR": [i for i, v in enumerate(r["attn_z"]) if v >= 0]} for r in pf]
print(f"  entail {det(ent_rows)} | attn {det(att_rows)}")
lab = [l == "poison" for r in pf for l in r["labels"] if l != "captured"]
for k in ("entail", "attn_z", "avidity"):
    v = [x for r in pf for x, l in zip(r[k], r["labels"]) if l != "captured"]
    print(f"  {k:8s} AUC {roc_auc_score(lab, v):.3f}")
arms(pf, ["attack", "delete_OR_backfill"])
exp = [r for r in pf if r["n_poison_retrieved"] > 0]
print(f"  exposed targets only (n={len(exp)}): attack endorsed {rate(exp, 'attack', 'endorsed'):.2f}, defended {rate(exp, 'delete_OR_backfill', 'endorsed'):.2f}")

print("\n== E25 S4 blockade mechanism (partial if <80)")
s4 = J("results/e25_s4_nq_k10.jsonl")
print(f"  n={len(s4)}; all poisons flagged in {sum(r['all_poison_flagged'] for r in s4)}")
arms(s4, ["block_answer_side", "block_from_row0", "delete_no_backfill"])
for a, b in (("block_answer_side", "block_from_row0"), ("block_from_row0", "delete_no_backfill"), ("block_answer_side", "delete_no_backfill")):
    print(f"    McNemar {a} vs {b}: endorsed p={mcn(s4, a, b, 'endorsed'):.2g} correct p={mcn(s4, a, b, 'correct'):.2g}")
af = [r for r in s4 if r["all_poison_flagged"]]
print(f"  all-flagged stratum (n={len(af)}): endorsed answer-side {rate(af, 'block_answer_side', 'endorsed'):.2f} row0 {rate(af, 'block_from_row0', 'endorsed'):.2f} delete {rate(af, 'delete_no_backfill', 'endorsed'):.2f}")
