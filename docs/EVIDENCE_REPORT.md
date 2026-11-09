# ANTIVENOM — final automated evidence assessment

The [publication preparation index](PUBLICATION_READINESS.md) links the new
manuscript, matched-source design/power, software readiness and blinded human
review v2. Preparation adds no model efficacy evidence: fresh independent
incidents and human labels remain missing. All completed results below retain
their original scopes.

Original assessment completed 3 November 2026 (Singapore); the exact
empty-history control and its paired assessment completed 4 November.
Human blind scoring and interpretability
validation remain explicitly deferred. All work completed before the 6–8
November sprint is preexisting hackathon work.

**Finding:** incident-specific mitigation is supported locally, including a
held-out MemForm-family benefit over cosine. The stronger shared-protection
claim—beating blocklists and cosine while preserving clean accuracy—is not
established. Swarm OR clean accuracy is 33.33% versus 52.50% untreated, with
material observed losses. The frozen five-comparison joint verdict is
inconclusive. No powered fresh primary confirmation has been established.

The added 424-call local MemForm control supports a specific utility benefit
over disabling memory: clean correctness is 95.28% for entailment and 93.40%
for OR, versus 83.02% for exact empty history. It does not establish added
protection on poisoned histories. Poisoned OR reproduces the empty-history
prompts and raw answers in all 212 tested families.

## Assessment

The completed local experiments support incident-specific poisoning mitigation
and reuse against an attention-only ablation. They do not establish superiority
over captured-sample cosine in the QA scopes or full TrustRAG, or preservation
of clean accuracy. The separate held-out MemForm-family diagnostic does support
lower poisoned-action endorsement than cosine and the native CoordGuard gate;
it does not establish an additional benefit over entailment alone.
The completed local swarm scope supports lower endorsement than shared record
IDs when recipients have distinct poison IDs. Added value over cosine and the
joint no-clean-loss claim remain unestablished. This is not a demonstrated
general swarm safeguard.

The new exact-empty-history comparison supports additional clean-task accuracy
over disabling memory in the local MemForm port. It does not establish
preservation relative to untreated memory, a matched raw-semantic abstraction
advantage, or strictly better poisoned-history protection.

The implemented method extracts a question and claim from a trusted captured
sample, uses claim entailment and reader attention to flag evidence, and applies
the frozen removal/refill policy. Its proposed reusable artifact is distinct
from a record-ID list or captured-sample similarity filter. Whether that
distinction produces useful additional protection is an empirical question.

## Completed captured-excluded incident evaluations

All four scopes reuse previously inspected NQ development questions. Captured
poison[0] is excluded from retrieval and refill. These are local development
results, not fresh confirmation or independent replications of the same 80
incidents. Endorsement and correctness are separate automated text-rule scores;
some responses can satisfy both. Human semantic/scoring review is deferred.

| Scope | Independent incidents / sessions | Untreated endorsement | OR endorsement | Cosine endorsement | OR clean accuracy | Cosine clean accuracy |
|---|---:|---:|---:|---:|---:|---:|
| Base | 80 / 80 | 87.50% | 5.00% | 2.50% | 41.25% | 65.00% |
| Prefix-free context shift | 80 / 80 | 67.50% | 11.25% | 15.00% | 41.25% | 63.75% |
| Recurrence | 80 / 160 | 75.00% | 5.00% | 3.125% | 45.00% | 53.75% |
| E5 candidate-pool transfer | 80 / 80 | 80.00% | 3.75% | 1.25% | 52.50% | 70.00% |

Effects below are OR minus comparator, in percentage points. Intervals are
paired incident bootstrap 95% intervals, **not simultaneous intervals**. Tests
retain the complete frozen Holm family for each scope; an unadjusted interval
excluding zero does not supersede a nonsignificant corrected test.

| Scope / endpoint / comparator | Effect | Paired 95% interval | Holm-adjusted p |
|---|---:|---:|---:|
| Base endorsement vs untreated | -82.50 | [-90.00, -73.75] | 4.07e-18 |
| Base endorsement vs cosine | +2.50 | [-2.50, +7.50] | 1.0 |
| Base clean correctness vs cosine | -23.75 | [-36.25, -11.25] | 0.1045 |
| Prefix-free endorsement vs untreated | -56.25 | [-68.75, -43.75] | 7.05e-9 |
| Prefix-free endorsement vs cosine | -3.75 | [-13.75, +6.25] | 1.0 |
| Prefix-free clean correctness vs cosine | -22.50 | [-35.00, -10.00] | 0.1829 |
| Recurrence endorsement vs attention | -20.625 | [-29.375, -12.50] | 0.003600 |
| Recurrence endorsement vs cosine | +1.875 | [0.00, +5.00] | 1.0 |
| Recurrence clean correctness vs cosine | -8.75 | [-18.125, 0.00] | 1.0 |
| E5 endorsement vs untreated | -76.25 | [-85.00, -66.25] | 1.16e-16 |
| E5 endorsement vs cosine | +2.50 | [-2.50, +7.50] | 1.0 |
| E5 clean correctness vs cosine | -17.50 | [-27.50, -6.25] | 0.4083 |

