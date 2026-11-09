"""Serial extension. Wait for E36-E38; preserve its frozen queue and GPU lock."""
import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from antivenom.continuation import freeze, save

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
own_lock = open("results/incident_queue.lock", "a+")
try: fcntl.flock(own_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError: raise SystemExit("An incident queue already owns this lock")
jobs = [
    ["weights_before", "analysis/incident_weights.py", ["before"]],
    ["calibrate_contriever", "experiments/incident_suite.py", ["calibrate"]],
    ["base", "experiments/incident_suite.py", ["base"]],
    ["power", "analysis/incident_power.py", []],
    ["prefixfree", "experiments/incident_suite.py", ["prefixfree"]],
    ["recurrence", "experiments/incident_suite.py", ["recurrence"]],
    ["calibrate_e5", "experiments/incident_suite.py", ["calibrate", "--engine", "e5"]],
    ["e5", "experiments/incident_suite.py", ["e5"]],
    ["swarm", "experiments/incident_swarm.py", []],
    ["memform_diagnostic", "experiments/incident_memform.py", []],
    ["memform_analysis", "analysis/incident_memform_summary.py", []],
    ["weights_after", "analysis/incident_weights.py", ["after"]],
    ["analysis", "analysis/incident_summary.py", []],
    ["integrity", "tests/incident_integrity.py", []],
]
code = sorted({j[1] for j in jobs} | {__file__, "src/antivenom/incident.py", "tests/incident_preflight.py",
                                      "analysis/continuation_stats.py", "src/antivenom/memform_port.py"})
assert subprocess.run([sys.executable, "-m", "compileall", "-q", *code]).returncode == 0
assert subprocess.run([sys.executable, "tests/incident_preflight.py"]).returncode == 0
manifest = freeze("results/incident_queue_manifest.json", code + ["docs/INCIDENT_RESPONSE_PROTOCOL.md", "docs/MEMFORM_DIAGNOSTIC_PROTOCOL.md", "uv.lock",
    "data/external/memform/accepted_mcq.jsonl", "data/external/memform/reference/memform/eval/core.py", "data/external/memform/LICENSE"],
       {"jobs": jobs, "NI_margin": .05, "independent_human_review": "deferred; does not block"})
state = {"queue_pid": os.getpid(), "status": "waiting_for_remaining_queue", "phase": "wait_E36_E38",
         "completed_phases": [], "protocol": "docs/INCIDENT_RESPONSE_PROTOCOL.md"}


def status(**kw):
    state.update(kw, updated_utc=datetime.now(timezone.utc).isoformat())
    save("results/incident_queue_status.json", state)


status()
print("Incident queue frozen; waiting for E36-E38 success before loading any model", flush=True)
while True:
    prior = json.load(open("results/remaining_queue_status.json"))
    if prior["status"] == "automated_runs_complete_external_validation_pending": break
    if prior["status"] == "failed":
        status(status="blocked_by_prior_queue_failure", prior_phase=prior["phase"])
        raise SystemExit("E36-E38 failed; no dependent experiment started")
    try: os.kill(prior["queue_pid"], 0)
    except ProcessLookupError:
        status(status="blocked_by_stopped_prior_queue", prior_phase=prior["phase"])
        raise SystemExit("Prior queue stopped before success; inspect logs")
    time.sleep(5)
shared_lock = open("results/remaining_queue.lock", "a+")
while True:
    try:
        fcntl.flock(shared_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break
    except BlockingIOError: time.sleep(5)
environment = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"}
for name, path, argv in jobs:
    import hashlib
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p, digest in manifest["inputs"].items()), "Frozen queue source changed"
    status(status="running", phase=name, child_pid=None)
    with open(f"results/incident_{name}.log", "a") as log:
        child = subprocess.Popen([sys.executable, "-u", path, *argv], cwd=ROOT, env=environment,
                                 stdout=log, stderr=subprocess.STDOUT)
        status(child_pid=child.pid)
        print("running", name, "pid", child.pid, flush=True)
        rc = child.wait()
    if rc:
        status(status="failed", returncode=rc)
        raise SystemExit(f"Incident phase {name} failed ({rc}); inspect its log")
    state["completed_phases"].append(name)
status(status="automated_incident_suite_complete", child_pid=None,
       fresh_confirmation="not established by development runs; inspect power and external-data eligibility")
print(state["status"], flush=True)
