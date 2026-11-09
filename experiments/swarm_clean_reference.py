"""E45: actual untreated answers on E42 receiver clean contexts; no extraction."""
import hashlib
import json
import time
from pathlib import Path

from antivenom.continuation import Reader, append, freeze, keyed, read_rows, save
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def verify(path):
    manifest = json.loads(Path(path).read_text())
    for filename, digest in manifest["inputs"].items():
        assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, (path, filename)


def verify_weights():
    expected = json.load(open("results/incident_weights_before.json"))
    base = Path.home() / ".cache/huggingface/hub/models--mlx-community--Qwen2.5-7B-Instruct-4bit"
    assert (base / "refs/main").read_text().strip() == expected["revision"]
    root = base / "snapshots" / expected["revision"]
    assert {p.name for p in root.glob("*.safetensors")} == set(expected["weights"])
    for name, metadata in expected["weights"].items():
        path, digest = root / name, hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        assert digest.hexdigest() == metadata["sha256"] and path.stat().st_size == metadata["bytes"]
    return expected


def main():
    for name in ("swarm_track4_manifest.json", "incident_queue_manifest.json",
                 "extraction_resilience_manifest.json", "performance_runtime_manifest.json",
                 "performance_validation_manifest.json", "performance_choice_frozen.json"):
        verify("results/" + name)
    assert json.load(open("results/incident_integrity.json"))["passed"]
    assert json.load(open("results/incident_queue_status.json"))["status"] == "automated_incident_suite_complete"
    rows = read_rows("results/incident_swarm.jsonl")
    assert len(rows) == 80 and len({r["id"] for r in rows}) == 80
    checkpoint_paths = [f"results/checkpoints/incident_swarm/{sha(r['id'])}.json" for r in rows]
    freeze("results/swarm_clean_reference_manifest.json", [
        "results/swarm_track4_manifest.json", "results/incident_swarm.jsonl",
        "results/incident_integrity.json", "results/incident_weights_after.json", *checkpoint_paths])
    before = verify_weights()
    import mlx.core as mx
    choice = json.load(open("results/performance_validation.json"))
    mx.set_cache_limit(choice["selected_cache_limit_bytes"])
    started = time.perf_counter()
    reader = Reader("mlx-community/Qwen2.5-7B-Instruct-4bit", 21)
    reader.fast = json.load(open("results/incident_contriever_fidelity.json"))["use_fast_ordinary"]
    load_seconds = time.perf_counter() - started
    # Generic warmup has no evaluation record, outcome or signature selection.
    reader.llm.generate([{"role": "user", "content": "Reply OK."}], temp=0., max_tokens=2)
    targets = {t.id: t for t in load("nq")[0]}
    out = "results/swarm_clean_reference.jsonl"
    done = keyed(out)
    for index, row in enumerate(rows):
        tid = row["id"]
        if tid in done:
            continue
        full = json.load(open(f"results/checkpoints/incident_swarm/{sha(tid)}.json"))
        path = Path(f"results/checkpoints/swarm_clean_reference/{sha(tid)}.json")
        result = json.load(path.open()) if path.exists() else {"id": tid, "receivers": {}}
        assert result["id"] == tid
        for rid, receiver in full["receivers"].items():
            if rid in result["receivers"]:
                continue
            pool = receiver["clean_context"]
            assert receiver["captured"] is False and all(p["label"] == "clean" for p in pool)
            began = time.perf_counter()
            answer = reader.answer(targets[tid], [p["text"] for p in pool[:10]])
            answer.update(flags=[], final_context_hashes=[sha(p["text"]) for p in pool[:10]],
                          answer_seconds=time.perf_counter() - began, untreated=True,
                          receiver=rid, captured=False)
            result["receivers"][rid] = answer
            save(path, result)
            print("swarm clean reference", f"{index+1}/80", tid, rid, flush=True)
        append(out, result)
    final = keyed(out)
    assert set(final) == {r["id"] for r in rows}
    count = 0
    for row in rows:
        tid = row["id"]
        full = json.load(open(f"results/checkpoints/incident_swarm/{sha(tid)}.json"))
        saved = json.load(open(f"results/checkpoints/swarm_clean_reference/{sha(tid)}.json"))
        assert saved == final[tid]
        assert set(saved["receivers"]) == set(full["receivers"]) and len(saved["receivers"]) == 6
        for rid, answer in saved["receivers"].items():
            pool = full["receivers"][rid]["clean_context"]
            assert answer["final_context_hashes"] == [sha(p["text"]) for p in pool[:10]]
            assert sha(targets[tid].poison[0]) not in answer["final_context_hashes"]
            assert answer["correct"] == bool(correct(answer["resp"], targets[tid].correct))
            assert answer["endorsed"] == bool(endorses(answer["resp"], targets[tid].incorrect))
            assert answer["flags"] == [] and answer["untreated"] and answer["captured"] is False
            count += 1
    after = verify_weights()
    assert before == after
    verify("results/swarm_clean_reference_manifest.json")
    save("results/swarm_clean_reference_integrity.json", {"passed": True, "incidents": 80,
        "actual_reference_answers": count, "reader_weights_unchanged": True,
        "configuration": choice["selected_configuration"], "cache_limit_bytes": choice["selected_cache_limit_bytes"],
        "reader_load_seconds": load_seconds, "timing_note": "Later supplementary run; not a randomized E42 latency comparator",
        "human_scoring": "deferred, not passed"})
    print("Swarm clean-reference integrity passed", count, flush=True)


if __name__ == "__main__":
    main()