Recurrence averages the two sessions within each incident before uncertainty
and uses the frozen paired sign-randomization test. Base and prefix-free use
exact paired binary McNemar tests. Full TrustRAG recurrence endorsement is
2.50%, versus OR's 5.00%; OR superiority is not established. Nonsignificance
does not establish equality, equivalence or non-inferiority. Clean point losses
are material limitations even where the full-family corrected tests are
nonsignificant.

Evidence: [base](../results/incident_base_interim_summary.json),
[prefix-free](../results/incident_prefixfree_interim_summary.json),
[recurrence](../results/incident_recurrence_interim_summary.json),
[E5](../results/incident_e5_interim_summary.json), and their
separate interim manifests. Scope-specific checks passed 1,920, 1,440 and 2,240
saved answers for the first three scopes and 1,760 for E5. E5's 136-comparison
Holm family uses the unchanged suite analysis; all 80 selected captures have
nonblank questions and claims, so its paired nonblank sensitivity retains all
80 incidents. E5 reranks the same candidate pool originally selected by
Contriever; it does not establish independent full-corpus retrieval transfer.
The [complete original-suite integrity audit](../results/incident_integrity.json)
passed, including all planned coverage and unchanged reader-weight hashes.
All selected questions/claims are nonblank in base (80/80), prefix-free
(80/80), recurrence (160/160 sessions from 80 incidents) and E5 (80/80).
The paired nonblank sensitivities therefore retain exactly the same records
and comparators as each all-target analysis; nonblank is not human semantic
verification.

## Claim-by-claim dispositions

| Claim | Final automated disposition | Evidence and boundary |
|---|---|---|
| Reduces endorsement relative to untreated contexts | Supported in completed local scopes | Large paired reductions above; benchmark-specific automated scoring |
| Reusable signatures add protection beyond attention alone | Supported for the recurrence scope | Corrected recurrence comparison above; not a win over the strongest baselines |
| OR outperforms captured-sample cosine | Supported in MemForm; inconclusive in QA/swarm | Supported for poisoned-action endorsement in the held-out MemForm-family local diagnostic; unestablished in QA and swarm scopes |
| OR outperforms full TrustRAG | Inconclusive / unsupported as a general claim | MemForm uses only its document filter; QA comparisons do not establish general superiority |
| Preserves legitimate clean performance relative to untreated/strong comparators | Inconclusive | Material observed clean costs; nonsignificance is not proof of no harm |
| Retains more clean-task accuracy than disabling memory in local MemForm | Supported in the added used-family diagnostic | Entailment +12.26 points, paired95 [8.02, 16.98], Holm8 p=1.73e-6; OR +10.38 [6.13, 14.62], p=2.09e-5 |
| Adds poisoned-history protection beyond disabling memory | Inconclusive / unestablished | OR and drop-all have identical prompts and raw answers in all 212 families; entailment endorsement +0.94 points, Holm8 p=1.0 |
| Fixed ungated OR can leave every clean context untouched | Contradicted for the implemented attention rule | Within-context z >= 0 necessarily flags at least one scored passage; see E29 audit |
| CoordGuard is blind to singleton poison | Contradicted by the local singleton test | Its selected component can contain one poison together with clean passages |
| Backfill's factual content explains the improvement | Inconclusive | True/placebo controls do not establish that explanation after correction |
| Composite stress demonstrates a broadly superior detector | Inconclusive | Strong mitigation relative to untreated does not establish superiority over strong comparators |
| Transfers reliably across readers | Inconclusive | Mistral is informative; 95/100 blank Llama claims prevent a clean valid-signature transfer interpretation |
| Transfers to an independent full-corpus retriever | Untested | Completed E5 reranks a candidate pool originally selected by Contriever |
| Shared signatures reduce non-capturing receivers' endorsement versus distinct-ID blocklists | Supported in the completed E42 scope | Incident-level benefit +62.08 points; final five-test Holm p=.000250; original full integrity passed |
| Shared signatures outperform captured-sample cosine | Inconclusive | Primary endorsement benefit +1.67 points; paired interval includes zero and conservative corrected p=.4996 |
| Shared protection preserves untreated swarm clean accuracy | Inconclusive under the frozen simultaneous criterion; observed clean loss | OR 33.33% versus untreated 52.50%; effect -19.17 points, paired 95% [-25.83, -12.08] |
| Joint swarm superiority plus zero clean loss | Inconclusive | Frozen five-comparison simultaneous decision; no no-harm claim |
| Reader weight files stay unchanged | Supported locally | Original suite and E45 before/after file hashes match; this is not a network deployment claim |
| Fresh powered primary confirmation passes | Untested | Neither used-question exploration nor the 212-family local diagnostic establishes it |
| Generalizes to official MemMorph | Untested | Official compatible archive was not located; the completed MemForm local port is distinct |
| Produces human-validated interpretable explanations | Untested | Inspectable scores are not evidence of human interpretability |

