"""Preserve the frozen supervisor; add only an explicit validated runtime guard."""
import runpy
import subprocess
import sys
import json

import antivenom.continuation as support

from antivenom.continuation import freeze

freeze("results/performance_runtime_manifest.json", [__file__, "experiments/performance_guard.py",
    "experiments/performance_validation.py", "docs/PERFORMANCE_RUNTIME_AMENDMENT.md",
    "results/incident_queue_manifest.json"], {"current_mac_only": True, "extra_model_workers": 0,
    "fallback": "unchanged default if calibration validation does not select cap"})
original = subprocess.Popen
original_save = support.save
scripts = {"experiments/incident_suite.py", "experiments/incident_swarm.py", "experiments/incident_memform.py"}


def guarded(args, *pos, **kw):
    if isinstance(args, (list,tuple)) and len(args) >= 3 and args[0] == sys.executable and args[1] == "-u" and args[2] in scripts:
        args = [sys.executable, "-u", "experiments/performance_guard.py", *args[2:]]
    return original(args, *pos, **kw)


def runtime_save(path, value):
    if str(path) == "results/incident_queue_status.json":
        value = {**value, "runtime_launcher": "experiments/run_incident_optimized.py",
                 "runtime_manifest": "results/performance_runtime_manifest.json",
                 "runtime_validation": "results/performance_validation.json"}
    return original_save(path, value)


subprocess.Popen = guarded
support.save = runtime_save
sys.argv = ["experiments/run_incident_suite.py"]
runpy.run_path("experiments/run_incident_suite.py", run_name="__main__")
