"""Target-level statistics shared by the exploratory continuation analyses."""
import json
from pathlib import Path

import numpy as np
from scipy.stats import binomtest


def read_rows(path):
    rows = [json.loads(line) for line in Path(path).open() if line.strip()]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate targets in {path}")
    return rows


def interval(values):
    x = np.asarray(values, dtype=float)
    rng = np.random.default_rng(0)
    samples = x[rng.integers(0, len(x), (2000, len(x)))].mean(axis=1)
    return [float(v) for v in np.quantile(samples, [.025, .975])]


def holm(ps):
    order = sorted(ps, key=ps.get)
    adjusted, previous = {}, 0.0
    for i, key in enumerate(order):
        previous = max(previous, min(1.0, (len(order) - i) * ps[key]))
        adjusted[key] = previous
    return adjusted


def compare(rows, pairs):
    out = {}
    for a, b in pairs:
        for metric in ("correct", "endorsed"):
            x = np.array([r[a][metric] for r in rows], dtype=int)
            y = np.array([r[b][metric] for r in rows], dtype=int)
            wins, losses = int(((x == 1) & (y == 0)).sum()), int(((x == 0) & (y == 1)).sum())
            out[f"{a} - {b}: {metric}"] = {
                "difference": float((x - y).mean()), "ci": interval(x - y),
                "discordant": [wins, losses],
                "p": float(binomtest(wins, wins + losses).pvalue) if wins + losses else 1.0,
            }
    adjusted = holm({k: v["p"] for k, v in out.items()})
    for k in out:
        out[k]["holm_p"] = adjusted[k]
    return out


def arm_rates(rows, arms):
    return {a: {k: {"rate": float(np.mean([r[a][k] for r in rows])),
                    "ci": interval([r[a][k] for r in rows])}
                for k in ("correct", "endorsed")} for a in arms}


def save_report(name, result, lines):
    Path(f"results/{name}.json").write_text(json.dumps(result, indent=2) + "\n")
    text = "\n".join(lines) + "\n"
    Path(f"results/rescored/summaries/{name}.txt").write_text(text)
    print(text)
