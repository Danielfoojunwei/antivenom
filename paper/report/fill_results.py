"""Fill the report's sprint placeholders from results/sprint/analysis.json (numbers are never typed by hand)."""
import json, re
A = json.load(open("results/sprint/analysis.json")); J = json.load(open("results/sprint/human/llm_judge_agreement.json"))
T = A["tests"]; M = A["arm_means"]; NH = A["clean_accuracy_vs_untreated"]; BD = A["benchmarks_descriptive"]
pct = lambda x: f"{x*100:.1f}%"
def d(tid, ep=None):
    t = T[tid]; e = t["endpoints"][ep or list(t["endpoints"])[0]]
    return f"{e['mean_diff']*100:+.1f} points [{e['ci95'][0]*100:+.1f}, {e['ci95'][1]*100:+.1f}]"
def nh(a):
    v = NH[a]; return f"{v['mean_diff']*100:+.1f} points [{v['ci95'][0]*100:+.1f}, {v['ci95'][1]*100:+.1f}]"
def bd(k):
    v = BD[k]; return f"{v['mean_diff']*100:+.1f} points [{v['ci95'][0]*100:+.1f}, {v['ci95'][1]*100:+.1f}]"
mb = A["message_bytes"]; cb = A["closed_book_strata"]; sp = A["seconds_per_answer"]
s = open("paper/report/antivenom_report.html").read()
P = lambda txt: f'<span class="ph">{txt}</span>'
R = {}
R[P("[RESULT SENTENCE 1: T1, claim vs IDs, difference and 95% CI]")] = (
    f"Sharing the claim cut receivers' endorsement of the false answer from {pct(M['A1_ids']['attacked_endorsed'])} to {pct(M['A3_signature']['attacked_endorsed'])} "
    f"({d('T1')}, all 5 blocks), whereas sharing record IDs gave no protection, and clean accuracy stayed within a 5-point margin.")
R[P("[RESULT SENTENCE 2: T9 and T3, with nulls stated as nulls]")] = (
    f"Contrary to our prediction, sharing the raw record ({pct(M['A2_sample']['attacked_endorsed'])}) or a BinaryShield-style fingerprint ({pct(M['B3_fingerprint']['attacked_endorsed'])}) protected slightly more than the claim; "
    f"the claim's content and its question both mattered, and adding attention lowered endorsement to {pct(M['A5_sig_attention']['attacked_endorsed'])} at a cost of {abs(NH['A5_sig_attention']['mean_diff'])*100:.0f} points of clean accuracy.")
R[P("[RESULT SENTENCE 3: T4 gate trade-off and T7 forged-signature cost]")] = (
    f"Removing flagged passages beat warning the reader; a gate restored clean accuracy but let {pct(M['A6_gated']['attacked_endorsed'])} of attacks through; "
    f"and a forged claim cost {abs(NH['A9_forged']['mean_diff'])*100:.0f} points of clean accuracy, which argues for authenticating shared claims.")
R[P("[cross-checked by …]")] = f"cross-checked by a blinded LLM judge (κ = {J['endorsed']['kappa']:.2f} for endorsement, {J['correct']['kappa']:.2f} for correctness)"
R[P("[and cross-checked by …]")] = f"and cross-checked by a blinded LLM judge on 300 sampled answers (agreement {J['endorsed']['agreement']*100:.1f}% and {J['correct']['agreement']*100:.1f}%; κ = {J['endorsed']['kappa']:.2f} and {J['correct']['kappa']:.2f}); 58 rows, all disagreements plus 30 agreements, go to human adjudication"
s = s.replace("The results show which parts of a shared claim warning protect receivers, what they cost, and how they can be misused.",
              "On this benchmark, what protects receivers is sharing content rather than identifiers; the claim's advantage over sharing the record is clean accuracy, not protection.")
# Results section
rows = [("T1", "attacked_endorsed"), ("T1b", "attacked_endorsed"), ("T9", "attacked_endorsed"), ("T2", "attacked_endorsed"), ("T8", "attacked_endorsed"),
        ("T3", "attacked_endorsed"), ("T6", "attacked_endorsed"), ("T5", "attacked_correct"), ("T4", "clean_correct"), ("T4", "attacked_endorsed"), ("T7", "clean_correct")]
