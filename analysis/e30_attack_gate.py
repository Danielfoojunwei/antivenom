"""E30 (CPU): attack gate. Fire the defence only if some passage in the
retrieved top-10 entails the captured claim (v1 hypothesis) with probability
>= g. g is chosen on NQ 1-20 (calibration): the largest g that still fires on
every attacked calibration context, excluding the captured passage itself (the
harder case). Clean-context entailment is computed fresh (NLI, CPU).
Evaluation: NQ dev and tier 1 (detection gate rates), tier 2 (gated answers
from stored E29 arms: gate off -> undefended answer)."""
import json

import numpy as np
from sentence_transformers import CrossEncoder

from antivenom.poisonedrag import load

nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")


def clean_top(d):
    targets, corpus = load(d)
    rel = json.load(open(f"data/external/poisonedrag/{d}-contriever.json"))
    return {t.id: [corpus[i]["title"] + " " + corpus[i]["text"] for i in sorted(t.clean_ids, key=lambda i: -rel[t.id][i])[:10]] for t in targets}


def hyp(q, c):
    return f'The answer to the question "{q}" is {c}.'


def attacked_max(ent, labels, excl_captured):
    return max([e for e, l in zip(ent, labels) if not (excl_captured and l == "captured")] or [0.0])


# NQ (calibration 1-20, development 21-100)
nq = [json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
ct = clean_top("nq")
rows = {}
for r in nq:
    h = hyp(r["question_extracted"], r["claim"])
    ce = nli.predict([(p, h) for p in ct[r["id"]]], apply_softmax=True)[:, 1]
    rows[r["id"]] = {"att_all": attacked_max(r["entail_qa"], r["labels"], False),
                     "att_excl": attacked_max(r["entail_qa"], r["labels"], True), "clean": float(ce.max())}
cal = [rows[r["id"]] for r in nq[:20]]
g = min(x["att_excl"] for x in cal) * 0.999
g = max(g, 1e-4)
print(f"gate threshold g (NQ 1-20) = {g:.5f}; calibration clean contexts firing {np.mean([x['clean'] >= g for x in cal]):.2f}")
out = {"g": g}


def report(name, R):
    fa = np.mean([x["att_all"] >= g for x in R]); fe = np.mean([x["att_excl"] >= g for x in R]); fc = np.mean([x["clean"] >= g for x in R])
    print(f"  {name:22s} n={len(R)}  fires on attacked {fa:.2f} (excl. captured {fe:.2f})  fires on clean {fc:.2f}")
    out[name] = {"attacked": fa, "attacked_excl": fe, "clean": fc}


report("NQ dev", [rows[r["id"]] for r in nq[20:]])
for d in ("hotpotqa", "msmarco"):
    ct = clean_top(d)
    R = []
    for r in (json.loads(l) for l in open(f"results/rescored/e15_cross_dataset_{d}_k10.jsonl")):
        h = hyp(r["question_extracted"], r["claim"])
        ce = nli.predict([(p, h) for p in ct[r["id"]]], apply_softmax=True)[:, 1]
        R.append({"att_all": attacked_max(r["entail"], r["labels"], False), "att_excl": attacked_max(r["entail"], r["labels"], True), "clean": float(ce.max())})
    report(f"{d} tier 1", R)

print("\n== tier 2 gated answers (gate decides; off -> undefended)")
ARM = {"v1": ("v1_delete_backfill", "defclean_v1"), "v2": ("v2_delete_backfill", "defclean_v2"), "coordguard": ("coordguard_af_refill", "defclean_coordguard")}
pooled = []
for d in ("hotpotqa", "msmarco"):
    ct = clean_top(d)
    for r in (json.loads(l) for l in open(f"results/e29_tier2_{d}_k10.jsonl")):
        h = hyp(r["question_extracted"], r["claim"])
        ce = nli.predict([(p, h) for p in ct[r["id"]]], apply_softmax=True)[:, 1]
        r["gate_att"] = attacked_max(r["entail_v1"], r["labels"], False) >= g
        r["gate_att_excl"] = attacked_max(r["entail_v1"], r["labels"], True) >= g
        r["gate_clean"] = float(ce.max()) >= g
        r["dataset"] = d
        pooled.append(r)
for scope in ("hotpotqa", "msmarco", "pooled"):
    R = [r for r in pooled if scope == "pooled" or r["dataset"] == scope]
    print(f"  {scope} n={len(R)}: gate fires attacked {np.mean([r['gate_att'] for r in R]):.2f} (excl. captured {np.mean([r['gate_att_excl'] for r in R]):.2f}), clean {np.mean([r['gate_clean'] for r in R]):.2f}")
    print(f"    no defence: attacked endorsed {np.mean([r['attack']['endorsed'] for r in R]):.2f} correct {np.mean([r['attack']['correct'] for r in R]):.2f} | clean correct {np.mean([r['clean']['correct'] for r in R]):.2f}")
    for name, (a, c) in ARM.items():
        for gk in ("gate_att", "gate_att_excl"):
            ae = np.mean([(r[a] if r[gk] else r["attack"])["endorsed"] for r in R]); ac = np.mean([(r[a] if r[gk] else r["attack"])["correct"] for r in R])
            cc = np.mean([(r[c] if r["gate_clean"] else r["clean"])["correct"] for r in R])
            print(f"    {name:10s} ungated: att endorsed {np.mean([r[a]['endorsed'] for r in R]):.2f} correct {np.mean([r[a]['correct'] for r in R]):.2f} clean-ctx correct {np.mean([r[c]['correct'] for r in R]):.2f}"
                  f" || gated({gk}): att endorsed {ae:.2f} correct {ac:.2f} clean-ctx correct {cc:.2f}")
json.dump(out, open("results/e30_attack_gate.json", "w"), indent=1)
