#!/bin/bash
# Run from the antivenom folder in your own terminal (needs the Mac GPU):
#   bash experiments/sprint/go.sh
# 1) dry run on NQ calibration questions only  2) automatic sanity checks
# 3) freeze + hash  4) git commit of the freeze  5) launch the 200-incident run (resumable)
set -euo pipefail
cd "$(dirname "$0")/../.."
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH="$PWD/src"
PY=.venv/bin/python

if [ ! -f results/sprint/raw.jsonl ]; then
  echo "== 1/5 dry run (NQ calibration test1, test11; never sprint data)"
  rm -rf results/sprint_dryrun
  $PY experiments/sprint/run.py --dry-run 2>&1 | grep -v -i "warn\|redirect\|loading weights" | tail -3

  echo "== 2/5 sanity checks"
  $PY - <<'EOF'
import json, sys
sys.path.insert(0, "experiments/sprint")
from design import ARMS
rows = [json.loads(l) for l in open("results/sprint_dryrun/raw.jsonl")]
assert len(rows) == 2, "dry run incomplete"
for r in rows:
    assert r["signature"]["valid"], f"blank signature for {r['key']}"
    assert len(r["answers"]) == 6 * len(ARMS), f"missing answers: {len(r['answers'])}"
    for a in ("A3_signature", "A5_sig_attention"):
        n = [len(r["answers"][f"r{k}:attacked:{a}"]["flags"]) for k in (1, 2, 3)]
        assert max(n) < 10, f"{a} flags whole contexts: {n}"
secs = [v["seconds"] for r in rows for v in r["answers"].values() if not v["reused"]]
new = sum(not v["reused"] for r in rows for v in r["answers"].values())
per_inc = sum(secs) / len(rows) + 30
print(f"dry run OK. unique answers per incident {new/len(rows):.0f}, est. {per_inc/60:.1f} min/incident -> {200*per_inc/3600:.1f} h for 200")
EOF

  echo "== 3/5 freeze"
  $PY experiments/sprint/freeze.py

  echo "== 4/5 commit the freeze"
  git add docs/WEEKEND_SWARM_PROTOCOL.md docs/WEEKEND_SWARM_PROTOCOL_AMENDMENT_1.md docs/V2_DETECTOR_FROZEN.md \
          experiments/sprint results/sprint/manifest.json results/sprint/incidents.json results/sprint_entail_only_calibration.json \
          results/v2_calibration.json results/e27_position_debias.json results/incident_calibration_contriever.json results/incident_contriever_fidelity.json
  GIT_ID=(); git config user.name >/dev/null || GIT_ID=(-c user.name="Daniel Foo" -c user.email="danielfoojunwei@gmail.com")
  git ${GIT_ID[@]+"${GIT_ID[@]}"} commit -q -m "Freeze sprint protocol, incidents and detector before any sprint outcome

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log -1 --format="committed %h at %ci" || echo "WARNING: commit failed; the manifest timestamp and hashes still record the freeze"
fi

echo "== 5/5 launching the sprint run in the background (resumable; rerun this script to resume)"
nohup $PY experiments/sprint/run.py > results/sprint_run.log 2>&1 < /dev/null &
echo "pid $!  progress: cat results/sprint/status.json   log: tail -f results/sprint_run.log"
