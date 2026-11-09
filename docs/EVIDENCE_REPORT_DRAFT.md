# ANTIVENOM evidence assessment — interim draft

**Archived preparation draft:** superseded by the completed
[final automated evidence assessment](EVIDENCE_REPORT.md) on 3 November 2026.
Pending statements below describe the earlier preparation state.

Updated 3 November 2026 (Singapore). **Not the final report:**
The original suite, all 212 MemForm families and original weight/integrity
audits are complete and passed. The untreated swarm clean reference and its
focused final analysis remain incomplete. No pending endpoint is treated as passed. The
runtime status files and `completion_monitor.json` are authoritative for live
processes; this document records scientific interpretation.

## Current assessment

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

## Claim dispositions so far

| Claim | Interim disposition | Evidence and boundary |
|---|---|---|
| Reduces endorsement relative to untreated contexts | Supported in completed local scopes | Large paired reductions above; benchmark-specific automated scoring |
| Reusable signatures add protection beyond attention alone | Supported for the recurrence scope | Corrected recurrence comparison above; not a win over the strongest baselines |
| OR outperforms captured-sample cosine | Scope-dependent | Supported for poisoned-action endorsement in the held-out MemForm-family local diagnostic; unestablished in QA and swarm scopes |
| OR outperforms full TrustRAG | Inconclusive / unsupported as a general claim | MemForm uses only its document filter; QA comparisons do not establish general superiority |
| Preserves legitimate clean performance | Not established | Material observed clean costs; nonsignificance is not proof of no harm |
| Fixed ungated OR can leave every clean context untouched | Contradicted for the implemented attention rule | Within-context z >= 0 necessarily flags at least one scored passage; see E29 audit |
| CoordGuard is blind to singleton poison | Contradicted by the local singleton test | Its selected component can contain one poison together with clean passages |
| Backfill's factual content explains the improvement | Inconclusive | True/placebo controls do not establish that explanation after correction |
| Composite stress demonstrates a broadly superior detector | Not established | Strong mitigation relative to untreated does not establish superiority over strong comparators |
| Transfers reliably across readers | Limited operational evidence | Mistral is informative; 95/100 blank Llama claims prevent a clean valid-signature transfer interpretation |
| Transfers to an independent full-corpus retriever | Untested | Completed E5 reranks a candidate pool originally selected by Contriever |
| Shared signatures reduce non-capturing receivers' endorsement versus distinct-ID blocklists | Supported in the completed E42 scope | Incident-level benefit +62.08 points; conservative interim five-test Holm p=.000250; original full integrity passed |
| Shared signatures outperform captured-sample cosine | Inconclusive | Primary endorsement benefit +1.67 points; paired interval includes zero and conservative corrected p=.4996 |
| Shared protection preserves untreated swarm clean accuracy | Pending | Requires E42 and the separate E45 actual untreated clean answers |
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

## Swarm and fresh-data gates

E42 completed all 80 incidents and 5,920 actual publisher/receiver answers.
The [completed-scope audit](../results/incident_swarm_interim_summary.json)
checks all 5,760 receiver answers, actual contexts and refill, capture exclusion,
delivered message hashes and isolated receiver state. It also checks 80 publisher
attacked answers against saved contexts and re-scores both publisher conditions.
The publisher's clean context is not stored, so those 80 clean answers receive
score checks only in this interim audit. Full original integrity and final
reader-weight checks have now passed; the missing publisher-clean context is
still a provenance limitation. All 80 selected captures have nonblank
questions/claims, so the identical paired nonblank sensitivity retains all 80;
this does not validate their semantics.

Primary distinct-ID layout results average three receivers per incident before
inference; 240 receiver observations remain only 80 independent incidents:

| Method | Attacked endorsement | Attacked correctness | Clean correctness |
|---|---:|---:|---:|
| Shared record-ID blocklist | 62.50% | 36.67% | 52.50% |
| Captured-sample cosine | 2.083% | 50.83% | 50.83% |
| Shared claim-plus-attention OR | 0.417% | 42.92% | 33.33% |
| Shared claim entailment (secondary) | 9.167% | 47.50% | 51.67% |
| Isolated attention | 1.25% | 42.50% | 33.75% |

