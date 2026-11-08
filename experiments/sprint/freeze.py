"""Freeze the sprint before any sprint outcome exists.

Draws the incidents and blocks (seeded), verifies disjointness from the
calibration and E42 swarm questions, hashes every frozen input into
results/sprint/manifest.json, and refuses to overwrite an existing freeze
once the run has produced outcomes.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from design import ARMS, DATASETS, K_BLOCKS, SPRINT_SEED, TESTS, V2, check_one_factor, draw_incidents  # noqa: E402

from antivenom.poisonedrag import load  # noqa: E402

OUT = Path("results/sprint")
FROZEN = ["docs/WEEKEND_SWARM_PROTOCOL.md", "docs/WEEKEND_SWARM_PROTOCOL_AMENDMENT_1.md", "docs/WEEKEND_SWARM_PROTOCOL_AMENDMENT_2.md",
          "docs/SPRINT_PLAN_FINAL.md", "results/sprint_fingerprint_calibration.json", "docs/V2_DETECTOR_FROZEN.md",
          "experiments/sprint/design.py", "experiments/sprint/run.py", "experiments/sprint/score.py", "experiments/sprint/freeze.py",
          "results/v2_calibration.json", "results/e27_position_debias.json", "results/incident_calibration_contriever.json",
          "results/incident_contriever_fidelity.json", "results/sprint_entail_only_calibration.json", "src/antivenom/continuation.py", "src/antivenom/antibody.py",
          "src/antivenom/masked.py", "src/antivenom/qa.py", "src/antivenom/retriever.py", "src/antivenom/poisonedrag.py",
          "src/antivenom/llm.py"] + [f"data/external/poisonedrag/{d}{s}" for d in DATASETS for s in (".json", "-contriever.json")]


def h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    amend = (OUT / "raw.jsonl").exists()
    if amend:
        # Version 2 freeze after a documented stop: keep v1, keep the identical incidents and seeds, add arms only.
        if not (OUT / "STOPPED.md").exists():
            raise SystemExit("sprint outcomes exist without a documented stop; refusing to refreeze")
        v1p = OUT / "manifest_v1.json"
        if not v1p.exists():
            (OUT / "manifest.json").rename(v1p)
        v1 = json.load(open(v1p))
        assert h(OUT / "incidents.json") == v1["hashes"]["results/sprint/incidents.json"], "incident list changed since v1"
        man = {"version": 2, "frozen_at_unix": time.time(), "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
               "note": "v2 freeze per docs/SPRINT_PLAN_FINAL.md: same 200 incidents and seeds as v1; adds benchmark arms "
                       "B2 (Stealth Lens AV filter) and B3 (BinaryShield-style fingerprint). Original 12 arms' decisions are "
                       "unchanged (verified on 36,000 synthetic cases). 3 incidents completed under v1 are resumed, not rerun; "
                       "their outcomes were not viewed.",
               "v1_manifest_sha256": h(v1p), "arms": ARMS, "tests": {k: list(v) for k, v in TESTS.items()},
               "one_factor_diffs": check_one_factor(), "detector": V2, "k_blocks": K_BLOCKS, "n_incidents": 200,
               "hashes": {p: h(p) for p in FROZEN + [str(OUT / "incidents.json")]}}
        json.dump(man, open(OUT / "manifest.json", "w"), indent=1)
        print("v2 frozen; manifest sha256", h(OUT / "manifest.json"))
        return
    diffs = check_one_factor()
    target_ids = {d: [t.id for t in load(d)[0]] for d in DATASETS}
    nq = [t.id for t in load("nq")[0]]
    e42 = {json.loads(l)["id"] for l in open("results/incident_swarm.jsonl")} if os.path.exists("results/incident_swarm.jsonl") else set()
    excluded = set(nq[:100]) | e42
    rows, blocks = draw_incidents(target_ids, excluded)
    keys = [f'{r["dataset"]}:{r["id"]}' for r in rows]
    assert len(keys) == len(set(keys)) == 200, "expected 200 distinct incidents"
    assert not ({r["id"] for r in rows} & excluded), "overlap with calibration/E42 questions"
    assert all(sum(r["block"] == b for r in rows) == 40 for b in range(K_BLOCKS))
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump({"incidents": rows, "blocks": blocks, "seed": SPRINT_SEED}, open(OUT / "incidents.json", "w"), indent=1)
    man = {"frozen_at_unix": time.time(), "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
           "note": "Frozen before any sprint model call on the incidents below.",
           "arms": ARMS, "tests": {k: list(v) for k, v in TESTS.items()}, "one_factor_diffs": diffs, "detector": V2,
           "k_blocks": K_BLOCKS, "n_incidents": len(rows),
           "hashes": {p: h(p) for p in FROZEN + [str(OUT / "incidents.json")]}}
    json.dump(man, open(OUT / "manifest.json", "w"), indent=1)
    print("frozen:", len(rows), "incidents in", K_BLOCKS, "blocks; manifest sha256", h(OUT / "manifest.json"))


if __name__ == "__main__":
    main()
