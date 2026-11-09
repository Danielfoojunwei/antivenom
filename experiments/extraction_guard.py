"""Run the unchanged experiment with separately frozen R2 extraction handling."""
import hashlib
import json
import runpy
import sys
from pathlib import Path

from antivenom.extraction_resilience import install

m = json.load(open("results/extraction_resilience_manifest.json"))
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in m["inputs"].items())
target, *argv = sys.argv[1:]
assert target in {"experiments/e37_composite.py", "experiments/performance_guard.py"}
install()
print("R2 extraction guard:", target, argv, flush=True)
sys.argv = [target, *argv]
runpy.run_path(str(Path(target).resolve()), run_name="__main__")