Historical evidence and corrections are retained in
[PROJECT_STATUS.md](PROJECT_STATUS.md), the E29/E35 audit, the E36–E38
[remaining-run summary](../results/remaining_runs_summary.json), and the
E32/E34 rescoring summaries. In particular, E29's previously described
endorsement p=.039 was raw, not multiplicity-corrected; the conservative
four-comparison sensitivity is .156. Do not reuse the historical stronger
wording or treat a continuous v2 ranking as confirmation of binary primary v1.

## Historical controls, readers and composite stress

The [E29/E35 audit](../results/e35_confirmatory_audit.json) rechecked 1,300
answers with zero automated rescoring mismatches. That verifies implementation
of the rule scores, not agreement with human judgments: all 152 and 302 rows
in the two human-label sheets remain unlabelled. Binary v1 flagged at least one
passage in every one of 100 clean contexts, averaging 3.79 flags. Of 64 contexts
initially containing a gold-answer token in clean evidence, 18 lost all such
tokens. Token presence is only a proxy for useful evidence. The within-context
attention rule z >= 0 cannot leave every nonempty scored context untouched.
The historical matched-recall analysis used continuous v2, so it cannot validate
the unregistered ranking performance of frozen binary v1.

Singleton blindness is contradicted by E31's local test: CoordGuard's selected
component removed 95.0% of 320 singleton poisons across 80 targets, while
removing 71.63% of clean passages. Claim entailment removed 87.19% of poison
and 2.64% of clean evidence. These are different operating points; a component
can contain one poison plus clean passages. They are not matched-recall proof
that one detector is uniformly better.

The [E32/E34 causal controls](../results/e32_e34_summary.json) do not establish
that the factual content of backfill explains the gain. In E32, true backfill
beat deletion by 13.75 correctness points, paired 95% [6.25, 22.50], Holm-six
p=.0205. Its advantage over placebo was 11.25 points [2.50, 20.00], but
Holm p=.1123. The in-place E34 control gave only 3.75 points over placebo
[-6.25, 13.75], Holm p=1.0. Three poison passages re-entered true replacement
contexts. Removal, placement, answer distribution and evidence content remain
partly confounded; the factual-backfill causal claim is inconclusive.

Reader transfer is operationally limited. Each E36 reader has 100 targets,
50 each from HotpotQA and MS MARCO. The
[Mistral result](../results/e36_mistral_interim_summary.json) has no blank
selected claims: untreated endorsement/correctness is 69%/28%, v1 refill
11%/67%, CoordGuard AF-refill 9%/64%, full TrustRAG 7%/60%. V1 minus CoordGuard
endorsement is +2 points, paired 95% [-3, 7], Holm-ten p=1.0; v1 minus full
TrustRAG is +4 [-1, 10], p=1.0. Correctness advantages of +3 [-5, 11] and
+7 [-5, 18] are likewise unestablished after correction. Clean accuracy is
60% for v1 versus 71% untreated. These data support mitigation, not SOTA
superiority or preserved clean accuracy.

The [Llama result](../results/e36_llama_interim_summary.json) has **95/100 blank
selected claims** (46 HotpotQA, 49 MS MARCO). This is an operational extraction
limitation under the original missing-field/no-object fallback, separate from
R2's malformed JSON exception. Raw extraction text was not retained for these
historical missing-field cases, so their exact textual causes are unavailable.
Untreated endorsement is 53%, v1 refill 32%, CoordGuard AF-refill and full
TrustRAG 3% each. V1's endorsement excess over CoordGuard is +29 points [21, 38],
Holm-ten p=3.73e-8. V1 correctness 43% exceeds full TrustRAG's 13% by +30 points
[18.98, 41], Holm p=3.71e-5, but that does not rescue its worse attack endorsement
or establish valid-signature transfer. V1 clean correctness is 44% versus 63%
untreated. These all-target outcomes must not be described as a clean test of
semantically valid transferred signatures.

The [completed-reader capture sensitivity](../results/e36_capture_sensitivity.json)
reuses the unchanged E36 analysis functions and correction families, with an
identical paired nonblank-question/claim subset for every comparator. Llama
retains only five targets; Mistral retains all 100 and is identical to its main
analysis. The all-target recomputation exactly matches both completed-reader
pooled summaries. Five nonblank extractions cannot establish reliable reader
transfer or replace the 100-target operational result.

