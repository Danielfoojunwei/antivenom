# Incident-response capability evaluation — 29 October 2026

User direction: test targeted, reusable protection after a confirmed incident,
including all listed trade-offs and additional controls. Human review is
deferred at the user's request and does not block automated execution. Existing
metrics remain explicitly rule-scored. Negative or inconclusive findings must
be reported; no empirical experiment can guarantee the desired claim.

The E36–E38 queue remains unchanged. This extension waits for that queue to
finish successfully and runs serially under the same model-job lock.

## Primary future confirmation

The user selected an endorsement non-inferiority margin of **0.05 absolute**
before any fresh test. This does not amend earlier pre-registrations. Proposed
single primary claim: gated claim-plus-attention filtering improves clean-task
accuracy while its attacked endorsement is no more than 0.05 worse than each
of CoordGuard's native geometry gate and TrustRAG. All four conditions must
pass. Freeze one implementation, calibration, comparators, family correction,
sample size and eligible incident/question IDs before fresh outcomes. Do not
choose the most favourable reader after examining its test results.

Estimate sample size using paired *development* disagreements for both attack
and clean endpoints, include clustering by incident/family, and account for
both comparators. Provide sensitivity to lower power and plausible effect
sizes. A new dataset with insufficient independent families supports a
diagnostic, not an automatically powered 5-point confirmation. There is no
fresh-question confirmation until compatible records and adequate sample
size exist. MemMorph is a tool-choice task; it is not automatically a drop-in
short-answer QA benchmark. Any MemForm evaluation is separately named and
must retain family clustering and distinguish a port from the native harness.

## E39: full ablation and mistaken-capture harm

Qwen, NQ calibration 1–20 and development 21–100. Remove captured poison[0]
from the candidate pool before retrieval, including backfill. Test entails-only
(tau=.01), attention-only (layer 21, z>=0), OR, calibration-fitted avidity,
captured-sample cosine, exact captured-text hash blocklist, CoordGuard AF,
native CoordGuard geometry gate, TrustRAG, no defence, and NLI-gated OR.
All receive identical actual contexts, 48-token greedy answer cap, and the
same unscreened delete+refill effector where applicable. TrustRAG keeps its
existing internal budgets. The sample-aware comparators receive the same
trusted captured sample. CoordGuard receives no extra privileged labels.

Avidity fits [logit(entailment), attention z] on the 20 captured-excluded
calibration contexts only; threshold is the clean-score 95th percentile.
Cosine threshold is the calibration clean 95th percentile. Other v1 thresholds
stay fixed. The NLI gate uses the E30 calibration recipe on these contexts.
The geometry gate uses the benign calibration 90th percentile. Report actual
recall/clean removal; these deployed points are not necessarily matched-cost.
Every method answers both attacked and clean contexts. Separately evaluate
wrongly trusting the top-ranked *clean* passage as a captured poison. That
passage is unchanged; no new attack content is created and no gold answer is
used to choose it. Measure additional clean harm and attack leakage.

Also run the detector ablations on the 80 prefix-free development contexts
with captured poison excluded. Apply the base calibration without refitting.
This is a context-shift test, not a fresh question set.

## E40: recurrence against strong and sample-aware baselines

Reuse the two already stored benign E18 paraphrases for each of 80 targets.
Rerun retrieval over the actual clean pool and released poisons[1:]; the
captured sample stays absent. Recompute attention, NLI and cosine. Compare
stored OR, attention alone, sample cosine, native CoordGuard gate, TrustRAG,
NLI-gated OR and no defence, on both attacked and clean contexts. Do not
infer superiority from the historical attention-only comparison. Two later
questions are clustered within the same target; they are not 160 independent
incidents. Stored paraphrase fidelity remains a limitation while review is
deferred.

## E41: second retriever

