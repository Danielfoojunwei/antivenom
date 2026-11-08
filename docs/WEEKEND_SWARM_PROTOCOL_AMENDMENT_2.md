# Amendment 2: analysis-only additions (8 November 2026, written about 15 minutes after the run started)

**No sprint outcome has been opened or summarised.** The run (commit b6dd0cd, manifest sha256 5432de80…) is in progress. This amendment adds no arms and no model calls, and changes no runner code. It changes only how already-planned arms are compared and what wording a result may support. It is committed and hashed before any outcome is viewed.

## Motivation
An external audit of the draft report (8 November) found that:
- the decisive comparison for the claim-signature idea is against the closest alternative that has the **same confirmed incident information**, namely sharing the raw record with a similarity matcher (a semantic fingerprint). This was not a pre-specified test;
- "not significantly different" was being written as "the same", and "similar" as "unchanged", without an equivalence margin.

## Added test (secondary family, Holm with T1b–T8)
| Test | Assumption | Only factor changed | Reference | Endpoint |
|---|---|---|---|---|
| T9 | Sharing a question-scoped claim protects receivers more than sharing the raw caught record (cosine matcher), given the same captured incident | payload: claim signature vs raw sample (each with its natural receiver rule, as in T1) | A2 | attacked endorsement; clean accuracy also reported |

Both arms (A3, A2) already run on identical incidents. T9 is two-sided: the result may favour either payload, and a null is reported as a null.

## Equivalence and non-inferiority margins (fixed now)
- **No-harm wording** ("keeps clean accuracy", "no clean loss") is allowed only if the lower bound of the 95% interval for clean-accuracy difference (arm − untreated) is above **−0.05**. Otherwise the wording must give the observed difference and its interval.
- **"Similar blocking" wording** is allowed only if the 95% interval for the attacked-endorsement difference lies within **±0.05**. Otherwise the observed difference and interval are given, and neither "same" nor "better" is said.
- The 0.05 margin is the one Daniel chose for future confirmation on 29 October, before any sprint data.

## Wording rules for the report (from the audit; binding on the sprint write-up)
- No universal mechanism claims, such as "every working poison must state its claim" or "attention cannot be escaped". Mechanism statements are about the tested records.
- No field-wide statements, such as "existing defences share nothing" or "prior work only examines form". Comparisons name the specific defences compared.
- "No training" becomes "no fine-tuning of the reader; uses a pretrained NLI model, a fitted logistic combiner and calibrated thresholds".
- "Never sends attacker text" becomes "does not send the full raw record".
- "Acts only when the claim is present" becomes "acts only when the NLI score for the claim crosses a calibrated threshold".
- Priority ("first") claims are removed or explicitly marked as unverified.
