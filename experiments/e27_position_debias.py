"""E27: position-debiased attention (pre-registered single re-test after E25
permutation). Slot offsets = mean attention z per slot in CLEAN-ONLY top-10
contexts of the NQ 1-20 calibration targets, under the original order and its
reverse (so every passage is seen at two slots). Debiased z = z - offset[slot].
Evaluated on NQ dev under the four E25 orderings. Output JSON + summary."""
import json
import random

import numpy as np

from antivenom.llm import LocalLLM
from antivenom.masked import attention_rows, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import wrap_prompt

K, LAYER, TAIL = 10, 21, 8
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
targets, corpus = load("nq")
by = {t.id: t for t in targets}
llm = LocalLLM(); hf = llm.tok._tokenizer


def zf(v):
    v = np.array(v, float); return (v - v.mean()) / (v.std() + 1e-9)


def attn_z(q, pieces):
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(q, pieces)}], add_generation_prompt=True, tokenize=False)
    ids, spans = token_spans(hf, text, pieces)
    a = attention_rows(llm.model, ids, list(range(len(ids) - TAIL, len(ids))), [LAYER])[LAYER].mean(axis=(0, 1))
    return zf([a[s:e].mean() for s, e in spans])


acc = np.zeros(K); n = 0
for tid in order[:20]:
    t = by[tid]
    clean = [corpus[i]["title"] + " " + corpus[i]["text"] for i in t.clean_ids[:K]]
    acc += attn_z(t.question, clean); acc += attn_z(t.question, clean[::-1]); n += 2
    print(tid, flush=True)
off = acc / n
print("slot offsets", np.round(off, 3).tolist())

pr = [json.loads(l) for l in open("results/e25_permute_nq_k10.jsonl")]
perms = {"z_orig": list(range(K)), "z_reversed": list(range(K))[::-1]}
for s in (0, 1):
    p = list(range(K)); random.Random(s).shuffle(p); perms[f"z_shuffle{s}"] = p
res = {"offsets": off.tolist()}
for k, p in perms.items():
    slot_of = np.empty(K, int); slot_of[p] = np.arange(K)  # original index -> slot
    for name, deb in (("raw", False), ("debiased", True)):
        tp = P = fp = N = 0
        flags_all = []
        for r in pr:
            z = np.array(r[k]) - (off[slot_of] if deb else 0)
            z = zf(z) if deb else z
            f = z >= 0; flags_all.append(f)
            for i, l in enumerate(r["labels"]):
                if l == "poison": P += 1; tp += f[i]
                elif l == "clean": N += 1; fp += f[i]
        res[f"{k}_{name}"] = {"recall": tp / P, "fpr": fp / N}
for name in ("raw", "debiased"):
    rec = [res[f"{k}_{name}"]["recall"] for k in perms]; fpr = [res[f"{k}_{name}"]["fpr"] for k in perms]
    print(f"{name:9s} recall by order {np.round(rec, 3).tolist()} (range {max(rec) - min(rec):.3f}) | FPR {np.round(fpr, 3).tolist()}")
json.dump(res, open("results/e27_position_debias.json", "w"), indent=1)
