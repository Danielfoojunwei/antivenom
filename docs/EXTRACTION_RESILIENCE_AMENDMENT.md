# R2: malformed extraction output is an invalid capture

Recorded after an actual failure, before resuming: E37 stopped at target
71/80, test423, on capture index 2. Captures 0/1 were saved; no variants or
reader answers for this target existed. The strict JSON parser raised
JSONDecodeError (expected comma, column 56). The 70 completed targets have
350 nonblank captures and 70 nonblank selected claims. Preserve all completed
records, checkpoints, logs, original scientific sources and frozen manifests.

This is an explicitly post-start exception-handling amendment, not an
unchanged original parser or a repaired valid-signature result. Do not tune
from the failed target's gold answer, downstream answers or detector scores.

Keep the prompt, greedy decoding, 160-token extraction cap, model and parser
unchanged for successful JSON. Catch **only JSONDecodeError** from that parser.
Record the full raw output in ignored checkpoints, its hash, the sample hash,
reader, script/arguments and parser error. Return an empty dictionary, using
the existing no-JSON/missing-field fallback: the sample's first sentence as
question and an empty claim. Do not fix quotes, infer missing text, regenerate
until successful, substitute another model/signature, or pass a gold answer.
Other exceptions still fail. Missing-field/no-object behavior is unchanged.

The first malformed reply was not retained by the original failed process.
Resume makes the same frozen greedy extraction call once for the unsaved
capture; retain and handle that output under the policy above. Already saved
captures and answers are not regenerated. Future malformed extraction calls
in the queued incident suite receive the same explicit policy. The current
Mac and shared model lock remain the only execution resources.

All planned target IDs remain in operational end-to-end results, including
failed captures. Blank hypotheses are a capture-prerequisite failure, not
evidence that a valid claim signature detected unseen poison. At final
analysis report failed-capture counts, selected-capture validity, and raw
operational results. Add a separately labelled paired sensitivity retaining
only cases with nonblank selected question/claim; apply the same subset to
every comparator, and never replace the all-target main report. No equivalent
or superiority conclusion may hide that exclusion or the post-start amendment.
For future MemForm results retain all planned families and disclose any
invalid P1 signature; any valid-capture-only sensitivity is secondary.

Implement this as an explicit external parser guard around the original
frozen scripts, not by editing antibody.py or relaxing old hash assertions.
Freeze the new guard/launcher and this amendment separately. Actual runtime
identity includes both the original manifest and R2. E36's completed Llama
and Mistral records stay unchanged. The current-Mac-only runtime R1 trial
and its strict valid-signature/exactness requirements stay unchanged.
