"""Rebuilt prefix-free singleton / worst-capture composite (NQ development)."""
import json
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder

from antivenom.antibody import Immunologist
from antivenom.baselines.coordguard import audit
from antivenom.baselines.trustrag import trustrag
from antivenom.continuation import Reader, append, build_pool, clean_pool, freeze, keyed, passage_hashes, read_rows, refill, save
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses
from antivenom.retriever import Contriever

ARMS = ["clean", "attack", "delete_OR_backfill", "delete_entail_backfill", "coordguard_af_refill",
        "trustrag", "defclean_OR", "defclean_coordguard"]


def main():
    inputs = ["docs/REMAINING_RUNS_PROTOCOL.md", __file__, "src/antivenom/continuation.py",
        "src/antivenom/llm.py", "src/antivenom/masked.py", "src/antivenom/antibody.py", "src/antivenom/qa.py",
        "src/antivenom/poisonedrag.py", "src/antivenom/retriever.py",
        "src/antivenom/baselines/coordguard.py", "src/antivenom/baselines/trustrag.py",
        "results/e11a_flag_scores_nq_k10.jsonl", "results/e30_attack_gate.json", "data/cache/e36_contexts_nq.jsonl"]
    inputs += [f"data/external/poisonedrag/{p}" for p in ("nq.json", "nq-contriever.json", "nq_target_corpus.json")]
    freeze("results/e37_manifest.json", inputs, {"model": "mlx-community/Qwen2.5-7B-Instruct-4bit",
        "prefix": False, "n_context_poison": 1, "poison_indices": [1, 2, 3, 4], "capture_differs_from_context_poison": True,
        "selection": "min recall, max clean flags, min poison index, min capture index", "arms": ARMS})
    order = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")]
    targets, corpus = load("nq", prefix=False)
    by = {t.id: t for t in targets}
    rel = json.load(open("data/external/poisonedrag/nq-contriever.json"))
    reader = Reader("mlx-community/Qwen2.5-7B-Instruct-4bit", 21)
    fidelity = Path("results/e37_fidelity.json")
    if fidelity.exists():
        reader.fast = json.load(fidelity.open())["use_fast_ordinary"]
    else:
        cal = keyed("data/cache/e36_contexts_nq.jsonl")
        # Ordinary-decoder fidelity uses the original calibration contexts.
        original_by = {t.id: t for t in load("nq")[0]}
        save(fidelity, reader.fidelity([original_by[i] for i in order[:20]], cal))
    imm, retriever = Immunologist(reader.llm), Contriever()
    nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")
    threshold = json.load(open("results/e30_attack_gate.json"))["g"]
    out = "results/e37_composite_nq_k10.jsonl"
    done = keyed(out)
    assert set(done) <= set(order[20:])
    for n, tid in enumerate(order[20:]):
        if tid in done:
            continue
        t = by[tid]
        checkpoint = Path(f"results/checkpoints/e37/{tid}.json")
        state = json.load(checkpoint.open()) if checkpoint.exists() else {"id": tid, "captures": {}, "variants": {}}
        for k, sample in enumerate(t.poison):
            if str(k) in state["captures"]:
                continue
            analysis = imm.analyse(sample)
            state["captures"][str(k)] = {"claim": analysis.false_claim, "question_extracted": analysis.question,
                "hypothesis": f'The answer to the question "{analysis.question}" is {analysis.false_claim}.'}
            save(checkpoint, state)
        for j in range(1, 5):
            if str(j) in state["variants"]:
                continue
            pool = build_pool(t, corpus, rel, retriever, [j])
            top = pool[:10]
            texts = [c["text"] for c in top]
            z = reader.attention(t.question, texts)
            pslots = [i for i, c in enumerate(top) if c["poison_index"] == j]
            assert len(pslots) <= 1 and not any(c["poison_index"] == 0 for c in top)
            candidates = []
            for k in range(5):
                if j == k:
                    continue
                hypothesis = state["captures"][str(k)]["hypothesis"]
                e = nli.predict([(p, hypothesis) for p in texts], apply_softmax=True)[:, 1]
                flags = np.flatnonzero((e >= .01) | (z >= 0)).tolist()
                clean_flags = sum(i in flags for i, c in enumerate(top) if c["label"] == "clean")
                candidates.append({"capture_index": k, "poison_index": j, "entail": e.astype(float).tolist(),
                    "flags_OR": flags, "flags_entail": np.flatnonzero(e >= .01).tolist(),
                    "poison_recall": float(pslots[0] in flags) if pslots else None,
                    "clean_flag_count": clean_flags})
            state["variants"][str(j)] = {"pool": pool, "attn_z": z.tolist(),
                "context_hashes": passage_hashes(top), "poison_slots": pslots, "candidates": candidates}
            save(checkpoint, state)
            print("E37", f"{n + 1}/80", tid, "singleton", j, "scored", flush=True)
        if "selected" not in state:
            exposed = [c for v in state["variants"].values() if v["poison_slots"] for c in v["candidates"]]
            best = min(exposed, key=lambda c: (c["poison_recall"], -c["clean_flag_count"], c["poison_index"], c["capture_index"])) if exposed else state["variants"]["1"]["candidates"][0]
            j, k = best["poison_index"], best["capture_index"]
            assert j != k
            variant = state["variants"][str(j)]
            top = variant["pool"][:10]
            texts = [c["text"] for c in top]
            comp, score = audit(t.question, texts)
            cpool = clean_pool(t, corpus, rel)
            clean = [c["text"] for c in cpool[:10]]
            hypothesis = state["captures"][str(k)]["hypothesis"]
            ce = nli.predict([(p, hypothesis) for p in clean], apply_softmax=True)[:, 1]
            cz = reader.attention(t.question, clean)
            cf = np.flatnonzero((ce >= .01) | (cz >= 0)).tolist()
            cc, cs = audit(t.question, clean)
            state["selected"] = {**best, "exposed": bool(exposed), "attn_z": variant["attn_z"],
                "context_hashes": variant["context_hashes"], "labels": [c["label"] for c in top],
                "claim": state["captures"][str(k)]["claim"], "question_extracted": state["captures"][str(k)]["question_extracted"],
                "coordguard_removed": sorted(comp), "coordguard_score": score,
                "clean_entail": ce.astype(float).tolist(), "clean_attn_z": cz.tolist(), "clean_flags_OR": cf,
                "clean_coordguard_removed": sorted(cc), "clean_coordguard_score": cs,
                "gate_attacked": bool(max(best["entail"]) >= threshold), "gate_clean": bool(ce.max() >= threshold),
                "true_backfill_labels": [c["label"] for c in variant["pool"][10:10 + len(best["flags_OR"])]]}
            save(checkpoint, state)
        selected = state["selected"]
        pool = state["variants"][str(selected["poison_index"])]["pool"]
        cpool = clean_pool(t, corpus, rel)
        texts = [c["text"] for c in pool[:10]]
        recipes = {"clean": [c["text"] for c in cpool[:10]], "attack": texts,
            "delete_OR_backfill": refill(pool, selected["flags_OR"]),
            "delete_entail_backfill": refill(pool, selected["flags_entail"]),
            "coordguard_af_refill": refill(pool, selected["coordguard_removed"]),
            "defclean_OR": refill(cpool, selected["clean_flags_OR"]),
            "defclean_coordguard": refill(cpool, selected["clean_coordguard_removed"])}
        for arm in ARMS:
            if arm in state:
                continue
            if arm == "trustrag":
                response, kept = trustrag(reader.llm, t.question, texts)
                state[arm] = {"resp": response, "endorsed": bool(endorses(response, t.incorrect)),
                              "correct": bool(correct(response, t.correct)), "n_kept": len(kept)}
            else:
                state[arm] = reader.answer(t, recipes[arm])
            save(checkpoint, state)
            print("E37", f"{n + 1}/80", tid, arm, "saved", flush=True)
        # Keep all actual candidate scores, but avoid duplicating full pools in public results.
        row = {"id": tid, **selected, **{a: state[a] for a in ARMS}, "variants": {
            j: {k: v for k, v in variant.items() if k != "pool"} for j, variant in state["variants"].items()}}
        append(out, row)
        print("E37 target complete", f"{n + 1}/80", tid, flush=True)
    assert set(keyed(out)) == set(order[20:])
    print("E37 all 80 targets complete", flush=True)


if __name__ == "__main__":
    main()