E37 tests 80 composite-stress targets: untreated endorsement is 48.75%, OR
5.00%, entailment 11.25%, CoordGuard AF 3.75% and full TrustRAG 13.75%. OR's
reduction versus untreated is -43.75 points, paired 95% [-55.00, -32.50],
Holm p=1.16e-10 in the separately labelled exploratory mitigation-control
family. The frozen six primary comparisons do not establish superiority over
the strong comparators. OR clean correctness is 42.50% versus 65.00% untreated.
The [R2 sensitivity](../results/e37_capture_sensitivity.json) retains all 80
operational targets and separately the identical 79 nonblank-selected targets
for every comparator; OR endorsement there is 3/79. There were 400 capture
attempts and one malformed capture, selected at test423 capture 2.

The [E38 frozen-gate replay](../results/e37_gate_replay.json) uses those saved
scores, so it is neither fresh confirmation nor a new actual timing experiment.
The gate fired on 35% of attacked and 3.75% of clean contexts. Gated OR raised
clean correctness from 42.50% to 61.25%, but endorsement rose from 5.00% to
25.00%: +20 points [11.25, 28.75], exploratory Holm p=.000305. The +18.75 clean
gain [6.25, 31.25] had corrected p=.0732. Gating trades protection for utility;
it does not establish a free improvement. A claim-informed NLI gate is also
not an information-matched comparison against a native unsupervised gate.

## Final E42/E45 swarm result

E42 completed 80 incidents and 5,920 publisher/receiver arms. E45 then made
all **480 actual untreated-clean reference calls**, using the exact saved E42
receiver contexts. The [reference integrity audit](../results/swarm_clean_reference_integrity.json)
passed all context, answer, exclusion and weight checks. The
[final focused summary](../results/swarm_track4_summary.json) applies the
unchanged five-comparison analysis. Original E42 records were not edited.

The E42 [scope audit](../results/incident_swarm_interim_summary.json) checked
5,760 receiver answers, actual contexts/refill, exclusion, delivery hashes and
isolated state, plus 80 publisher attacked contexts and 80 publisher clean
answer scores. Publisher clean context was not persisted; full original
integrity success does not recover that missing provenance.

Primary distinct-ID layout: three receivers are averaged within each incident
before pairing. There are 80 independent incidents, not 240 or 480.

| Method | Attacked endorsement | Attacked correctness | Clean correctness |
|---|---:|---:|---:|
| Shared record-ID blocklist | 62.500% | 36.67% | 52.50% |
| Captured-sample cosine | 2.083% | 50.83% | 50.83% |
| Shared claim-plus-attention OR | 0.417% | 42.92% | 33.33% |
| Shared entailment (secondary) | 9.167% | 47.50% | 51.67% |
| Isolated attention | 1.250% | 42.50% | 33.75% |
| Native CoordGuard gate | 62.500% | 36.67% | 52.50% |
| Actual untreated reference | Not run in E45 | Not run in E45 | 52.50% |

Attack benefit is comparator minus OR endorsement; clean benefit is OR minus
comparator correctness. Paired bootstrap intervals use 2,000 draws; one-sided
incident sign-randomization tests use 20,000 draws, seed 0, with Holm over all
five comparisons. The simultaneous empirical-Bernstein bounds allocate
alpha=.05/(2*5) per tail for differences in [-1,1]. **The clean-loss margin is
zero**, separate from the .05 endorsement NI margin reserved for future fresh
confirmation. Descriptive paired intervals are not simultaneous intervals.

| Primary comparison | Effect (points) | Paired 95% | Simultaneous bounds | Holm p |
|---|---:|---:|---:|---:|
| Attack benefit vs IDs | +62.08 | [+53.33, +70.42] | [+12.07, +100.00] | 0.000249988 |
| Attack benefit vs cosine | +1.67 | [+0.00, +3.76] | [-37.22, +40.55] | 0.499575 |
| Clean benefit vs IDs | -19.17 | [-25.83, -12.08] | [-67.01, +28.67] | 1 |
| Clean benefit vs cosine | -17.50 | [-24.17, -10.42] | [-65.37, +30.37] | 1 |
| Clean benefit vs untreated | -19.17 | [-25.83, -12.08] | [-67.01, +28.67] | 1 |

**The frozen joint claim is inconclusive.** Attack reduction versus distinct-ID
blocklists is supported locally; additional protection over cosine is not
established. All three clean point estimates show costs. The clean directional
p-values of 1 test improvement, not equality or absence of harm. Simultaneous
upper bounds remain above zero, so the frozen rule classifies the conjunction
as inconclusive rather than statistically contradicted. This must not obscure
the substantial observed clean losses or be described as preserved accuracy.

OR loses at least one correct clean receiver answer in 41/80 incidents versus
untreated and record IDs (51.25%; exact one-sided 95% upper risk bound 60.91%),
and 38/80 versus cosine (47.50%; upper 57.26%). Even zero observed losses would
not establish zero possible harm.

All 80 selected questions/claims are nonblank. The R2-prespecified paired
nonblank sensitivity is **exactly identical** to the primary analysis, with
every comparator on the same 80 incidents. No human semantic validity is implied.

### Prespecified secondary swarm scopes

