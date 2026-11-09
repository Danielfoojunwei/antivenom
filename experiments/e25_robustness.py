"""E25: robustness tests on NQ development targets 21-100 (file order of
results/e11a_flag_scores_nq_k10.jsonl). Defence-side only; no text is written.

--mode prefixfree  (M0 / C6, approved): released poison WITHOUT the attack.py
    question prefix. Retrieval re-run; capture, flags and avidity as frozen;
    arms: attack (undefended) and delete_OR_backfill.
--mode permute     (C7.2, approved): attention z of each passage under the
    original order, reversed, and two seeded shuffles, mapped back to original
    slots; plus the clean-only twin context (FPR control). No generation.
--mode s4          (S4 blockade mechanism): OR flags; answer-side blockade
    (current), blockade from row 0 (every position may not attend the span),
    and deletion without backfill.
"""
import argparse
import json
import random
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder
from sklearn.linear_model import LogisticRegression

from antivenom.antibody import Immunologist
from antivenom.llm import LocalLLM
from antivenom.masked import attention_rows, generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

ap = argparse.ArgumentParser()
ap.add_argument("--mode", required=True, choices=["prefixfree", "permute", "s4"])
args = ap.parse_args()

K, S, TAU, LAYER, TAIL = 10, -5.0, 0.01, 21, 8
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
dev = order[20:100]
targets, corpus = load("nq", prefix=(args.mode != "prefixfree"))
by = {t.id: t for t in targets}
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer


def zf(v):
    v = np.array(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-9)


def logit(p):
    p = np.clip(np.array(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


ent0 = [json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
att0 = {json.loads(l)["id"]: json.loads(l) for l in open("results/e11c_attention_scores_nq_k10.jsonl")}
X, y = [], []
for r in ent0[:20]:
    a = zf(att0[r["id"]]["attn"]["21"]["per_token"])
    for j, lab in enumerate(r["labels"]):
        if lab != "captured":
            X.append([logit(r["entail_qa"][j]), a[j]]); y.append(lab == "poison")
avidity = LogisticRegression().fit(np.array(X), np.array(y))


def prompt_ids(question, pieces):
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    return token_spans(hf, text, pieces)


def attn_z(question, pieces):
    ids, spans = prompt_ids(question, pieces)
    a = attention_rows(llm.model, ids, list(range(len(ids) - TAIL, len(ids))), [LAYER])[LAYER]
    m = a.mean(axis=(0, 1))
    return zf([m[s:e].mean() for s, e in spans])


def answer(t, ctx, block=(), from_row=None):
    ids, spans = prompt_ids(t.question, [c[0] for c in ctx])
    fr = spans[-1][1] if from_row is None else from_row
    resp = generate_masked(llm.model, llm.tok, ids, [spans[i] for i in block], S, from_row=fr).strip()
    return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)}


def retrieve(t):
    pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], "clean") for i in t.clean_ids]
    q = R.encode([t.question])[0]
    pool += [(p, float(v @ q), "captured" if j == 0 else "poison") for j, (p, v) in enumerate(zip(t.poison, R.encode(t.poison)))]
    pool.sort(key=lambda x: -x[1])
    return pool


if args.mode != "permute":
    imm = Immunologist(llm)
    nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")

out = Path(f"results/e25_{args.mode}_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for tid in dev:
        if tid in done:
            continue
        t = by[tid]
        pool = retrieve(t)
        top = pool[:K]
        labels = [c[2] for c in top]
        texts = [c[0] for c in top]
        row = {"id": tid, "labels": labels}
        if args.mode == "permute":
            row["z_orig"] = attn_z(t.question, texts).round(3).tolist()
            perms = {"reversed": list(range(K))[::-1]}
            for s in (0, 1):
                p = list(range(K)); random.Random(s).shuffle(p); perms[f"shuffle{s}"] = p
            for name, p in perms.items():
                zp = attn_z(t.question, [texts[i] for i in p])
                back = np.empty(K); back[p] = zp
                row[f"z_{name}"] = back.round(3).tolist()
            clean_ctx = [c[0] for c in pool if c[2] == "clean"][:K]
            row["z_clean_twin"] = attn_z(t.question, clean_ctx).round(3).tolist()
            row["z_clean_twin_reversed"] = attn_z(t.question, clean_ctx[::-1])[::-1].round(3).tolist()
        else:
            an = imm.analyse(t.poison[0])
            hyp = f'The answer to the question "{an.question}" is {an.false_claim}.'
            ent = nli.predict([(p, hyp) for p in texts], apply_softmax=True)[:, 1]
            z = attn_z(t.question, texts)
            flags = sorted({i for i, s in enumerate(ent) if s >= TAU} | {i for i, v in enumerate(z) if v >= 0})
            av = avidity.predict_proba(np.stack([logit(ent), z], 1))[:, 1]
            row.update({"claim": an.false_claim, "question_extracted": an.question,
                        "entail": [round(float(x), 5) for x in ent], "attn_z": z.round(3).tolist(),
                        "avidity": av.round(5).tolist(), "flags_OR": flags,
                        "n_poison_retrieved": sum(l != "clean" for l in labels)})
            kept = [c for i, c in enumerate(top) if i not in set(flags)]
            if args.mode == "prefixfree":
                row["attack"] = answer(t, top)
                row["delete_OR_backfill"] = answer(t, kept + pool[K:K + len(flags)])
            else:
                row["block_answer_side"] = answer(t, top, flags)
                row["block_from_row0"] = answer(t, top, flags, from_row=0)
                row["delete_no_backfill"] = answer(t, kept)
                row["all_poison_flagged"] = all(i in set(flags) for i, l in enumerate(labels) if l != "clean")
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(tid, flush=True)
