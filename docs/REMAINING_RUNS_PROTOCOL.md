# Remaining-runs protocol — 29 October 2026

User authorization: proceed with the remaining runs and tests. This document
is written before new calibration, transfer or composite outcomes. Original
results, scoring rules and frozen code remain unchanged. New files use E36+.
Released passages are used verbatim; no attack passages are generated.

## E36: reader-transfer extension

Readers, serially: `mlx-community/Meta-Llama-3-8B-Instruct-4bit`, then
`mlx-community/Mistral-7B-Instruct-v0.3-4bit`. Evaluation: all 50 HotpotQA and
50 MS-MARCO tier-2 IDs per reader. These IDs have already been examined with
Qwen. This is a pre-specified transfer extension, not fresh-question evidence.

V1 uses the existing E22 files without tuning: Llama layer 18, Mistral layer
15, z >= 0.25, NLI >= 0.01, OR, unscreened deletion and refill. Each reader
extracts its own captured signature. V2 is calibrated only on the 20 NQ
calibration IDs: mean clean original/reversed slot offsets, a logistic model
on [logit(entailment), re-z-scored debiased attention], excluding the captured
slot, and the clean-score 95th percentile as threshold. The existing yes/no
rewrite recipe is applied consistently in calibration and evaluation. Save
all calibration scores and coefficients before that reader's tier-2 runs.

Run all 13 E29 arms with the same 48-token greedy answer cap, including both
defended-clean variants, count-matched controls, CoordGuard and TrustRAG.
TrustRAG's two internal stages retain their existing 256-token caps. Reuse
reader-independent CoordGuard attacked removals only after rebuilding and
checking canonical contexts and validating the cached algorithm on sample
contexts; clean audit scores are computed and saved. A separate geometry gate
uses Q=0.90 of 20 benign NQ calibration scores, fixed here.

Ordinary greedy generation may use mlx_lm only after byte-for-byte agreement
with unblocked masked generation on three NQ calibration prompts for that
reader. Blocked arms continue to use the unchanged masked decoder. If the
comparison fails, use masked decoding for ordinary answers too. Persist this
decision; never switch based on tier-2 outcomes. All arms checkpoint separately
so interruptions do not regenerate completed answers. No non-inferiority or
equivalence claim will be introduced after observing these additional runs.

## E37: rebuilt composite stress test, Qwen, NQ development

All 80 development IDs. Use released passage bodies with no added question
prefix. For each target, form four separately retrieved single-poison contexts
using poison j=1..4, each plus the released clean pool. Extract all five
captured signatures from prefix-free samples. A candidate capture k must
differ from j: the poison used for the signature is absent from the context.
Recompute NLI and attention on each actual reconstructed top-10 context.

Choose an exposed (j,k) pair adversarially against frozen Qwen v1 OR: smallest
poison recall, then largest clean-removal count, then smallest j, then k.
No reader answer is consulted during selection. If no variant retrieves
poison, retain j=1,k=0 as unexposed and report it separately. This is a specific
detector-aware lower-bound stress scenario, not a globally optimized attack.

On the selected context run clean, attack, OR delete+refill, entailment-only
delete+refill, CoordGuard AF+refill, TrustRAG, defended-clean OR and defended-
clean CoordGuard. Save all candidate detector scores, selected identities,
replacement labels and raw answers. Report all-target and exposed-target
outcomes. Gate variants reuse these answers with fixed E30 threshold and
remain development analyses. Passage deletion, refilling and NLI are freshly
computed; stored full-context attention must never substitute here.

## E38: cached gate replay and paired uncertainty

Recompute/save Qwen clean-context NLI scores for the 100 original E29 targets,
using the unchanged E30 threshold. Recover the original printed gate rates
and answer rates within display rounding; stop/report discrepancies rather
than silently replacing historical outputs. Add paired target bootstrap
intervals and exact McNemar comparisons. For E36 readers, use a reader-specific
gate threshold from NQ 1–20 using the E30 rule (minimum attacked non-captured
maximum times 0.999, lower-bounded by 0.0001). Save these thresholds before
evaluation. Also report the separately calibrated CoordGuard geometry gate.
All replay results on used questions are exploratory.

## Fresh data and human validation

Search for released, usable poison records with new question IDs, source,
licence and clean evidence. Freeze a new question split and gate protocol
before any outcome if a compatible source exists. Do not relabel used
PoisonedRAG questions as fresh, generate new attacks, or treat mismatched
single-captured-poison Chinese tasks as confirmation of unseen-poison
English generalization. Record the specific data blocker if none is available.
The two independent human labelers remain an external dependency. Prepare
separate blind reviewer copies and an agreement/acceptance checker; never
populate their columns using model predictions or rule decisions.

## Execution, checks and statistics

One model job at a time. Freeze protocol, code and input hashes in a separate
manifest before execution. Each dataset/reader/target/arm has one result;
resume incomplete targets from per-arm checkpoints. Use an exclusive queue
lock and save PID, phase and counts. Queue failure stops dependent work.
Success requires expected ID coverage, no duplicates, correct context labels,
frozen manifests, answer rescoring, and successful run exit.

Use 2,000 paired target resamples (seed 0), exact McNemar tests, and report
effect sizes and intervals. Reader pooling resamples targets with all readers
kept together; any hierarchical reader bootstrap must state its three-reader
limitation. Holm-adjust superiority comparisons within clearly listed
families. Frozen v1 has no continuous matched-recall ranking: report its
deployed point and use continuous v2 frontier only as a labelled sensitivity.
Do not announce primary superiority, equivalence or human validation from an
unfinished run or a nonsignificant difference.
