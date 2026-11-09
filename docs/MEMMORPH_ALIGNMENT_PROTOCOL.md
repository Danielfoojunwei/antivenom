# ANTIVENOM native MemMorph alignment — preparation v1

Prepared 3 November 2026. This is new development after the completed QA,
MemForm and E42/E45 evaluations, not an amendment of their scientific sources.
It is preexisting work for the 6–8 November sprint. No result on MemForm or QA
is renamed MemMorph. No native MemMorph efficacy result has been obtained.

## Research question and current gate

Can one independently confirmed compromised memory provide a conditional
tool-policy signature that reduces later native MemMorph tool hijacking on
other memories, with explicit legitimate-task and operational costs?

The primary source is [MemMorph](https://arxiv.org/html/2605.26154v1), especially
sections 3, 5 and Appendix B. The native endpoint is actual tool selection
after memory processing, not a short QA answer. The paper describes ReAct,
Mem0, rewritten stored memories, and three tool-use benchmarks. Its storage
filters and retrieval-time post-incident response have different information
and intervention stages; they must not be treated as interchangeable.

An author-linked MemMorph harness and saved record archive were not found in
the paper or the current targeted source search. Mem0 is a dependency, not
the MemMorph evaluation release. Third-party implementations are not used as
official data. This access gap blocks native validation. Missing data must
not be filled with newly optimized attacks, hand-authored poison, MemForm,
or results from the old QA runner.

## What this implementation does

`src/antivenom/tool_policy_signature.py` constructs a capture-only extraction
prompt and validates exactly four nonblank fields: asserted condition,
asserted rationale, induced tool preference, and scope limitations. It does
not assume that every assertion in a compromised record is false. It does
not supply a corrected policy or a gold safe tool. Scorer metadata and opaque
case/campaign identifiers are excluded from extraction inputs.

Parsing is a new strict policy: exact JSON object, no extra or duplicate
keys, fences, missing fields or non-string values. Invalid extraction retains
the exact raw decoder output and hashes, and passes memories through unchanged
without retries, repair or attention fallback. It remains an operational
failure in the planned denominator. This does not change historical R2.

The filtering functions consume actual post-rewrite memory texts and an
explicit NLI scoring callback. The focal candidate is entailment-only;
optional OR is an ablation motivated by the already observed QA/swarm clean
costs. This choice is development-informed, not a retroactive preregistration.
A raw-sample semantic baseline receives the same captured text without claim
extraction. Thresholds must be explicitly supplied; none has been calibrated
or selected for MemMorph. No refill is added by this adapter. Scope text in
a hypothesis is not a verified applicability gate; its semantic behaviour
requires human review and native tests.

`src/antivenom/memmorph_eval.py` validates a saved-fixture export contract,
preserves full denominators, scores actual selected tool names, and keeps
retrieval exposure separate from tool-choice attack success. Abstention and
parse failures are separately reported and never count as clean task success.
Per-case labels permit the same tool to be appropriate in another clean task.
The captured raw record and its exact rewritten equivalent are excluded from
transfer contexts. Hash exclusion does not establish semantic independence
of other rewrites; family grouping and manual review remain required.

The fixture validator enforces clean/attacked pairing and identical task/tool
definitions. Task labels, poison IDs and provenance hashes are scorer-only;
the defence receives the real state, tool definitions and memory text. The
model-visible projection is a filtering input, not a replacement for an
unknown native tool-selection prompt. The native harness still needs review
and integration. These modules never invoke an LLM, execute a tool, generate
an attack, or run downloaded upstream code.

Shared capture IDs or raw/stored capture hashes cannot be split across
campaign buckets. Output counts are labelled declared campaign groups, not
independence certified by software. Distinct captures can still share an
attack family; that requires an independent grouping review. Native exports
and author-validated local ports retain different provenance classifications
in both validation and score reports.

## Required author-issued inputs

Under ignored `data/external/memmorph/`, supply:

1. `native_bundle.json`: versioned exported native cases, raw and stored
   confirmed captures, paired clean/attacked contexts, actual tool catalogs,
   scorer-only tool labels, campaign grouping, source hashes and pipeline
   revisions. Follow the `antivenom.memmorph.native.v1` validator contract;
   export conversion itself is not native-harness parity.
2. `native_harness_manifest.json`: exact native system/user prompts, tool
   schemas, writer, retrieval/top-k, parser/scorer, model revisions and
   quantization, and source-file hashes. This file is reviewed metadata; no
   embedded code is executed by preparation tools.
3. `reference_baseline.json`: author reference outputs and configuration for
   clean/attacked native reproduction, with full task/campaign IDs. Reproduce
   the original setting before the separate captured-excluded transfer test.
4. `provenance_review.json`: reviewer, review date, author-linkage evidence,
   native-prompt/scorer and campaign-independence review, classification as native export or explicitly
   author-validated local port, and SHA256 bindings to the preceding files.

Native provenance flags are declarations, not authentication. Human review
must establish author linkage and protocol fidelity. The helper verifies
file bindings and schema, not that the declaration is true. Reference baseline
contents need native execution review; their existence is not reproduction.
The untouched evaluation split and calibration data, independent campaigns,
and all allowed local model configurations are still required.

## Baselines and information budget

The candidate methods and controls are recorded in
`experiments/memmorph_alignment_plan.json`: no defence, conditional claim
entailment, captured-sample cosine, strong raw-sample semantic matching, and
OR ablation; confirmed, unrelated and mistaken capture controls. All
sample-aware methods receive the same one-record confirmed-incident budget.
The official perplexity, classifier and memory-auditor baselines remain
separately labelled storage-time references with their original information
access. A retrieval-time auditor port would be a new labelled comparator.

The native memory auditor uses a different model from our local reader.
Current-Mac-only/no-paid-compute authorization remains in force: do not
silently replace a native API model with Qwen and call it reproduction.
Author-supplied reference outputs or a clearly disclosed compatible local
configuration are needed. Tool selection can be observed using inert tool
adapters; no destructive action needs to be executed.

## Before a scientific run can be frozen

The preparation software can be pinned now. It is **not** an execution freeze:
there are no official task IDs, held-out campaigns, calibrated operating
points, power calculation, approved local native configuration, or reviewed
native prompt/parser yet. Freeze those, the intervention stage, method list,
method order, budgets, failure policy and corrected test family before outputs.
All future model inference must acquire `results/remaining_queue.lock` and
preserve resumable checkpoints and raw logs. No new automation is started.

The primary uncertainty unit is independent campaign/capture; queries and
receivers sharing it do not inflate N. Report all-target attack tool choice,
legitimate choice, abstention, parsing and extraction failures, retrieval
exposure, and timings. Pair methods on identical cases and report paired
campaign uncertainty with multiplicity correction after the family is fixed.
The scoring module currently supplies descriptive rates and paired campaign
differences only; it performs no significance test or success declaration.

Attack reduction must beat a strong matched-information comparator in the
prespecified analysis to support added protection. Utility preservation needs
its own prespecified endpoint and criterion; none is inferred from a small p
value for attack reduction or a nonsignificant clean difference. MemMorph's
benign-record FPR calibration is not a clean-task accuracy allowance. The old
.05 future endorsement margin and zero swarm clean margin retain their old
scopes; neither is repurposed here. Even zero observed attack successes does
not demonstrate universal immunity. Human scoring/semantic validation is
required and has not passed.

## Commands and honest status

Run software checks only:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*memmorph*.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_tool_policy_signature.py' -v
.venv/bin/python experiments/prepare_memmorph.py --freeze-software
```

Exit 2 from preparation is expected while native inputs are absent. The status
is saved in `results/memmorph_alignment_status.json`; no model is loaded.
The immutable software manifest covers new sources and tests, not old results.
Future reviewed native exports can be descriptively rescored with:

```sh
.venv/bin/python analysis/memmorph_score.py \
  --bundle data/external/memmorph/native_bundle.json \
  --observations results/memmorph_native_observations.jsonl \
  --output results/memmorph_native_descriptive_summary.json
```

The input observation file must come from the reviewed native parser, one
explicit selected/abstained/parse-failure result per planned case. Existing
reports are not overwritten. No synthetic fixture is accepted as native
evidence. Passing these tests establishes software behaviour only. The
software cannot prove native effectiveness without the missing artifacts,
native execution, independent outcomes and human review.
