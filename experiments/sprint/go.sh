#!/bin/bash
# Run from the antivenom folder (needs the Mac GPU):  bash experiments/sprint/go.sh
# v2 restart per docs/SPRINT_PLAN_FINAL.md:
# 1) dry run (NQ calibration only) with all arms incl. B2/B3  2) automatic checks
# 3) v2 freeze (keeps v1, same incidents)  4) git commit  5) resume the run (3 v1 incidents are resumed, not rerun)
set -euo pipefail
cd "$(dirname "$0")/../.."
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH="$PWD/src"
PY=.venv/bin/python

if ! grep -q '"version": 2' results/sprint/manifest.json 2>/dev/null; then
  echo "== 1/5 dry run (NQ calibration test1, test11; never sprint data)"
  rm -rf results/sprint_dryrun
  $PY experiments/sprint/run.py --dry-run 2>&1 | grep -v -i "warn\|redirect\|loading weights\|reach the hub" | tail -3

  echo "== 2/5 sanity checks"
  $PY - <<'EOF'
import json, sys
sys.path.insert(0, "experiments/sprint")
from design import ARMS
rows = [json.loads(l) for l in open("results/sprint_dryrun/raw.jsonl")]
last = {r["key"]: r for r in rows}
assert len(last) == 2, "dry run incomplete"
for r in last.values():
    assert r["signature"]["valid"], f"blank signature for {r['key']}"
    assert len(r["answers"]) == 6 * len(ARMS), f"missing answers: {len(r['answers'])} of {6*len(ARMS)}"
    for a in ("A3_signature", "A5_sig_attention"):
        n = [len(r["answers"][f"r{k}:attacked:{a}"]["flags"]) for k in (1, 2, 3)]
        assert max(n) < 10, f"{a} flags whole contexts: {n}"
    assert "fingerprint" in r["finder"], "no fingerprint"
    for k in (1, 2, 3):
        assert len(r["answers"][f"r{k}:attacked:B2_stealth_av"]["flags"]) <= 1, "Stealth Lens removed more than one passage"
secs = [v["seconds"] for r in last.values() for v in r["answers"].values() if not v["reused"]]
per_inc = sum(secs) / len(last) + 30
print(f"dry run OK. est. {per_inc/60:.1f} min/incident -> {197*per_inc/3600:.1f} h for the remaining 197")
EOF

  echo "== 3/5 v2 freeze"
  $PY experiments/sprint/freeze.py

  echo "== 4/5 commit the freeze"
  git add docs/SPRINT_PLAN_FINAL.md docs/WEEKEND_SWARM_PROTOCOL_AMENDMENT_2.md experiments/sprint \
          results/sprint/manifest.json results/sprint/manifest_v1.json results/sprint/STOPPED.md results/sprint_fingerprint_calibration.json
  GIT_ID=(); git config user.name >/dev/null || GIT_ID=(-c user.name="Daniel Foo" -c user.email="danielfoojunwei@gmail.com")
  git ${GIT_ID[@]+"${GIT_ID[@]}"} commit -q -m "v2 freeze: add Stealth Lens and BinaryShield-style benchmarks; same incidents; before viewing any outcome

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log -1 --format="committed %h at %ci" || echo "WARNING: commit failed; manifest timestamp and hashes still record the freeze"
fi

echo "== 5/5 resuming the sprint run in the background (rerun this script to resume again)"
nohup $PY experiments/sprint/run.py > results/sprint_run.log 2>&1 < /dev/null &
echo "pid $!  progress: cat results/sprint/status.json   log: tail -f results/sprint_run.log"
