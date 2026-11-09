"""Appendix figures from results/sprint/raw.jsonl and the human/LLM agreement files (no re-analysis of endpoints)."""
import json
from collections import defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
OUT = "paper/report/fig"; INK, MUTE, OURS, BAD, BENCH, GRID = "#1f2430", "#6b7280", "#0f766e", "#dc2626", "#7c3aed", "#e5e7eb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
rows = {}
for l in open("results/sprint/raw.jsonl"):
    r = json.loads(l); rows[r["key"]] = r
ARMS = ["A0_untreated", "A1_ids", "A2_sample", "A3_signature", "A4_sham", "A5_sig_attention", "A6_gated", "A7_no_refill",
        "A8_warn", "A9_forged", "A10_bare_claim", "B1_self_check", "B2_stealth_av", "B3_fingerprint"]
NAME = {"A0_untreated": "Untreated", "A1_ids": "Shared IDs", "A2_sample": "Raw record", "A3_signature": "Claim",
        "A4_sham": "Sham claim", "A5_sig_attention": "Claim + attention", "A6_gated": "Gated", "A7_no_refill": "No refill",
        "A8_warn": "Warn", "A9_forged": "Forged claim", "A10_bare_claim": "Claim, no question", "B1_self_check": "Self-check",
        "B2_stealth_av": "Stealth Lens", "B3_fingerprint": "Fingerprint"}
blk = defaultdict(lambda: defaultdict(list)); rem = defaultdict(lambda: defaultdict(list))
for r in rows.values():
    for key, v in r["answers"].items():
        rk, cond, arm = key.split(":")
        if cond == "attacked":
            blk[arm][r["block"]].append(v["endorsed"]); rem[arm]["poison"].append(v["poison_removed"]); rem[arm]["clean_att"].append(v["clean_removed"])
        else:
            rem[arm]["clean_cl"].append(v["clean_removed"])
# C1 per-block heatmap
M = np.array([[100 * np.mean(blk[a][b]) for b in range(5)] for a in ARMS])
f, ax = plt.subplots(figsize=(6.4, 5.2)); im = ax.imshow(M, cmap="Reds", vmin=0, vmax=70, aspect="auto")
for i in range(len(ARMS)):
    for j in range(5):
        ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=8.5, color="white" if M[i, j] > 40 else INK)
ax.set_xticks(range(5)); ax.set_xticklabels([f"Block {b+1}" for b in range(5)]); ax.set_yticks(range(len(ARMS))); ax.set_yticklabels([NAME[a] for a in ARMS])
ax.spines[:].set_visible(False); cb = f.colorbar(im, ax=ax, shrink=.8); cb.set_label("Receivers endorsing the false answer, attacked (%)")
f.savefig(f"{OUT}/app_blocks.png", dpi=200, bbox_inches="tight"); plt.close(f)
# C2 what each receiver removed
SEL = [a for a in ARMS if a not in ("A0_untreated", "B1_self_check", "A8_warn")]
pc = [100 * np.mean(rem[a]["poison"]) for a in SEL]; cc = [np.mean(rem[a]["clean_cl"]) for a in SEL]
f, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
col = [BENCH if a.startswith("B") else (BAD if a in ("A4_sham", "A9_forged") else (MUTE if a == "A1_ids" else OURS)) for a in SEL]
y = np.arange(len(SEL))[::-1]
a1.barh(y, pc, color=col); a1.set_yticks(y); a1.set_yticklabels([NAME[a] for a in SEL]); a1.set_xlabel("Planted copy removed, attacked (%)"); a1.set_xlim(0, 105)
a2.barh(y, cc, color=col); a2.set_xlabel("Clean passages removed per clean context (of 10)")
for ax_, vals, fmt in ((a1, pc, "{:.0f}"), (a2, cc, "{:.2f}")):
    for yy, v in zip(y, vals): ax_.text(v, yy, " " + fmt.format(v), va="center", fontsize=8)
    ax_.xaxis.grid(True, color=GRID); ax_.set_axisbelow(True)
f.savefig(f"{OUT}/app_removed.png", dpi=200, bbox_inches="tight"); plt.close(f)
# C3 scoring validation + message size
L = json.load(open("results/sprint/human/llm_judge_agreement.json")); H = json.load(open("results/sprint/human/human_agreement.json"))
f, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.2), gridspec_kw={"width_ratios": [1.6, 1]})
cats = ["Rule = LLM judge\n(300 answers)", "Human = rule\n(30 random agreements)", "Human sides with\nLLM on disagreements"]
e = [100 * L["endorsed"]["agreement"], 100 * 29 / 30, 100 * 10 / 11]; c = [100 * L["correct"]["agreement"], 100 * 28 / 30, 100 * 15 / 19]
x = np.arange(3); a1.bar(x - .18, e, .36, color=OURS, label="endorses false answer"); a1.bar(x + .18, c, .36, color="#5eead4", label="correct")
for xx, v in zip(list(x - .18) + list(x + .18), e + c): a1.text(xx, v + 1, f"{v:.0f}", ha="center", fontsize=8)
a1.set_xticks(x); a1.set_xticklabels(cats, fontsize=8); a1.set_ylim(0, 110); a1.set_ylabel("%"); a1.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(.5, -.3), ncol=2)
mb = json.load(open("results/sprint/analysis.json"))["message_bytes"]
nm = {"ids": "IDs", "fingerprint": "Fingerprint", "signature": "Claim", "sample": "Raw record"}
ks = ["ids", "fingerprint", "signature", "sample"]; a2.bar([nm[k] for k in ks], [mb[k] for k in ks], color=[MUTE, BENCH, OURS, MUTE])
for i, k in enumerate(ks): a2.text(i, mb[k] + 5, f"{mb[k]:.0f}", ha="center", fontsize=8)
a2.set_ylabel("Message size (bytes, mean)"); a2.tick_params(axis="x", labelsize=8)
f.savefig(f"{OUT}/app_scoring.png", dpi=200, bbox_inches="tight"); plt.close(f)
print({NAME[a]: (round(p, 1), round(q, 2)) for a, p, q in zip(SEL, pc, cc)})
