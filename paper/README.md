# ANTIVENOM manuscript and evidence tables

Start with [manuscript.md](manuscript.md). It is a complete scoped empirical
draft, with unresolved validation clearly labelled. It is not a submitted,
accepted or author-approved paper. The authors, affiliations and venue have
not been invented.

The supported completed finding is local clean-task utility beyond exact
empty history. The distinctive abstraction advantage over matched raw-capture
semantics, fresh independent confirmation, human validity and native MemMorph
protection are not completed findings.

The next-study [scientific design](../docs/PUBLICATION_CONFIRMATION_PROTOCOL_V1.md)
is now frozen separately, with four margin-free primary superiority components
and Holm4. Its [power and availability report](../results/publication_power_v1.json)
uses hypothetical outcome-free assumptions and certifies zero usable fresh
independent local families. An accepted N, fresh cohort, calibration and complete
execution manifest are still missing. The current
[human-review protocol v2](../docs/PUBLICATION_HUMAN_REVIEW_V2.md) prepares 2,641
rows per reviewer; [actual review status](../data/validation/publication_v2/review_status.json)
remains pending, with no human labels or validation pass invented.

## Rebuild the paper evidence

From the project checkout:

```sh
python paper/generate_tables.py
```

Python's standard library is sufficient. No model is loaded, no network call is
made, and no original source/result is written. The command exports four CSV
and Markdown tables, embeds three tables into the manuscript, creates a
standalone SVG figure, and records authoritative source hashes and JSON
pointers in [evidence_index.json](evidence_index.json).

It requires the complete saved input summaries and added-control completion
audit. It verifies the completion audit's bound summary hash. It formats the
already-computed results; it does not rerun inference, recreate an independent
study, change test families or independently validate human judgments. Full
scientific replay must follow the original protocols and their pinned inputs.

The complete added-control table deliberately preserves all eight comparisons,
including inconclusive/adverse point effects, descriptive paired intervals,
conservative simultaneous bounds, discordant counts and Holm8 p-values. The
sharing table similarly retains all five primary comparisons. Percentages are
rounded only at export, while machine-readable original summaries preserve
full precision.

## Contents

- `manuscript.md`: finished draft prose with generated evidence tables.
- `references.bib`: primary-paper and official-software source records.
- `tables/`: CSV and Markdown, regenerated from saved results.
- `figures/exact_control.svg`: two-panel all-target control figure, common
  0–100% axes; paired inference is in the table rather than implied by bars.
- `evidence_index.json`: source hashes, exact JSON pointers and limits.
- `render_manuscript.py`: renders the editable manuscript and completed
  evidence tables as a review PDF, with no research model calls. It requires
  ReportLab and local DejaVu fonts; `--font-dir` can specify their directory.

To render the manuscript in an environment providing those PDF dependencies:

```sh
python paper/render_manuscript.py
```

The default output is
[`output/pdf/antivenom_manuscript_draft.pdf`](../output/pdf/antivenom_manuscript_draft.pdf).
Regenerate it after manuscript changes. The PDF is a review copy of this draft,
not a submitted venue-formatted paper. The standalone SVG is editable vector
evidence; rendering the PDF does not rerun its underlying experiments.

Third-party data and weights are not copied into this directory. Respect
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) and the original dataset and
model terms before redistribution. This is not yet a public release archive;
its purpose is to make the proposed paper and its evidence reviewable.

Before submission, resolve the fresh validation and blinded-review gates,
perform author review and consent, select a venue and format, and perform the
project's release review. Native MemMorph artifacts are necessary only for a
claim of native MemMorph protection. No automatic upload or submission occurs.
