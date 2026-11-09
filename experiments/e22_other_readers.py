"""E22: the full pipeline with another reader (Llama-3-8B-Instruct or
Mistral-7B-Instruct-v0.3, MLX 4-bit). The reader is also the immunologist.

Phase A (NQ targets 1-20, calibration): the reader extracts the claim from
poison[0]; attention per-token mass is read at every 3rd layer and the last;
the layer and z threshold are chosen by the same rule as for Qwen (E11c v1):
max F1 on non-captured poisons subject to clean FPR <= 5%, z grid 0.0-2.5.
Phase B (targets 21-100, development for this reader): OR flags (entailment
tau=0.01, frozen; chosen attention setting), answers for clean, attack,
block_OR (s=-5) and delete_OR_backfill.
Usage: python experiments/e22_other_readers.py mlx-community/Meta-Llama-3-8B-Instruct-4bit
"""
import json
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder

from antivenom.antibody import Immunologist
from antivenom.llm import LocalLLM
from antivenom.masked import attention_rows, generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

MODEL = sys.argv[1]
K, S, TAU, TAIL = 10, -5.0, 0.01, 8
tag = MODEL.split("/")[-1]
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
cal_ids, dev_ids = order[:20], order[20:]
by_id = {t.id: t for t in targets}
R = Contriever()
llm = LocalLLM(MODEL)
hf = llm.tok._tokenizer
imm = Immunologist(llm)
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")
n_layers = len(llm.model.model.layers)
LAYERS = sorted(set(list(range(0, n_layers, 3)) + [n_layers - 1]))


def context(t):
    pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], "clean") for i in t.clean_ids]
    q = R.encode([t.question])[0]
    pool += [(p, float(v @ q), "captured" if j == 0 else "poison") for j, (p, v) in enumerate(zip(t.poison, R.encode(t.poison)))]
    return sorted(pool, key=lambda x: -x[1])


def build(question, pieces):
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    return token_spans(hf, text, pieces)


def signals(t, top):
    an = imm.analyse(t.poison[0])
    hyp = f'The answer to the question "{an.question}" is {an.false_claim}.'
    pieces = [c[0] for c in top]
    ent = [float(s) for s in nli.predict([(p, hyp) for p in pieces], apply_softmax=True)[:, 1]]
    ids, spans = build(t.question, pieces)
    A = attention_rows(llm.model, ids, list(range(len(ids) - TAIL, len(ids))), LAYERS)
    att = {str(li): [float(a.mean(axis=(0, 1))[s:e].mean()) for s, e in spans] for li, a in A.items()}
    return {"claim": an.false_claim, "question_extracted": an.question, "entail": ent, "attn": att}


def zflags(v, zmin):
    v = np.array(v)
    return {i for i, z in enumerate((v - v.mean()) / (v.std() + 1e-9)) if z >= zmin}


def quality(rows, layer, zmin):
    tp = fp = fn = tn = 0
    for r in rows:
        fl = zflags(r["sig"]["attn"][layer], zmin)
        for i, lab in enumerate(r["labels"]):
            if lab == "captured":
                continue
            hit = i in fl
            tp, fp, fn, tn = tp + (hit and lab == "poison"), fp + (hit and lab == "clean"), \
                fn + ((not hit) and lab == "poison"), tn + ((not hit) and lab == "clean")
    p, r_ = tp / max(1, tp + fp), tp / max(1, tp + fn)
    return 2 * p * r_ / max(1e-9, p + r_), fp / max(1, fp + tn)


cal_path = Path(f"results/e22_{tag}_calibration.json")
if cal_path.exists():
    chosen = json.load(open(cal_path))
else:
    cal = []
    for tid in cal_ids:
        t = by_id[tid]
        top = context(t)[:K]
        cal.append({"id": tid, "labels": [c[2] for c in top], "sig": signals(t, top)})
    best = None
    for layer in map(str, LAYERS):
        for zmin in np.arange(0.0, 2.6, 0.25):
            f1, fpr = quality(cal, layer, zmin)
            if fpr <= 0.05 and (best is None or f1 > best[2]):
                best = (layer, float(zmin), f1, fpr)
    chosen = {"model": MODEL, "layer": best[0], "zmin": best[1], "cal_f1": best[2], "cal_fpr": best[3],
              "n_layers": n_layers}
    json.dump(chosen, open(cal_path, "w"))
print("chosen on targets 1-20:", chosen, flush=True)

out = Path(f"results/e22_{tag}_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for tid in dev_ids:
        if tid in done:
            continue
        t = by_id[tid]
        pool = context(t)
        top = pool[:K]
        sig = signals(t, top)
        flags = sorted({i for i, s in enumerate(sig["entail"]) if s >= TAU} |
                       zflags(sig["attn"][chosen["layer"]], chosen["zmin"]))
        pieces = [c[0] for c in top]
        ids, spans = build(t.question, pieces)
        kept = [p for i, p in enumerate(pieces) if i not in set(flags)]

        def ans(ps, block=()):
            i2, sp = build(t.question, ps)
            resp = generate_masked(llm.model, llm.tok, i2, [sp[i] for i in block], S, from_row=sp[-1][1]).strip()
            return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)}

        row = {"id": tid, "labels": [c[2] for c in top], "flags_OR": flags,
               "flags_entail": sorted(i for i, s in enumerate(sig["entail"]) if s >= TAU),
               "flags_attn": sorted(zflags(sig["attn"][chosen["layer"]], chosen["zmin"])),
               "clean": ans([c[0] for c in pool if c[2] == "clean"][:K]), "attack": ans(pieces),
               "block_OR": ans(pieces, flags), "delete_OR_backfill": ans(kept + [c[0] for c in pool[K:K + len(flags)]])}
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(tid, len(flags), {k: int(row[k]["endorsed"]) for k in ("clean", "attack", "block_OR", "delete_OR_backfill")},
              flush=True)