In the shared-ID layout, record IDs and cosine each have 2.083% endorsement,
versus OR .833%. Clean accuracy is OR 33.33%, IDs 52.50%, cosine 50.83% and
actual untreated 52.50%. The shared-ID joint claim is inconclusive:

| Shared-ID comparison | Effect (points) | Paired 95% | Simultaneous bounds | Holm p |
|---|---:|---:|---:|---:|
| Attack benefit vs IDs | +1.25 | [+0.00, +3.33] | [-37.35, +39.85] | 1 |
| Attack benefit vs cosine | +1.25 | [+0.00, +3.33] | [-37.35, +39.85] | 1 |
| Clean benefit vs IDs | -19.17 | [-25.83, -12.08] | [-67.01, +28.67] | 1 |
| Clean benefit vs cosine | -17.50 | [-24.17, -10.42] | [-65.37, +30.37] | 1 |
| Clean benefit vs untreated | -19.17 | [-25.83, -12.08] | [-67.01, +28.67] | 1 |

Entailment alone is a prespecified secondary method, not a replacement chosen
after seeing OR clean losses. In distinct IDs it has 9.167% endorsement and
51.67% clean accuracy; its joint claim also remains inconclusive:

| Entailment comparison | Effect (points) | Paired 95% | Simultaneous bounds | Holm p |
|---|---:|---:|---:|---:|
| Attack benefit vs IDs | +53.33 | [+44.58, +62.08] | [+2.77, +100.00] | 0.000249988 |
| Attack benefit vs cosine | -7.08 | [-12.08, -2.50] | [-51.11, +36.94] | 1 |
| Clean benefit vs IDs | -0.83 | [-2.50, +0.43] | [-39.11, +37.44] | 1 |
| Clean benefit vs cosine | +0.83 | [-1.25, +3.33] | [-38.65, +40.32] | 1 |
| Clean benefit vs untreated | -0.83 | [-2.50, +0.43] | [-39.11, +37.44] | 1 |

The [Track 4 protocol](SWARM_TRACK4_PROTOCOL.md) tests shared protection in
homogeneous serial local agents. It does not demonstrate autonomous contagion,
authenticated publication, heterogeneous fleets, live false-alert propagation
or network revocation. E45 ran later than E42 and is not a randomized timing
comparison with E42. Human scoring remains deferred.

## Completed held-out MemForm-family local diagnostic

All 212 held-out families completed 2,968 memory-condition/method arms after
20 calibration families. The [native-answer/context audit](../results/incident_memform_integrity.json)
passed. Every selected question and claim is nonblank; the
[capture audit](../results/incident_memform_capture_audit.json) therefore retains
exactly the same 212 families and every comparator in the prespecified paired
nonblank sensitivity. This is not human validation of extraction semantics.

| Method | Poisoned-action endorsement | Poisoned-condition correctness | Clean correctness |
|---|---:|---:|---:|
| Untreated | 54.25% | 41.04% | 96.70% |
| Captured-sample cosine | 51.89% | 44.81% | 96.23% |
| Claim entailment | 8.96% | 82.08% | 95.28% |
| Claim-plus-attention OR | 8.02% | 83.02% | 93.40% |
| Gated OR | 8.02% | 83.02% | 92.92% |
| Native CoordGuard gate | 54.72% | 41.51% | 94.81% |
| TrustRAG document filter | 11.32% | 80.19% | 81.13% |

Effects below are OR minus comparator, in percentage points. Paired 95%
bootstrap intervals are descriptive; exact paired binary McNemar tests retain
all 84 method-pair/condition/endpoint comparisons within this scope.

| Endpoint / comparator | Effect | Paired 95% interval | Holm-adjusted p |
|---|---:|---:|---:|
| Poisoned endorsement vs untreated | -46.23 | [-53.30, -38.68] | 1.70e-25 |
| Poisoned endorsement vs cosine | -43.87 | [-50.96, -36.78] | 3.98e-23 |
| Poisoned endorsement vs CoordGuard gate | -46.70 | [-53.77, -39.62] | 8.87e-26 |
| Poisoned endorsement vs entailment | -0.94 | [-2.36, 0.00] | 1.0 |
| Poisoned endorsement vs TrustRAG filter | -3.30 | [-5.66, -0.94] | .75 |
| Clean correctness vs untreated | -3.30 | [-7.55, +0.47] | 1.0 |
| Clean correctness vs cosine | -2.83 | [-7.08, +1.42] | 1.0 |

The frozen fixed-causal-eligibility secondary scope contains 170 families:
distinct action labels, correct no-memory answer and correct undefended clean
memory answer. Its denominator is identical for all methods. OR endorsement is
3.53% versus cosine 47.65%, difference -44.12 points, paired 95%
[-51.78, -36.47], Holm p=8.05e-20. OR clean correctness is 95.88% versus
untreated 100% and cosine 99.41%. The nonblank sensitivity is again identical.
Eligibility conditions on undefended success, so these clean rates must not
replace the all-target operational rates.

