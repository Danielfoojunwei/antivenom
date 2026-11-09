"""E42: real local agents with separate memory, contexts and delivered updates."""
import json
import random
from pathlib import Path

from antivenom.continuation import append, freeze, keyed, read_rows, save
from antivenom.incident import IncidentLab, sha

METHODS = {"isolated_attention": "attention", "shared_record_ids": "record_blocklist",
           "shared_sample_cosine": "cosine", "shared_claim_entail": "entail",
           "shared_claim_OR": "OR", "coordguard_gate": "coordguard_gate"}
LAYOUTS = ("shared_ids", "distinct_ids")


def partition(ids):
    # Deterministic partition of real clean records; no relevance/gold information.
    return {a: [i for i in ids if int(sha("17:" + str(i)), 16) % 4 == a] for a in range(4)}


def wire(kind, payload):
    raw = json.dumps({"kind": kind, "payload": payload}, ensure_ascii=False, sort_keys=True)
    return {"wire": raw, "sha256": sha(raw), "bytes": len(raw.encode())}


def main():
    paths = [__file__, "docs/INCIDENT_RESPONSE_PROTOCOL.md", "src/antivenom/incident.py",
             "src/antivenom/continuation.py", "src/antivenom/llm.py", "src/antivenom/masked.py",
             "src/antivenom/qa.py", "src/antivenom/antibody.py", "src/antivenom/retriever.py",
             "src/antivenom/poisonedrag.py", "src/antivenom/baselines/coordguard.py",
             "results/incident_calibration_contriever.json", "results/incident_contriever_fidelity.json",
             "results/e11a_flag_scores_nq_k10.jsonl", "data/external/poisonedrag/nq.json",
             "data/external/poisonedrag/nq-contriever.json", "data/external/poisonedrag/nq_target_corpus.json"]
    freeze("results/incident_swarm_manifest.json", paths,
           {"agents": 4, "receivers": [1, 2, 3], "seed": 17, "methods": METHODS, "layouts": list(LAYOUTS)})
    lab = IncidentLab()
    lab.reader.fast = json.load(open("results/incident_contriever_fidelity.json"))["use_fast_ordinary"]
    lab.prewarm()
    fit = json.load(open("results/incident_calibration_contriever.json"))
    order = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][20:]
    out = "results/incident_swarm.jsonl"
    done = keyed(out)
    for n, tid in enumerate(order):
        if tid in done:
            continue
        t = lab.by[tid]
        parts = partition(t.clean_ids)
        assert all(len(v) >= 10 for v in parts.values())
        assert set.union(*(set(v) for v in parts.values())) == set(t.clean_ids)
        check = Path(f"results/checkpoints/incident_swarm/{sha(tid)}.json")
        if check.exists():
            row = json.load(check.open())
        else:
            art = lab.artifact(t.poison[0], tid)
            claim = {k: art[k] for k in ("schema", "incident_id", "question", "claim", "sample_sha256")}
            # Publisher alone has the confirmed capture and derives the record list locally.
            publisher_pool = lab.retrieve(t, clean_ids=parts[0], poison_indices=(1,))
            publisher_answer = lab.run_method("OR", t, t.question, publisher_pool, art, t.poison[0], fit)
            publisher_clean_pool = lab.retrieve(t, clean_ids=parts[0], clean=True)
            publisher_clean = lab.run_method("OR", t, t.question, publisher_clean_pool, art, t.poison[0], fit)
            record_ids = [publisher_pool[i]["doc_id"] for i in publisher_answer["flags"]]
            row = {"id": tid, "target_id": tid, "publisher": {"agent": 0, "captured": True,
                   "artifact": art, "record_blocklist": record_ids, "attacked": publisher_answer,
                   "clean": publisher_clean, "context": publisher_pool},
                   "messages": {"claim": wire("claim_signature", claim),
                                "sample": wire("captured_sample", {"text": t.poison[0], "sha256": sha(t.poison[0])}),
                                "blocklist": wire("record_ids", record_ids)}, "receivers": {}}
            save(check, row)
        lab.prepare_sample(t.poison[0])
        for layout in LAYOUTS:
            for agent in (1, 2, 3):
                rid = f"{layout}:agent{agent}"
                if rid not in row["receivers"]:
                    poison_index = 1 if layout == "shared_ids" else agent + 1
                    row["receivers"][rid] = {"agent": agent, "layout": layout, "captured": False,
                        "clean_record_ids": parts[agent],
                        "attacked_context": lab.retrieve(t, clean_ids=parts[agent], poison_indices=(poison_index,)),
                        "clean_context": lab.retrieve(t, clean_ids=parts[agent], clean=True), "answers": {}}
                    save(check, row)
                receiver = row["receivers"][rid]
                recipes = [(c, m) for c in ("clean", "attacked") for m in METHODS]
                random.Random("17:" + tid + rid).shuffle(recipes)
                for condition, name in recipes:
                    key = f"{condition}:{name}"
                    if key in receiver["answers"]:
                        continue
                    # Each arm starts from a new, isolated receiver memory state.
                    state = {"captured": False, "messages_received": [], "registry": {}}
                    artifact, sample, local_fit = None, "", dict(fit)
                    kind = {"shared_claim_entail": "claim", "shared_claim_OR": "claim",
                            "shared_sample_cosine": "sample", "shared_record_ids": "blocklist"}.get(name)
                    if kind:
                        message = row["messages"][kind]
                        received = json.loads(message["wire"])
                        assert sha(message["wire"]) == message["sha256"]
                        state["messages_received"].append(message["sha256"])
                        state["registry"][kind] = received["payload"]
                        if kind == "claim": artifact = received["payload"]
                        if kind == "sample": sample = received["payload"]["text"]
                        if kind == "blocklist": local_fit["record_blocklist"] = received["payload"]
                    answer = lab.run_method(METHODS[name], t, t.question, receiver[condition + "_context"],
                                            artifact, sample, local_fit)
                    answer["receiver_state"] = state
                    receiver["answers"][key] = answer
                    save(check, row)
                    print("swarm", f"{n + 1}/80", tid, rid, key, flush=True)
        public = json.loads(json.dumps(row))
        public["publisher"].pop("context")
        # The sample body is already released data; keep it only in ignored checkpoints.
        public["messages"]["sample"] = {k: v for k, v in row["messages"]["sample"].items() if k != "wire"}
        for r in public["receivers"].values():
            for c in ("clean", "attacked"):
                pool = r.pop(c + "_context")
                r[c + "_context_metadata"] = [{k: v for k, v in p.items() if k != "text"} | {"sha256": sha(p["text"])} for p in pool]
            for answer in r["answers"].values():
                if "sample" in answer["receiver_state"]["registry"]:
                    answer["receiver_state"]["registry"]["sample"].pop("text")
        append(out, public)
    assert len(keyed(out)) == 80


if __name__ == "__main__":
    main()
