# Exact empty-history control result

New diagnostic on already-used local MemForm families; not native MemMorph or fresh confirmation.

All424 uncached calls and integrity checks completed. Each comparison uses212 paired families.

| Condition | Method | Correctness | Poisoned-action endorsement | Parse failure |
|---|---|---:|---:|---:|
| clean | entail | 95.28% | 2.83% | 0.94% |
| clean | OR | 93.40% | 4.25% | 0.94% |
| clean | drop_all | 83.02% | 8.02% | 4.25% |
| poisoned | entail | 82.08% | 8.96% | 4.25% |
| poisoned | OR | 83.02% | 8.02% | 4.25% |
| poisoned | drop_all | 83.02% | 8.02% | 4.25% |

Differences below are signature minus drop-all. Higher correctness and lower endorsement are favourable.

| Comparison | Difference pp | Paired95% CI pp | Holm8 p | Directional advantage |
|---|---:|---|---:|---|
| clean:entail-drop_all:correct | +12.26 | [+8.02, +16.98] | 1.72853e-06 | supported |
| clean:entail-drop_all:endorsed | -5.19 | [-8.49, -2.36] | 0.0205078 | supported |
| clean:OR-drop_all:correct | +10.38 | [+6.13, +14.62] | 2.08616e-05 | supported |
| clean:OR-drop_all:endorsed | -3.77 | [-6.60, -0.94] | 0.107422 | inconclusive |
| poisoned:entail-drop_all:correct | -0.94 | [-2.36, +0.00] | 1 | inconclusive |
| poisoned:entail-drop_all:endorsed | +0.94 | [+0.00, +2.36] | 1 | inconclusive |
| poisoned:OR-drop_all:correct | +0.00 | [+0.00, +0.00] | 1 | inconclusive |
| poisoned:OR-drop_all:endorsed | +0.00 | [+0.00, +0.00] | 1 | inconclusive |

The95% paired intervals are descriptive, not simultaneous. Conservative simultaneous bounds are retained in JSON.

| Method | Clean correctness advantage | Poisoned endorsement advantage | Strict joint superiority |
|---|---|---|---|
| entail | supported | inconclusive | inconclusive |
| OR | supported | inconclusive | inconclusive |

No noninferiority/equivalence margin was selected. A clean utility advantage can be supported while the stricter joint claim remains inconclusive.

Useful-history selectivity is not proved by task outcomes alone. Identical original/control prompts are audited separately; their answer differences cannot be attributed to a different filtering intervention.

The paired nonblank sensitivity retains the same comparator subset. Nonblank capture is not human semantic validation.
