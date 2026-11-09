"""Explicit runtime wrapper around an unchanged frozen GPU experiment."""
import hashlib
import json
import runpy
import sys
import time
from pathlib import Path

import mlx.core as mx

from antivenom.continuation import save, freeze
from performance_validation import validate


def verify(path):
    m = json.load(open(path))
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in m["inputs"].items()), f"Frozen runtime inputs changed: {path}"


target, *argv = sys.argv[1:]
assert target in {"experiments/incident_suite.py", "experiments/incident_swarm.py", "experiments/incident_memform.py"}
verify("results/performance_runtime_manifest.json")
if Path("results/performance_validation.json").exists():
    verify("results/performance_validation_manifest.json")
    if not Path("results/performance_choice_frozen.json").exists():
        # Recover an interruption after the atomic result save, before its freeze.
        recovered = json.load(open("results/performance_validation.json"))
        assert len(recovered["records"]) == 6 and "selected_configuration" in recovered
        freeze("results/performance_choice_frozen.json", ["results/performance_validation.json", "results/performance_validation_manifest.json"],
               {"configuration": recovered["selected_configuration"]})
    verify("results/performance_choice_frozen.json")
    choice = json.load(open("results/performance_validation.json"))
else:
    choice = validate()
mx.set_cache_limit(choice["selected_cache_limit_bytes"])
print("Runtime guard:", choice["selected_configuration"], "original experiment:", target, argv, flush=True)
started = time.perf_counter()
telemetry = {"script": target, "arguments": argv, "configuration": choice["selected_configuration"],
             "cache_limit_bytes": choice["selected_cache_limit_bytes"], "scientific_source_unchanged": True}
name = hashlib.sha256(json.dumps([target,argv]).encode()).hexdigest()
sys.argv = [target, *argv]
try:
    runpy.run_path(str(Path(target).resolve()), run_name="__main__")
except BaseException as exc:
    telemetry.update(status="failed", error=repr(exc))
    raise
else:
    telemetry["status"] = "complete"
finally:
    telemetry.update(wall_seconds=time.perf_counter()-started, peak_memory_bytes=mx.get_peak_memory())
    save(f"results/performance_runs/{name}.json", telemetry)