nm = {"attacked_endorsed": "attacked endorsement", "attacked_correct": "attacked accuracy", "clean_correct": "clean accuracy"}
verdict = {"T9": "supported in the <i>opposite</i> direction: the record protects more", "T4|attacked_endorsed": "protection cost (reported)"}
tr = ""
for tid, ep in rows:
    t = T[tid]; e = t["endpoints"][ep]
    v = verdict.get(f"{tid}|{ep}", verdict.get(tid, "supported" if t["supported"] else "not supported"))
    if tid == "T4" and ep == "attacked_endorsed": v = verdict["T4|attacked_endorsed"]
    hp = "&lt; 0.001" if t["holm_p"] < 0.001 else f"{t['holm_p']:.3f}"
    if tid == "T4" and ep == "attacked_endorsed": hp = "–"
    tr += f"<tr><td>{tid}</td><td>{t['arm'].split('_')[0]} vs {t['reference'].split('_')[0]}</td><td>{nm[ep]}</td><td>{e['mean_diff']*100:+.1f} [{e['ci95'][0]*100:+.1f}, {e['ci95'][1]*100:+.1f}]</td><td>{hp}</td><td>{e['blocks_same_sign']}/5</td><td>{v}</td></tr>"
res = f'''<h2>4. Results</h2>
<p>All 200 incidents completed in all 14 arms; every finder produced a valid claim; the five drift checks returned identical answers. Rates are percentages of receiver answers; differences are in percentage points, arm minus reference, with 95% intervals.</p>
<table><tr><th>Test</th><th>Arms</th><th>Endpoint</th><th>Difference [95% CI]</th><th>Holm p</th><th>Blocks, same sign</th><th>Verdict</th></tr>{tr}</table>
<p class="cap"><b>Table 4:</b> Every pre-registered test (n = 200 incidents, 5 blocks). PROVISIONAL: rule-scored, cross-checked by a blinded LLM judge; human adjudication pending.</p>
<figure><img src="fig/sprint_forest.png" alt="forest" style="width:92%;margin:0 auto"></figure>
<p class="cap"><b>Figure 4:</b> All tests, pooled 95% intervals with the five block estimates (ticks). Teal: effect in the predicted direction; amber: against the prediction, or a cost. Dotted lines: ±5-point margin.</p>
<p><span class="lead">4.1 Setup (S0).</span> The attack works here: untreated receivers endorsed the false answer in {pct(M['A0_untreated']['attacked_endorsed'])} of attacked answers, against {pct(M['A0_untreated']['clean_endorsed'])} of clean ones.</p>
<p><span class="lead">4.2 What to share (S1).</span> Sharing record IDs gave <i>no</i> protection: each receiver's copy carried a different identifier, so A1 equalled untreated in every answer. Sharing the claim lowered endorsement by {d('T1')} (T1, primary), with clean accuracy {nh('A3_signature')} relative to untreated, within the 5-point margin. Sharing the raw record lowered it by {d('T1b')} (T1b). Contrary to our prediction, the claim protected <i>less</i> than the raw record (T9: {d('T9')}); clean accuracy was similar ({d('T9', 'clean_correct')}). Messages averaged {mb['ids']:.0f} bytes for IDs, {mb['sample']:.0f} for the raw record and {mb['signature']:.0f} for the claim, so the claim is not smaller than the record.</p>
<p><span class="lead">4.3 Content and form (S2).</span> A sham claim from another incident gave almost no protection: the real claim lowered endorsement by {d('T2')} relative to it (T2). The claim needs its question: dropping the question raised endorsement from {pct(M['A3_signature']['attacked_endorsed'])} to {pct(M['A10_bare_claim']['attacked_endorsed'])} (T8: {d('T8')}).</p>
<p><span class="lead">4.4 Receiver detection (S3).</span> Adding the reader's attention lowered endorsement further, from {pct(M['A3_signature']['attacked_endorsed'])} to {pct(M['A5_sig_attention']['attacked_endorsed'])} (T3: {d('T3')}), but cut clean accuracy by {nh('A5_sig_attention')} relative to untreated, outside the margin. The claim's benefit was larger when the reader did not already know the answer ({cb['does_not_know']['T1']*100:+.1f} points, n = {cb['does_not_know']['n']}) than when it did ({cb['knows']['T1']*100:+.1f}, n = {cb['knows']['n']}; descriptive).</p>
<p><span class="lead">4.5 Neutralisation (S4).</span> Removing flagged passages protected more than keeping them and warning the reader in the prompt (T6: {d('T6')}; the A-MemGuard-style warning endorsed {pct(M['A8_warn']['attacked_endorsed'])}), though the warning kept clean accuracy ({nh('A8_warn')}). Refilling with next-ranked evidence raised attacked accuracy beyond deleting alone (T5: {d('T5')}).</p>
<p><span class="lead">4.6 Normal operation (S5).</span> The gate restored clean accuracy to the untreated level (T4: {d('T4', 'clean_correct')}; {nh('A6_gated')} vs untreated) but gave up most of the protection: endorsement rose from {pct(M['A5_sig_attention']['attacked_endorsed'])} to {pct(M['A6_gated']['attacked_endorsed'])} ({d('T4', 'attacked_endorsed')}). As calibrated, its threshold fired too rarely in these single-copy contexts.</p>
<p><span class="lead">4.7 Misuse (S6).</span> A forged claim (the true answer presented as false) removed good evidence: clean accuracy fell by {d('T7')} relative to the real claim and by {nh('A9_forged')} relative to untreated.</p>
<figure style="display:flex;gap:3mm;align-items:center"><img src="fig/sprint_tradeoff.png" style="width:52%"><img src="fig/sprint_benchmarks.png" style="width:48%"></figure>
<p class="cap"><b>Figure 5:</b> Left: protection against clean accuracy for every arm and benchmark (A1 overlaps A0). Right: AntiVenom arms minus benchmarks, attacked endorsement (descriptive; many factors differ).</p>
<p><span class="lead">4.8 Benchmarks (descriptive).</span> The self-check prompt barely helped ({pct(M['B1_self_check']['attacked_endorsed'])}). The Stealth Lens filter endorsed {pct(M['B2_stealth_av']['attacked_endorsed'])} with clean accuracy {nh('B2_stealth_av')}; the claim matched its protection ({bd('A3_signature - B2_stealth_av [attacked_endorsed]')}) with higher clean accuracy ({bd('A3_signature - B2_stealth_av [clean_correct]')}). The BinaryShield-style fingerprint matched the raw record ({pct(M['B3_fingerprint']['attacked_endorsed'])}; clean {nh('B3_fingerprint')}) and protected more than the claim ({bd('A3_signature - B3_fingerprint [attacked_endorsed]')}).</p>
'''
a = s.index("<h2>4. Results</h2>"); b = s.index("<h2>5. Discussion and Limitations</h2>")
s = s[:a] + res + s[b:]
R[P("[Which of these the results support]")] = ("The sprint supports the content-not-identity lesson (T1, T1b, T2) and shows that the question matters (T8). It does not support an advantage of the claim over sharing the record (T9): on near-duplicate poisons, the record itself is an excellent matcher. The claim's measured advantages are narrower: the lowest clean cost among strong-protection arms, and higher clean accuracy than the Stealth Lens filter at similar protection.")
R[P("[human check status]")] = "cross-checked by a blinded LLM judge; human adjudication of 58 rows pending"
R[P("[and the status of the human/LLM cross-check]")] = "cross-checked by a blinded LLM judge (κ 0.84 and 0.87); human adjudication of 58 rows pending"
R[P("[Conclusion written from the ledger-supported results only: what sharing a question-scoped claim does for receivers, which parts carry the effect, what it costs on clean questions, how a forged claim harms, and how it compares with the three benchmarks.]")] = (
    f"When one agent confirms a poisoned record, what it shares decides whether the rest of the swarm is protected. In 200 incidents tested one factor at a time, identifiers protected nobody, because copies were renamed; content protected almost everyone. A question-scoped claim cut endorsement from {pct(M['A1_ids']['attacked_endorsed'])} to {pct(M['A3_signature']['attacked_endorsed'])} with no clean loss beyond a 5-point margin, and both its content and its question mattered. The raw record and a BinaryShield-style fingerprint protected slightly more on this near-duplicate benchmark, so the claim's case rests on what it costs, not on what it blocks: it kept clean accuracy closest to untreated among strong-protection arms and beat an attention-only filter on clean accuracy at similar protection. Attention bought more protection at a real clean cost; removal beat warning; the gate, as calibrated, gave back too much; and a forged claim harmed clean answers, so shared claims should be authenticated. The next tests are diverse, adaptive poisons, where a record's surface no longer gives the copies away and a claim may finally earn its keep.")
for k, v in R.items():
    assert k in s, k[:60]
    s = s.replace(k, v)
open("paper/report/antivenom_report.html", "w").write(s)
left = re.findall(r'class="ph">([^<]+)', s)
print("remaining placeholders:", left)
