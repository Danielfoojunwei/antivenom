# Remaining-runs queue

Authorized 29 October 2026. The frozen scientific recipe is
`docs/REMAINING_RUNS_PROTOCOL.md`. This batch is a transfer/development
extension; it does not turn previously inspected questions into a fresh test.

## Queue and live progress

The queue runs serially, under an exclusive lock, with a separate process for
each reader. Read `results/remaining_queue_status.json` for the current phase,
process IDs and failure/completion state. For current target and saved-arm
counts without loading models, run:

```sh
.venv/bin/python analysis/remaining_progress.py
```

It also saves `results/remaining_progress.json`. The phase logs are
`results/remaining_prepare.log`, `remaining_llama.log`, `remaining_mistral.log`,
`remaining_composite.log`, `remaining_gate_cache.log`, `remaining_analysis.log`
and `remaining_integrity.log`. Reading a log is sufficient; do not start a
second queue while the lock is held.

| Phase | Scope | Completion requirement |
|---|---|---|
| Prepare | NQ calibration 20; tier-2 50+50 canonical contexts and clean CG scores | all expected IDs; cached baseline compatibility checks |
| Llama | 20 calibration; HotpotQA 50 + MS-MARCO 50, all 13 arms | coefficients frozen first; 100 complete targets |
| Mistral | same scope, separate calibration | 100 complete targets |
| Composite | NQ development 80; four fresh single-poison contexts and eligible captures per target | selection before answers; 80 complete targets |
| Gate replay | Qwen tier-2 100, cached clean NLI probabilities | recover historical printed rates; paired uncertainty |
| Analysis | per-reader results, gates, composite and clustered reader pooling | full coverage; saved JSON and readable report |
| Integrity | identities, masks, manifests, selection and rescoring | no model inference; all checks pass |
| Human status | two independent 302-row review files | external labels; blank files stay pending |

Llama and Mistral preserve their E22 v1 z threshold of 0.25. Ordinary greedy
decoding is accelerated only after three calibration prompts match the masked
decoder byte-for-byte. Blocked answers keep the original decoder. Every
completed answer arm is checkpointed separately; completed final rows are not
regenerated on resume. A failed phase stops the queue and records its log.

After resolving a reported failure, resume with:

```sh
.venv/bin/python -u experiments/run_remaining.py
```

The active queue manifest is `results/remaining_queue_manifest_v2.json`.
An initial restart-only tuple/list serialization problem was caught and
corrected during calibration, before any tier-2 answers were generated.
The original queue source/manifest are preserved in `results/provenance/`;
the calibration and experimental recipes were unchanged. The corrected
manifest has passed a serialization round-trip/resume check.

## Human and data dependencies

Independent reviewer files are `data/validation/independent_review/reviewer_a.csv`
and `reviewer_b.csv`, with instructions in that directory. Both are blank.
Run `analysis/human_validation_gate.py --require-complete` after human labels
arrive; incomplete or failing validation exits nonzero. No model-generated
labels are substituted for humans.

All 300 locally released PoisonedRAG questions have already been used in
calibration, development or earlier evaluation. A new reader is not a new
question set. The available SafeRAG data are a different Chinese task; they
cannot establish the intended unseen-poison English claim. No compatible
fresh released set has been identified in the bounded source check so far.
[CPA-RAG's public repository](https://github.com/lcy5201314/CPA-RAG) currently
contains a release notice, and the examined
[RAGuard download script](https://github.com/RAGuard-AI/RAGuard/blob/main/datasets/download_datasets.py)
prepares clean data rather than supplying released poisoning records. The
three repository-tree checks and commit IDs are saved in
`results/released_data_availability.json`. Do not run attack generators to
fill this gap.

Consequently, the queue may finish every available automated run while human
validation and fresh gate confirmation remain pending. Its completion state
names those dependencies explicitly; it never marks them passed.
