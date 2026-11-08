# Amendment 1 to the weekend swarm protocol (DRAFT, 8 November 2026, 11:15 SGT)

Status: **draft for Daniel's approval. No sprint outcome has been generated or seen.** On approval, this file, the incident list, the seeds and all thresholds are hashed into a frozen manifest and committed before the first model call.

## Why an amendment is needed
1. **Fresh incidents are unavailable.** PoisonedRAG released exactly 100 targets per dataset (NQ, HotpotQA, MS MARCO; 5 poisons each), verified programmatically on 8 November. All 300 are already used: NQ 1–100 (calibration and development), HotpotQA and MS MARCO 1–100 (confirmatory tiers 1 and 2). We generate no attack text, so no new poison can be made. The protocol's "fresh only" rule cannot be met.
2. **The design is replaced** by a one-factor-at-a-time ladder with replicate blocks, as Daniel asked.
3. **External baselines.** SecureCollaRAG and MAPLE-Guard are not implemented yet. SecureCollaRAG needs its repository cloned and a graph network trained on poison data, and MAPLE-Guard needs a port. See decision D3.

## Incidents (decision D1)
- **Proposed:** HotpotQA and MS MARCO targets 1–100 (200 incidents). The swarm design has never been run on these questions: E42/E45 used NQ 21–100 only. They were used for single-agent tests, so results are labelled **"previously used questions, new design"**, not fresh confirmation.
- **Alternative:** tier 2 only (HotpotQA and MS MARCO 51–100, 100 incidents), which halves the runtime.
- Calibration questions (NQ 1–20) and the E42 swarm questions (NQ 21–100) are excluded. Disjointness is checked in code.

## Replicate blocks
- K = 5 blocks. Incidents are assigned to blocks at random, stratified by dataset, with a recorded seed. That gives 40 incidents per block, or 20 with the alternative.
- **Without new poison, each block's randomness comes from:**
  - its own seed for which released copy the finder catches;
  - its own seed for which remaining copies each of the 3 receivers holds, under distinct identifiers;
  - its own seed for the order in which arms run.
- Greedy decoding is deterministic, so reruns are not replicates. Blocks are the replicates.

## Arms
Each arm runs in two conditions, attacked and clean, with 3 receivers per incident.

| Arm | Payload shared | Receiver filter |
|---|---|---|
| A0 Untreated | none | none |
| A1 IDs | record IDs of the caught record | drop matching IDs |
| A2 Raw sample | the caught record's text | cosine ≥ calibrated threshold |
| A3 Signature | claim signature | signal set **entailment only**: flag if e ≥ 0.00217 (calibrated to 5% clean removal on NQ 1–20); delete and refill |
| A4 Sham signature | a claim from an unrelated incident, same format | identical rule to A3 |
| A5 Signature + attention | claim signature | signal set **entailment + attention**: frozen v2 rule s = σ(0.938·logit e + 2.347·z + 4.974) ≥ 0.0989 (also 5% clean removal on NQ 1–20); delete and refill |
| A6 Signature + attention + gate | claim signature | as A5, acting only if max entailment ≥ 0.975 |

C0 is A0-clean and C1 is A0-attacked.

## Factor table
In every test, everything not named is identical to the reference arm: the same incidents, poisons, receivers and contexts; the Qwen2.5-7B reader on MLX; the prompt; 48-token greedy decoding; Contriever top-10 retrieval; and the calibration thresholds.

| Test | Assumption | Only factor changed | Reference |
|---|---|---|---|
| C0 vs C1 | The attack works (manipulation check, not a claim) | attack on or off | C0 |
| **T1 (primary)** | Sharing the claim signature protects receivers better than sharing IDs | payload: IDs or signature (receiver applies the matching filter) | A1 |
| T1b | Sharing the raw record protects better than sharing IDs | payload: IDs or raw sample | A1 |
| T2 | The signature's content matters, not just that something was shared | real signature or sham | A4 |
| T3 | Attention adds protection on top of the signature | signal set: entailment only, or entailment + attention (each rule calibrated by the same procedure to the same 5% clean budget) | A3 |
| T4 | The gate restores clean accuracy without losing protection | gate off or on | A5 |

**A note on T1.** The payload and its matching filter change together, because an ID cannot be checked by entailment. So T1 tests what is shared, together with its natural receiver rule. This is stated as the factor; it is not two factors hidden as one.

**A note on T3.** Two earlier drafts were not single-factor. The first changed the signal and an arbitrary threshold; the second set attention to 0 inside the fitted formula, which a synthetic check showed flags every passage (z = 0 is an average passage, which the fitted model treats as risky). The factor is now the signal set, with the calibration procedure (same data, same 5% clean-removal budget) held fixed. This was found and fixed on synthetic inputs before any sprint data was touched.

## Safeguards against last sprint's feedback
The feedback was: *"The two studies change roles, rewards, reviewer and prompt at once, so they can't support five general claims. Test one assumption, change one factor at a time, and run more than one group per arm."*

