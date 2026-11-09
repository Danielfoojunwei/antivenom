"""Full E29 arm set on additional readers; see REMAINING_RUNS_PROTOCOL.md."""
import argparse
import json
import random
import re
import time
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder
from sklearn.linear_model import LogisticRegression

from antivenom.antibody import Immunologist
from antivenom.baselines.trustrag import trustrag
from antivenom.continuation import Reader, append, clean_pool, freeze, keyed, logit, read_rows, refill, save, zf
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses
from antivenom.retriever import Contriever  # also fixes torch CPU thread count

YN = re.compile(r"^(are|is|was|were|do|does|did|can|could|has|have|had|will|would|should)\b", re.I)
STRIP = re.compile(r'^\s*the record claims(\s+that)?\s*:?\s*"?', re.I)
REWRITE = '''Question: {q}
A record claims: "{c}"
Rewrite the record's claim as one self-contained declarative sentence that names every person, place or thing explicitly (no pronouns) and states the claim as a direct answer to the question. Keep the record's position exactly; do not add or correct anything. Return only the sentence.'''
ARMS = ["clean", "attack", "v1_block", "v1_delete_backfill", "v2_delete_backfill",
        "random_delete_backfill", "lowrel_delete_backfill", "coordguard_af", "coordguard_af_refill",
        "trustrag", "defclean_v1", "defclean_v2", "defclean_coordguard"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", choices=["mlx-community/Meta-Llama-3-8B-Instruct-4bit",
                                      "mlx-community/Mistral-7B-Instruct-v0.3-4bit"])
    args = ap.parse_args()
    tag = args.model.split("/")[-1]
    prefix = f"results/e36_{tag}"
    cal22_path = f"results/e22_{tag}_calibration.json"
    cal22 = json.load(open(cal22_path))
    inputs = ["docs/REMAINING_RUNS_PROTOCOL.md", __file__, "src/antivenom/continuation.py", cal22_path,
        "src/antivenom/llm.py", "src/antivenom/masked.py", "src/antivenom/qa.py",
        "src/antivenom/antibody.py", "src/antivenom/baselines/trustrag.py",
        "results/e36_geometry_gate_calibration.json"]
    inputs += [f"data/cache/e36_contexts_{d}.jsonl" for d in ("nq", "hotpotqa", "msmarco")]
    inputs += [f"data/external/poisonedrag/{d}.json" for d in ("nq", "hotpotqa", "msmarco")]
    freeze(prefix + "_manifest.json", inputs, {"model": args.model, "v1_layer": cal22["layer"],
        "v1_zmin": cal22["zmin"], "answer_cap": 48, "arms": ARMS})
    contexts = {d: keyed(f"data/cache/e36_contexts_{d}.jsonl") for d in ("nq", "hotpotqa", "msmarco")}
    cal_targets_by = {t.id: t for t in load("nq")[0]}
    order = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][:20]
    cal_targets = [cal_targets_by[i] for i in order]
    assert set(order) == set(contexts["nq"])
    reader = Reader(args.model, cal22["layer"])
    fidelity_path = prefix + "_fidelity.json"
    if Path(fidelity_path).exists():
        reader.fast = json.load(open(fidelity_path))["use_fast_ordinary"]
    else:
        save(fidelity_path, reader.fidelity(cal_targets, contexts["nq"]))
    print(tag, "ordinary decoder fast:", reader.fast, flush=True)
    imm = Immunologist(reader.llm)
    nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")

    def claim(t):
        an = imm.analyse(t.poison[0])
        h1 = f'The answer to the question "{an.question}" is {an.false_claim}.'
        yn = bool(YN.match(an.question.strip()))
        h2 = h1
        if yn:
            h2 = reader.llm.generate([{"role": "user", "content": REWRITE.format(q=an.question, c=an.false_claim)}],
                                      temp=0.0, max_tokens=80).strip().strip('"')
            h2 = STRIP.sub("", h2).strip().strip('"')
        return {"claim": an.false_claim, "question_extracted": an.question, "yesno": yn,
                "hyp_v1": h1, "hyp_v2": h2}

    def signals(t, texts, sig):
        e1 = nli.predict([(p, sig["hyp_v1"]) for p in texts], apply_softmax=True)[:, 1]
        e2 = e1 if sig["hyp_v1"] == sig["hyp_v2"] else nli.predict(
            [(p, sig["hyp_v2"]) for p in texts], apply_softmax=True)[:, 1]
        return {"entail_v1": e1.astype(float).tolist(), "entail_v2": e2.astype(float).tolist(),
                "attn_z": reader.attention(t.question, texts).tolist()}

    cal_path = prefix + "_calibration_rows.jsonl"
    done = keyed(cal_path)
    for n, t in enumerate(cal_targets):
        if t.id in done:
            continue
        ctx = contexts["nq"][t.id]
        texts = [c["text"] for c in ctx["pool"][:10]]
        clean = [c["text"] for c in ctx["clean_pool"][:10]]
        sig = claim(t)
        values = signals(t, texts, sig)
        append(cal_path, {"id": t.id, "labels": [c["label"] for c in ctx["pool"][:10]], **sig, **values,
            "clean_attn_z": reader.attention(t.question, clean).tolist(),
            "reversed_clean_attn_z": reader.attention(t.question, clean[::-1]).tolist()})
        print(tag, "calibration", n + 1, "/20", t.id, flush=True)
    calibration = keyed(cal_path)
    assert set(calibration) == set(order)
    offset = np.mean([calibration[i][k] for i in order for k in ("clean_attn_z", "reversed_clean_attn_z")], axis=0)
    X, y = [], []
    for tid in order:
        r = calibration[tid]
        a = zf(np.array(r["attn_z"]) - offset)
        for i, label in enumerate(r["labels"]):
            if label != "captured":
                X.append([logit(r["entail_v2"][i]).item(), a[i]])
                y.append(label == "poison")
    X, y = np.array(X), np.array(y)
    model = LogisticRegression().fit(X, y)
    score = model.predict_proba(X)[:, 1]
    gate = max(1e-4, .999 * min(max(e for e, l in zip(calibration[i]["entail_v1"], calibration[i]["labels"])
                                     if l != "captured") for i in order))
    fitted = {"model": args.model, "layer": cal22["layer"], "zmin": cal22["zmin"], "offsets": offset.tolist(),
        "coef": model.coef_[0].tolist(), "intercept": float(model.intercept_[0]),
        "threshold": float(np.quantile(score[~y], .95)), "gate_threshold": float(gate), "ids": order}
    fit_path = prefix + "_calibration.json"
    if Path(fit_path).exists():
        assert json.load(open(fit_path)) == fitted
    else:
        save(fit_path, fitted)
    freeze(prefix + "_evaluation_manifest.json", [fit_path, cal_path, fidelity_path, prefix + "_manifest.json"],
           {"tier2_ids": {d: list(contexts[d]) for d in ("hotpotqa", "msmarco")}})
    print(tag, "calibration frozen; entering tier 2", flush=True)

    def flags(sig):
        e1, e2, z = np.array(sig["entail_v1"]), np.array(sig["entail_v2"]), np.array(sig["attn_z"])
        zd = zf(z - offset)
        sc = model.predict_proba(np.stack([logit(e2), zd], axis=1))[:, 1]
        return {"flags_v1": np.flatnonzero((e1 >= .01) | (z >= cal22["zmin"])).tolist(),
                "flags_v2": np.flatnonzero(sc >= fitted["threshold"]).tolist(),
                "attn_z_debiased": zd.tolist(), "avidity_v2": sc.tolist()}

    for dataset in ("hotpotqa", "msmarco"):
        selected = load(dataset)[0][50:100]
        out = prefix + f"_{dataset}_k10.jsonl"
        completed = keyed(out)
        assert set(completed) <= {t.id for t in selected}
        for n, t in enumerate(selected):
            if t.id in completed:
                continue
            started = time.monotonic()
            ctx = contexts[dataset][t.id]
            pool, cpool = ctx["pool"], ctx["clean_pool"]
            texts = [c["text"] for c in pool[:10]]
            clean = [c["text"] for c in cpool[:10]]
            checkpoint = Path(f"results/checkpoints/e36/{tag}/{dataset}/{t.id}.json")
            if checkpoint.exists():
                row = json.load(checkpoint.open())
            else:
                sig = claim(t)
                values = signals(t, texts, sig)
                fv = flags(values)
                cs = signals(t, clean, sig)
                cf = flags(cs)
                row = {"id": t.id, "dataset": dataset, "model": args.model, "labels": [c["label"] for c in pool[:10]],
                    "context_hashes": ctx["context_hashes"], **sig, **values, **fv,
                    "coordguard_removed": ctx["coordguard_removed"], "coordguard_score": ctx["coordguard_score"],
                    "clean_coordguard_score": ctx["clean_coordguard_score"],
                    "defclean_coordguard_removed": ctx["clean_coordguard_removed"],
                    "defclean_flags_v1": cf["flags_v1"], "defclean_flags_v2": cf["flags_v2"],
                    "clean_signals": cs, "gate_attacked": max(values["entail_v1"]) >= gate,
                    "gate_attacked_excl": max(e for e, l in zip(values["entail_v1"], [c["label"] for c in pool[:10]]) if l != "captured") >= gate,
                    "gate_clean": max(cs["entail_v1"]) >= gate}
                save(checkpoint, row)
            assert row["context_hashes"] == ctx["context_hashes"] and row["model"] == args.model
            v1, v2, comp = row["flags_v1"], row["flags_v2"], ctx["coordguard_removed"]
            random_flags = random.Random(t.id).sample(range(10), len(v1))
            recipes = {"clean": clean, "attack": texts, "v1_block": texts,
                "v1_delete_backfill": refill(pool, v1), "v2_delete_backfill": refill(pool, v2),
                "random_delete_backfill": refill(pool, random_flags),
                "lowrel_delete_backfill": refill(pool, list(range(10 - len(v1), 10))),
                "coordguard_af": [p for i, p in enumerate(texts) if i not in comp],
                "coordguard_af_refill": refill(pool, comp), "defclean_v1": refill(cpool, row["defclean_flags_v1"]),
                "defclean_v2": refill(cpool, row["defclean_flags_v2"]),
                "defclean_coordguard": refill(cpool, ctx["clean_coordguard_removed"])}
            for arm in ARMS:
                if arm in row:
                    continue
                if arm == "trustrag":
                    response, kept = trustrag(reader.llm, t.question, texts)
                    row[arm] = {"resp": response, "endorsed": bool(endorses(response, t.incorrect)),
                                "correct": bool(correct(response, t.correct)),
                                "poison_kept": sum(p in t.poison for p in kept),
                                "clean_kept": sum(p not in t.poison for p in kept)}
                else:
                    row[arm] = reader.answer(t, recipes[arm], v1 if arm == "v1_block" else ())
                if arm == "random_delete_backfill":
                    row[arm]["removed"] = random_flags
                save(checkpoint, row)
                print(tag, dataset, f"{n + 1}/50", t.id, arm, "saved", flush=True)
            append(out, row)
            print(tag, dataset, "target complete", f"{n + 1}/50", f"{time.monotonic() - started:.1f}s", flush=True)
        assert set(keyed(out)) == {t.id for t in selected}
    print(tag, "all 100 tier-2 targets complete", flush=True)


if __name__ == "__main__":
    main()
