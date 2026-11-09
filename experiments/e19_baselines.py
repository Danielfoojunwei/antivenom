"""E19: SOTA baselines on the same held-out NQ targets (21-100) and the same
attacked top-10 contexts as E11/E12: TrustRAG and RobustRAG keyword
aggregation, both ported from released code (see src/antivenom/baselines/).
Released prompts are sent to our chat reader as a single user message.
Scored with the validated endorses rule and correct."""
import json
from pathlib import Path

from antivenom.baselines.coordguard import audit
from antivenom.baselines.robustrag import keyword_agg
from antivenom.baselines.trustrag import trustrag
from antivenom.llm import LocalLLM
from antivenom.masked import generate_masked
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

K = 10
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
order = [json.loads(l)["id"] for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
held_out = set(order[20:])
R = Contriever()
llm = LocalLLM()


def answer(t, pieces):
    """Same prompt (PoisonedRAG MULTIPLE_PROMPT) and 48-token greedy decoder as
    every other arm, with no blockade."""
    text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}],
                                       add_generation_prompt=True, tokenize=False)
    ids = llm.tok._tokenizer(text, add_special_tokens=False)["input_ids"]
    resp = generate_masked(llm.model, llm.tok, ids, [], 0.0, from_row=0).strip()
    return {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct)}

out = Path("results/e19_baselines_nq_k10.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
with out.open("a") as f:
    for t in targets:
        if t.id not in held_out or t.id in done:
            continue
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i], False) for i in t.clean_ids]
        q = R.encode([t.question])[0]
        pool += [(p, float(v @ q), True) for p, v in zip(t.poison, R.encode(t.poison))]
        top = sorted(pool, key=lambda x: -x[1])[:K]
        docs = [c[0] for c in top]
        resp, kept = trustrag(llm, t.question, docs)
        poison_set = set(t.poison)
        row = {"id": t.id,
               "trustrag": {"resp": resp, "endorsed": endorses(resp, t.incorrect), "correct": correct(resp, t.correct),
                            "kept": len(kept), "poison_kept": sum(d in poison_set for d in kept),
                            "clean_kept": sum(d not in poison_set for d in kept),
                            "clean_in": sum(not c[2] for c in top)}}
        rr, info = keyword_agg(llm, t.question, docs)
        row["robustrag_keyword"] = {"resp": rr, "endorsed": endorses(rr, t.incorrect),
                                    "correct": correct(rr, t.correct), "hints": info["hints"]}
        # CoordGuard always-filter: remove C*; and the paper's relevance-refill variant
        comp, score = audit(t.question, docs)
        kept_cg = [d for i, d in enumerate(docs) if i not in set(comp)]
        refill = kept_cg + [c[0] for c in sorted(pool, key=lambda x: -x[1])[K:K + len(comp)]]
        for name, ctx in (("coordguard_af", kept_cg), ("coordguard_af_refill", refill)):
            r = answer(t, ctx)
            r.update(removed=comp, audit_score=score,
                     removed_poison=sum(top[i][2] for i in comp), removed_clean=sum(not top[i][2] for i in comp))
            row[name] = r
        f.write(json.dumps(row) + "\n")
        f.flush()
        print(t.id, row["trustrag"]["poison_kept"], row["trustrag"]["clean_kept"],
              int(row["trustrag"]["endorsed"]), int(row["trustrag"]["correct"]), flush=True)
