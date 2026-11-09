# ANTIVENOM: evidence and continuation status

**3 November 2026 completion update:** the original suite and supplemental E45
run have finished, with all required integrity outputs passed and reader-weight
hashes unchanged. The [final automated evidence assessment](EVIDENCE_REPORT.md)
supersedes the scientific status below. Shared OR clean accuracy is 33.33%
versus 52.50% untreated and 50.83% cosine; the joint swarm claim remains
inconclusive. MemForm shows a local attack benefit over cosine. Human blind
scoring/interpretability are deferred and powered fresh confirmation remains
unestablished. All pre-sprint work must be disclosed as preexisting hackathon
work. The following 29 October handoff is retained as history.

Updated 29 October 2026. This is the current handoff; historical designs and
the original notebook entries are retained as records, not current claims.
The subsequently authorized remaining batch is tracked in
`docs/REMAINING_RUNS_STATUS.md` and `results/remaining_queue_status.json`.

## Where the project actually stopped

E29 finished both confirmatory datasets on 28 October: 50 HotpotQA and 50
MS-MARCO targets. E30 attack gating finished the same day. E31 single-poison
detection and E32 backfill placebo finished on 29 October, with no notebook
entries or analyses tying them together. No experiment was running when this
continuation began. The README was empty and Git had no commits; all project
files were untracked. There is no commit history from which to recover an
earlier state or independently verify the claimed freeze times.

The functioning research pipeline is a single-reader RAG defence: extract a
claim from one known poisoned sample, score retrieved passages with NLI and
reader attention, then remove flagged passages and refill from retrieval.
The older structural/swarm and receptor-steering designs are research
proposals or early branches, not the implemented best-performing pipeline.

## What the existing evidence supports

E29, pooled 100 tier-2 targets, Qwen reader:

| Arm | Endorses target answer | Rule-correct under attack | Rule-correct on clean context |
|---|---:|---:|---:|
| No defence | 0.76 | 0.19 | 0.61 |
| v1 delete + backfill | 0.12 | 0.54 | 0.35 |
| v2 delete + backfill | 0.07 | 0.53 | 0.39 |
| CoordGuard AF + refill | 0.05 | 0.47 | 0.37 |
| TrustRAG | 0.12 | 0.53 | not run |

Source: `results/rescored/summaries/e29_confirmatory.txt` and raw E29 JSONL.
These are benchmark-specific comparisons to the local baseline implementations,
not a new verification of the wider literature or current state of the art.

The defence substantially reduces endorsement on these released poisons.
Count-matched controls show that the detector matters. Primary superiority
was not demonstrated. Nonsignificant differences do not establish parity,
equivalence or non-inferiority.

At deployed thresholds, v1/v2 retain more clean passages, but catch fewer
poisons than CoordGuard. At CoordGuard's 99.74% recall, the continuous v2
score removes 40.2% of clean passages versus CoordGuard's 20.6%.

There is a structural source of false alarms in v1: attention is z-scored
within each context and flagged at z >= 0. At least one passage must satisfy
that rule, including in an entirely clean context. OR therefore cannot choose
to leave a clean context untouched without a separate gate. All 100 E29 clean
contexts have v1 flags (mean 3.79 passages). After deletion and backfill, 18 of
the 64 contexts initially containing the gold-answer token sequence lose all
such occurrences. This token test is a proxy, not proof of causal evidence loss.

### Corrections to the previous handoff

- Historical E29 claim 1 uses **v2 continuous avidity scores**, although v1 OR
  is the pre-registered primary detector. Frozen v1 is binary; its deployed
  recall is lower than CoordGuard's, and no continuous v1 ranking was frozen.
  This comparison cannot be presented as confirmation of the v1 primary.
- E29 applies Holm correction to **two tests only**. The endorsement
  p=0.039 is raw. A conservative four-comparison Holm sensitivity gives
  p=0.156 for that comparison. CoordGuard's lower endorsement point estimate
  remains, but the claimed multiplicity-corrected significance does not.
- E35 recomputes matched recall with discrete attainable thresholds and adds
  the above sensitivity analysis. Its bootstrap sign-tail calculation follows
  the historical method; it is not a newly validated null-hypothesis test.
- All latest frozen hashes match. The hash log contains an older v2-document
  hash followed by a superseding version; that is not a current mismatch.
