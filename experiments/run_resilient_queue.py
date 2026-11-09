"""Resume original queues with auditable R2 handling; preserve R1 for incidents."""
import runpy
import subprocess
import sys
from pathlib import Path

import antivenom.continuation as support

role = sys.argv[1]
assert role in {"remaining", "incident"}
support.freeze("results/extraction_resilience_manifest.json", [__file__,
    "src/antivenom/extraction_resilience.py", "experiments/extraction_guard.py",
    "docs/EXTRACTION_RESILIENCE_AMENDMENT.md", "src/antivenom/antibody.py",
    "results/remaining_queue_manifest_v2.json", "results/incident_queue_manifest.json",
    "results/performance_runtime_manifest.json"],
    {"roles": ["remaining", "incident"], "exception": "JSONDecodeError only",
     "fallback": "existing no-JSON empty-dictionary behavior; no text repair or better-output retries"})
original_popen = subprocess.Popen
original_save = support.save


def guarded(args, *pos, **kw):
    if isinstance(args, (list,tuple)) and len(args) >= 3 and args[0] == sys.executable and args[1] == "-u" and args[2] in {"experiments/e37_composite.py", "experiments/performance_guard.py"}:
        args = [sys.executable, "-u", "experiments/extraction_guard.py", *args[2:]]
    return original_popen(args, *pos, **kw)


def status_save(path, value):
    if str(path) == f"results/{role}_queue_status.json":
        value = {**value, "runtime_launcher": "experiments/run_resilient_queue.py", "runtime_arguments": [role],
                 "extraction_amendment": "docs/EXTRACTION_RESILIENCE_AMENDMENT.md",
                 "extraction_runtime_manifest": "results/extraction_resilience_manifest.json"}
    return original_save(path, value)


subprocess.Popen = guarded
support.save = status_save
target = "experiments/run_remaining.py" if role == "remaining" else "experiments/run_incident_optimized.py"
sys.argv = [target]
runpy.run_path(str(Path(target).resolve()), run_name="__main__")
