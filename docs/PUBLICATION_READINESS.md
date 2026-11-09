# Publication preparation status - 4 November 2026

The manuscript and review software are prepared. The stronger methods claim
has **not** gained new empirical support from this preparation. No new model
inference, public submission, author outreach or paid/remote compute occurred.

## Completed and reviewable

| Workstream | Deliverable | What it establishes |
|---|---|---|
| Scoped paper | [Full manuscript](../paper/manuscript.md), [PDF](../output/pdf/antivenom_manuscript_draft.pdf), [references](../paper/references.bib) | A complete empirical draft, not author approval or peer review |
| Reproducible evidence | [Table/figure exporter](../paper/generate_tables.py), [hash index](../paper/evidence_index.json), four CSV tables | Traceable formatting of completed results, not independent replication |
| Matched controls | [Six-method contracts](../src/antivenom/publication_study.py), [preparation command](../experiments/prepare_publication_confirmation.py) | Information projections, failure handling, calibration and input gates tested without models |
| Fresh-study design | [Frozen protocol v1](PUBLICATION_CONFIRMATION_PROTOCOL_V1.md), [outcome-free power](../results/publication_power_v1.json) | Fixed scientific question/endpoints; execution still blocked |
| Blinded semantic review | [Current v2 protocol](PUBLICATION_HUMAN_REVIEW_V2.md), [local status](../data/validation/publication_v2/review_status.json) | Full coverage and blank independent rating sheets; no human validation pass |
| Review archive | `output/publication/antivenom_publication_review_v1.zip` and its manifest | Deterministic private candidate for paper/table review, not a public release |

The supported local claim remains: incident-derived filters retain more clean
task accuracy than exact empty history in this MemForm port. Entailment's
paired clean correctness gain is 12.26 percentage points and OR's is 10.38,
with Holm8-corrected evidence. Poisoned OR exactly matches drop-all prompts
and raw answers for all 212 families. Additional protection over disabling
memory, abstraction benefit over raw NLI, general clean preservation and
native MemMorph protection are not established. The draft retains the clean
sharing costs, extraction failures, broad simultaneous bounds and nulls.

## The new decisive question

The candidate focal method is entailment-only, selected after development,
using the four-field tool-policy representation. This is a **new interface**,
not a retrospective redefinition of the completed question-claim method or
the original shared-OR primary. It receives the same canonical raw/stored
capture views as both raw NLI controls and cosine.

The six methods are policy-signature entailment, joined raw NLI, fixed
max-over-views raw NLI, cosine, exact drop-all and untreated. They share a
declared calibration procedure: at most 5% observed benign-record removals
on fresh calibration groups, with explicit tied-score handling. This is
neither a clean-task utility margin nor a population guarantee. Actual model
bodies, input lengths/truncation and calibrated thresholds still need binding.

Four primary paired comparisons use Holm4: clean correctness versus drop-all;
poisoned unsafe decisions versus untreated; and both endpoints versus joined
raw NLI. Unsafe means the poisoned action **or an invalid/missing attacked
decision**. A two-component claim needs both favorable corrected results.
No NI margin is chosen, no failure is safety success and no nonsignificant
difference is equivalence. Raw-max and cosine remain mandatory secondary
robustness results rather than outcome-selected substitutes.

This is a demanding superiority design, not a promise that extraction must
win or that publication requires this exact strongest claim. A negative
result supports a narrower empirical paper. The old .05 future endorsement
margin and strict-zero swarm clean criterion retain their earlier scopes.

## Work that needs external input

1. **Fresh independent incidents.** All 232 eligible released MemForm families
   are used: 20 calibration and 212 evaluation. Another interface, paraphrase,
   renamed ID, receiver or session of these families is not fresh independent
   confirmation. The input-only inventory certifies zero eligible untouched
   local families. Obtain an independently reviewed new cohort; freeze
   campaign grouping, capture exclusion, same-tool/memory-dependent clean
   cases, calibration/test split, primary task pairs and sample size before
   outcomes. The [readiness report](../results/publication_confirmation_readiness_v1.json)
   correctly remains blocked. Preparation cannot launch inference or write
   a complete execution freeze.
2. **Two independent human reviewers.** V2 covers all 212 completed families
   with 2,641 rows per reviewer: 212 extraction, 212 reference-policy, 1,484
   unique experience and 733 unique response ratings. Every human field is
   blank. Release phases in order, give each person only their own file,
   keep administrator mappings private, then preserve both ratings and human
   adjudication. These retrospective labels do not certify a new cohort's
   independence. Software cannot recruit, impersonate or attest a human.
3. **Author decisions and release review.** Add actual authors/affiliations,
   obtain author consent, choose a venue/format and the original code license.
   The private archive excludes external data/weights, reviewer sheets,
   private mappings, logs and source-rich checkpoints. Its hashes and tables
   support review; the archive alone does not reproduce every experiment.
   Full replay needs pinned external inputs and preserved local raw records.
   Review local path/privacy information and third-party terms before upload.

Native MemMorph data and the reviewed author harness are additionally needed
**only if claiming native MemMorph protection**. They are missing. A fresh,
well-scoped local benchmark can support a paper under its own name; it must
not be presented as a cure for MemMorph. No upload or submission has occurred.
All preparation before the 6-8 November sprint is preexisting hackathon work.

## Checks and corrections before new inference

Cross-review found and corrected two software defects before any real human
labels or fresh outcomes existed:

- Human-review v1 reassessment overwrote adjudication entries. Its files and
  hashes remain archived. V2 preserves signed judgments and partial notes,
  binds them to rows/reviewer ratings and rejects tampering. No human work
  was lost; use V2.
- The first preparation gate checked stored text but omitted declared raw
  lineage from global historical/cross-campaign exclusions. The corrected
  gate checks raw and stored hashes. The prior readiness snapshot is preserved
  and the current report discloses the correction.

The original 30 scientific manifests, v1 MemMorph preparation and 597 unique
bound files were reverified; the original E37 first-70 prefix is preserved.
New software checks exercise calibration ties/failures, source/gold leakage,
historical and cross-group overlap, reviewer/adjudication persistence and
archive integrity. They are software checks, not model safety evidence.

## Reproduce preparation without models

From the full project checkout:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python paper/generate_tables.py
.venv/bin/python analysis/prepare_publication_review_v2.py
.venv/bin/python experiments/prepare_publication_confirmation.py
.venv/bin/python analysis/prepare_publication_release.py
```

The power report is already frozen; rerun only to verify the identical plan.
PDF rendering uses `paper/render_manuscript.py` with ReportLab and DejaVu fonts,
independently of research-model dependencies. The archive builder refuses to
replace a changed candidate: preserve it and make a new version instead.
Do not restart completed queues or create another heartbeat for a study
without a fresh input cohort.
