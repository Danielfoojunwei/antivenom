# Continuation protocol — 29 October 2026

This continuation starts after E29–E32 have completed. All new results are
exploratory. Tier 2 has been inspected and is not a fresh confirmation set.
Existing raw results, frozen detectors, and historical hashes are preserved.
Only released benchmark passages are used; no attack text is generated.

## E33: score-aware selection, stored-context analysis

Use NQ development targets 21–100, with calibration restricted to NQ 1–20.
Within each original retrieved top-10, exclude the captured passage and select
the m=1,2,3,4 released poisons with the smallest frozen detector score. Report
recall and the fraction of targets with at least one missed selected poison.
For binary detectors, selecting misses first defines the exact worst case;
ties are broken by original slot index. Report entailment, attention, OR,
calibration-fitted avidity, and CoordGuard AF on identical stored contexts.
Separately combine E21 capture rotation with this selection for entailment
and OR. Exclude the selected captured poison for each capture; include all
five captured samples, even if a captured passage did not reach top-10.

This is a conditional detection stress test. It does not estimate reader
attack success. Removing passages changes attention and CoordGuard geometry,
so stored scores cannot stand in for re-running retrieval and detection in a
new context. No such deployment claim will be made.

## E34: M3 passage-slot placement control

Use all 80 NQ development targets and the exact E32 frozen v1 OR flags,
retrieval, true replacements and next-target placebo replacements. Add two
arms: put true replacements into flagged passage slots in increasing slot
order, and do the same for placebo replacements. Unflagged passages keep
their passage slot. Compare with E32's appended true/placebo arms and deletion.
Use the same Qwen model, prompt, greedy decoder and 48-token cap.

This controls passage ordering/slot placement, not absolute token positions,
token count or passage length. Save passage identity hashes, flags, context
sizes, replacement labels and prompt token counts. Assert exact alignment with
E11a labels and exact replacement counts. Stop on a mismatch. Keep separate
append-only output; resume by target ID without re-generating finished rows.
Freeze input/code hashes before the first generated answer in a separate
`results/e34_manifest.json` file. Model-level repeatability is checked by
reproducing one existing E32 answer before generating new arms.

## Analysis and reporting

Unit is target (not passage or four single-poison variants). Paired bootstrap
95% intervals use 2,000 target resamples with seed 0; binary outcomes also get
exact two-sided McNemar tests. E32 and E34 each have a descriptive family of
six comparisons (three arm pairs × correctness/endorsement), with Holm
adjustment within each family. Additional comparisons are explicitly secondary.
Rescore stored responses with the unchanged frozen scoring rules and report
any mismatch. Do not label outcomes human-validated: the blind label sheet is
still incomplete.

Audit E29 without replacing its historical output: distinguish the frozen
binary v1 primary from the continuous v2 score used by its claim-1 code;
use discrete attainable recall thresholds rather than interpolated quantiles;
show both the historical two-test family and a conservative four-test Holm
sensitivity including both endorsement comparisons. No equivalence or
non-inferiority claim follows from nonsignificant superiority tests.
