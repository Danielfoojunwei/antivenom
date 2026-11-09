"""Exploratory E34; see docs/CONTINUATION_PROTOCOL.md. Offline cached models only."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from antivenom.llm import DEFAULT_MODEL, LocalLLM
from antivenom.masked import generate_masked, token_spans
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    sources = [__file__, "docs/CONTINUATION_PROTOCOL.md", "src/antivenom/qa.py",
               "src/antivenom/masked.py", "src/antivenom/llm.py", "src/antivenom/retriever.py",
               "src/antivenom/poisonedrag.py", "results/e11a_flag_scores_nq_k10.jsonl",
               "results/e11c_attention_scores_nq_k10.jsonl", "results/e32_backfill_placebo_nq_k10.jsonl",
               *[f"data/external/poisonedrag/{p}" for p in
                 ("nq.json", "nq-contriever.json", "nq_target_corpus.json")]]
    manifest = {"model": DEFAULT_MODEL, "max_tokens": 48, "split": "NQ development 21-100",
                "hashes": {str(Path(p).relative_to(Path.cwd())) if Path(p).is_absolute() else p:
                           hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources}}
    mpath = Path("results/e34_manifest.json")
    if mpath.exists():
        assert json.loads(mpath.read_text()) == manifest, "E34 frozen inputs changed"
    else:
        mpath.write_text(json.dumps(manifest, indent=2) + "\n")
    ent = [json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")]
    att = {r["id"]: r for r in map(json.loads, open("results/e11c_attention_scores_nq_k10.jsonl"))}
    prior = {r["id"]: r for r in map(json.loads, open("results/e32_backfill_placebo_nq_k10.jsonl"))}
    dev = [r["id"] for r in ent[20:]]
    assert len(dev) == len(prior) == 80 and set(dev) == set(prior)
    targets, corpus = load("nq")
    by = {t.id: t for t in targets}
    rel = json.load(open("data/external/poisonedrag/nq-contriever.json"))
    retriever, llm = Contriever(), LocalLLM()
    hf = llm.tok._tokenizer

    def pool_of(t):
        q = retriever.encode([t.question])[0]
        pool = [(corpus[i]["title"] + " " + corpus[i]["text"], rel[t.id][i], "clean") for i in t.clean_ids]
        pool += [(p, float(v @ q), "captured" if j == 0 else "poison")
                 for j, (p, v) in enumerate(zip(t.poison, retriever.encode(t.poison)))]
        return sorted(pool, key=lambda c: -c[1])

    def answer(t, pieces):
        text = llm.tok.apply_chat_template([{"role": "user", "content": wrap_prompt(t.question, pieces)}],
                                            add_generation_prompt=True, tokenize=False)
        ids, _ = token_spans(hf, text, pieces)
        resp = generate_masked(llm.model, llm.tok, ids, [], 0.0, from_row=0).strip()
        return {"resp": resp, "endorsed": bool(endorses(resp, t.incorrect)),
                "correct": bool(correct(resp, t.correct)), "prompt_tokens": len(ids)}

    out = Path("results/e34_fixed_slots_nq_k10.jsonl")
    existing = [json.loads(l) for l in out.open()] if out.exists() else []
    done = {r["id"] for r in existing}
    assert len(done) == len(existing) and done <= set(dev)
    count, checked = 0, False
    with out.open("a") as f:
        for n, r in enumerate(ent[20:]):
            tid = r["id"]
            if tid in done:
                continue
            start = time.monotonic()
            t = by[tid]
            pool = pool_of(t)
            top = pool[:10]
            assert [c[2] for c in top] == r["labels"] == att[tid]["labels"], tid
            a = np.array(att[tid]["attn"]["21"]["per_token"])
            z = (a - a.mean()) / (a.std() + 1e-9)
            flags = sorted({i for i, v in enumerate(r["entail_qa"]) if v >= .01} |
                           {i for i, v in enumerate(z) if v >= 0})
            other = by[dev[(n + 1) % len(dev)]]
            true = pool[10:10 + len(flags)]
            placebo = [c for c in pool_of(other) if c[2] == "clean"][10:10 + len(flags)]
            assert len(true) == len(placebo) == len(flags) == prior[tid]["n_flags"]
            assert other.id == prior[tid]["placebo_from"]
            if not checked:
                kept = [c[0] for i, c in enumerate(top) if i not in flags]
                repeat = answer(t, kept + [c[0] for c in true])
                assert repeat["resp"] == prior[tid]["delete_true_backfill"]["resp"], "E32 repeatability failed"
                checked = True
                print("E32 repeatability passed:", tid, flush=True)
            row = {"id": tid, "flags": flags, "labels": r["labels"], "placebo_from": other.id,
                   "original_passage_hashes": [digest(c[0]) for c in top], "repeatability_checked": checked and count == 0}
            for name, repl in (("true_inplace", true), ("placebo_inplace", placebo)):
                pieces = [c[0] for c in top]
                for i, c in zip(flags, repl):
                    pieces[i] = c[0]
                assert len(pieces) == 10
                assert all(pieces[i] == top[i][0] for i in range(10) if i not in flags)
                row[name] = {**answer(t, pieces), "n_passages": len(pieces),
                             "replacement_labels": [c[2] for c in repl],
                             "replacement_hashes": [digest(c[0]) for c in repl]}
            f.write(json.dumps(row) + "\n")
            f.flush()
            count += 1
            print(tid, f"{len(done) + count}/80", f"{time.monotonic() - start:.1f}s", flush=True)
            if args.limit and count >= args.limit:
                break


if __name__ == "__main__":
    main()
