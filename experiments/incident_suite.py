"""E39/E40/E41/E43 captured-excluded incident-response suite."""
import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from antivenom.continuation import append, freeze, keyed, logit, read_rows, save
from antivenom.incident import FULL_METHODS, IncidentLab, sha
from antivenom.poisonedrag import load
from antivenom.baselines.coordguard import audit

METHODS = {"base": FULL_METHODS, "prefixfree": [m for m in FULL_METHODS if m not in ("exact_hash", "coordguard_af")],
    "recurrence": ["none", "attention", "OR", "cosine", "coordguard_gate", "trustrag", "gated_OR"],
    "e5": FULL_METHODS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["calibrate", "base", "prefixfree", "recurrence", "e5"])
    ap.add_argument("--engine", choices=["contriever", "e5"], default="contriever")
    args = ap.parse_args()
    engine = "e5" if args.mode == "e5" else args.engine
    paths = [__file__, "docs/INCIDENT_RESPONSE_PROTOCOL.md", "src/antivenom/incident.py", "src/antivenom/continuation.py",
        "src/antivenom/llm.py", "src/antivenom/masked.py", "src/antivenom/antibody.py", "src/antivenom/qa.py", "src/antivenom/poisonedrag.py",
        "src/antivenom/baselines/coordguard.py", "src/antivenom/baselines/trustrag.py", "src/antivenom/retriever.py",
        "results/e11a_flag_scores_nq_k10.jsonl", "data/external/poisonedrag/nq.json",
        "data/external/poisonedrag/nq-contriever.json", "data/external/poisonedrag/nq_target_corpus.json",
        "data/cache/e36_contexts_nq.jsonl"]
    if args.mode == "recurrence":
        paths += ["results/e18_recurrence_nq_k10.jsonl", "data/cache/nq_clean_vecs.npz"]
    prefix = f"results/incident_{args.mode}_{engine}"
    freeze(prefix + "_manifest.json", paths, {"mode": args.mode, "engine": engine,
        "methods": METHODS.get(args.mode), "captured_excluded_from_pool": True})
    order = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")]
    lab = IncidentLab(engine)
    cal_context = keyed("data/cache/e36_contexts_nq.jsonl")
    fidelity_path = Path(f"results/incident_{engine}_fidelity.json")
    if fidelity_path.exists():
        lab.reader.fast = json.load(fidelity_path.open())["use_fast_ordinary"]
    else:
        save(fidelity_path, lab.reader.fidelity([lab.by[i] for i in order[:20]], cal_context))
    prewarm_seconds = lab.prewarm()
    fit_path = Path(f"results/incident_calibration_{engine}.json")
    if args.mode == "calibrate":
        cal_path = f"results/incident_calibration_{engine}_rows.jsonl"
        done = keyed(cal_path)
        for n, tid in enumerate(order[:20]):
            if tid in done:
                continue
            t = lab.by[tid]
            art = lab.artifact(t.poison[0], tid)
            attacked = lab.retrieve(t)
            clean = lab.retrieve(t, clean=True)
            texts = [p["text"] for p in attacked[:10]]
            _, cg = audit(t.question, [p["text"] for p in clean[:10]])
            append(cal_path, {"id": tid, "labels": [p["label"] for p in attacked[:10]],
                "context_hashes": [sha(p) for p in texts], "entail": lab.entail(texts, art).tolist(),
                "attention_z": lab.reader.attention(t.question, texts).tolist(),
                "cosine": lab.cosine(texts, t.poison[0]).tolist(), "clean_geometry_score": cg,
                "artifact": art})
            print("incident calibration", engine, f"{n + 1}/20", tid, flush=True)
        rows = keyed(cal_path)
        assert set(rows) == set(order[:20])
        X, y, cos_clean = [], [], []
        for tid in order[:20]:
            r = rows[tid]
            for e, a, c, label in zip(r["entail"], r["attention_z"], r["cosine"], r["labels"]):
                X.append([float(logit(e)), a]); y.append(label == "poison")
                if label == "clean": cos_clean.append(c)
        X, y = np.array(X), np.array(y)
        model = LogisticRegression().fit(X, y)
        scores = model.predict_proba(X)[:, 1]
        fitted = {"engine": engine, "ids": order[:20], "coef": model.coef_[0].tolist(),
            "intercept": float(model.intercept_[0]), "avidity_threshold": float(np.quantile(scores[~y], .95)),
            "cosine_threshold": float(np.quantile(cos_clean, .95)),
            "nli_gate": max(1e-4, .999 * min(max(rows[i]["entail"]) for i in order[:20])),
            "geometry_gate": float(np.quantile([rows[i]["clean_geometry_score"] if rows[i]["clean_geometry_score"] is not None else -1e9 for i in order[:20]], .9)),
            "calibration_contexts_exclude_captured": True}
        if fit_path.exists(): assert json.load(fit_path.open()) == fitted
        else: save(fit_path, fitted)
        freeze(f"results/incident_calibration_{engine}_frozen.json", [cal_path, fit_path, fidelity_path], {"ids": order[:20]})
        # Real decoder/registry round trip and revocation checks on a calibration case.
        t = lab.by[order[0]]; art = rows[t.id]["artifact"]
        assert json.loads(json.dumps(art)) == art
        pool = lab.retrieve(t, clean=True)
        isolated = lab.run_method("attention", t, t.question, pool, None, t.poison[0], fitted)
        revoked = lab.run_method("OR", t, t.question, pool, None, t.poison[0], fitted)
        assert isolated["resp"] == revoked["resp"] and isolated["flags"] == revoked["flags"]
        save(f"results/incident_revocation_{engine}.json", {"id": t.id, "identical_response": True,
            "isolated": isolated, "revoked": revoked, "serialized_artifact_round_trip": True})
        return
    assert fit_path.exists(), "Run calibration first"
    fit = json.load(fit_path.open())
    freeze(prefix + "_evaluation_manifest.json", [fit_path, prefix + "_manifest.json", fidelity_path], {"ids": order[20:]})
    by = lab.by if args.mode != "prefixfree" else {t.id: t for t in load("nq", prefix=False)[0]}
    recurrence = keyed("results/e18_recurrence_nq_k10.jsonl") if args.mode == "recurrence" else {}
    out = prefix + ".jsonl"
    done = keyed(out)
    for n, tid in enumerate(order[20:]):
        t = by[tid]
        questions = [s["question"] for s in recurrence[tid]["sessions"]] if recurrence else [t.question]
        for session, question in enumerate(questions):
            case_id = f"{tid}:s{session}" if recurrence else tid
            if case_id in done:
                continue
            check = Path(f"results/checkpoints/incident_cases/{args.mode}_{engine}/{sha(case_id)}.json")
            if check.exists():
                row = json.load(check.open())
            else:
                art = lab.artifact(t.poison[0], tid)
                attacked = lab.retrieve(t, question=question)
                clean = lab.retrieve(t, question=question, clean=True)
                row = {"id": case_id, "target_id": tid, "session": session, "question": question,
                    "mode": args.mode, "engine": engine, "artifact": art, "setup_prewarm_seconds": prewarm_seconds,
                    "model_initialization_seconds": lab.initialization_seconds,
                    "attacked_context": attacked, "clean_context": clean, "answers": {}}
                save(check, row)
            assert row["artifact"]["sample_sha256"] == sha(t.poison[0])
            lab.prepare_sample(t.poison[0])
            assert not any(p["poison_index"] == 0 for p in row["attacked_context"])
            recipes = [(condition, method) for condition in ("clean", "attacked") for method in METHODS[args.mode]]
            random.Random("incident:" + case_id).shuffle(recipes)
            for condition, method in recipes:
                key = f"{condition}:{method}"
                if key in row["answers"]: continue
                pool = row[condition + "_context"]
                row["answers"][key] = lab.run_method(method, t, question, pool, row["artifact"], t.poison[0], fit)
                save(check, row)
                print("incident", args.mode, engine, f"{n + 1}/80", case_id, key, "saved", flush=True)
            if args.mode == "base":
                # Fixed rank-1 clean record; no gold answer consulted when selecting a mistaken capture.
                sample = row["clean_context"][0]["text"]
                mistaken = lab.artifact(sample, "mistaken:" + tid)
                for condition in ("clean", "attacked"):
                    key = f"{condition}:mistaken_capture_OR"
                    if key not in row["answers"]:
                        row["answers"][key] = lab.run_method("OR", t, question, row[condition + "_context"], mistaken, sample, fit)
                        save(check, row)
                row["mistaken_artifact"] = mistaken
            # Public results retain hashes/labels; full source text stays in ignored checkpoints.
            public = {k: v for k, v in row.items() if k not in ("attacked_context", "clean_context")}
            for condition in ("attacked", "clean"):
                pool = row[condition + "_context"]
                public[condition + "_hashes"] = [sha(p["text"]) for p in pool[:10]]
                public[condition + "_labels"] = [p["label"] for p in pool[:10]]
            append(out, public)
            print("incident case complete", args.mode, case_id, flush=True)
    expected = 160 if args.mode == "recurrence" else 80
    assert len(keyed(out)) == expected


if __name__ == "__main__":
    main()
