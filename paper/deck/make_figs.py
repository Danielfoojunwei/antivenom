"""Figures for the 5-slide deck. Every number is copied from a results file:
tier 2 = results/rescored/summaries/e29_confirmatory.txt (pooled n=100);
single poison = results/e31_single_poison.json; prefix-free = results/e26_coordguard_prefixfree.json;
latency = docs/EVIDENCE_REPORT.md (incident_summary.json); swarm = results/swarm_track4_summary.json;
worst-case capture = results/rescored/summaries/e21_summary.txt."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa

OUT = "fig/"
INK, MUTE, GRID = "#1f2430", "#6b7280", "#e5e7eb"
OURS, CG, TR, BASE, WARN = "#0f766e", "#7c3aed", "#d97706", "#9ca3af", "#dc2626"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.edgecolor": MUTE, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False})


def save(f, n):
    f.savefig(OUT + n, dpi=220, bbox_inches="tight", transparent=True); plt.close(f)


# 1. Tier 2 parity: endorsement vs correct per arm
arms = ["No defence", "AntiVenom", "CoordGuard", "TrustRAG"]
end = [76, 7, 5, 12]; cor = [19, 53, 47, 53]
col = [BASE, OURS, CG, TR]
f, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for a, v, t in ((ax[0], end, "Endorses the false answer (%)  lower is better"), (ax[1], cor, "Correct answer (%)  higher is better")):
    b = a.barh(arms[::-1], v[::-1], color=col[::-1], height=.62)
    for r, x in zip(b, v[::-1]): a.text(x + 1, r.get_y() + r.get_height() / 2, f"{x}", va="center", color=INK, fontsize=13, fontweight="bold")
    a.set_title(t, fontsize=13, color=INK, loc="left"); a.set_xlim(0, 85); a.xaxis.grid(True, color=GRID); a.set_axisbelow(True)
ax[1].axvline(61, ls="--", color=MUTE); ax[1].text(61.5, 3.35, "clean context 61", color=MUTE, fontsize=11)
ax[1].set_yticklabels([])
save(f, "parity.png")

# 2. 3D bars: clean passages discarded, 3 conditions x 2 detectors
conds = ["Deployed", "One poison", "No prefix"]
ours = [14.7, 2.6, 8.9]; cg = [20.6, 71.6, 52.3]
f = plt.figure(figsize=(7.5, 5.6)); ax = f.add_subplot(111, projection="3d")
xs = np.arange(3)
ax.bar3d(xs - .3, np.zeros(3), np.zeros(3), .5, .5, ours, color=OURS, alpha=.95, shade=True)
ax.bar3d(xs - .3, np.ones(3) * 1.1, np.zeros(3), .5, .5, cg, color=CG, alpha=.9, shade=True)
for x, o, c in zip(xs, ours, cg):
    ax.text(x - .2, -.25, o + 9, f"{o:g}%", color="white", fontsize=12, fontweight="bold", bbox=dict(boxstyle="round,pad=.25", fc=OURS, ec="none"), zorder=10)
    ax.text(x - .2, 1.35, c + 6, f"{c:g}%", color="white", fontsize=12, fontweight="bold", bbox=dict(boxstyle="round,pad=.25", fc=CG, ec="none"), zorder=10)
ax.set_xticks(xs); ax.set_xticklabels(conds, fontsize=10); ax.set_yticks([.25, 1.35]); ax.set_yticklabels(["AntiVenom", "CoordGuard"], fontsize=11)
ax.set_title("Clean passages discarded (%)", fontsize=13, color=INK); ax.set_zlim(0, 85); ax.view_init(22, -58)
ax.xaxis.pane.fill = ax.yaxis.pane.fill = ax.zaxis.pane.fill = False
save(f, "precision3d.png")

# 3. Latency
names = ["No defence", "Cosine", "AntiVenom", "CoordGuard", "TrustRAG"]; sec = [7.19, 12.20, 18.44, 24.59, 35.94]
f, ax = plt.subplots(figsize=(5.6, 3.6))
b = ax.bar(names, sec, color=[BASE, BASE, OURS, CG, TR], width=.62)
for r, s in zip(b, sec): ax.text(r.get_x() + r.get_width() / 2, s + .8, f"{s:.1f}s", ha="center", fontsize=12, fontweight="bold", color=INK)
ax.set_ylabel("Seconds per attacked question"); ax.set_ylim(0, 42); ax.yaxis.grid(True, color=GRID); ax.set_axisbelow(True)
plt.xticks(rotation=18, ha="right"); save(f, "latency.png")

# 4. Failure profile stacked
prof = {"AntiVenom": [48, 7, 29, 16], "CoordGuard": [42, 5, 42, 11], "TrustRAG": [45, 12, 0, 43]}
lab = ["True answer", "False answer", "Says 'don't know'", "Other wrong answer"]; cc = ["#16a34a", WARN, "#93c5fd", "#fbbf24"]
f, ax = plt.subplots(figsize=(5.6, 3.6)); left = np.zeros(3); ks = list(prof)
for i in range(4):
    v = np.array([prof[k][i] for k in ks]); ax.barh(ks[::-1], v[::-1], left=left[::-1], color=cc[i], label=lab[i], height=.6)
    for y, (l, x) in enumerate(zip(left[::-1], v[::-1])):
        if x >= 8: ax.text(l + x / 2, y, f"{x}", ha="center", va="center", fontsize=11, color=INK)
    left = left + v
ax.set_xlim(0, 100); ax.set_xlabel("Share of attacked questions (%)")
ax.legend(ncol=2, fontsize=10, frameon=False, loc="upper center", bbox_to_anchor=(.5, -.28)); save(f, "failure.png")

# 5. Worst-case capture robustness
f, ax = plt.subplots(figsize=(4.6, 3.6))
b = ax.bar(["Signature only", "Signature +\nreader attention"], [66.5, 95.3], color=[BASE, OURS], width=.55)
for r, s in zip(b, [66.5, 95.3]): ax.text(r.get_x() + r.get_width() / 2, s + 1.5, f"{s:g}%", ha="center", fontsize=13, fontweight="bold")
ax.set_ylabel("Poison caught, unluckiest capture (%)"); ax.set_ylim(0, 105); ax.yaxis.grid(True, color=GRID); ax.set_axisbelow(True)
save(f, "worstcase.png")

# 6. Swarm trade-off: receiver attack endorsement vs clean accuracy (E42/E45)
pts = {"Shared record IDs": (62.5, 52.5, BASE), "Shared sample (cosine)": (2.1, 50.8, BASE),
       "Shared claim signature": (9.2, 51.7, OURS), "Signature + attention": (0.4, 33.3, OURS)}
f, ax = plt.subplots(figsize=(7, 4.6))
ax.axhline(52.5, ls="--", color=MUTE); ax.text(40, 53.4, "untreated clean accuracy 52.5%", color=MUTE, fontsize=11)
for k, (x, y, c) in pts.items():
    ax.scatter(x, y, s=260, color=c, edgecolor="white", linewidth=2, zorder=3)
    dx, dy = (2, -3.2) if k != "Shared record IDs" else (-24, -3.5)
    if k == "Shared claim signature": dx, dy = (2.5, 1)
    ax.annotate(k, (x, y), xytext=(x + dx, y + dy), fontsize=12, color=INK)
ax.annotate("", xy=(9.2, 51.7), xytext=(62.5, 52.5), arrowprops=dict(arrowstyle="->", color=OURS, lw=2.2))
ax.set_xlabel("Receivers endorsing the false answer (%)  lower is better")
ax.set_ylabel("Receivers' clean accuracy (%)"); ax.set_xlim(-3, 70); ax.set_ylim(28, 58)
ax.grid(True, color=GRID); ax.set_axisbelow(True); save(f, "swarm.png")
print("ok")

# 7. Worked example: NQ test363 (results/e11a_flag_scores_nq_k10.jsonl, e11c layer 21)
ent = [1.0, .99, 1.0, 0.0, .98, 0, 0, 0, 0, 0]
z = [2.2, 1.2, .2, .6, -.1, -.8, -.8, -.9, -.9, -.7]
kind = ["planted"] * 5 + ["clean"] * 5
rows = [f"Passage {i+1}  ({k})" for i, k in enumerate(kind)]
f, ax = plt.subplots(1, 3, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1, .45]})
y = np.arange(10)[::-1]
cc = [WARN if k == "planted" else "#16a34a" for k in kind]
ax[0].barh(y, ent, color=cc, height=.6); ax[0].axvline(.01, color=INK, ls="--", lw=1)
ax[0].set_yticks(y); ax[0].set_yticklabels(rows, fontsize=11); ax[0].set_xlim(0, 1.05)
ax[0].set_title("① Signature check\nentails the shared claim?", fontsize=12, loc="left")
ax[1].barh(y, z, color=cc, height=.6); ax[1].axvline(0, color=INK, ls="--", lw=1)
ax[1].set_yticks([]); ax[1].set_xlim(-1.2, 2.5)
ax[1].set_title("② Attention check\nreader focuses on it? (z)", fontsize=12, loc="left")
ax[1].annotate("missed by ①,\ncaught by ②", xy=(.6, y[3]), xytext=(1.0, y[3] - 1.6), fontsize=11, color=OURS,
               arrowprops=dict(arrowstyle="->", color=OURS, lw=1.8))
ax[2].axis("off"); ax[2].set_ylim(-.5, 9.5); ax[2].set_title("③ Decision", fontsize=12, loc="left")
for yy, e_, z_ in zip(y, ent, z):
    flag = e_ >= .01 or z_ >= 0
    ax[2].text(.05, yy, "removed" if flag else "kept", fontsize=12, fontweight="bold", va="center",
               color=WARN if flag else "#16a34a")
for a in ax[:2]: a.xaxis.grid(True, color=GRID); a.set_axisbelow(True)
save(f, "worked.png")
print("worked ok")
