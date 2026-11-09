# ANTIVENOM v6: a receptor-level, cocktail defence against knowledge poisoning

*26 Oct 2026. Replaces the claim-signature-only plan in SOTA_GAP.md §3. It is built on (a) E01/E02, (b) verified antivenom biology, and (c) a verified sweep of activation-level defences.*

## 1. The biology we use, verified against primary sources

| Fact | Source | What it means for us |
|---|---|---|
| Broadly neutralising antibodies from a hyperimmune donor bind **conserved epitopes** on long and short neurotoxins. Crystal structures show they **mimic the toxin–receptor (nAChR) interface**. | Glanville et al., *Cell* 188:3117–3134 (2025) | A toxin can mutate its surface but not the part that docks onto its receptor. **Breadth comes from targeting what the toxin must bind.** |
| Two antibodies plus **varespladib** (a small-molecule PLA2 inhibitor) rescued mice against all 19 WHO elapid species tested, with complete protection against most. | Same | **A cocktail of complementary mechanisms**: binding agents plus an inhibitor of the toxin's action. |
| The donor's breadth came from **years of exposure to many venoms**, not one. | Same | Breadth needs a **library** of exposures. |
| Fast-cleared Fab let venom rebound: late recurrence 29.7% vs 5–10% for longer-lived F(ab')2. Venom rebounded in 4 of 6 Fab patients. | Randomised pit-viper trial (ECU repository; PubMed 23948058) | **Short-lived treatment invites recurrence.** You need a long-acting component or maintenance dosing. |

## 2. The receptor-mimicry principle for knowledge poisoning

The attacker controls the poison's *surface*: style, wording, how passages cluster. DnD (2609.27090) shows this. But for any poison to work, the reader must **adopt an answer from that context passage**. That adoption runs through a specific internal mechanism, and the attacker cannot avoid engaging it.

Mechanistic evidence that this "receptor" exists and is low-dimensional:
- **2610.20067** (Oct 2026, verified): the choice between context and parametric knowledge is "linearly represented and can be controlled along a single direction". The direction transfers across formats and datasets, and to RAG and memory tasks.
- **2601.12075** (EMNLP 2026, verified): **copying is easier to induce than recall**. Inducing copying is robust to position; restoring recall is fragile and tied to **object tokens**. This is consistent with the side chat's single last-token steering vector curing 0 of 6.
- **CounterSteer** (2609.36570, verified): a library-fitted residual direction, subtracted from untrusted-span tokens at prefill, cuts indirect-injection ASR to 0.00–0.17 with 93–100% benign utility. It also resists white-box attacks on the vector (2 of 52 episodes compromised).

**The gap no one has closed** (sweep, plus our own reading of CounterSteer's stated limits):
- CounterSteer targets *instruction takeover*. Its authors report that attacker-chosen content inside otherwise legitimate actions (parameter manipulation) was only partly resisted (13 of 18), and was **not linearly readable before generation**.
- **False-claim adoption from poisoned knowledge is exactly that kind of content-level hijack.** In our sweeps (alphaXiv and the web, to 26 Oct 2026) we found no paper that fits a mechanism-level defence for it from a library of released poisons, or tests it under retrieval crowding and diverse-style poison.

## 3. The cocktail: three components, one per biological role

### C1. Broadly neutralising "receptor antagonist": span-gated adoption suppression (inference-time; the Fab analogue)
- **Fit** a direction for "answer adopted from this passage" from a **venom library**: many released PoisonedRAG targets, all three datasets, varied framings.
- **Contrast** cases where the reader adopts an injected false answer against matched cases where it answers from clean evidence.
- **Validate before deploying**, following CounterSteer's practice:
  - check the direction causally on held-out targets and framings;
  - pick layers by separation, not guesswork. CounterSteer used 12/16/20 on Llama-8B, and the optimum can move by up to 17 layers under perturbation (2606.07696);
  - prefer object-token sites, per 2601.12075.
- **Apply it only inside flagged passage spans**, not uniformly over all retrieved text. This is the new element compared with CounterSteer, and it is what should protect legitimate RAG utility, which uniform "trust parametric memory" steering destroys.
- **Flagging is localisation-free with respect to style.** Two signals, used together:
  - a document-level attention-collapse signal (D-SCAN, 2608.06947, which has released code);
  - entailment of a captured claim signature (SOTA_GAP §3).
- **Paraspecific test:** fit on NQ targets, evaluate on held-out NQ targets, then on HotpotQA and MS-MARCO. This is the analogue of testing an antivenom against snake species it was never raised against.

### C2. Long-acting component: bound counter-records (persistent; the F(ab')2 analogue)
- Counter-records from E02 are attached to any record that entails the captured claim, so they no longer compete for top-k slots.
- They persist in memory and cover re-reads, the analogue of venom recurrence.
- **E02 is consistent with the active ingredient working:** when an antibody was in the top-5 alongside 2–3 poisons, endorsement was 0.12–0.15, vs 1.00 without one. This split is observational: targets where antibodies reached the context may be easier.

### C3. Doubt-passage neutraliser (the varespladib analogue: targets a different "toxin class")
- DnD's doubt passage never asserts the false claim. Instead it suppresses the correct answer. So it attacks the *recall* side of the mechanism, which 2601.12075 shows is the fragile side.
- **Measure** whether C1's direction also catches suppression of recall. If it doesn't, fit a second direction for "evidence being doubted", as a separate component, just as varespladib covers a toxin class the antibodies miss.

## 4. Pharmacology-grade measurement

- **Dose–response:** Hill fits of endorsement against steering strength (C1) and counter-record titer (C2). Report the effective dose as EC50.
- **Therapeutic index:** TI = (dose that costs clean accuracy) / EC50. Report clean accuracy, as CoordGuard does.
- **Specificity audit:** off-target KL divergence on unrelated prompts (SteerCheck-style), so reviewers can't call it a capability lobotomy.
- **Recurrence:**
  - C1 alone vs C1 + C2 under re-reads and later sessions. This is the Fab vs F(ab')2 trial, with matched budgets.
  - A cheap framed comparison we did not find in prior work (sweep verdict).
- **Detection ≠ resistance:** report endorsement, not just detection AUROC (2608.17153).

## 5. Baselines that must be beaten

- **Released code:**
  - TrustRAG, RobustRAG, ReliabilityRAG, InstructRAG, SeCon-RAG, RAGDefender;
  - the 2610.20067 direction ("just steer toward parametric");
  - CounterSteer's recipe re-fit on our task;
  - CAD/AdaCAD.
- **Re-implemented:** CoordGuard (2610.24834), which has no code link, compared at matched clean-accuracy cost with count-matched controls.
- **Our own E02 arms:** near-neighbour deletion and anchored antibodies.

## 6. Experiments, in order (each gates the next)

| ID | Question | Pass criterion |
|---|---|---|
| E09 | **Oracle upper bound:** if attention from answer positions into the *true* poison spans is suppressed, does the reader's preference return to the correct answer? | If even the oracle can't cure, C1 is dead; stop. |
| E10 | Fit C1 from a venom library (NQ targets 1–50); causal check on targets 51–100 | Held-out endorsement drops significantly vs attack; clean accuracy within CI |
| E11 | Real flagging (attention collapse + claim entailment) replaces oracle spans | Most of E09's gain retained |
| E12 | Paraspecific: NQ-fit vector on HotpotQA and MS-MARCO; second and third readers | Transfer without refitting |
| E13 | Full cocktail C1 + C2 (+ C3) vs all baselines; recurrence trial; TI and specificity | Beats CoordGuard on the ASR / clean-accuracy frontier |
| E14 | Diverse poison: decision pending (SOTA_GAP §4) | Gain holds on diverse poison |
| E15 | Swarm: compartmentalised readers sharing fitted antagonists and signatures fleet-wide (DIS-style broker); independence from retrieval-ID overlap | Herd protection with fewer captures |

## 7. Scope and honesty notes

- **Defence-only.** Fitting uses released poisons and the reader's own activations. No new attack content is generated.
  - The adaptive attack reviewers expect (optimising poison against the deployed vector) is still an open user decision.
- **Engineering risk:** none of the released steering code is MLX. Plan to fit in PyTorch or port the hooks.
- **Known failure modes to pre-empt:**
  - non-identifiable directions (2602.06801);
  - error-correcting basins that absorb small edits (2610.04183);
  - corrupted contrast sets (2603.03206).
- **Unverified:** pre-2026 citations quoted from memory by the sweep (retrieval heads, TaskTracker, Attention Tracker, Lookback Lens, PH3, ITI/RepE/CAA, CAD/AdaCAD). Check each before citing. D-SCAN's numbers were read only from its abstract.
