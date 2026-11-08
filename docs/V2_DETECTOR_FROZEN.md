# Frozen v2 detector (frozen 2026-10-28, before any confirmatory tier-2 run)

Design data: NQ 1-20 (calibration), NQ 21-100 (development), and HotpotQA/MS-MARCO 1-50 (tier 1, already used; post hoc). Tier 2 (HotpotQA/MS-MARCO 51-100) has not been touched.

1. **Capture and claim.** Unchanged from v1: the reader extracts (question, false_claim) from the captured poison[0] with `ANALYSE_PROMPT`.
2. **Yes/no rule (E28).** If the extracted question matches `^(are|is|was|were|do|does|did|can|could|has|have|had|will|would|should)\b` (case-insensitive), the reader restates the claim with the E28 `PROMPT` (greedy, 80 tokens). The leading "The record claims (that):" is stripped with the E28 `STRIP` regex. The NLI hypothesis is that sentence. Otherwise the hypothesis is the v1 template: "The answer to the question \"Q\" is C."
3. **Entailment.** `cross-encoder/nli-deberta-v3-base`, entailment probability.
4. **Attention (E27).** Qwen layer 21, last 8 prompt rows, head mean, per-token mass, z-scored within context. Subtract the E27 slot offsets [0.596, -0.097, -0.214, -0.337, 0.235, 0.135, -0.432, -0.323, -0.187, 0.624], then re-z-score. Other readers use their E22 layer; their slot offsets are fitted the same way on NQ 1-20 before tier 2.
5. **Avidity score.** Logistic regression on [logit(entailment), attention z], fitted on NQ 1-20 (coefficients 0.926, 2.507 for v1 signals). It is refitted once on NQ 1-20 with the debiased attention before tier 2, and the coefficients are recorded here.
6. **Operating point.** The threshold that removes 5% of clean passages on NQ 1-20 contexts. It is recorded here before tier 2.
7. **Effector.** Delete + backfill (unscreened), as in the pre-registration.

Primary claims and analysis are unchanged from `PREREG_CONFIRMATORY.md`. The v1 pipeline is also run on tier 2 as pre-registered, and v2 is reported beside it.

**Known residual weaknesses, stated in advance:** order dependence remains (E27 range 0.08); Llama-3-8B transfers only partly (E22); the E28 rewrite can hallucinate entities (seen once in 21); HotpotQA misses not of yes/no form remain.

## Recorded calibration (NQ 1-20, `analysis/v2_calibrate.py` → `results/v2_calibration.json`)
- Avidity coefficients [logit entailment, debiased attention z] = [0.9382, 2.3472], intercept 4.9740.
- Operating threshold 0.09886 (5% clean removal on calibration; calibration recall 1.00).
- One calibration target has a yes/no-form question; it uses the v1 template here, because the rewrite affects only the hypothesis.