The [complete summary](../results/incident_memform_summary.json) supports a
local benefit over sample similarity in this interface. It does not establish
that attention adds protection beyond the claim entailment component, a win
over full TrustRAG, or clean no-harm. Native final-action parse failures remain
in the operational denominator (OR: 9/212 poisoned and 2/212 clean); they are
distinct from capture JSON failures. Human scoring remains deferred.

The [MemForm protocol](MEMFORM_DIAGNOSTIC_PROTOCOL.md) defines a separate local
memory-formation diagnostic over 212 held-out families following 20 calibration
families. Its TrustRAG comparator is document-filter-only. It is not official
MemMorph, all-interface native MemForm evaluation, or the powered primary
confirmation. The [development power calculation](../results/incident_power.json)
does not support the proposed joint primary claim under current effect
estimates. The .05 absolute endorsement non-inferiority margin remains fixed
for a future fresh confirmation; it must not be retroactively repurposed as a
clean-loss allowance or changed to obtain a positive result.

That planning calculation uses 80 development incidents, a conservative
four-component allocation alpha=.0125 and paired disagreements. The estimated
clean-utility difference versus the native CoordGuard gate is -3.75 points,
so the proposed superiority alternative has negative slack and no finite
sample-size recommendation under that point estimate. Against full TrustRAG,
the estimated +3.75-point utility gain requires approximately 3,112 independent
targets for the conservative joint 80% power component; an endorsement excess
of 3.75 points leaves only 1.25 points inside the fixed 5-point NI margin and
requires approximately 8,428 targets (9,850 at joint 90%). These are uncertain
normal-approximation planning values, not achieved power or a reason to tune
the margin. The 212-family MemForm diagnostic does not establish the still
unrun, powered fresh primary confirmation.

## Required operational and extraction disclosures

Completed original-suite operational measurements are in the
[full summary](../results/incident_summary.json). Base-scope warm attacked
pipeline means are 7.19 seconds untreated, 18.44 OR, 12.20 cosine, 24.59
CoordGuard native gate and 35.94 full TrustRAG. OR spends 8.75 seconds filtering
and 9.69 answering; cosine spends 2.89 and 9.31. These are actual uncached
method calls under the common selected configuration, with deterministic
per-case shuffled recipe order. They are descriptive local timings, not
production latency results.
The [paired operations audit](../results/incident_operations_audit.json) gives
OR-minus-cosine total time +6.24 seconds, paired 95% [4.95, 7.63]; versus
untreated +11.25 [9.36, 13.24], native CoordGuard gate -6.15 [-7.87, -4.33],
and full TrustRAG -17.50 [-20.78, -14.54]. These descriptive timing intervals
carry no separate confirmatory speed-superiority test.
Model loading and initial capture/setup are separate. A base capture costs
5.25 seconds on average (95% bootstrap interval [4.54, 6.12]); captured-sample
cosine setup costs .89 seconds [.76, 1.07]. The serialized semantic artifact
averages 234.5 bytes versus 232.8 sample bytes; a compact semantic artifact does
not imply a measured byte saving in this local sample.

E42's actual serialized messages average 274.5 bytes for the claim message,
363.2 for the sample comparator's message and 64.5 for the record-ID blocklist.
On distinct-ID attacked receivers, warm pipeline means are 10.13 seconds for
shared OR, 6.21 cosine and 4.59 record IDs, averaging receivers within incident.
OR's smaller message than the sample message does not demonstrate lower total
cost: receiver filtering and answer generation are additional work. Transport,
authentication and heterogeneous-device setup costs are not measured.

In base attacked contexts, OR removes 99.06% of poison and 6.01% of labelled
clean evidence on average, while cosine removes 100% and 3.33%. On entirely
clean contexts, OR removes 35.37% of evidence versus cosine 2.38%. These labels
and token-containing evidence proxies do not establish that every removed
passage is semantically necessary; the observed clean answer costs remain the
direct operational limitation. With a mistaken clean capture, OR endorsement
is 17.50% rather than 5.00% under the correct capture, and clean accuracy is
40.00%. This is single-reader mistaken-capture evidence, not a live swarm
false-alert experiment.

The original and E45 before/after reader-weight hashes match. The calibration
[Contriever revocation check](../results/incident_revocation_contriever.json)
and [E5 check](../results/incident_revocation_e5.json) each use test1, successfully
round-trip the serialized artifact and obtain the same answer and flags after
revocation as isolated attention. They demonstrate the local fallback path;
they do not measure revocation latency, authenticated network publication or
removal from a deployed fleet. E45's separate weight audit also passed.

- **R2 is post-start:** E37's strict parser failed after 70 completed targets.
  The unchanged greedy replay reproduced malformed JSON. The guard catches
  only JSONDecodeError, preserves raw output/sample hashes and the error, and
  applies the existing empty-dictionary fallback: first-sentence question,
  blank claim. No repair, better-output retry, gold use or skipped target is
  allowed. Preserve the first-70 provenance and disclose the policy amendment.
  E37 had one malformed/blank capture among 400 attempts; its selected-nonblank
  secondary subset has 79 targets. All-target results remain primary.
