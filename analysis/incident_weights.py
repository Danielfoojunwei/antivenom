"""Hash actual reader weights before/after signature-only interventions."""
import argparse
import hashlib
import json
from pathlib import Path

from antivenom.continuation import save


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("phase", choices=["before", "after"])
    phase = ap.parse_args().phase
    base = Path.home() / ".cache/huggingface/hub/models--mlx-community--Qwen2.5-7B-Instruct-4bit"
    revision = (base / "refs/main").read_text().strip()
    root = base / "snapshots" / revision
    files = {}
    for path in sorted(root.glob("*.safetensors")):
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""): h.update(chunk)
        files[path.name] = {"sha256": h.hexdigest(), "bytes": path.stat().st_size}
    assert files
    state = {"model": "mlx-community/Qwen2.5-7B-Instruct-4bit", "revision": revision, "weights": files}
    if phase == "before":
        p = Path("results/incident_weights_before.json")
        if p.exists(): assert json.load(p.open()) == state
        else: save(p, state)
    else:
        assert json.load(open("results/incident_weights_before.json")) == state, "Reader weights changed"
        save("results/incident_weights_after.json", {**state, "identical_to_before": True})
    print("Reader weight hashing passed:", phase, revision)


if __name__ == "__main__": main()
