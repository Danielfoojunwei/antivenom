# ANTIVENOM research answers and next tests

**4 November publication preparation:** the [full manuscript](../paper/manuscript.md),
[matched-comparison design](PUBLICATION_CONFIRMATION_PROTOCOL_V1.md), outcome-free
power, six-method software contracts and [blinded review v2](PUBLICATION_HUMAN_REVIEW_V2.md)
are prepared. See [current readiness](PUBLICATION_READINESS.md). This adds no
efficacy result: fresh incidents are missing, all eligible local MemForm
families are used, and independent human ratings remain blank.

The completed local experiments establish attack mitigation under trusted
capture, but they do not yet establish selective preservation of useful memory,
an abstraction advantage over raw semantic matching, or native MemMorph
protection. The completed-record audit makes the first limitation concrete:
OR emptied all 212 poisoned MemForm histories. The added exact empty-history
control, completed on 4 November, now supports a narrower positive result:
signatures retain more clean-task accuracy than disabling memory. Added
poisoned-history protection remains unestablished.

## What was built and tested now

The [completed-record component audit](COMPONENT_UTILITY_AUDIT.md) verified
1,384 saved contexts without new inference. It checked detector vectors,
flag unions, deletion or refill, resulting context hashes, paired answers and
all-target denominators. It is posthoc descriptive, not fresh confirmation.

New local software implements matched raw/rewritten capture access, a portable
signature registry with permanent revocation tombstones, and run records bound
to the exact expected context, method, capture and configuration. An inert
integration test connects mistaken sharing, filtering, revocation and restart.
These checks demonstrate software behaviour; fake scorer values and toy
selectors are not model accuracy or human semantic validation. The reproducible
[verification report](../results/memmorph_extensions_verification_v1.json)
records 94 passing CPU checks (31 original and 63 new), zero skipped tests,
unchanged bindings for 30 original scientific manifests and 597 referenced
files, and preservation of the E37 first-70 prefix. It retains the blocked
native-artifact gate: zero native cases and zero new model calls.

The [exact drop-all control](MEMFORM_DROP_ALL_CONTROL.md) completed all 424
independent local calls after the competing experiment exited. Its separately
recorded runtime guard yielded only our worker when new local work appeared;
checkpoints resumed unchanged. The [paired result](../results/memform_drop_all_summary_v1.md)
and [completion audit](../results/memform_drop_all_completion_audit_v1.json)
passed full coverage, parser/scorer, frozen-input and reader-weight checks.
The earlier 94 software checks remain software evidence; the 424 added calls
are actual local model answers, and native MemMorph cases remain zero.

## Answers to the research questions

| Question | Current answer | Decisive remaining test |
|---|---|---|
| Can removing implicated evidence reduce poisoned behaviour? | Yes in the tested local scopes. Oracle localization and deployed local filters are different evidence. | Independent native campaigns with unchanged author harness. |
| Does a compact extracted signature add value over the captured text itself? | Unestablished. A cosine comparison does not isolate abstraction from semantic matching, and the old comparator did not expose both capture views. | New matched-source raw NLI versus policy NLI with common calibration and explicit pair/token cost. |
| Do signatures add value over disabling memory? | Yes for clean-task accuracy here: entailment 95.28%, OR 93.40%, drop-all 83.02%. Their corrected paired advantages are supported. Extra poisoned-history protection is unestablished. | Untouched native replication and matched raw-source semantics; no noninferiority inferred from this diagnostic. |
| Does the MemForm result prove selective preservation of useful poisoned history? | No. All 212 poisoned OR histories became empty history, and every prompt/raw answer now matches exact drop-all. Entailment emptied 207. | Memory-dependent clean and poisoned tasks plus blinded passage/applicability review; the exact drop-all control itself is now complete. |
| Is attention a free improvement? | No. It can add attack protection but adds clean removals and observed clean answer losses. | Prespecified protection/utility comparison; no threshold selected from these outcomes. |
| Can non-capturing receivers benefit from sharing? | Yes versus distinct-ID blocklists in the completed local sharing scope. Superiority over cosine and clean preservation remain unestablished. | Independent incidents, matched strong baselines and legitimate same-tool use. |
| Can a mistaken signature be revoked? | Local tombstones and exact input restoration now pass software tests, including restart and delayed publication. | Actual model decisions after revocation, then authenticated network delivery and operational recovery tests. |
| Have we cured MemMorph? | No native cases have run. Compatible author-issued data and native harness review remain missing. | Native reproduction followed by captured-excluded transfer, not a renamed MemForm result. |

## What the new audit says about attention

In clean MemForm histories, adding attention removed 128 extra experiences and
changed five correct entailment answers to wrong OR answers, with one reverse.
Clean correctness was 95.28% for entailment and 93.40% for OR. In the distinct-ID
sharing scope, adding attention removed 718 additional labelled-clean passages;
57 receiver answers changed from correct to wrong and 13 reversed. The 240
receiver answers remain clustered within 80 incidents. These associations are
not a causal mediation estimate or a new corrected superiority claim.