- E29's 1,300 stored responses reproduce the frozen scoring rules. However,
  some responses count as both correct and endorsing the false answer. The
  overlap cases are exported for review in `data/validation/e29_overlap_review.csv`.
  Agreement with the code is not human validation. Both existing blind label
  sheets have **zero completed rows** (152 and 302 rows respectively).

Source: `analysis/e35_confirmatory_audit.py` and
`results/rescored/summaries/e35_confirmatory_audit.txt`.

### Targeted baseline-source check

I checked the [CoordGuard paper, sections 3.2–3.3 and 4.1](https://arxiv.org/html/2610.24834v1)
against the frozen local implementation. Query-weighted affinity, median/MAD
normalization, graph threshold 1.0, components of size at least two, and the
density × query-relevance × log-size selector agree. The local e5 input
prefixes remain an implementation assumption; I found no prefix prescription
in the paper text.

The paper already includes a benign-calibrated gate and compares relevance
with random backfill (appendix A, table 7). Therefore generic gating and
showing that relevant refill helps are not new contributions by themselves.
Our captured-claim NLI gate and different controls can still be evaluated as
specific variants. The paper's primary setting uses top-5 and three injected
passages; ours uses top-10 and five released passages. Its headline numbers
cannot be substituted for the local paired comparison.

## Results recovered after E29

### E30: attack gate, exploratory

Threshold 0.97490412 was chosen on NQ 1–20. A defence fires if any retrieved
passage entails the captured claim above that threshold. On the already used
tier-2 targets, it fires on 91% of attacked contexts and 4% of clean contexts.

| Arm | Gated endorsement under attack | Gated clean-context accuracy |
|---|---:|---:|
| v1 | 0.17 | 0.61 |
| v2 | 0.14 | 0.61 |
| CoordGuard + refill | 0.12 | 0.61 |

This exchanges some protection for clean utility; it does not preserve the
ungated endorsement rates. It assumes a trusted captured sample/signature is
available even when the current retrieved context is clean. Excluding the
captured passage from the gate raises pooled endorsement to 0.19/0.20/0.18.
The CoordGuard row uses our NLI gate on its AF+refill answers; it is not the
paper's original benign-calibrated geometry gate, which has not been evaluated
on these targets.
The original JSON stores only gate rates for development/tier 1; the tier-2
answer summary survives in `results/rescored/summaries/e30_attack_gate.txt`.
Per-target clean NLI scores were not persisted, so a paired uncertainty
analysis of the gate would require a new cached CPU scoring run. This is not
confirmation: tier 2 was already inspected before the gate was proposed.

### E31: single non-captured poison, development

Completed 320 contexts: 80 NQ targets × four released poisons, excluding
poison[0] from the context and using its stored extracted claim.

| Detector | Poison recall | Clean passages removed |
|---|---:|---:|
| Entailment, tau=0.01 | 87.19% | 2.64% |
| CoordGuard AF | 95.00% | 71.63% |

The proposed singleton blind spot is **not observed**. CoordGuard components
can contain one poison together with clean passages. Its large removal cost
here explains why component size >=2 does not imply singleton immunity.
These are different operating points, not a matched-recall superiority test.
Only aggregates and progress logs were saved, so 320 must not be treated as
320 independent targets or used for naive passage-level significance tests.

Source: `results/e31_single_poison.json`, `experiments/e31_single_poison.py`.

### E32: M3 backfill placebo, development

All 80 NQ development targets finished. On the 75 targets also present in E12,
all **150** shared true-backfill/deletion responses are byte-identical.

| Arm | Rule-correct | Endorses target answer |
|---|---:|---:|
| True backfill appended after survivors | 60.00% | 10.00% |
| Unrelated real passages appended | 48.75% | 7.50% |
| Deletion alone | 46.25% | 7.50% |

Paired correctness advantage: true vs placebo +11.25 points, bootstrap 95%
CI [2.5, 20.0], raw McNemar p=0.0225, six-comparison Holm p=0.1123.
True vs deletion +13.75 points, CI [6.25, 22.5], Holm p=0.0205.
Placebo vs deletion is not distinguishable at this sample size. Evidence
content is a plausible explanation, but the true-vs-placebo result does not
survive this exploratory multiplicity adjustment.
No placebo document occurs in the receiver's clean top-100; three placebo
contexts contain the gold-answer token sequence, and none contains the target
answer token sequence. Token overlap alone does not establish relevance.

Source: `analysis/e32_e34_summary.py`, `results/e32_e34_summary.json`.

## Work added by this continuation

### E33: score-aware selection on stored contexts, completed

NQ development, target-level averages; captured poison excluded. Select the
hardest unseen released poison per target using the detector's own scores.

| Detector | Original recall | Hardest-one recall | Targets with a miss |
|---|---:|---:|---:|
| Entailment | 87.2% | 76.3% | 19/80 |
| Attention | 81.6% | 36.3% | 51/80 |
| OR | 97.8% | 91.3% | 7/80 |
| Calibration-fitted avidity | 99.1% | 96.3% | 3/80 |
| CoordGuard AF | 99.7% | 98.8% | 1/80 |

Operating points differ; this is not a superiority ranking at matched clean
cost. Worst captured sample plus hardest-one selection reduces entailment
recall to 47.5% and OR to 82.5% (14/80 targets with a missed poison). Thus a
high average worst-capture recall does not imply all poisons are caught.

Scores come from the original full contexts. Attention and graph geometry
would change after rebuilding a reduced context. These results measure
conditional detection vulnerability, **not end-to-end adaptive attack success**.
The jointly rebuilt prefix-free/low-occupancy/worst-capture experiment is
still missing; these stored scores cannot complete it.

Source: `analysis/e33_score_aware.py`, `results/e33_score_aware_targets.jsonl`,
`results/rescored/summaries/e33_score_aware.txt`.

### E34: original passage-slot backfill, completed

Protocol and input hashes were saved before generation. It reproduced one
existing E32 response before adding two arms: true and placebo replacements
placed into the original flagged passage slots. Unflagged passage slots stay
fixed. Token positions, token counts and passage lengths vary.

All 80 targets completed; all 160 new responses passed score consistency
checks. Independent checks also verify original passage identities, exact
flags, donor identity, replacement counts, and all manifest hashes.

| Arm | Rule-correct | Endorses target answer |
|---|---:|---:|
| True backfill in original passage slots | 55.00% | 11.25% |
| Placebo backfill in original passage slots | 51.25% | 5.00% |
| Deletion alone (E32 comparator) | 46.25% | 7.50% |

True vs placebo correctness: +3.75 points, paired bootstrap 95% CI
[-6.25, 13.75], raw McNemar p=0.6291, Holm p=1.0. True vs deletion:
+8.75 points, CI [0.0, 17.5], raw p=0.0923, Holm p=0.4614.
Neither correctness nor endorsement comparison in this six-test family
survives adjustment. Three released poison passages re-enter through the
unscreened true-backfill pool; none enters the placebo replacements.

The true-vs-placebo correctness gap falls from 11.25 points with appended
backfill to 3.75 points in original slots. This does not establish a causal
placement effect: the direct paired placement comparisons are not significant
either (true accuracy raw p=0.2891; placebo accuracy p=0.7266). It does show
that the evidence-content explanation is not robustly established by these
controls. It also does not prove that refill is merely padding.

Outputs: `results/e34_fixed_slots_nq_k10.jsonl`,
`results/e34_integrity.txt`, `results/e32_e34_summary.json`, and
`results/rescored/summaries/e32_e34_summary.txt`. The inference job exited
 successfully. The subsequent E36+ batch has its own queue and status files.

## Remaining work and decisions

1. Independently label the frozen blind sheet with two labellers. Do not
   silently replace human validation with another model or the scoring rules.
2. Any gate confirmation needs genuinely new questions and a frozen protocol;
   reusing the 100 E29 targets would remain exploratory.
3. Llama/Mistral have NQ development transfer results (E22), **not tier-2
   confirmation**. Other readers/retrievers, a rebuilt composite stress test,
   diverse released poison, and an actual swarm remain uncompleted branches.
4. A targeted release check found no dataset link in the current
   [DnD paper](https://arxiv.org/html/2609.27090v1); the
   [ProvenanceGuard repository](https://github.com/nv262-lab/ProvenanceGuard)
   describes sample data. The DataPort DOI could not be fetched by the web
   tool (robots restriction). This does not prove no release exists elsewhere.
   The diverse-poison evidence gap remains. No new attack generation or
   contact with authors was attempted.

The defensible research narrative is complementary detection signals,
failure modes under capture/position/occupancy changes, and the utility cost
of filtering with an exploratory gate remedy. Novel receptor mechanisms,
swarm protection, broad robustness to diverse poison, human-validated
headlines, and a state-of-the-art win are not established by these runs.
