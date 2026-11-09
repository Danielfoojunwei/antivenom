# MemMorph preparation extension and local validation

Prepared 3 November 2026 after reviewing completed QA, MemForm and sharing
results. This is new engineering and posthoc analysis. It preserves every
original scientific source, result, manifest and the frozen preparation v1.
All work before the 6 to 8 November sprint is preexisting hackathon work.

## Questions this extension can answer now

The local registry tests whether a published signature reaches two local
receiver objects consistently, whether conflicting or stale updates are
handled deterministically, and whether revocation survives restart and delayed
delivery. A permanent tombstone prevents every later revision of that logical
ID from reactivating it. Filtering always recomputes from the supplied original
memory; revocation cannot undo earlier actions or earlier memory writes.

The matched-source module gives extraction and the joined raw-semantic
comparator the same canonical raw and rewritten capture views, excluding IDs
and scorer labels. A second, explicitly separate comparator scores every
unique source view and takes a fixed maximum. This uses up to twice the number
of NLI pairs. Equal information is not equal computational or token cost.
Neither variant is selected after observing outcomes.

Bound run records retain the declared plan, configuration, method, capture
control, model and parser identities, original and post-filter contexts, raw
outputs, extraction status, failures and timing fields. They reject records
that do not match the expected inputs. An inert integration test connects
mistaken publication, filtering, revocation, restart and exact input recovery
to an explicitly defined toy selector. It tests state plumbing, not LLM safety.

## Evidence boundaries

Synthetic callback values are fixtures, not semantic accuracy measurements.
Hashes bind reported data; they do not authenticate publishers, certify real
execution or establish independent campaigns. Two receiver objects do not
establish network delivery, authenticated publication, heterogeneous fleets
or distributed revocation latency. The inert selector projection is not a
replacement for the unknown native MemMorph prompt.

The current semantic filter scores memory against an extracted hypothesis.
Its scope field is descriptive text, not a verified current-task applicability
gate. Label invariance tests prevent scorer leakage but do not prove the same
tool remains usable in legitimate contexts. Native selected-tool accuracy
also does not by itself establish completion of the executed task.

## Completed-record audit

The separately frozen [component audit](COMPONENT_UTILITY_AUDIT.md) checks
actual saved all-target records and identically paired nonblank sensitivities.
It is posthoc descriptive, without new significance tests, new inference,
threshold changes or response substitution. It asks what changes when
attention is added to entailment, and whether a history remains at all.

## Next empirical controls

1. Exact always-drop-history, using the native empty-history fallback and
   identical prompts on every clean and attacked case. Make independent
   uncached calls for each declared arm. Report setup and actual timing
   separately; saved no-memory responses use a different prompt condition.
2. Matched-information policy abstraction versus both declared raw-source
   semantic comparators and cosine, with common calibration procedures and
   explicit pair/token costs. Prespecify the comparison family.
3. Legitimate same-tool contexts, unrelated and mistaken captures, and actual
   post-revocation decisions. Keep capture/extraction failures in denominators.
4. Native author-issued data, reviewed harness reproduction, untouched campaign
   groups and blinded extraction/applicability/scoring review.

The native clean utility margin, operating point and sample size are not
frozen here. Choose and justify them before native outcomes. The existing
future endorsement margin .05 and original zero-loss swarm criterion retain
their original scopes. Nonsignificance is not equivalence.

## Reproducible local checks

Run `.venv/bin/python experiments/verify_memmorph_extensions.py` from the
project root. It verifies the old scientific manifests and v1 preparation,
pins the new software separately, runs old and new CPU tests, and writes a
report retaining the blocked native-artifact gate. It loads no model, calls
no tools, executes no downloaded native runtime and generates no attacks.

The exact MemForm drop-all control is a separate local diagnostic, not native
MemMorph or fresh confirmation. Its planning path does not load a model; its
explicit execution path requires the shared lock and an idle-host check. A
busy or uninspectable host is a stop condition, never permission to pause
another experiment.
