"""Extra report figures. Sources: step2_offline.txt (AUCs), e26 (prefix-free), e21_summary.txt (capture),
e30_attack_gate.txt (gate), e29_confirmatory.txt (tier 2), e36 interim summaries via EVIDENCE_REPORT.md (readers)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
INK, MUTE, GRID = "#1f2430", "#6b7280", "#e5e7eb"
OURS, CG, TR, BASE, WARN, OK = "#0f766e", "#7c3aed", "#d97706", "#9ca3af", "#dc2626", "#16a34a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTE})
def save(f, n): f.savefig("fig/" + n, dpi=220, bbox_inches="tight"); plt.close(f)

# A3: shortcut. Detection AUC on tier 1 (HotpotQA / MS MARCO)
names = ["Cosine to caught\nrecord (trivial)", "AntiVenom\n(combined)", "Attention\nalone", "Entailment\nalone", "Passage length\nalone"]
hp = [1.000, .977, .979, .940, .727]; ms = [.993, .984, .962, .956, .856]
f, ax = plt.subplots(figsize=(7.4, 3.6)); x = np.arange(5); w = .36
b1 = ax.bar(x - w/2, hp, w, color=[WARN, OURS, OURS, OURS, BASE], alpha=.95, label="HotpotQA")
b2 = ax.bar(x + w/2, ms, w, color=[WARN, OURS, OURS, OURS, BASE], alpha=.55, label="MS MARCO")
for bars in (b1, b2):
    for r in bars: ax.text(r.get_x() + r.get_width()/2, r.get_height() + .008, f"{r.get_height():.2f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(names, fontsize=10); ax.set_ylim(.6, 1.05); ax.set_ylabel("Detection AUC")
ax.text(4.55, 1.0, "solid = HotpotQA\nfaded = MS MARCO", ha="right", va="top", fontsize=9, color=MUTE)
ax.yaxis.grid(True, color=GRID); ax.set_axisbelow(True); save(f, "shortcut.png")

# A3b: prefix-free collapse (NQ dev, E25/E26)
f, ax = plt.subplots(figsize=(4.6, 3.6))
lab = ["With prefix\n(tier 2, CG)", "Without prefix\n(CG)", "Without prefix\n(AntiVenom)"]
v = [20.6, 52.3, 8.9]
b = ax.bar(lab, v, color=[CG, CG, OURS], width=.6)
b[0].set_alpha(.5)
for r, s in zip(b, v): ax.text(r.get_x() + r.get_width()/2, s + 1, f"{s:g}%", ha="center", fontweight="bold")
ax.set_ylabel("Clean passages discarded\nat near-full poison recall (%)"); ax.set_ylim(0, 62); ax.tick_params(axis="x", labelsize=9)
ax.yaxis.grid(True, color=GRID); ax.set_axisbelow(True); save(f, "prefix.png")

# A4: capture dependence (NQ dev, E21)
f, ax = plt.subplots(figsize=(7.2, 3.4))
lab = ["caught #1", "#2", "#3", "#4", "#5", "unluckiest\ncatch,\nentailment", "unluckiest\ncatch,\n+ attention"]
v = [87.1, 89.3, 90.9, 91.8, 89.3, 66.5, 95.3]
c = [OURS] * 5 + [WARN, OK]
b = ax.bar(lab, v, color=c, width=.62)
for r, s in zip(b, v): ax.text(r.get_x() + r.get_width()/2, s + 1.2, f"{s:g}", ha="center", fontsize=10, fontweight="bold")
ax.axvline(4.5, color=MUTE, ls=":"); ax.set_ylim(0, 108); ax.set_ylabel("Poison recall (%)")
ax.text(2, 101, "average over targets, by which record was caught", ha="center", fontsize=9, color=MUTE)
ax.text(5.5, 101, "per-target worst case", ha="center", fontsize=9, color=MUTE)
ax.yaxis.grid(True, color=GRID); ax.set_axisbelow(True); save(f, "capture.png")

# A5: false-alarm cost and the gate (tier 2 pooled, E29 + E30)
arms = ["No defence", "AntiVenom", "CoordGuard", "AntiVenom\n+ gate"]
clean_acc = [61, 39, 37, 61]; att_end = [76, 7, 5, 14]
f, ax = plt.subplots(1, 2, figsize=(9.6, 3.5))
col = [BASE, OURS, CG, OK]
b = ax[0].barh(arms[::-1], clean_acc[::-1], color=col[::-1], height=.6)
for r, s in zip(b, clean_acc[::-1]): ax[0].text(s + 1, r.get_y() + r.get_height()/2, f"{s}", va="center", fontweight="bold")
ax[0].set_title("Accuracy when NO attack is present (%)", loc="left", fontsize=11); ax[0].set_xlim(0, 75)
b = ax[1].barh(arms[::-1], att_end[::-1], color=col[::-1], height=.6)
for r, s in zip(b, att_end[::-1]): ax[1].text(s + 1, r.get_y() + r.get_height()/2, f"{s}", va="center", fontweight="bold")
ax[1].set_title("Endorses false answer under attack (%)", loc="left", fontsize=11); ax[1].set_xlim(0, 90); ax[1].set_yticklabels([])
for a in ax: a.xaxis.grid(True, color=GRID); a.set_axisbelow(True)
save(f, "gate.png")

# Readers (E22 dev + E36 tier 2)
f, ax = plt.subplots(figsize=(6.4, 3.4))
rd = ["Qwen2.5-7B\n(tier 2)", "Mistral-7B\n(tier 2)", "Llama-3-8B\n(tier 2)"]
und = [76, 69, 53]; ours = [7, 11, 33]; cg = [5, 9, 3]
x = np.arange(3); w = .26
for i, (v, c, l) in enumerate(((und, BASE, "No defence"), (ours, OURS, "AntiVenom"), (cg, CG, "CoordGuard"))):
    bb = ax.bar(x + (i - 1) * w, v, w, color=c, label=l)
    for r, s in zip(bb, v): ax.text(r.get_x() + r.get_width()/2, s + 1, str(s), ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(rd, fontsize=10); ax.set_ylabel("Endorses false answer (%)"); ax.set_ylim(0, 88)
ax.annotate("95/100 claim\nextractions blank", xy=(2, 35), xytext=(1.35, 60), fontsize=9, color=WARN, arrowprops=dict(arrowstyle="->", color=WARN))
ax.legend(frameon=False, fontsize=9, loc="upper right"); ax.yaxis.grid(True, color=GRID); ax.set_axisbelow(True)
save(f, "readers.png")
print("ok")
