"""Results figures from results/sprint/analysis.json (no re-analysis; reads the frozen scorer's output).

Figure 4: forest plot, T1-T9 on each test's primary endpoint, pooled CI plus per-block points.
Figure 5: protection vs clean accuracy for every arm and benchmark.
Figure 6: benchmark comparison (A3, A5, A6 minus B1-B3), descriptive.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

A = json.load(open("results/sprint/analysis.json"))
OUT = "paper/report/fig"
os.makedirs(OUT, exist_ok=True)
INK, MUTE, GRID, OURS, BAD, BENCH = "#1f2430", "#6b7280", "#e5e7eb", "#0f766e", "#dc2626", "#7c3aed"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
LABEL = {"T1": "T1 claim vs IDs", "T1b": "T1b record vs IDs", "T9": "T9 claim vs record", "T2": "T2 real vs sham",
         "T8": "T8 with vs without question", "T3": "T3 + attention", "T6": "T6 delete vs warn", "T5": "T5 refill",
         "T4": "T4 gate", "T7": "T7 forged claim"}
ORDER = ["T1", "T1b", "T9", "T2", "T8", "T3", "T6", "T5", "T4", "T7"]

# Figure 4: forest plot (every test's primary endpoint; T4 shows both endpoints)
tests = A["tests"]
# predicted sign of each effect under the pre-registered assumption (arm - reference)
ROWS = [("T1", "attacked_endorsed", -1), ("T1b", "attacked_endorsed", -1), ("T9", "attacked_endorsed", -1),
        ("T2", "attacked_endorsed", -1), ("T8", "attacked_endorsed", -1), ("T3", "attacked_endorsed", -1),
        ("T6", "attacked_endorsed", -1), ("T5", "attacked_correct", +1), ("T4", "clean_correct", +1),
        ("T4", "attacked_endorsed", 0), ("T7", "clean_correct", -1)]
AGAINST = "#b45309"
f, ax = plt.subplots(figsize=(8.8, 5.6))
for y, (tid, epn, pred) in enumerate(ROWS[::-1]):
    t = tests[tid]; ep = t["endpoints"][epn]
    lo, hi = ep["ci95"]; m = ep["mean_diff"]
    sig = not (lo <= 0 <= hi)
    col = MUTE if not sig else (OURS if (pred == 0 or np.sign(m) == pred) else AGAINST)
    if tid == "T4" and epn == "attacked_endorsed":
        col = AGAINST if sig and m > 0 else col           # protection given up by the gate
    ax.plot([lo, hi], [y, y], color=col, lw=2.4); ax.plot(m, y, "o", color=col, ms=8, zorder=3)
    for v in ep["per_block"].values():
        if v is not None:
            ax.plot(v, y + 0.18, "|", color=col, ms=8, alpha=.6)
    pv = "p < 0.001" if t["holm_p"] < 0.001 else f"p = {t['holm_p']:.3f}"
    if tid == "T4" and epn == "attacked_endorsed":
        pv = "cost (reported)"
    ax.text(1.02, y, f"{m:+.3f} [{lo:+.3f}, {hi:+.3f}]  {pv}", transform=ax.get_yaxis_transform(), va="center", fontsize=8.5, color=col)
ax.axvline(0, color=INK, lw=1)
for x in (-0.05, 0.05):
    ax.axvline(x, color=MUTE, lw=.8, ls=":")
names = {"attacked_endorsed": "attacked endorsement", "attacked_correct": "attacked accuracy", "clean_correct": "clean accuracy"}
ax.set_yticks(range(len(ROWS))); ax.set_yticklabels([f"{LABEL[t]}  [{names[e]}]" for t, e, _ in ROWS[::-1]], fontsize=8.5)
ax.set_xlabel("Paired difference, arm − reference (pooled 95% CI; ticks = the 5 blocks; dotted = ±0.05 margin)")
ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], color=OURS, marker="o", lw=2, label="in the predicted direction"),
                   Line2D([], [], color=AGAINST, marker="o", lw=2, label="against the prediction / cost")],
          loc="lower left", fontsize=8.5, frameon=False)
f.savefig(f"{OUT}/sprint_forest.png", dpi=220, bbox_inches="tight"); plt.close(f)

# Figure 5: protection vs clean accuracy
means = A["arm_means"]
NAMES = {"A0_untreated": "A0 untreated = A1 IDs", "A2_sample": "A2 raw record", "A3_signature": "A3 claim",
         "A4_sham": "A4 sham claim", "A5_sig_attention": "A5 claim + attention", "A6_gated": "A6 gated",
         "A7_no_refill": "A7 no refill", "A8_warn": "A8 warn", "A9_forged": "A9 forged", "A10_bare_claim": "A10 bare claim",
         "B1_self_check": "B1 self-check", "B2_stealth_av": "B2 Stealth Lens", "B3_fingerprint": "B3 fingerprint"}
OFF = {"A0_untreated": (-10, -13), "B1_self_check": (-8, 8), "A7_no_refill": (6, -10), "A9_forged": (6, 4),
       "A2_sample": (6, -11), "B3_fingerprint": (6, 7), "A8_warn": (6, 5), "A3_signature": (10, -3),
       "A5_sig_attention": (6, -13), "B2_stealth_av": (7, 3), "A6_gated": (-6, 7)}
f, ax = plt.subplots(figsize=(7.6, 5.0))
for a, v in means.items():
    if a == "A1_ids":
        continue                                     # identical to A0 (IDs never match renamed copies)
    x, y = v["attacked_endorsed"] * 100, v["clean_correct"] * 100
    col = BENCH if a.startswith("B") else (MUTE if a == "A0_untreated" else (BAD if a in ("A9_forged", "A4_sham") else OURS))
    ax.scatter(x, y, s=90, color=col, edgecolor="white", zorder=3)
    dx, dy = OFF.get(a, (6, 4))
    ax.annotate(NAMES[a], (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8.5, color=INK, ha="right" if dx < 0 else "left")
u = means["A0_untreated"]["clean_correct"] * 100
ax.axhline(u, ls="--", color=MUTE); ax.text(19, u - 1.1, f"untreated clean {u:.1f}%", fontsize=8.5, color=MUTE)
ax.set_xlabel("Receivers endorsing the false answer, attacked (%)  lower is better")
ax.set_ylabel("Receivers' accuracy, clean (%)  higher is better")
ax.set_xlim(-3, 66); ax.grid(True, color=GRID); ax.set_axisbelow(True)
f.savefig(f"{OUT}/sprint_tradeoff.png", dpi=220, bbox_inches="tight"); plt.close(f)

# Figure 6: benchmarks (descriptive)
bd = A["benchmarks_descriptive"]
keys = [k for k in bd if "attacked_endorsed" in k]
f, ax = plt.subplots(figsize=(8.0, 4.0))
for y, k in enumerate(keys[::-1]):
    lo, hi = bd[k]["ci95"]; m = bd[k]["mean_diff"]
    ax.plot([lo, hi], [y, y], color=BENCH, lw=2); ax.plot(m, y, "o", color=BENCH)
ax.axvline(0, color=INK, lw=1)
NB = {"A3_signature": "A3 claim", "A5_sig_attention": "A5 claim + attention", "A6_gated": "A6 gated",
      "B1_self_check": "B1 self-check", "B2_stealth_av": "B2 Stealth Lens", "B3_fingerprint": "B3 fingerprint"}
def nb(k):
    a_, b_ = k.replace(" [attacked_endorsed]", "").split(" - ")
    return f"{NB[a_]}  −  {NB[b_]}"
ax.set_yticks(range(len(keys))); ax.set_yticklabels([nb(k) for k in keys[::-1]], fontsize=8.5)
ax.set_xlabel("Difference in attacked endorsement (descriptive; negative = AntiVenom arm lower)")
ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
f.savefig(f"{OUT}/sprint_benchmarks.png", dpi=220, bbox_inches="tight"); plt.close(f)
print("figures written")