The saved actual no-memory MemForm answers give 82.55% correctness and 6.13%
poisoned-action endorsement, versus poisoned OR 83.02% and 8.02%. They use
different prompt conditions (`None` versus the empty-history fallback), so
their proximity does not establish equivalence. The exact drop-all arm is now
complete below. The full [audit and case inventory](COMPONENT_UTILITY_AUDIT.md)
retain all families and identical nonblank subsets for every comparator.

## What the completed empty history control establishes

Each method comparison uses the same 212 families, with all failures retained.
Entailment improves clean accuracy over exact drop-all by **12.26 percentage
points**, paired descriptive 95% interval **[8.02, 16.98]**, Holm8
**p=1.73e-6**. OR improves it by **10.38 points**, **[6.13, 14.62]**,
**p=2.09e-5**. This supports useful clean-task performance beyond turning
memory off, rather than merely a software capability claim.

On poisoned histories, OR and drop-all both give 83.02% correctness and 8.02%
poisoned-action endorsement. All 212 prompts, raw responses and predictions
match. Entailment endorsement is 8.96%, a +0.94-point difference with Holm8
p=1.0. Added attack protection is unestablished; strict joint superiority is
inconclusive for both signature methods. Zero observed difference is not
equivalence or noninferiority, and no margin was chosen from these outcomes.
The conservative simultaneous OR poisoned-effect bounds remain broad at
[-23.33, 23.33] points, despite the zero empirical bootstrap interval.

Drop-all parse failures are 4.25% per condition, versus 0.94% on clean
signature histories and 4.25% on poisoned signature histories. These failures
stay in operational accuracy denominators. All-target and paired nonblank
sensitivities are identical; nonblank does not mean human-verified semantics.
Actual answer timers total 22.77 minutes, plus incompletely retained setup
and resource waiting; later collection is not a controlled latency comparison.

The defensible local claim is: **incident-derived filtering retains more
clean-task accuracy than disabling memory, while the tested poisoned OR path
reproduces empty-history outcomes.** That is useful evidence for the system's
operating tradeoff. It does not isolate abstraction, establish selective
useful-history preservation within attacked contexts, or validate MemMorph.

## The novelty question

Reusable defensive memory is prior work.
[AgentAntibody](https://arxiv.org/html/2608.04053v1) learns security boundaries
and uses contrastive conditions/exclusions to protect benign neighbours.
[A-MemGuard](https://arxiv.org/html/2510.02373v1) archives negative reasoning
lessons and revises actions. The candidate ANTIVENOM contribution is a
capture-derived representation that directly filters evidence before the
reader, with explicit reuse, sharing and measurable operating costs. Its
empirical advantage under a matched information budget still needs testing.

The current tool-policy filter is also task-unaware at its scoring boundary:
it receives memory and a signature, not the current task state. A textual
scope field alone cannot establish legitimate same-tool selectivity. That
must be tested rather than inferred from the schema or from label-leakage
checks. Adding task conditioning would be new development and would need its
own calibration and untouched evaluation.

## The minimum convincing paper result

A strong central question is whether a captured incident can produce a
portable abstraction that protects new memories better than raw semantic
matching or disabling memory, while meeting a justified clean-task criterion.
The evidence needs all of the following:

1. A clearly named, independently reviewed fresh benchmark and native task
   outcome. Author-native MemMorph reproduction is required if claiming
   MemMorph protection; it is not a universal prerequisite for a scoped
   paper. In that target, report selected tools and retrieval exposure
   separately and label storage-time versus post-incident read-time stages
   and capture information. Its record-level benign FPR allowance is not a
   clean-task utility margin.
2. Untouched, independently reviewed campaign/capture groups, excluding the
   captured record and exact rewrite; task rows and receivers do not inflate
   independent sample size. Prespecify uncertainty, correction family,
   utility margin and power before native outcomes.
3. Exact drop-all, raw-source semantic and cosine controls; representation,
   attention and applicability ablations; honest extraction, refusal, parse,
   model and missing-result denominators.
4. Benign contexts requiring the same tool or memory, unrelated and mistaken
   captures, and actual recovery after revocation. Include blinded extraction
   faithfulness, applicability and scoring review.
5. Direct, stage- and information-labelled comparison with the closest
   reusable-defence approaches. Distinct implementation alone does not
   establish broad novelty or guarantee publication.

The [MemMorph paper](https://arxiv.org/html/2605.26154v1), especially sections
3 and 5 and Appendix B.5, defines the native target. A validated local port,
if authors later endorse one, must remain labelled separately from a native
export. No paid APIs or other hosts are authorized by this preparation.

For the present hackathon demonstration, the defensible story is reusable
incident response with an honest protection/utility tradeoff and a verifiable
local revocation lifecycle. Track 4 remains the recorded project anchor; all
pre-sprint work must be disclosed. This does not establish autonomous
contagion, authenticated publication or production fleet safety.