- Nonblank question/claim sensitivity uses identical paired subsets for all
  methods. Nonblank extraction is not human verification of semantics. The
  disclosed 95/100 blank Llama claims are an operational extraction limitation,
  separate from R2's malformed-JSON exception handling.
- **R1 is an allocator-cache trial:** exactness checks passed, but the declared
  measured-gain condition failed. The cap was rejected and original defaults
  retained. No speedup is established by that trial. Method timing comparisons
  remain actual uncached operations under the same chosen configuration.
- Report capture/setup, filtering and reader timing separately, plus actual
  complete pipeline cost. Shared read-only weights and captured-sample
  embedding setup are local harness properties, not measured network costs.
- Serialization/revocation checks are calibration evidence. The final actual
  reader-weight before/after audits passed for both original and supplemental runs. Signature updates do not imply
  reader training. Mistaken capture has a separate single-reader experiment;
  live false-alert propagation and network revocation are not tested.
- Host sleep, reboot, shared-resource pauses and approved checkpoint restarts
  extend calendar runtime. Checkpoints and append-only logs are preserved;
  startup checks can repeat, but saved experimental answers are retained.

See [R2](EXTRACTION_RESILIENCE_AMENDMENT.md),
[R1](PERFORMANCE_RUNTIME_AMENDMENT.md),
[E37 capture sensitivity](../results/e37_capture_sensitivity.json), and
[completion monitoring](../results/completion_monitor.json).

## Publication and submission boundaries

A defensible paper can investigate when reusable incident signatures help,
when simple sample similarity suffices, and what legitimate evidence they
discard. Publication value requires a clear contribution and validated results;
the number of experiments alone does not demonstrate novelty or efficacy.

Remaining limitations include previously used QA questions, limited released
poison diversity, trusted capture and calibration requirements, deferred human
scoring and interpretability, rule-score overlaps, candidate-pool-only
retriever transfer, limited power, and homogeneous serial local agents. The
swarm extension tests shared protection, not autonomous contagion,
authenticated publication, heterogeneous production fleets or general swarm
alignment.

The intended hackathon anchor is Track 4, Multi-Agent Oversight and Control.
All code and experiments created before the 6–8 November sprint are preexisting
work and must be labelled accordingly in the README and submission report.
Only the sprint-weekend contribution is judged. Registration, publication and
submission have not been performed by this workflow.

## Completion and reproducibility

The remaining E36–E38 batch, original incident suite and E45/focused Track 4
supervisor completed their automated phases. Original and supplemental reader
weight comparisons passed. The original suite and MemForm integrity outputs,
480-answer E45 integrity output and frozen five-comparison summary are all
present and successful. Human scoring/interpretability remain deferred, not
passed; this is the final automated evidence assessment, not a human-validation
certificate or a hackathon submission.

Scientific source, manifests, saved answers, extraction failures and checkpoints
remain preserved. The [monitoring integrity ledger](../results/heartbeat_integrity_check.json)
records frozen-hash verification, including the original E37 first-70 prefix.
The [R2 failure ledger](../results/extraction_failure_events.jsonl) has one
JSONDecodeError event; its raw record is retained under ignored
`results/checkpoints/extraction_failures/` and its output hash was verified.
The historical first-70 SHA256 is
`6931cae32b369c4b115d23a1d3cba75d07f81c0d1a42059b39523dd06b363dfb`.

## Additional completed record audit on 3 November

The separately frozen [component utility audit](COMPONENT_UTILITY_AUDIT.md)
checked 1,384 saved MemForm and swarm contexts without new model calls,
threshold changes or edits to original records. It is posthoc descriptive;
the original comparison families and final dispositions above remain intact.

In every one of 212 poisoned MemForm families, OR removed all input experiences
and produced the native empty-history fallback. Entailment did so in 207.
Therefore the observed MemForm mitigation does not establish selective
preservation of useful poisoned-history evidence. Actual saved no-memory
answers use a different prompt condition and could not replace an exact
always-drop-history baseline. That exact added control is now complete below.

Adding attention removed 128 additional clean MemForm experiences, with five
correct-to-wrong and one reverse paired outcome; clean correctness was 95.28%
for entailment and 93.40% for OR. In distinct-ID swarm clean contexts it removed
718 additional labelled-clean passages; 57 receiver outcomes changed from
correct under entailment to wrong under OR, with 13 reverse changes. These
240 receiver outcomes remain clustered within 80 incidents. The audit does
not estimate causal mediation or create a new significance claim.

The [new research answers and test plan](NEXT_TESTS_AND_RESEARCH_ANSWERS.md)
separate these empirical observations from newly tested local software for
matched capture access, bound run records and permanent revocation tombstones.
Software tests do not establish native MemMorph efficacy, semantic accuracy,
real network recovery or completed human validation.