Endorsement benefit is comparator minus OR; clean benefit is OR minus comparator.
Paired 95% intervals are descriptive, not simultaneous. The interim directional
tests retain the frozen five-comparison family by reserving a p=1 slot for the
unavailable untreated-clean endpoint. This is conservative multiplicity
accounting, not an imputed outcome; the complete frozen analysis will run after
E45. The same frozen simultaneous bounds retain family size five throughout.

| Primary comparison | Effect (points) | Paired 95% interval | Conservative interim Holm p |
|---|---:|---:|---:|
| Endorsement benefit vs record IDs | +62.08 | [+53.33, +70.42] | .000250 |
| Endorsement benefit vs cosine | +1.67 | [0.00, +3.76] | .4996 |
| Clean benefit vs record IDs | -19.17 | [-25.83, -12.08] | 1.0 |
| Clean benefit vs cosine | -17.50 | [-24.17, -10.42] | 1.0 |

The clean p-values above test the prespecified improvement direction; they are
not tests establishing equality or evidence against observed harm. OR lost at
least one correct receiver answer in 41/80 incidents versus record IDs (exact
one-sided 95% upper loss-risk bound 60.91%) and 38/80 versus cosine (upper 57.26%).
The substantial observed clean costs must be reported. The conservative
simultaneous lower bound for endorsement benefit versus record IDs is +12.07
points; versus cosine it is -37.22 points. The clean simultaneous intervals also
span zero, so the full prespecified joint disposition cannot be promoted to
supported, nor replaced with conclusions from unadjusted intervals.

In the secondary shared-ID layout, endorsement was 2.083% for record IDs and
cosine versus 0.833% for OR; neither improvement is established (conservative
interim Holm p=1.0). Clean accuracy has the same material observed OR losses.
The experiment demonstrates why exact IDs fail on distinct released variants;
it does not establish that OR provides additional protection over captured-sample
cosine while preserving clean utility.

The [Track 4 protocol](SWARM_TRACK4_PROTOCOL.md) fixes shared_claim_OR as the
focal method before receiver outcomes, with distinct poison IDs as primary.
One publisher and three non-capturing receiver states make real local model
calls. Receivers, layouts and repeated questions are clustered by incident;
they cannot inflate the independent sample size beyond 80 incidents.

The five jointly required comparisons are lower endorsement than shared IDs
and cosine, and no loss in clean correctness against IDs, cosine and untreated
contexts. The clean loss margin is strictly zero. Conservative simultaneous
bounds remain nonzero even with zero observed losses; zero observed losses
must not be equated with proof of zero possible harm. E45's 480 actual
generation calls use the exact saved E42 clean receiver contexts after the
entire original queue and original integrity succeed. They are not 480
independent incidents, nor a randomized timing comparison with earlier E42.

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

The original before/after reader-weight hashes match. The calibration
[Contriever revocation check](../results/incident_revocation_contriever.json)
and [E5 check](../results/incident_revocation_e5.json) each use test1, successfully
round-trip the serialized artifact and obtain the same answer and flags after
revocation as isolated attention. They demonstrate the local fallback path;
they do not measure revocation latency, authenticated network publication or
removal from a deployed fleet. E45's separate weight audit remains pending.

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
  reader-weight before/after audit passed; E45 has its own pending audit. Signature updates do not imply
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

## Finalization checklist

The original suite, MemForm analysis, original final weight audit and full
original integrity are complete. Finish E45, its integrity and the focused swarm summary. Inspect
raw records and all failure events; reconcile every claim with paired effects,
the frozen corrected tests and simultaneous bounds. Replace pending cells with
supported, contradicted, inconclusive or untested dispositions without choosing
a more favorable method or subset after outcomes. Deliver the final report and
evidence links before disabling the monitoring heartbeat. Deferred human work
must remain explicitly deferred rather than passed.
