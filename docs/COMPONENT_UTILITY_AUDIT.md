# What the completed component audit adds

This is a **posthoc descriptive audit**, prepared after inspecting the completed
records. It is not fresh confirmation, a new preregistration, a significance
claim or a causal-mediation analysis. No model was invoked, no threshold was
tuned, and original scientific sources and results were not edited.

The [audit source](../analysis/component_utility_audit.py) and its exact inputs
were frozen in a [new manifest](../results/component_utility_audit_v1_manifest.json)
before producing the saved outputs. The original MemForm manifest and Track4
evaluation manifest also verified. The audit checked **1,384 saved contexts**:
424 MemForm condition/family contexts and 960 swarm condition/layout/receiver
contexts. Swarm receivers and the two layouts are not independent new incidents.

For every comparison, the NLI vectors agree across the entailment and OR arms,
entailment flags match the original `.01` threshold, and OR flags match the
union with original attention `z >= 0`. Saved resulting-context hashes match
the actual deletion/refill recipe, or the MemForm no-refill recipe. This checks
the software and saved interventions; it does not validate extraction semantics
or the necessity of individual removed passages.

## A substantial qualification to the MemForm mechanism claim

In all **212/212 poisoned-condition families**, OR removed every supplied
experience before the native memory compiler. The resulting memory was the
native empty-history fallback, `No reusable decision rule has been learned yet.`
Entailment alone removed every experience in 207/212 families. Thus the large
benefit over cosine in this interface does **not** demonstrate that OR retained
useful evidence from poisoned histories. Its poisoned-condition behaviour was
complete history suppression in these records.

| Completed MemForm arm | Correctness | Poisoned-action endorsement |
|---|---:|---:|
| Poisoned memory, untreated | 41.04% | 54.25% |
| Poisoned memory, entailment | 82.08% | 8.96% |
| Poisoned memory, OR | 83.02% | 8.02% |
| Actual saved no-memory prompt | 82.55% | 6.13% |

The actual no-memory prompt is informative but uses `None`, whereas an empty
filtered history supplies the fallback sentence above. Those prompt conditions
are different. The table therefore does not establish equivalence or inferential
superiority, and it cannot stand in for an exact always-drop-history arm on
every clean and attacked task. That exact baseline is an important next test.

On clean histories, entailment removed 55.07% of input experiences on average;
OR removed 70.17%. Adding attention introduced removals in 105/212 clean
contexts, removed 128 additional experiences, and raised the number of fully
emptied clean histories from 48 to 64. Clean correctness was 95.28% for
entailment and 93.40% for OR: five families changed from correct to wrong and
one changed from wrong to correct. These are actual paired saved outcomes,
not modelled counterfactual answers.

## The swarm clean cost is strongly associated with added intervention

In the primary distinct-ID layout, adding attention to entailment removed
**718 additional labelled-clean passages** out of 2,400 initial clean passages.
It added removals in 238/240 receiver contexts. Mean removal rose from 2.04%
under entailment to 31.96% under OR.

Entailment clean correctness was 51.67%, OR 33.33%, and the actual untreated
reference 52.50%. There were 57 correct-entailment/wrong-OR receiver outcomes
versus 13 reverse outcomes. Forty of the 80 incidents contained at least one
receiver correctness loss relative to entailment. These receiver-level counts
are descriptive; uncertainty must still use 80 incident clusters.

On attacked contexts, OR also lowers endorsement relative to entailment
(0.42% versus 9.17%) while lowering attacked correctness (42.92% versus 47.50%).
This is a measured protection/utility tradeoff, not evidence that one component
is uniformly better. The original frozen five-test joint swarm verdict remains
inconclusive. The secondary shared-ID layout is reported separately and must
not be pooled as another independent sample.

Gold-answer token retention is only a proxy. Neither those tokens nor these
record labels certify human semantic utility. Four swarm input contexts contain
repeated passage hashes; positions were validated as recorded, without claiming
semantic independence of repeated passages.

## What to test next

These observations motivate a new, prospectively frozen comparison family:

1. **Always drop retrieved memory**, with the exact same native empty-history
   fallback and reader prompt, on both clean and attacked cases. This asks
   whether the representation offers protection beyond disabling memory.
2. **Raw-capture semantic filtering versus extracted policy filtering**, with
   the same captured information, scorer and operating-point procedure. Cosine
   alone does not isolate the value of abstraction.
3. **Legitimate use of the same tool or policy**, with correct, unrelated and
   mistaken captures. This tests whether capture scope preserves useful memory
   instead of broadly suppressing a decision context.
4. **Independent blind review of capture meaning and paired outcomes.**
   Nonblank text and correct hashes do not establish semantic validity.

These are proposed tests, not results. They must not be represented as additions
to the original frozen experiment family. Native MemMorph still requires
author-issued compatible artifacts, native reproduction and native tool-choice
measurements. Existing MemForm results remain a labelled local port.

## Outputs

- [Machine-readable audit](../results/component_utility_audit_v1.json), including
  all-target results and identically paired nonblank sensitivities.
- [Compact table](../results/component_utility_audit_v1.md).
- [Exact source/input bindings](../results/component_utility_audit_v1_manifest.json).
- [Complete case inventory](../results/component_utility_audit_v1_cases.jsonl),
  retaining IDs, flags, hashes, prediction labels and response hashes for later
  review. This inventory is unblinded audit metadata; no human review is marked
  complete.

Every selected capture in these completed scopes is nonblank, so the nonblank
subsets are identical to the all-target subsets for every comparator. The
historical R2 malformed-capture amendment and the separate Llama blank-claim
limitation remain unchanged. This audit neither repairs nor replaces them.
