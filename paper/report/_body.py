head=open("_head.html").read()
fig1=open("_fig1.html").read().replace("values are those of Figure 4.","illustrative development values (Figure 3).")
tiles=open("_tiles.html").read()
tiles=tiles.replace('<b>Figure 3:</b> One receiver\'s ten retrieved passages for NQ question test363 (development set; real stored values). Each tile is coloured by the strength of its signal.',
 '<b>Figure 3:</b> The two receiver signals on one development question (NQ test363; stored pre-sprint values, shown for illustration). The "Decision" row uses a simple entailment-or-attention rule for illustration only; the sprint uses the calibrated rules in Section 3.3.')
P='<span class="ph">'; E='</span>'
body=f'''
<style>.ph{{background:#fef3c7;border:1px dashed #d97706;border-radius:1mm;padding:0 1mm;font-family:Inter,Arial,sans-serif;font-size:8.2pt;color:#92400e}}
.box{{border:1.4px dashed #d97706;background:#fffbeb;border-radius:2.5mm;padding:2mm 3mm;margin:1.5mm 0 3mm;font-family:Inter,Arial,sans-serif;font-size:8.4pt;break-inside:avoid}}</style>
<h1 class="title">AntiVenom: Turning One Captured Poison into Protection for a Whole Agent Swarm<sup>1</sup></h1>
<p class="author"><b>Daniel Foo</b></p>
<p class="aff">Nanyang Technological University (NTU), Singapore</p>
<p class="author"><b>With</b></p>
<p class="aff">Apart Research</p>

<div class="abstract-h">Abstract</div>
<p class="abstract">Agents in a swarm read shared memory and retrieval, so a few planted records can mislead many agents at once. When one agent confirms a poisoned record, what should it pass to the others? We test AntiVenom, which turns the confirmed record into a question-scoped false claim (about 275 bytes). Receivers flag retrieved passages whose NLI entailment of that claim crosses a calibrated threshold, optionally fused with their reader's attention, then remove and refill them. In a pre-registered sprint experiment on 200 PoisonedRAG incidents (5 replicate blocks, 3 receivers each, local Qwen2.5-7B), we changed one factor per test to measure what each part contributes: what is shared (claim vs record IDs vs the raw record), the claim's content and form, the attention signal, removal versus a warning, refill, a gate, and a forged signature. We also report three external benchmarks: a self-check prompt, the Stealth Lens attention filter and BinaryShield-style shared fingerprints. {P}[RESULT SENTENCE 1: T1, claim vs IDs, difference and 95% CI]{E} {P}[RESULT SENTENCE 2: T9 and T3, with nulls stated as nulls]{E} {P}[RESULT SENTENCE 3: T4 gate trade-off and T7 forged-signature cost]{E} Scores are rule-based and {P}[cross-checked by …]{E}. The results show which parts of a shared claim warning protect receivers, what they cost, and how they can be misused.</p>

<p class="fn"><sup>1</sup> Research conducted at the Swarm Alignment Hackathon (Apart Research, with the AI Alignment Foundation and AE Studio), 6–8 November 2026. Track 4 (Multi-Agent Oversight and Control). This project builds on the author's unpublished earlier prototype of the AntiVenom detector and exploratory experiments, which fixed the method, its calibration settings and the hypotheses tested here. Everything reported in Section 4 was run during the sprint (Appendix A.2).</p>

<h2>1. Introduction</h2>
<p><span class="lead">The inspiration: how antivenom works.</span> A snakebite is dangerous because venom travels through the blood and acts wherever it lands. Antivenom is made from a small captured sample: animals are given tiny doses, and the antibodies they produce are purified and given to patients. The antibodies recognise the toxin by its shape, not by which snake bit, and bind it wherever it circulates. Because antivenom has side effects, clinicians give it only on signs of envenoming.</p>
<p><span class="lead">Why this fits poisoning in a swarm.</span> A planted record enters a shared store and reaches every agent that retrieves it, often as copies under different identifiers. Antivenom suggests a design: capture one sample, describe the poison by what it claims rather than where it is stored, distribute that description, neutralise matching records, and intervene only on evidence of the claim (Figure 1). We treat this as a design hypothesis to test, not as a guarantee: an attack can also mislead by misapplying true evidence, without stating any false claim [Lazy Grounding].</p>
<p><span class="lead">A warning that only protects the agent who found it.</span> Five planted passages tell a retrieval-augmented agent that the main industry of the Canadian Shield is fishing (the truth is mining). If the agent that catches one of them shares its identifier, an agent whose copy is stored under a different identifier is not protected. If it shares what the record claims, the second agent can look for that claim in its own context.</p>
{fig1}
<p><span class="lead">Why it matters.</span> In the Hugging Face agent incident, one agent assigned work to hundreds of others, and about 1,200 agents used 7,905 names [1, 2]. When agents rename, copy and paraphrase, identifiers become unreliable warnings. Track 4 asks what oversight and control still work when the untrusted side is many agents. Here the untrusted side is the shared store, and the control is the warning one agent passes to the others.</p>
<p><span class="lead">What we test.</span> Rather than argue that AntiVenom is better than existing defences, we decompose it along the stages of one incident and test each stage separately, changing one factor at a time (Table 1). Our contribution is this controlled decomposition: evidence of which parts of a shared claim warning protect receivers, what each costs, and how it can be misused, together with descriptive comparisons against three external benchmarks.</p>
<table>
<tr><th style="width:17%">Stage</th><th style="width:43%">Question</th><th style="width:10%">Test</th><th>Only factor changed</th></tr>
<tr><td>S0 Setup</td><td>Does the attack work in this setup? (manipulation check)</td><td>C0/C1</td><td>attack on or off</td></tr>
<tr><td rowspan="3">S1 What to share</td><td>Does sharing the claim protect more than sharing record IDs?</td><td><b>T1</b></td><td>payload</td></tr>
<tr><td>Does sharing the raw record protect more than sharing IDs?</td><td>T1b</td><td>payload</td></tr>
<tr><td>Does a question-scoped claim protect more than the raw record?</td><td>T9</td><td>payload</td></tr>
<tr><td rowspan="2">S2 Content and form</td><td>Does the claim's content matter, not just that something was shared?</td><td>T2</td><td>real or sham claim</td></tr>
<tr><td>Does the claim need its question?</td><td>T8</td><td>question + claim, or claim only</td></tr>
<tr><td>S3 Receiver detection</td><td>Does the reader's attention add to the claim check?</td><td>T3</td><td>signal set (same calibration)</td></tr>
<tr><td rowspan="2">S4 Neutralisation</td><td>Does removing beat warning the reader?</td><td>T6</td><td>delete or warn</td></tr>
<tr><td>Does refilling restore accuracy beyond deleting?</td><td>T5</td><td>refill on or off</td></tr>
<tr><td>S5 Normal operation</td><td>Does a gate restore clean accuracy, at what protection cost?</td><td>T4</td><td>gate on or off</td></tr>
<tr><td>S6 Misuse</td><td>Does a forged signature delete good evidence?</td><td>T7</td><td>real or forged claim</td></tr>
</table>
<p class="cap"><b>Table 1:</b> The sprint experiment: one question per stage of an incident, one factor per test. T1 is the pre-registered primary test.</p>

<h2>2. Related Work</h2>
<p><span class="lead">Poisoning.</span> PoisonedRAG plants passages that make a reader give a chosen false answer [3]; we use its released poison and generate no attack text. Lazy Grounding shows agents misled by true evidence for a nearby question [16], a failure a claim check cannot catch.</p>
<p><span class="lead">Detecting poison in one agent.</span> TrustRAG clusters and self-assesses passages [4]; RobustRAG aggregates isolated answers [13]; CoordGuard removes coordinated clusters and offers both always-on and benign-calibrated gated modes [5]; Stealth Lens filters passages by the variance of the reader's attention [17]; SeCon-RAG checks entity, intent and relation consistency [18]; MIRAGE gates generation on an NLI claim graph [19]. Several of these already reason about meaning; AntiVenom differs in using a known false claim from a confirmed incident as side information.</p>
<p><span class="lead">Reusing and sharing what was learned.</span> BinaryShield shares privacy-preserving semantic fingerprints of suspicious prompts across services, and recipients match their own traffic [20]. A-MemGuard turns detected memory failures into lessons that trigger revision [21]; AgentAntibody turns confirmed prompt injections into reusable abstract antibodies inside one agent [8]; Membrane stores block and permit conditions [22]; Cordon-MAS passes structured claim cards between role agents for semantic audit [23]; MAPLE-Guard, PerMIT and SecureCollaRAG share trust, endorsements or source reliability [6, 7, 14]. Matching new statements to known false claims is older still in fact-checking [24], and transferable alerts with locally generated filters date to worm containment [25].</p>
<table>
<tr><th style="width:21%">Defence</th><th style="width:37%">What is reused or shared after a detection</th><th>Role in this paper</th></tr>
<tr><td>BinaryShield [20]</td><td>binary semantic fingerprint of the attack text</td><td><b>Run</b> as benchmark B3 (BinaryShield-style)</td></tr>
<tr><td>Stealth Lens [17]</td><td>nothing; local attention-variance filter</td><td><b>Run</b> as benchmark B2 (authors' code semantics)</td></tr>
<tr><td>A-MemGuard [21]</td><td>lesson injected into the prompt</td><td><b>Run</b> as arm A8 (warn), tested in T6</td></tr>
<tr><td>Raw record + cosine</td><td>the captured record itself</td><td><b>Run</b> as arm A2, tested in T1b and T9</td></tr>
<tr><td>CoordGuard, TrustRAG</td><td>nothing</td><td>cited; not re-run in the sprint</td></tr>
<tr><td>SeCon-RAG, MIRAGE, Membrane, Cordon-MAS</td><td>consistency checks, claim graphs, conditions, claim cards</td><td>cited; only loose stand-ins were possible</td></tr>
<tr class="ours"><td>AntiVenom</td><td>a question-scoped false claim, about 275 bytes</td><td>tested stage by stage (Table 1)</td></tr>
</table>
<p class="cap"><b>Table 2:</b> Closest prior work and what this paper does with each.</p>
<p><span class="lead">What we add.</span> A narrow formulation (after a confirmed incident, represent the poison as a question-scoped false claim for receiver-side containment) and a controlled test of each of its parts against the closest alternatives given the same incident information. We make no priority claim.</p>

<h2>3. The Defence and Setup</h2>
<p><span class="lead">3.1 Threat model.</span> An attacker plants five records (the released PoisonedRAG poison for one question) in a store that agents retrieve from. One agent, the finder, holds one confirmed planted record; capture is assumed, not detected. Each of three receivers holds a different planted copy under its own identifier, among its own clean records. The attacker does not adapt to the defence.</p>
<p><span class="lead">3.2 Study design.</span> All 200 HotpotQA and MS MARCO released targets (the only released targets not used for calibration) form the incidents; they were used in earlier single-agent tests, so results are labelled "previously used questions, new design". Incidents are split at random into 5 blocks of 40, stratified by dataset, each with its own seeds for which copy is caught, which copies receivers hold, the sham assignment and the order arms run (Figure 2). Every threshold comes from NQ calibration questions 1–20. The protocol, incidents and code were frozen and committed before any sprint answer existed (Appendix E).</p>
<figure><div class="design">
 <div class="seg s1"><span class="hd">Calibration</span><span class="q">NQ 1–20</span><ul><li>all thresholds, each at 5% clean removal</li><li>attention slot offsets; logistic weights</li></ul></div>
 <div class="seg s2"><span class="hd">Sprint blocks 1–5</span><span class="q">HotpotQA + MS MARCO 1–100 · 200 incidents</span><ul><li>40 per block, 20 + 20 by dataset</li><li>own seeds per block</li></ul></div>
 <div class="seg s3"><span class="hd">Per incident</span><span class="q">1 finder · 3 receivers</span><ul><li>attacked and clean context per receiver</li><li>14 arms each; signals computed once</li></ul></div>
 <div class="seg s4"><span class="hd">Frozen before outcomes</span><span class="q">commits b6dd0cd · 2a0b100 · 5f92518</span><ul><li>one-factor check in code</li><li>claims ledger and margins</li></ul></div>
</div></figure>
<p class="cap"><b>Figure 2:</b> Study design.</p>
<p><span class="lead">3.3 Receiver rules.</span> For passage i the receiver computes the NLI entailment e<sub>i</sub> of "The answer to the question Q is C." (DeBERTa-v3) and, where used, the reader's slot-corrected attention z<sub>i</sub> (layer 21, last 8 prompt tokens). Entailment-only arms flag e<sub>i</sub> ≥ 0.00217. Fused arms flag σ(0.938·logit e<sub>i</sub> + 2.347·z<sub>i</sub> + 4.974) ≥ 0.0989. Both thresholds were fixed on calibration data at 5% clean removal. The gate acts only if max<sub>i</sub> e<sub>i</sub> ≥ 0.975. Flagged passages are removed and replaced by the next-ranked ones. The reader is not fine-tuned; the pipeline uses a pretrained NLI model, a fitted logistic combiner and calibrated thresholds.</p>
<table>
<tr><th style="width:21%">Arm</th><th style="width:30%">Finder shares</th><th>Receiver rule</th></tr>
<tr><td>A0 Untreated</td><td>nothing</td><td>none</td></tr>
<tr><td>A1 IDs</td><td>IDs of caught and finder-flagged records</td><td>drop matching IDs</td></tr>
<tr><td>A2 Raw record</td><td>caught record text</td><td>Contriever cosine ≥ 0.666</td></tr>
<tr><td>A3 Claim</td><td>claim signature</td><td>entailment only</td></tr>
<tr><td>A4 Sham</td><td>claim from an unrelated incident</td><td>as A3</td></tr>
<tr><td>A5 Claim + attention</td><td>claim signature</td><td>fused rule</td></tr>
<tr><td>A6 Gated</td><td>claim signature</td><td>A5 behind the gate</td></tr>
<tr><td>A7 No refill</td><td>claim signature</td><td>A5, delete only</td></tr>
<tr><td>A8 Warn</td><td>claim signature</td><td>keep all; prompt warns the claim is planted (A-MemGuard-style)</td></tr>
<tr><td>A9 Forged</td><td>question + <i>true</i> answer</td><td>A5</td></tr>
<tr><td>A10 Bare claim</td><td>claim without question</td><td>A3</td></tr>
<tr><td>B1 Self-check</td><td>nothing</td><td>prompt: ignore passages that seem planted</td></tr>
<tr><td>B2 Stealth Lens</td><td>nothing</td><td>attention-variance filter, δ = 26.2 (authors' code), no refill</td></tr>
<tr><td>B3 Fingerprint</td><td>binary fingerprint of the record (α = 2)</td><td>Hamming ≤ 255 of 768 bits</td></tr>
</table>
<p class="cap"><b>Table 3:</b> Arms. Each runs in an attacked and a clean condition for every receiver. B1–B3 are benchmarks and enter no causal test.</p>
{tiles}
<p><span class="lead">3.4 Analysis.</span> The unit is the incident (mean of its three receivers). Each test is a paired difference, arm minus reference, with a 95% bootstrap interval (B = 2,000) resampling incidents within block, an exact sign test, and per-block estimates. T1 is primary; T1b–T9 form a Holm-corrected secondary family. A claim is supported only if its corrected p &lt; 0.05 and its interval excludes zero. "Similar" requires the interval to lie within ±0.05, and "no clean loss" requires its lower bound above −0.05. A frozen claims ledger lists the only statements the results may support; each test is reported, nulls as nulls. Answers are scored by rules (endorses the false answer; correct, with abstention counted as incorrect) {P}[and cross-checked by …]{E}.</p>

<h2>4. Results</h2>
<div class="box"><b>Placeholder.</b> Results are inserted from <span class="mono">results/sprint/analysis.json</span> once the run completes. Layout: Table 4 (all tests: difference, 95% CI, Holm p, blocks with the same sign, supported or not); Figure 4 (forest plot of T1–T9 by block); Figure 5 (protection vs clean accuracy for all arms and benchmarks); Figure 6 (benchmarks vs A3, A5 and A6).</div>
<p><span class="lead">4.1 Setup check (S0).</span> {P}[C0 vs C1: attacked vs clean endorsement]{E}</p>
<p><span class="lead">4.2 What to share (S1).</span> {P}[T1 primary; T1b; T9; message bytes]{E}</p>
<p><span class="lead">4.3 Content and form (S2).</span> {P}[T2 sham; T8 bare claim]{E}</p>
<p><span class="lead">4.4 Receiver detection (S3).</span> {P}[T3; closed-book strata]{E}</p>
<p><span class="lead">4.5 Neutralisation (S4).</span> {P}[T6 delete vs warn; T5 refill]{E}</p>
<p><span class="lead">4.6 Normal operation (S5).</span> {P}[T4: clean accuracy and protection, with margins]{E}</p>
<p><span class="lead">4.7 Misuse (S6).</span> {P}[T7 forged signature]{E}</p>
<p><span class="lead">4.8 Benchmarks.</span> {P}[B1–B3 vs A3, A5, A6: descriptive differences with intervals; seconds per answer]{E}</p>

<h2>5. Discussion and Limitations</h2>
<p><span class="lead">Interpreting the mechanism.</span> On PoisonedRAG, each planted record is written to assert its question's false answer, which is what a claim check looks for; clean passages about the same question rarely assert it. Attention can flag planted passages the claim check misses. These are properties of the tested records, not of all poisoning: evidence that is true but misapplied [16] would not entail a false claim. {P}[Which of these the results support]{E}</p>
<p><span class="lead">What flatters the results.</span> PoisonedRAG's poisons for one question are near-copies, which makes any record-based matching easier; the attacker does not adapt; one reader is used; agents are serial and homogeneous, with no transport or authentication; capture is assumed.</p>
<p><span class="lead">Limitations.</span> Previously used questions (not fresh); one benchmark; rule-based scoring {P}[human check status]{E}; prior defences beyond the three benchmarks were not run (Table 2). Appendix A gives the full list.</p>

<h2>6. Conclusion</h2>
<p>{P}[Conclusion written from the ledger-supported results only: what sharing a question-scoped claim does for receivers, which parts carry the effect, what it costs on clean questions, how a forged claim harms, and how it compares with the three benchmarks.]{E}</p>

<h3>Acknowledgements</h3>
<p>This work is supported and funded by the Pathfinder Fellowship, a program run by Kairos. The author also expresses gratitude to the Nanyang AI Safety group at Nanyang Technological University (NTU) for their feedback.</p>
<h3>Code and Data</h3>
<p>Code, frozen protocol (docs/SPRINT_PLAN_FINAL.md), manifests and analysis scripts: {P}[repository link]{E}. External data and model weights are not redistributed; PoisonedRAG poison is the authors' release.</p>
<h3>References</h3>
<ol class="refs">
<li>METR (2026). Hugging Face agent incident report. {P}[citation]{E}</li>
<li>Swarm Traces (2026). {P}[citation]{E}</li>
<li>Zou et al. (2025). PoisonedRAG. USENIX Security.</li>
<li>TrustRAG. {P}[citation]{E}</li>
<li>Li, Guo, Xu (2026). CoordGuard. arXiv:2610.24834.</li>
<li>MAPLE-Guard (2026). arXiv:2608.00426.</li>
<li>PerMIT (2026). arXiv:2610.28987.</li>
<li>Weng et al. (2026). AgentAntibody. arXiv:2608.04053.</li>
<li>Ranking Is Not Deciding (2026). arXiv:2610.33849.</li>
<li>GRAD (2026). arXiv:2610.22828.</li>
<li>The Price of Safety (2026). arXiv:2609.22818.</li>
<li>AgentPoison; MINJA. {P}[citations]{E}</li>
<li>RobustRAG. {P}[citation]{E}</li>
<li>Wang et al. (2026). SecureCollaRAG. arXiv:2608.04366.</li>
<li>Copying is easier than recall (2026). arXiv:2601.12075.</li>
<li>Zhang et al. (2026). Lazy Grounding: Attacking Search Agents with Factual Evidence. EMNLP. arXiv:2608.30303.</li>
<li>Choudhary et al. (2026). Through the Stealth Lens: Attention-Aware Defenses Against Poisoning in RAG. ICML. arXiv:2506.04390.</li>
<li>Si et al. (2025). SeCon-RAG. NeurIPS. arXiv:2510.09710.</li>
<li>Eletter et al. (2026). MIRAGE: Defending Long-Form RAG Against Misinformation Pollution. arXiv:2607.05069.</li>
<li>Gill, Isak, Dressman (2026). BinaryShield. IEEE SaTML. arXiv:2509.05608.</li>
<li>Wei et al. (2025). A-MemGuard. arXiv:2510.02373.</li>
<li>Choi et al. (2026). Membrane. arXiv:2606.05743.</li>
<li>Yu et al. (2026). Cordon-MAS. arXiv:2605.26754.</li>
<li>Shaar et al. (2020). That is a Known Lie. ACL.</li>
<li>Costa et al. (2005). Vigilante: End-to-End Containment of Internet Worms. SOSP.</li>
</ol>

<h2 class="pb">Appendix A. Limitations, Dual-Use and Ethical Considerations</h2>
<h3>A.1 Limitations</h3>
<ul>
<li>Previously used questions; one benchmark whose poisons are near-copies; non-adaptive attacker.</li>
<li>One reader (Qwen2.5-7B, 4-bit, local); serial homogeneous agents; no transport, identity or authentication.</li>
<li>Capture is assumed; extraction can fail (a blank claim counts as a failed signature).</li>
<li>Claim checks cannot catch true-but-misapplied evidence [16].</li>
<li>External defences beyond B1–B3 were not run; loose stand-ins would misrepresent them.</li>
<li>Rule-based scoring {P}[and the status of the human/LLM cross-check]{E}.</li>
</ul>
<h3>A.2 Prior work and sprint work</h3>
<p><b>Before the sprint (unpublished, marked preexisting in the README):</b> the AntiVenom detector, its calibration settings, a packaged tool, and exploratory experiments that motivated the hypotheses. <b>During the sprint (6–8 November):</b> the protocol and its amendments, the one-factor experiment and benchmarks, the 200-incident run, all analyses in Section 4, and this report.</p>
<h3>A.3 Dual use and ethics</h3>
<p>Defence-only; all poison is the published PoisonedRAG release, and no attack text was generated. T7 measures how a forged claim could delete good evidence; deployments should authenticate claims and gate their use. We report only aggregate patterns of what escapes detection.</p>

<h2>Appendix B. Calibration Details</h2>
<p>All values from NQ 1–20: entailment-only threshold 0.00217 (5% clean removal; 95% poison recall on calibration); fused logistic weights (0.938, 2.347, 4.974) and threshold 0.0989; slot offsets [0.596, −0.097, −0.214, −0.337, 0.235, 0.135, −0.432, −0.323, −0.187, 0.624]; gate 0.975; cosine 0.666; fingerprint τ = 255 of 768 bits (α = 2, 5% clean removal); Stealth Lens δ = 26.207 (the released code's default).</p>

<h2>Appendix C. Protocol History</h2>
<p>v1 frozen (b6dd0cd, 11:50, 8 Nov). Amendment 2, analysis-only, adds T9 and margins (2a0b100, 12:09). Run stopped after 3 of 200 incidents to add benchmarks after an external literature audit; no outcome was viewed (results/sprint/STOPPED.md). v2 frozen with the same incidents and seeds (5f92518, 12:42); the original 12 arms' decision code was unchanged, verified on 36,000 synthetic cases, and the 3 completed incidents were resumed, not rerun.</p>

<h2>Appendix E. Verification</h2>
<p>Every number is read from the run's analysis file; figures are regenerated by scripts in the repository. Manifests record SHA-256 hashes of the protocol, incidents, code, data and calibration files; the runner refuses to start if any differs.</p>

<h3>LLM Usage Statement</h3>
<p>LLM coding assistants were used to write experiment and analysis code, run analyses, draft text and produce figures. All results come from logged runs; the author is responsible for every claim.</p>
</body></html>'''
open("antivenom_report.html","w").write(head+body)
print("written")