Use cached e5-large-v2 with query/passage prefixes and normalized dot products
to rerank each target's same released candidate pool. Calibrate only on NQ
1–20 under this retriever, then evaluate all 80 development targets with the
same detector/baseline comparisons. This is *candidate-pool retriever transfer*;
the pool was originally selected by Contriever, so it cannot establish a
second independent full-corpus retrieval result.

## E42: actual local multi-agent shared-signature experiment

Four separate agent memory states, one capturing publisher and three agents
that did not capture the incident. Use all 80 development targets, seed 17,
and two layouts: identical poison record IDs across recipients, and distinct
released poisons[1:4] across recipients. Partition clean records by a stable
hash. All agents make real model calls on their own retrieved contexts; do
not relabel cached single-agent answers as multi-agent observations.

The publisher derives a claim artifact and a local detected-record-ID list.
Receivers get (a) no update / attention only, (b) shared exact-ID blocklist,
(c) shared captured sample with cosine filtering, (d) shared claim entailment,
(e) shared claim+attention, or (f) native CoordGuard gate. Claim recipients
receive only the question, extracted claim and provenance hashes, not poison
locations or benchmark labels. Log publication, delivery, payload bytes,
receiver state, affected records, and answers. Compare non-capturing agents;
cluster all layouts and agents by target. Report shared-ID and distinct-ID
results separately. A single-model, serial local harness is not evidence of
network deployment, heterogeneous production fleets, social contagion or a
herd-immunity threshold. E36 supplies separate reader-transfer evidence.

## E43: operations, cost, update and revocation audit

Record signature extraction time and serialized bytes once per incident,
component filtering and answer-generation wall time, and actual complete
pipeline time for each method. Warm model loading is separated from incident
setup. Randomize method order deterministically within each case. Report
latency as measured on this host, with paired target intervals; do not turn
shared preprocessing timing into a claim of measured end-to-end speedup.
The cosine baseline precomputes its captured-sample embedding once per
incident; log that setup separately. Recipient embeddings are computed from
their actual contexts. The local harness shares read-only model weights and
cached captured-sample embeddings, while message authorization and mutable
agent registries are separate; this can favour baseline setup latency and
must not be presented as measured network deployment cost.
Hash reader weight files before and after the suite. Changing signatures must
not change these files; classifier fitting is distinct from reader training.
Test serialize/reload equality and signature revocation on calibration cases
before deployment. Inspectable entailment scores are an explanation artifact;
human interpretability itself remains unmeasured while reviews are deferred.

## E44: fresh external-memory diagnostic / confirmation gate

Audit MemMorph record availability. Do not run a new attack generator or call
a third-party reimplementation an official released MemMorph dataset. MemForm
has released paired cases and deterministic action labels; inspect schema and
the native protocol before specifying any port. Hold out whole families and
exclude the schema-inspection family from fresh evaluation. Never pass condition
names, family IDs, gold labels, or oracle memory to a defence prompt. A missing
capture or insufficient unseen records is a recorded eligibility failure, not
permission to synthesize an attack. Release a separate frozen diagnostic
protocol before any external-data model outcomes. Whether it qualifies as the
powered primary confirmation depends on the development power calculation.
The concrete independent P2 diagnostic is specified in
[MEMFORM_DIAGNOSTIC_PROTOCOL.md](MEMFORM_DIAGNOSTIC_PROTOCOL.md). Its 212
held-out families and document-filter-only TrustRAG comparator do not fulfil
the full primary confirmation specification, regardless of its outcomes.

## Statistics and completion

Save raw per-case/per-arm answers, detector scores, actual context hashes,
refill composition, timing, agent messages and immutable input/code hashes.
Checkpoint each arm. Target/family is the independent unit. Use paired target
bootstrap B=2000, seed=0, exact paired tests for one binary outcome per target,
and explicitly declared Holm families. Aggregate repeated sessions/agents
within target before uncertainty estimates. Report useful-evidence token
retention only as a proxy; task correctness is the utility endpoint. No failed
phase is skipped; no missing data, human label, or test is marked passed.