| Feedback point | Safeguard in this run |
|---|---|
| Several things changed at once | Each arm is a config object. Before any model call, code asserts that each test's arm differs from its reference in **exactly one named field**, and aborts otherwise. The diff is written to the manifest. |
| Claims broader than the evidence | A **claims ledger** (below) is frozen with this file. The report may state only claims backed by one ledger test, in the ledger's wording. Everything else is labelled background or exploratory. |
| One group per arm | K = 5 blocks with their own questions and seeds. Results are reported per block and pooled; a claim needs the pooled interval to exclude zero after Holm correction, and the block estimates are shown, signs included. |
| Hidden confounds | Paired design (identical incidents, poisons, receivers, contexts); randomised, interleaved arm order with a recorded seed; frozen calibration thresholds; deterministic decoding. A reference-arm rerun at the end checks for drift. |
| Selective reporting | Every test is reported, including nulls, and with the pre-specified primary (T1). |

## Claims ledger (frozen; the only claims the report may make from this run)
| Claim, if supported | Test | Endpoint | Stated as null if |
|---|---|---|---|
| The attack works in this setup | C0 vs C1 | endorsement | no difference (then the run is uninformative) |
| Sharing the claim signature protects receivers more than sharing record IDs | T1 | attacked endorsement | pooled interval includes 0 |
| Sharing the raw record protects more than sharing IDs | T1b | attacked endorsement | pooled interval includes 0 |
| Protection comes from the signature's content, not from sharing anything | T2 | attacked endorsement | pooled interval includes 0 |
| The attention signal adds protection beyond the signature | T3 | attacked endorsement | pooled interval includes 0 |
| The gate restores clean accuracy, at a stated protection cost | T4 | clean accuracy and attacked endorsement, both reported | clean-accuracy interval includes 0 |

No claim about AntiVenom versus SecureCollaRAG, MAPLE-Guard, CoordGuard or TrustRAG comes from this run. Those comparisons change many factors and are reported as benchmarks only.

## Endpoints and analysis
- **Endpoints:** (i) receiver endorsement of the false answer, attacked condition; (ii) receiver accuracy, clean condition. T4 is judged on both; all others on (i), with (ii) reported.
- **Unit and estimates:** the incident, averaging its 3 receivers. Paired differences per test are reported per block and pooled. Intervals are 95% bootstrap intervals clustered by question within block (B = 2,000).
- **Corrections and checks:** Holm correction over T1–T4. T1 is primary; T1b and T2–T4 are secondary. An exact paired sign test is a cross-check. Every result is reported, nulls as nulls.
- **Status of scores:** rule scores are labelled PROVISIONAL. A blinded two-rater sheet is exported, with arm labels stripped, rows shuffled with a recorded seed, the key stored separately, and Cohen's kappa ready to compute.

## Power check (prior: E42 development effects)
- **T1:** IDs 62.5% vs signature 9.2% (difference 53 points). Any n ≥ 10 incidents gives over 99% power.
- **T3:** 9.2% vs 0.4% (about 9 points, discordance about 10%). About 100 incidents gives about 80% power.
- **T4:** about 7 points of protection given up for about 25 points of clean accuracy. The clean-accuracy side is well powered at 100 incidents; the protection side needs about 150–200.
- **Assumptions:** E42 effects transfer to HotpotQA and MS MARCO, and receivers within an incident are averaged. With 200 incidents, T1–T3 are well powered and T4 is adequate. With 100, T4's protection side is underpowered.

## Size and runtime
Estimated from logged E42/E45 timings (about 3.2 s per answer, about 7 s per filtering pass).

| Option | Incidents | Receiver contexts | Answer calls (upper bound) | Estimated runtime |
|---|---|---|---|---|
| D1 proposed | 200 | 1,200 | 8,400 | about 10 h (about 6–7 h with deduplication) |
| D1 alternative | 100 | 600 | 4,200 | about 5 h (about 3–4 h) |

**Deduplication:** when two arms leave an identical context, the deterministic answer is reused. Signals are computed once per context. Externals, if run, add about 30% for MAPLE-Guard. SecureCollaRAG adds more, plus training.

## Added tests (approved 8 November: "proceed all")
| Test | Assumption | Only factor changed | Reference |
|---|---|---|---|
| T5 | Refilling with next-ranked evidence restores accuracy beyond deleting alone | refill on or off | A5 |
| T6 | Removing poison protects more than warning the reader about the claim | neutralise: delete flagged, or keep all and warn | A5 |
| T7 | A forged signature (true answer as claim) deletes good evidence and costs accuracy | signature source: real or forged | A5 |
| T8 | The signature needs the question, not just the claim | hypothesis: question + claim, or claim only | A3 |

Elicitations: a closed-book answer per incident (a reader-only covariate for stratifying T1 and T3), and a self-check monitor benchmark (B1). B1 is not part of any test. The claims ledger extends to T5–T8 in the same form. All 200 incidents are used, in 5 blocks of 40, run block by block so that completed blocks are complete replicates. SecureCollaRAG and MAPLE-Guard are not run (time, and SecureCollaRAG needs training on poison data); this is stated as a limitation.

## Decisions needed from Daniel
- **D1** Incidents: 200 (HotpotQA and MS MARCO 1–100), or 100 (tier 2 only).
- **D2** Accept the blocks as defined (seeded catch and receiver assignment, no new poison).
- **D3** External benchmarks: (a) skip both and state why; (b) MAPLE-Guard retrieval gate only, after about 1 hour of porting; or (c) both, which needs permission to clone SecureCollaRAG's repository and adds hours of training. Recommended: (a) or (b).
- **D4** Endpoint for the report: rule scores labelled provisional, with human scores added if two raters finish before the deadline.
