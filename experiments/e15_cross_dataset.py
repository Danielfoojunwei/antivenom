"""E15: cross-dataset test with every setting frozen at its NQ value.

Per target: the immunologist extracts the claim from poison[0] only; passages
in the attacked top-10 are flagged by entailment (NQ phrasing, tau=0.01) and by
attention concentration (layer 21, per-token mass, z>=0); OR combines them.
Answers are generated for clean, attack, OR-blockade and OR-deletion+backfill.
Usage: python experiments/e15_cross_dataset.py hotpotqa --limit 50
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder

from antivenom.antibody import Immunologist
from antivenom.llm import LocalLLM
from antivenom.masked import attention_rows, generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

ap = argparse.ArgumentParser()
ap.add_argument("dataset")
ap.add_argument("--limit", type=int, default=50)
args = ap.parse_args()

K, S, TAU, LAYER, TAIL = 10, -5.0, 0.01, 21, 8
targets, corpus = load(args.dataset)
targets = targets[: args.limit]
released = json.load(open(f"data/external/poisonedrag/{args.dataset}-contriever.json"))
R = Contriever()
llm = LocalLLM()
hf = llm.tok._tokenizer
imm = Immunologist(llm)
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")


def prompt_ids(question, pieces):
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    return token_spans(hf, text, pieces)


def answer(t, ctx, block=()):
    ids, spans = prompt_ids(t.question, [c[0] for c in ctx])
    resp = generate_masked(llm.model, llm.tok, ids, [spans[i] for i in block], S,
                           from_row=spans[-1][1]).strip()
    return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)}


out = Path(f"results/e15_cross_dataset_{args.dataset}_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id in done:
            continue
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], "clean") for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), "captured" if j == 0 else "poison")
                 for j, (p, v) in enumerate(zip(t.poison, R.encode(t.poison)))]
        pool.sort(key=lambda x: -x[1])
        top = pool[:K]
        labels = [c[2] for c in top]

        an = imm.analyse(t.poison[0])
        hyp = f'The answer to the question "{an.question}" is {an.false_claim}.'
        ent = nli.predict([(c[0], hyp) for c in top], apply_softmax=True)[:, 1]
        ent_flags = {i for i, s in enumerate(ent) if s >= TAU}

        ids, spans = prompt_ids(t.question, [c[0] for c in top])
        a = attention_rows(llm.model, ids, list(range(len(ids) - TAIL, len(ids))), [LAYER])[LAYER]
        m = a.mean(axis=(0, 1))
        per_tok = np.array([m[s:e].mean() for s, e in spans])
        z = (per_tok - per_tok.mean()) / (per_tok.std() + 1e-9)
        att_flags = {i for i, v in enumerate(z) if v >= 0}
        or_flags = sorted(ent_flags | att_flags)

        kept = [c for i, c in enumerate(top) if i not in set(or_flags)]
        row = {"id": t.id, "labels": labels, "claim": an.false_claim, "question_extracted": an.question,
               "entail": [round(float(x), 5) for x in ent], "attn_z": [round(float(x), 3) for x in z],
               "flags_entail": sorted(ent_flags), "flags_attn": sorted(att_flags), "flags_OR": or_flags,
               "clean": answer(t, [c for c in pool if c[2] == "clean"][:K]),
               "attack": answer(t, top),
               "block_OR": answer(t, top, or_flags),
               "delete_OR_backfill": answer(t, kept + pool[K:K + len(or_flags)])}
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, len(or_flags), {k: int(row[k]["endorsed"]) for k in
                                    ("clean", "attack", "block_OR", "delete_OR_backfill")}, flush=True)
