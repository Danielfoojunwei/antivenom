"""Exclusive, resumable serial queue for the authorized remaining local runs."""
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from antivenom.continuation import freeze, save

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
Path("results").mkdir(exist_ok=True)
lock = open("results/remaining_queue.lock", "a+")
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit("Another remaining-runs queue already holds the lock.")
lock.seek(0)
lock.truncate()
lock.write(str(os.getpid()) + "\n")
lock.flush()

jobs = [
    ("prepare", "experiments/e36_prepare.py", []),
    ("llama", "experiments/e36_other_readers.py", ["mlx-community/Meta-Llama-3-8B-Instruct-4bit"]),
    ("mistral", "experiments/e36_other_readers.py", ["mlx-community/Mistral-7B-Instruct-v0.3-4bit"]),
    ("composite", "experiments/e37_composite.py", []),
    ("gate_cache", "experiments/e38_gate_cache.py", []),
    ("analysis", "analysis/remaining_summary.py", []),
    ("integrity", "tests/remaining_integrity.py", []),
    ("human_status", "analysis/human_validation_gate.py", []),
]
code = sorted({j[1] for j in jobs} | {__file__, "src/antivenom/continuation.py"})
preflight = subprocess.run([sys.executable, "-m", "compileall", "-q", *code])
assert preflight.returncode == 0, "Compilation preflight failed"
for model in ("Meta-Llama-3-8B-Instruct-4bit", "Mistral-7B-Instruct-v0.3-4bit", "Qwen2.5-7B-Instruct-4bit"):
    base = Path.home() / ".cache/huggingface/hub" / ("models--mlx-community--" + model)
    revision = (base / "refs/main").read_text().strip()
    snapshot = base / "snapshots" / revision
    assert (snapshot / "config.json").exists() and list(snapshot.glob("*.safetensors")), f"Cached model missing: {model}"
freeze("results/remaining_queue_manifest.json", code + ["docs/REMAINING_RUNS_PROTOCOL.md", "uv.lock",
    "results/e22_Meta-Llama-3-8B-Instruct-4bit_calibration.json",
    "results/e22_Mistral-7B-Instruct-v0.3-4bit_calibration.json"], {"jobs": jobs})
environment = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"}
state = {"queue_pid": os.getpid(), "status": "running", "completed_phases": [],
         "protocol": "docs/REMAINING_RUNS_PROTOCOL.md"}
print("preflight passed; starting serial queue", flush=True)
for name, path, argv in jobs:
    state.update(phase=name, child_pid=None, updated_utc=datetime.now(timezone.utc).isoformat())
    save("results/remaining_queue_status.json", state)
    log_path = f"results/remaining_{name}.log"
    with open(log_path, "a") as log:
        log.write(f"\n=== phase {name} started {state['updated_utc']} ===\n")
        log.flush()
        child = subprocess.Popen([sys.executable, "-u", path, *argv], cwd=ROOT, env=environment,
                                 stdout=log, stderr=subprocess.STDOUT)
        state["child_pid"] = child.pid
        save("results/remaining_queue_status.json", state)
        print("running", name, "pid", child.pid, "log", log_path, flush=True)
        code = child.wait()
    if code:
        state.update(status="failed", returncode=code, updated_utc=datetime.now(timezone.utc).isoformat())
        save("results/remaining_queue_status.json", state)
        raise SystemExit(f"phase {name} failed ({code}); inspect {log_path}. Resume after resolving it.")
    state["completed_phases"].append(name)
state.update(status="automated_runs_complete_external_validation_pending", child_pid=None,
             updated_utc=datetime.now(timezone.utc).isoformat())
save("results/remaining_queue_status.json", state)
print(state["status"], flush=True)