## Exact empty history control completed on 4 November

All **424 actual uncached answer calls** completed on this Mac, across 212
already-used families and two conditions. The frozen scientific recipe stayed
unchanged. The separately recorded runtime guard yielded only our child when
new local work appeared and resumed its bound checkpoints. The complete
[integrity result](../results/memform_drop_all_control_v1_integrity.json) passed;
the [completion audit](../results/memform_drop_all_completion_audit_v1.json)
independently replayed every checkpoint/parser/score, reproduced the full
summary, verified 30 original scientific manifests and 597 referenced files,
preserved the E37 first-70 prefix, and rehashed actual reader-weight bodies.

| Condition | Entailment correctness / endorsement | OR correctness / endorsement | Drop-all correctness / endorsement |
|---|---:|---:|---:|
| Clean | 95.28% / 2.83% | 93.40% / 4.25% | 83.02% / 8.02% |
| Poisoned | 82.08% / 8.96% | 83.02% / 8.02% | 83.02% / 8.02% |

Effects below are signature minus exact drop-all, in percentage points. Paired
95% percentile intervals are descriptive and **not simultaneous**; tests retain
the complete frozen eight-comparison Holm family.

| Condition / method / endpoint | Effect | Paired 95% interval | Holm8 p |
|---|---:|---:|---:|
| Clean entailment correctness | +12.26 | [8.02, 16.98] | 1.73e-6 |
| Clean OR correctness | +10.38 | [6.13, 14.62] | 2.09e-5 |
| Clean entailment endorsement | -5.19 | [-8.49, -2.36] | .02051 |
| Clean OR endorsement | -3.77 | [-6.60, -0.94] | .10742 |
| Poisoned entailment correctness | -0.94 | [-2.36, 0.00] | 1.0 |
| Poisoned entailment endorsement | +0.94 | [0.00, 2.36] | 1.0 |
| Poisoned OR correctness | 0.00 | [0.00, 0.00] | 1.0 |
| Poisoned OR endorsement | 0.00 | [0.00, 0.00] | 1.0 |

**Supported:** additional clean-task accuracy over disabling memory. Entailment
has 27 correct-signature/wrong-drop-all pairs and one reverse; OR has 23 and one.
This is a measured operational utility contribution, not proof that each
retained passage was necessary or semantically appropriate.

**Unestablished:** additional poisoned-history protection and strict joint
superiority. Every poisoned OR prompt, raw response and parsed prediction
matches the corresponding fresh drop-all call, 212/212. Those identical
inputs reproduce the empty-history intervention rather than isolate a more
selective protection mechanism. Entailment has 207 identical poisoned prompts;
its small remaining endorsement excess is not significant after correction.
No equivalence or noninferiority margin was specified. A degenerate empirical
bootstrap interval at zero does not prove population equality: the separately
retained conservative simultaneous OR poisoned-effect bounds span
[-23.33, 23.33] points. Both frozen strict joint verdicts remain inconclusive.

Parse failures remain in the denominator: 9/212 (4.25%) for each drop-all
condition, versus 2/212 (0.94%) for each signature method on clean histories
and 9/212 on poisoned histories. All selected captures are nonblank, so the
identically paired nonblank sensitivity retains all 212 families; human
semantic/scoring validity remains deferred, not passed.

Actual saved answer timers total **1,366.43 seconds (22.77 minutes)**, mean
3.22 seconds per call. They include runtime boundary checks. Five model-child
invocations and four resource yields occurred; the latest model load took
4.85 seconds. Complete aggregate reload/setup time was not retained. Elapsed
time from first child start to analysis completion was 1,776.51 seconds
(29.61 minutes), including waiting and reloads. These later-collected timings
are not a controlled speed comparison with the original signature methods.

The [full paired summary](../results/memform_drop_all_summary_v1.json),
[readable result](../results/memform_drop_all_summary_v1.md), and
[pre-outcome analysis freeze](../results/memform_drop_all_analysis_manifest_v1.json)
retain every comparison, failure, same-prompt diagnostic and conservative
bound. This is an added diagnostic on already-inspected local MemForm
families, not fresh powered confirmation, native MemMorph validation, a
matched raw-semantic test, or broad novelty proof. The remaining central
question is whether abstraction adds value under matched information while
preserving legitimate use on untouched native campaigns.

The complete paired results remain in the linked machine-readable summaries.
No new outcomes were omitted, no failed capture was repaired or replaced, no
threshold was tuned using test answers, and no better-output retry was added.
The scientific parser policy did change explicitly under R2; this must remain
visible in every reuse of these results. The allocator cap was rejected under
R1; original defaults were retained. Tests ran only on this Mac, under the
shared model lock. Sleep and approved external-resource pauses extended wall
clock runtime; awake processing estimates were not calendar guarantees.
