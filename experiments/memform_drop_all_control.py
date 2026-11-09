"""Separate, post-hoc-added MemForm drop-all control. Default is planning only.

No model module is imported until explicit execution has passed the shared
nonblocking lock, process inspection, input/recipe checks and weight checks.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"
FALLBACK = "No reusable decision rule has been learned yet."
CONDITIONS = ("clean", "poisoned")
PLAN = "results/memform_drop_all_plan_v1.json"
CHECKPOINT_DIR = "results/checkpoints/memform_drop_all_control_v1"
OUT = "results/memform_drop_all_control_v1.jsonl"
STATUS = "results/memform_drop_all_control_v1_status.json"
INTEGRITY = "results/memform_drop_all_control_v1_integrity.json"
SOURCE_FILES = (
    "experiments/memform_drop_all_control.py", "docs/MEMFORM_DROP_ALL_CONTROL.md",
    "tests/test_memform_drop_all_control.py", "src/antivenom/memform_port.py",
    "src/antivenom/continuation.py", "src/antivenom/llm.py", "uv.lock",
    "data/external/memform/accepted_mcq.jsonl",
    "data/external/memform/reference/memform/eval/core.py",
    "results/incident_memform_manifest.json", "results/incident_memform_integrity.json",
    "results/incident_memform.jsonl", "results/incident_weights_before.json",
    "results/incident_weights_after.json", "results/performance_runtime_manifest.json",
    "results/performance_validation_manifest.json", "results/performance_validation.json",
    "results/performance_choice_frozen.json",
)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temp.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    os.replace(temp, path)


def native_functions():
    # This reviewed port imports only stdlib and compiles allowlisted native
    # functions. It does not initialize upstream models or execute upstream main.
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from antivenom.memform_port import native_functions as selected
    return selected()


def load_cases():
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from antivenom.memform_port import family_split
    rows = [json.loads(line) for line in (ROOT / "data/external/memform/accepted_mcq.jsonl").read_text().splitlines() if line.strip()]
    families, calibration, heldout = family_split(rows)
    assert len(calibration) == 20 and len(heldout) == 212
    return families, calibration, heldout


def verify_original_manifests():
    for filename in ("results/incident_memform_manifest.json", "results/performance_runtime_manifest.json",
                     "results/performance_validation_manifest.json", "results/performance_choice_frozen.json"):
        for name, expected in json.loads((ROOT / filename).read_text())["inputs"].items():
            assert file_hash(ROOT / name) == expected, (filename, name)
    assert json.loads((ROOT / "results/incident_memform_integrity.json").read_text())["passed"]


def make_messages(native, case, task):
    # Empty native history does not call a memory-writing model.
    memory = native["build_batch_memory"](None, case, [], case["memory_building"]["batch_prompt"], 120)
    assert memory == FALLBACK
    system, user = native["task_prompt"](case, task, memory)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_plan():
    verify_original_manifests()
    families, calibration, heldout = load_cases()
    native = native_functions()
    saved_rows = [json.loads(line) for line in (ROOT / "results/incident_memform.jsonl").read_text().splitlines() if line.strip()]
    saved = {row["id"]: row for row in saved_rows}
    assert len(saved) == len(saved_rows) == 212 and set(saved) == set(heldout)
    arms = []
    for fid in heldout:
        case = families[fid]["P2"]
        texts = native["exp_texts"](case)
        for condition in CONDITIONS:
            evidence = case["memory_building"][condition + "_condition"]["evidence_ids"]
            hashes = [sha(texts[eid]) for eid in evidence]
            assert saved[fid]["answers"][condition + ":none"]["input_hashes"] == hashes
            for task in case["evaluation"]["trigger_tasks"]:
                assert task["task_id"] in saved[fid]["no_memory"]
                messages = make_messages(native, case, task)
                arm_id = fid + ":" + condition + ":" + task["task_id"]
                arms.append({"arm_id": arm_id, "family_id": fid, "condition": condition,
                             "task_id": task["task_id"], "messages_sha256": sha(canonical(messages)),
                             "input_hashes": hashes, "flags": list(range(len(evidence))), "kept_hashes": [],
                             "memory_sha256": sha(FALLBACK), "valid_labels": [str(c["label"]) for c in task["choices"]],
                             "score_labels": {"clean": task["clean_answer"], "poisoned": task["poisoned_answer"]}})
    assert len(arms) == 424 and len({arm["arm_id"] for arm in arms}) == 424
    assert len({arm["messages_sha256"] for arm in arms}) == 212
    weights = json.loads((ROOT / "results/incident_weights_before.json").read_text())
    after_weights = json.loads((ROOT / "results/incident_weights_after.json").read_text())
    assert all(weights[key] == after_weights[key] for key in ("model", "revision", "weights"))
    assert weights["model"] == MODEL
    model_root = Path.home() / ".cache/huggingface/hub/models--mlx-community--Qwen2.5-7B-Instruct-4bit"
    assert (model_root / "refs/main").read_text().strip() == weights["revision"]
    snapshot = model_root / "snapshots" / weights["revision"]
    config_hashes = {str(path): file_hash(path) for path in sorted(snapshot.iterdir()) if path.is_file() and not path.name.endswith(".safetensors")}
    configuration = json.loads((snapshot / "config.json").read_text())
    assert configuration["quantization"] == {"group_size": 64, "bits": 4}
    runtime = json.loads((ROOT / "results/performance_validation.json").read_text())
    assert runtime["selected_configuration"] == "original_default" and not runtime["accepted"]
    versions = {}
    for package in ("mlx", "mlx-lm", "transformers"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    assert all(versions.values()), "Use the existing project .venv; do not install/upgrade dependencies."
    return {"schema": "antivenom.memform_drop_all_control.v1", "classification": "new diagnostic control on already-used families; not fresh confirmation",
            "scope": "local MemForm P2 port, not native MemMorph", "heldout_in_original_split": heldout,
            "original_calibration_families": calibration, "independent_families": 212, "actual_required_answer_calls": 424,
            "conditions": list(CONDITIONS), "arms": arms, "fallback": FALLBACK,
            "generation": {"model": MODEL, "layer": 21, "temp": 0., "top_p": 0., "max_tokens": 128, "seed": None},
            "runtime": {"configuration": runtime["selected_configuration"], "cache_limit_bytes": runtime["selected_cache_limit_bytes"], "packages": versions},
            "source_hashes": {name: file_hash(ROOT / name) for name in SOURCE_FILES},
            "reader": {"snapshot": str(snapshot), "revision": weights["revision"], "weights": weights["weights"], "config_tokenizer_hashes": config_hashes},
            "no_response_reuse": True, "timing_comparison_to_old_runs": "not controlled; no speed superiority claim",
            "comparison_family": {"focal_methods": ["entail", "OR"], "conditions": list(CONDITIONS),
                                  "endpoints": ["correct", "endorsed"], "total_binary_paired_comparisons": 8,
                                  "intended_analysis": "family-paired effects/intervals, exact two-sided McNemar with Holm8; descriptive used-family diagnostic"},
            "not_established": ["native MemMorph protection", "fresh confirmation", "human semantics", "clean equivalence", "broad novelty"]}


def save_plan(plan, path):
    if path.exists():
        assert json.loads(path.read_text()) == plan, "Existing version is frozen; do not silently replace its recipe."
    else:
        atomic_json(path, plan)
    return sha(canonical(plan))


@contextmanager
def shared_lock(path):
    handle = path.open("a+")
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Shared model lock is occupied. Control did not start; no waiting or signalling.") from exc
        yield
    finally:
        handle.close()


def process_blockers(output, own_pid):
    parsed = {}
    for line in output.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) != 4 or not parts[0].isdigit() or not parts[1].isdigit():
            raise RuntimeError("Process inspection was incomplete; refusing model initialization.")
        parsed[int(parts[0])] = (int(parts[1]), parts[2], parts[3])
    if own_pid not in parsed:
        raise RuntimeError("Current process absent from inspection; refusing model initialization.")
    ancestors = {own_pid}
    parent = parsed[own_pid][0]
    while parent in parsed and parent not in ancestors:
        ancestors.add(parent)
        parent = parsed[parent][0]
    blockers = []
    for pid, (_, state, command) in parsed.items():
        if pid in ancestors or state.startswith("Z"):
            continue
        # Deliberately conservative: unknown Python programs can own model
        # allocations. This is not a GPU-idleness certificate or a bypass flag.
        python = bool(re.search(r"(?:^|[/\s])python(?:[0-9.]*)?(?:\s|$)", command))
        model = bool(re.search(r"mlx|qwen|llama|ollama|vllm|inference|final_evaluate|incident_memform|swarm_clean_reference", command, re.I))
        if python or model:
            blockers.append({"pid": pid, "state": state, "command": command})
    return blockers


def inspect_processes():
    try:
        result = subprocess.run(["/bin/ps", "-axo", "pid=,ppid=,stat=,command="], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Cannot inspect local processes; control refuses model initialization.") from exc
    blockers = process_blockers(result.stdout, os.getpid())
    if blockers:
        raise RuntimeError("Other possible local model/Python workers exist; no inference started: " + canonical(blockers))


def verify_reader(plan):
    reader = plan["reader"]
    snapshot = Path(reader["snapshot"])
    assert (snapshot.parent.parent / "refs/main").read_text().strip() == reader["revision"]
    assert {path.name for path in snapshot.glob("*.safetensors")} == set(reader["weights"])
    for name, expected in reader["weights"].items():
        path = snapshot / name
        assert path.stat().st_size == expected["bytes"] and file_hash(path) == expected["sha256"]
    assert all(file_hash(Path(path)) == expected for path, expected in reader["config_tokenizer_hashes"].items())


def validate_checkpoint(value, arm, plan_sha, parser):
    for name in ("arm_id", "family_id", "condition", "task_id", "messages_sha256", "input_hashes", "flags", "kept_hashes", "memory_sha256"):
        assert value[name] == arm[name], ("Checkpoint binding mismatch", name)
    assert value["plan_sha256"] == plan_sha
    assert value["uncached_actual_call"] is True
    assert re.fullmatch(r"[0-9a-f]{32}", value["call_id"])
    assert re.fullmatch(r"[0-9a-f]{64}", value["formatted_prompt_sha256"])
    assert value["raw_response_sha256"] == sha(value["resp"])
    assert math.isfinite(value["answer_seconds"]) and value["answer_seconds"] >= 0
    assert isinstance(value["generation_started_utc"], str) and value["generation_started_utc"]
    prediction, parse_method = parser(value["resp"], arm["valid_labels"])
    assert value["prediction"] == prediction and value["parse_method"] == parse_method
    assert value["correct"] == (prediction == arm["score_labels"]["clean"])
    assert value["endorsed"] == (prediction == arm["score_labels"]["poisoned"])


def checkpoint_path(arm):
    return ROOT / CHECKPOINT_DIR / (sha(arm["arm_id"]) + ".json")


def execute(plan, plan_sha):
    with shared_lock(ROOT / "results/remaining_queue.lock"):
        inspect_processes()
        verify_reader(plan)
        verify_original_manifests()
        assert build_plan() == plan
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
        # No inference, model initialization or backend import occurs before
        # the lock and fail-closed checks above.
        import mlx.core as mx
        from antivenom.continuation import Reader
        native = native_functions()
        parser = native["parse_final_label_details"]
        old = {}
        call_ids = set()
        for arm in plan["arms"]:
            path = checkpoint_path(arm)
            if path.exists():
                value = json.loads(path.read_text())
                validate_checkpoint(value, arm, plan_sha, parser)
                assert value["call_id"] not in call_ids, "A saved call identity was reused across arms."
                call_ids.add(value["call_id"]); old[arm["arm_id"]] = value
        mx.set_cache_limit(plan["runtime"]["cache_limit_bytes"])
        before = time.perf_counter()
        reader = Reader(MODEL, 21)
        load_seconds = time.perf_counter() - before
        families, _, _ = load_cases()
        inhibitor = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        state = {"status": "running", "pid": os.getpid(), "inhibitor_pid": inhibitor.pid,
                 "plan_sha256": plan_sha, "required_calls": 424, "completed_calls": len(old),
                 "model_load_seconds": load_seconds, "new_calls_this_invocation": 0}
        atomic_json(ROOT / STATUS, state)
        # Fixed mixed-condition order; no outcome-dependent ordering or selection.
        import random
        ordered = list(plan["arms"])
        random.Random(17045).shuffle(ordered)
        try:
            for arm in ordered:
                case = families[arm["family_id"]]["P2"]
                task = next(task for task in case["evaluation"]["trigger_tasks"] if task["task_id"] == arm["task_id"])
                messages = make_messages(native, case, task)
                assert sha(canonical(messages)) == arm["messages_sha256"]
                formatted_hash = sha(reader.llm._prompt(messages))
                if arm["arm_id"] in old:
                    assert old[arm["arm_id"]]["formatted_prompt_sha256"] == formatted_hash
                    continue
                started_utc = datetime.now(timezone.utc).isoformat()
                began = time.perf_counter()
                raw = reader.llm.generate(messages, temp=0., top_p=0., max_tokens=128).strip()
                seconds = time.perf_counter() - began
                prediction, parse_method = parser(raw, arm["valid_labels"])
                value = {key: arm[key] for key in ("arm_id", "family_id", "condition", "task_id", "messages_sha256", "input_hashes", "flags", "kept_hashes", "memory_sha256")}
                value.update(plan_sha256=plan_sha, call_id=uuid.uuid4().hex,
                             uncached_actual_call=True, formatted_prompt_sha256=formatted_hash,
                             generation_started_utc=started_utc, resp=raw, raw_response_sha256=sha(raw),
                             prediction=prediction, parse_method=parse_method,
                             correct=prediction == arm["score_labels"]["clean"],
                             endorsed=prediction == arm["score_labels"]["poisoned"], answer_seconds=seconds)
                validate_checkpoint(value, arm, plan_sha, parser)
                assert value["call_id"] not in call_ids
                call_ids.add(value["call_id"])
                atomic_json(checkpoint_path(arm), value)
                old[arm["arm_id"]] = value
                state.update(completed_calls=len(old), new_calls_this_invocation=state["new_calls_this_invocation"] + 1)
                atomic_json(ROOT / STATUS, state)
                print("drop-all", len(old), "/ 424", arm["arm_id"], flush=True)
            assert len(old) == len(call_ids) == 424
            verify_reader(plan)
            assert build_plan() == plan
            output = "".join(json.dumps(old[arm["arm_id"]], sort_keys=True, ensure_ascii=False) + "\n" for arm in plan["arms"])
            (ROOT / OUT).write_text(output)
            atomic_json(ROOT / INTEGRITY, {"passed": True, "plan_sha256": plan_sha, "actual_answer_calls": 424,
                                         "independent_families": 212, "reader_weights_unchanged": True,
                                         "output_sha256": sha(output), "fresh_confirmation": False,
                                         "human_semantics": "deferred, not passed"})
            state["status"] = "complete"
            atomic_json(ROOT / STATUS, state)
        except BaseException as exc:
            state.update(status="failed", error=repr(exc))
            atomic_json(ROOT / STATUS, state)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--plan", action="store_true", help="CPU-only recipe and prompt-hash planning (default)")
    modes.add_argument("--execute", action="store_true", help="Explicit424-call run; refuse rather than wait if unavailable")
    args = parser.parse_args()
    os.chdir(ROOT)
    plan = build_plan()
    path = ROOT / PLAN
    if args.execute:
        assert path.exists(), "Create and review the plan first."
        assert json.loads(path.read_text()) == plan, "Frozen recipe differs from current inputs."
        execute(plan, sha(canonical(plan)))
    else:
        plan_sha = save_plan(plan, path)
        print(json.dumps({"status": "planned_only", "plan": str(path), "plan_sha256": plan_sha,
                          "families": 212, "required_future_answer_calls": 424,
                          "new_answer_calls": 0, "model_initialized": False,
                          "execution": "not started; other work is never paused or signalled"}, indent=2))


if __name__ == "__main__":
    main()
