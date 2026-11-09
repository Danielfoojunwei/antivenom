"""Summarise E09: share of targets where the reader prefers the correct answer,
overall and split by how many top-k passages were poison."""
import json
import sys

import numpy as np

rows = [json.loads(line) for line in open(sys.argv[1] if len(sys.argv) > 1 else "results/e09_oracle_blockade_nq.jsonl")]
rng = np.random.default_rng(0)
conds = [k for k in rows[0] if k not in ("id", "n_poison")]


def share(vals):
    v = (np.array(vals) > 0).astype(float)
    b = rng.choice(v, size=(5000, len(v))).mean(axis=1)
    return f"{v.mean():.2f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]"


groups = {"all": rows,
          "all 5 poison": [r for r in rows if r["n_poison"] == 5],
          "some clean left": [r for r in rows if r["n_poison"] < 5]}
for name, g in groups.items():
    if not g:
        continue
    print(f"\n== {name} (n={len(g)}): share preferring correct answer [95% CI], median margin")
    for c in conds:
        vals = [r[c] for r in g]
        print(f"  {c:24s} {share(vals):22s} {np.median(vals):7.2f}")
