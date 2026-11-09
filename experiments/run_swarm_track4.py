"""Wait for the unchanged incident queue, then run the frozen Track 4 supplement."""
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from antivenom.continuation import save

ROOT = Path(__file__).resolve().parents[1]


def verify():
    for name in ("swarm_track4_manifest.json", "incident_queue_manifest.json",
                 "remaining_queue_manifest_v2.json", "extraction_resilience_manifest.json",
                 "performance_runtime_manifest.json", "performance_validation_manifest.json",
                 "performance_choice_frozen.json"):
        manifest = json.load(open("results/" + name))
        for filename, digest in manifest["inputs"].items():
            assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, (name, filename)


def main():
    os.chdir(ROOT)
    own = open("results/swarm_track4.lock", "a+")
    try:
        fcntl.flock(own, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("A Track 4 supervisor already owns its lock")
    state = {"queue_pid": os.getpid(), "status": "waiting_for_incident_queue", "child_pid": None,
             "runtime_launcher": "experiments/run_swarm_track4.py", "runtime_arguments": [],
             "protocol": "docs/SWARM_TRACK4_PROTOCOL.md", "completed_phases": []}
    inhibitor = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    state["idle_sleep_inhibitor_pid"] = inhibitor.pid

    def status(**kwargs):
        state.update(kwargs, updated_utc=datetime.now(timezone.utc).isoformat())
        save("results/swarm_track4_status.json", state)

    try:
        verify()
        status()
        while True:
            prior = json.load(open("results/incident_queue_status.json"))
            if prior["status"] == "automated_incident_suite_complete":
                break
            if prior["status"] != "running" and not prior["status"].startswith("waiting"):
                raise RuntimeError("Original incident queue requires recovery: " + prior["status"])
            try:
                os.kill(prior["queue_pid"], 0)
            except ProcessLookupError:
                raise RuntimeError("Original incident supervisor stopped; preserve and recover it first")
            time.sleep(30)
        assert json.load(open("results/incident_integrity.json"))["passed"]
        shared = open("results/remaining_queue.lock", "a+")
        status(status="waiting_for_model_lock")
        fcntl.flock(shared, fcntl.LOCK_EX)
        env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"}
        for name, script in (("clean_reference", "experiments/swarm_clean_reference.py"),
                             ("focused_analysis", "analysis/swarm_track4_summary.py")):
            verify()
            status(status="running", phase=name, child_pid=None)
            with open(f"results/swarm_track4_{name}.log", "a") as log:
                child = subprocess.Popen([sys.executable, "-u", script], cwd=ROOT, env=env,
                                         stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                status(child_pid=child.pid)
                rc = child.wait()
            if rc:
                raise RuntimeError(f"Track 4 {name} failed ({rc}); no phase skipped")
            state["completed_phases"].append(name)
        status(status="automated_swarm_extension_complete", child_pid=None)
    except BaseException as exc:
        status(status="failed", error=repr(exc))
        raise


if __name__ == "__main__":
    main()
