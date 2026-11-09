"""Operational waiting/guard wrapper; frozen scientific control is unchanged."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "results/memform_drop_all_wait_config_v1.json"
MANIFEST = "results/memform_drop_all_wait_runtime_manifest_v1.json"
STATUS = "results/memform_drop_all_wait_status.json"
JOURNAL = "results/memform_drop_all_wait_events.jsonl"
CONTROL = "experiments/memform_drop_all_control.py"
PLAN = "results/memform_drop_all_plan_v1.json"
SCHEMA = "antivenom.memform-drop-all.wait-config.v1"
BUSY_EXIT = 75
PYTHON = re.compile(r"(?:^|[/\s])python(?:[0-9.]*)?(?:\s|$)", re.I)
MODEL = re.compile(r"mlx|qwen|llama|ollama|vllm|inference|final_evaluate|incident_memform|swarm_clean_reference|torchrun|tensorflow|lmstudio|text-generation", re.I)
GPU_FILE = re.compile(r"mlx|metal|torch|tensorflow|jax|coreml|mps|ggml|llama|vllm|opencl|cuda|cudnn|cupy|onnxruntime", re.I)

class ResourceBusy(RuntimeError):
    """Inspection cannot support starting or continuing our model call."""

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def names_sha256(names):
    return digest(canonical(sorted(set(names))))

def now():
    return datetime.now(timezone.utc).isoformat()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)

def read_json(path):
    return json.loads(Path(path).read_text())

def local_path(name):
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Runtime-controlled file escapes ANTIVENOM root")
    return path

def parse_inventory(output):
    rows = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        p = line.strip().split(None, 10)
        if len(p) != 11 or not p[0].isdigit() or not p[1].isdigit() or not p[3].isdigit():
            raise ResourceBusy("Incomplete process inventory")
        pid = int(p[0])
        if pid in rows:
            raise ResourceBusy("Duplicate PID in inventory")
        rows[pid] = dict(pid=pid, ppid=int(p[1]), state=p[2], rss_kib=int(p[3]), cpu_time=p[4],
                         start=" ".join(p[5:10]), command=p[10])
    if not rows:
        raise ResourceBusy("Empty process inventory")
    return rows

def read_inventory():
    try:
        p = subprocess.run(["/bin/ps", "-axo", "pid=,ppid=,stat=,rss=,time=,lstart=,command="], capture_output=True, text=True)
    except OSError as exc:
        raise ResourceBusy("Cannot inspect local processes") from exc
    if p.returncode or p.stderr.strip():
        raise ResourceBusy("Process inspection failed or may be incomplete")
    return parse_inventory(p.stdout)

def parse_lsof_names(output, pid):
    owners = {int(s[1:]) for s in output.splitlines() if s.startswith("p") and s[1:].isdigit()}
    # An exact `n` field can represent an unnamed descriptor. Retain it in
    # the complete witness rather than silently changing the frozen set.
    names = sorted({s[1:] for s in output.splitlines() if s.startswith("n")})
    if owners != {pid} or not names:
        raise ResourceBusy("Missing or mismatched complete lsof witness")
    return names

def read_lsof_names(pid):
    try:
        p = subprocess.run(["/usr/sbin/lsof", "-n", "-P", "-a", "-p", str(pid), "-Fn"], capture_output=True, text=True)
    except OSError as exc:
        raise ResourceBusy("Cannot inspect dormant file witness") from exc
    if p.returncode or p.stderr.strip():
        raise ResourceBusy("Dormant file inspection failed or may be incomplete")
    return parse_lsof_names(p.stdout, pid)

def identity_matches(observed, expected):
    return all(observed.get(k) == expected.get(k) for k in ("pid", "ppid", "start", "command"))

def validate_config(config):
    if not isinstance(config, dict) or config.get("schema") != SCHEMA:
        raise ValueError("Unsupported wait-runtime config")
    targets, exemptions = config.get("wait_targets"), config.get("exemptions")
    if not isinstance(targets, list) or not targets or not isinstance(exemptions, list):
        raise ValueError("Need wait_targets and exemptions lists")
    ids = []
    for identity in targets + [e.get("identity") for e in exemptions]:
        if not isinstance(identity, dict) or type(identity.get("pid")) is not int or type(identity.get("ppid")) is not int:
            raise ValueError("Need exact process identity")
        if identity["pid"] <= 0 or identity["ppid"] < 0 or any(not isinstance(identity.get(k), str) or not identity[k].strip() for k in ("start", "command")):
            raise ValueError("Invalid process identity")
        ids.append(identity["pid"])
    if len(set(ids)) != len(ids):
        raise ValueError("Targets and exemptions must use distinct PIDs")
    if type(config.get("poll_seconds")) is not int or not 10 <= config["poll_seconds"] <= 300:
        raise ValueError("poll_seconds must be an integer in10..300")
    if type(config.get("clear_confirmations")) is not int or config["clear_confirmations"] < 2:
        raise ValueError("Need at least two clear observations")
    for e in exemptions:
        command, kind = e["identity"]["command"], e.get("classification")
        if kind == "stdlib_http_server":
            if not PYTHON.search(command) or "-m http.server" not in command or MODEL.search(command):
                raise ValueError("HTTP exemption is not the exact stdlib server")
        elif kind == "stdlib_resource_tracker":
            if "from multiprocessing.resource_tracker import main;main(" not in command or MODEL.search(command):
                raise ValueError("Tracker exemption is not the exact stdlib helper")
        elif kind == "dormant_cpu_spawn":
            if "from multiprocessing.spawn import spawn_main" not in command or "--multiprocessing-fork" not in command or MODEL.search(command):
                raise ValueError("Dormant exemption is not a bounded spawn worker")
            names = e.get("lsof_names")
            if not isinstance(names, list) or not names or any(not isinstance(n, str) for n in names):
                raise ValueError("Need complete dormant file witness")
            if names != sorted(set(names)) or e.get("lsof_sha256") != names_sha256(names) or any(GPU_FILE.search(n) for n in names):
                raise ValueError("Dormant witness is noncanonical, unbound or has GPU/backend markers")
            if not isinstance(e.get("cpu_time"), str) or not e["cpu_time"].strip() or type(e.get("rss_kib")) is not int or not 0 <= e["rss_kib"] <= 65536:
                raise ValueError("Need bounded dormant CPU/RSS baseline")
            if any(e["identity"].get(k) != e[k] for k in ("cpu_time", "rss_kib")):
                raise ValueError("Dormant CPU/RSS differs from frozen identity")
        else:
            raise ValueError("Unknown exemption classification")
    return config

def assess_inventory(config, inventory, own_pid, names_reader=read_lsof_names):
    validate_config(config)
    blockers, exempted = [], []
    if own_pid not in inventory:
        return dict(clear=False, blockers=[dict(reason="own_process_missing")], exempted=[])
    ancestors, parent = {own_pid}, inventory[own_pid]["ppid"]
    while parent in inventory and parent not in ancestors:
        ancestors.add(parent); parent = inventory[parent]["ppid"]
    special = {i["pid"] for i in config["wait_targets"]} | {e["identity"]["pid"] for e in config["exemptions"]}
    for expected in config["wait_targets"]:
        observed = inventory.get(expected["pid"])
        if observed is not None:
            blockers.append(dict(reason="priority_target_alive" if identity_matches(observed, expected) else "priority_target_identity_changed", identity=observed))
    for e in config["exemptions"]:
        observed = inventory.get(e["identity"]["pid"])
        if observed is None:
            continue
        reason = None
        if not identity_matches(observed, e["identity"]):
            reason = "exempt_identity_changed"
        elif e["classification"] == "dormant_cpu_spawn":
            if observed["cpu_time"] != e["cpu_time"]:
                reason = "dormant_cpu_time_changed"
            elif observed["rss_kib"] > e["rss_kib"]:
                reason = "dormant_rss_increased"
            else:
                try:
                    names = names_reader(observed["pid"])
                    if names != e["lsof_names"] or names_sha256(names) != e["lsof_sha256"] or any(GPU_FILE.search(n) for n in names):
                        reason = "dormant_file_witness_changed"
                except (OSError, ValueError, ResourceBusy) as exc:
                    reason = "dormant_file_inspection_unavailable: " + str(exc)
        if reason:
            blockers.append(dict(reason=reason, identity=observed))
        else:
            exempted.append(dict(pid=observed["pid"], classification=e["classification"]))
    for pid, observed in inventory.items():
        if pid in ancestors or pid in special or observed["state"].startswith("Z"):
            continue
        if PYTHON.search(observed["command"]) or MODEL.search(observed["command"]):
            blockers.append(dict(reason="unclassified_python_or_model_process", identity=observed))
    return dict(clear=not blockers, blockers=blockers, exempted=exempted)

def inspect_guard(config):
    try:
        return assess_inventory(config, read_inventory(), os.getpid())
    except (OSError, ValueError, ResourceBusy) as exc:
        return dict(clear=False, blockers=[dict(reason="process_inspection_unavailable", error=str(exc))], exempted=[])

def require_clear(config):
    report = inspect_guard(config)
    if not report["clear"]:
        raise ResourceBusy(canonical(report))
    return report

def next_clear_count(previous, report):
    return previous + 1 if report["clear"] else 0

def load_control():
    spec = importlib.util.spec_from_file_location("frozen_drop_all_control", ROOT / CONTROL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def config_paths(config):
    return dict(amendment=config.get("amendment", "docs/MEMFORM_DROP_ALL_RUNTIME_AMENDMENT.md"),
                analysis_manifest=config.get("analysis_manifest", "results/memform_drop_all_analysis_manifest_v1.json"),
                analysis_script=config.get("analysis_script", "analysis/memform_drop_all_summary.py"))

def verify_bindings(path):
    manifest = read_json(path)
    inputs = manifest.get("inputs", manifest.get("source_and_inputs"))
    if not isinstance(inputs, dict) or not inputs:
        raise ValueError("Analysis manifest needs nonempty file-to-SHA inputs")
    for name, expected in inputs.items():
        if file_sha(ROOT / name) != expected:
            raise ValueError("Frozen analysis input changed: " + name)

def manifest_payload(config):
    paths = config_paths(config)
    sources = [str(Path(__file__).relative_to(ROOT)), "tests/test_memform_drop_all_wait.py", CONFIG,
               PLAN, CONTROL, paths["amendment"], paths["analysis_manifest"], paths["analysis_script"]]
    return dict(schema="antivenom.memform-drop-all.wait-runtime.v1",
        inputs={name: file_sha(local_path(name)) for name in sources},
        settings=dict(scope="Operational waiting only; frozen scientific recipe unchanged",
            poll_seconds=config["poll_seconds"], clear_confirmations=config["clear_confirmations"],
            guard_override="Read-only exact process and dormant-file witnesses",
            reader_wrapper="Resource check before/after init and before every unchanged generate call",
            no_foreign_signals=True, no_response_reuse=True))

def verify_runtime(config):
    if read_json(ROOT / MANIFEST) != manifest_payload(config):
        raise ValueError("Frozen runtime inputs changed; preserve this version")
    verify_bindings(local_path(config_paths(config)["analysis_manifest"]))

def freeze_runtime(config):
    control = load_control()
    if control.build_plan() != read_json(ROOT / PLAN):
        raise ValueError("Frozen scientific control plan changed")
    verify_bindings(local_path(config_paths(config)["analysis_manifest"]))
    payload = manifest_payload(config)
    if (ROOT / MANIFEST).exists():
        if read_json(ROOT / MANIFEST) != payload:
            raise ValueError("Runtime version already frozen with different inputs")
    else:
        atomic_json(ROOT / MANIFEST, payload)
    return payload

@contextmanager
def supervisor_lock(path):
    handle = Path(path).open("a+")
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("A drop-all waiting supervisor already holds the lock") from exc
        yield
    finally:
        handle.close()

def event(kind, **fields):
    with (ROOT / JOURNAL).open("a") as stream:
        stream.write(json.dumps(dict(utc=now(), event=kind, **fields), ensure_ascii=False) + "\n")
        stream.flush()

def update(state, **fields):
    state.update(fields, updated_utc=now())
    atomic_json(ROOT / STATUS, state)

def completed_control():
    integrity = ROOT / "results/memform_drop_all_control_v1_integrity.json"
    output = ROOT / "results/memform_drop_all_control_v1.jsonl"
    if not integrity.exists() or not output.exists():
        return False
    record = read_json(integrity)
    return (record.get("passed") is True and record.get("actual_answer_calls") == 424
        and record.get("independent_families") == 212
        and record.get("plan_sha256") == digest(canonical(read_json(ROOT / PLAN)))
        and record.get("output_sha256") == file_sha(output))

def install_reader_guard(continuation, check):
    original_reader = continuation.Reader
    def guarded_reader(*args, **kwargs):
        check()
        reader = original_reader(*args, **kwargs)
        check()
        original_generate = reader.llm.generate
        def guarded_generate(*call_args, **call_kwargs):
            check()
            return original_generate(*call_args, **call_kwargs)
        reader.llm.generate = guarded_generate
        return reader
    continuation.Reader = guarded_reader
    return original_reader

def child(config):
    stage = "preload_verification"
    state = dict(schema="antivenom.memform-drop-all.child-status.v1", pid=os.getpid(),
                 status=stage, runtime_manifest=MANIFEST)
    def child_update(**fields):
        state.update(fields, updated_utc=now())
        atomic_json(ROOT / "results/memform_drop_all_wait_child_status.json", state)
    try:
        child_update()
        verify_runtime(config)
        require_clear(config)
        control = load_control()
        plan = read_json(ROOT / PLAN)
        if control.build_plan() != plan:
            raise ValueError("Frozen control plan changed before execution")
        if str(ROOT / "src") not in sys.path:
            sys.path.insert(0, str(ROOT / "src"))
        import antivenom.continuation as continuation
        def boundary_check():
            verify_runtime(config)
            require_clear(config)
        control.inspect_processes = boundary_check
        original_reader = install_reader_guard(continuation, boundary_check)
        stage = "frozen_control_execute"
        child_update(status="entering_frozen_control", phase=stage)
        try:
            control.execute(plan, control.sha(control.canonical(plan)))
        finally:
            continuation.Reader = original_reader
        if not completed_control():
            raise ValueError("Control returned without complete bound integrity")
        child_update(status="complete", phase="control_complete")
        return 0
    except ResourceBusy as exc:
        child_update(status="yielded_for_resources", phase=stage, error=str(exc))
        event("our_child_yielded", pid=os.getpid(), phase=stage, error=str(exc))
        return BUSY_EXIT
    except BaseException as exc:
        child_update(status="failed", phase=stage, error=repr(exc))
        event("our_child_failed", pid=os.getpid(), phase=stage, error=repr(exc))
        raise

def run_analysis(config, state):
    verify_runtime(config)
    if not completed_control():
        raise ValueError("Analysis requires complete frozen control integrity")
    command = [sys.executable, "-u", str(local_path(config_paths(config)["analysis_script"])), *config.get("analysis_arguments", [])]
    update(state, status="running_analysis", phase="analysis", child_pid=None)
    with (ROOT / "results/memform_drop_all_wait_analysis.log").open("a") as log:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        update(state, child_pid=process.pid)
        code = process.wait()
    if code:
        raise RuntimeError("Analysis failed with exit code " + str(code))
    update(state, status="complete", phase="complete", child_pid=None, completed_calls=424)
    event("control_and_analysis_complete", supervisor_pid=os.getpid(), completed_calls=424)

def supervise(config):
    with supervisor_lock(ROOT / "results/memform_drop_all_wait.lock"):
        state = dict(schema="antivenom.memform-drop-all.wait-status.v1", supervisor_pid=os.getpid(),
            runtime_launcher="experiments/run_memform_drop_all_wait.py", runtime_arguments=["--supervise"],
            runtime_manifest=MANIFEST, configuration=CONFIG, plan=PLAN, status="verifying_runtime",
            phase="preload", child_pid=None, clear_observations=0, completed_calls=0)
        update(state)
        try:
            verify_runtime(config)
            inhibitor = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            update(state, inhibitor_pid=inhibitor.pid)
            event("supervisor_started", supervisor_pid=os.getpid(), inhibitor_pid=inhibitor.pid)
            if completed_control():
                run_analysis(config, state)
                return
            previous = None
            while True:
                verify_runtime(config)
                report = inspect_guard(config)
                count = next_clear_count(state["clear_observations"], report)
                update(state, status="waiting_for_clear_host", phase="waiting", child_pid=None,
                    clear_observations=count, observed_blockers=report["blockers"], exempted=report["exempted"])
                key = canonical([(b["reason"], b.get("identity", {}).get("pid")) for b in report["blockers"]])
                if key != previous:
                    event("resource_observation_changed", clear=report["clear"], blockers=report["blockers"], exempted=report["exempted"])
                    previous = key
                if count >= config["clear_confirmations"]:
                    verify_runtime(config)
                    with (ROOT / "results/memform_drop_all_wait_child.log").open("a") as log:
                        process = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "--child"], cwd=ROOT,
                            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                            env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
                        update(state, status="running_control", phase="control", child_pid=process.pid)
                        event("our_child_started", supervisor_pid=os.getpid(), child_pid=process.pid)
                        code = process.wait()
                    update(state, child_pid=None, child_exit_code=code)
                    if code == BUSY_EXIT:
                        update(state, status="waiting_after_resource_yield", phase="waiting", clear_observations=0)
                        event("waiting_after_our_child_yield", child_pid=process.pid)
                    elif code:
                        raise RuntimeError("Control child failed with exit code " + str(code))
                    elif completed_control():
                        break
                    else:
                        raise RuntimeError("Control child exited0without complete integrity")
                time.sleep(config["poll_seconds"])
            run_analysis(config, state)
        except BaseException as exc:
            update(state, status="failed", error=repr(exc), child_pid=None)
            event("supervisor_failed", supervisor_pid=os.getpid(), error=repr(exc))
            raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--supervise", action="store_true")
    group.add_argument("--child", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    config = validate_config(read_json(ROOT / CONFIG))
    if args.freeze:
        payload = freeze_runtime(config)
        print(json.dumps(dict(status="runtime_frozen_only", manifest=MANIFEST,
                             manifest_sha256=digest(canonical(payload)), model_calls=0), indent=2))
        return 0
    if args.child:
        return child(config)
    supervise(config)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
