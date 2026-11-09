# Deferred local execution of the exact empty history control

On 4 November 2026 the user explicitly requested the frozen 424-call control
after the other local experiment finishes, without interfering with it, followed
by an assessment of whether signatures add value over disabling memory. This
authorizes the new waiting supervisor described here. The old preparation
protocol had no waiting supervisor. This is a disclosed operational addition,
not a change to its scientific recipe or an inference of permission from a
local flag.

## Preserved scientific inputs

Keep `experiments/memform_drop_all_control.py`, its tests, protocol, frozen plan,
the original signatures/answers, all old manifests, and the reader weights
unchanged. The control still makes 424 independently executed answer calls,
212 already-used families times two declared conditions, using the exact native
empty-history fallback, fixed prompts/parser, temperature, token limit,
quantization and R1-selected allocator configuration. It does not copy answers
between byte-identical clean and poisoned prompts.

The analysis is separately frozen before added-control outcomes in
`results/memform_drop_all_analysis_manifest_v1.json`. It retains eight
family-paired comparisons, exact McNemar tests with Holm8 correction, paired
intervals and simultaneous bounds. Human review remains deferred. Neither
nonsignificance nor a zero observed difference establishes equivalence.

## Waiting and eligibility

The new supervisor owns only `results/memform_drop_all_wait.lock` while waiting.
It does not load a model or hold the shared model lock during that period.
The exact currently observed coordinator, model child, guard and inhibitor
identities are frozen in `results/memform_drop_all_wait_config_v1.json`.
Both start time and full command bind an identity; PID reuse does not prove an
old process is still running or that a new one is safe. A missing child alone
is not eligibility while its coordinator or another model worker remains.

Read-only process inventory checks continue after those identities disappear.
New or unknown Python/model workers block initialization. Two clear snapshots
are required, followed by a fresh check inside the frozen runner's shared
`results/remaining_queue.lock`. A new waiting worker is never a reason to
resume, suspend, kill, reprioritize or restart somebody else's experiment.
This workflow sends no messages to other chats and inspects no other project's
scientific outcomes.

The frozen runner's broad guard treats every unrelated Python process as a
possible model worker. This wrapper replaces only that operational inspection
callback, using the following narrowly bound evidence:

- Exact standard-library HTTP server and resource-tracker identities are
  classified by their complete observed commands. This is not a general
  exemption for Python programs.
- Two old orphaned multiprocessing workers have exact PID/start/command,
  cumulative CPU time and baseline RSS witnesses. The complete read-only
  open-file name inventories show Python, NumPy/SciPy CPU libraries and an
  existing log, with no observed MLX/Metal/Torch or other model backend. An
  exemption applies only while identity, CPU time, non-rising tiny RSS and
  the complete open-file inventory remain unchanged. Generic multiprocessing
  workers are not exempted.

Every witness and classification is pinned separately with the wrapper,
tests and this amendment. Missing or incomplete inspection, changed process
identity, CPU use, memory use or open files fails closed. These observations
are engineering evidence, not mathematical certification of physical GPU
idleness. Polling has transition races; no claim of atomic coordination with
unrelated projects is made.

## Our model process and resumption

The supervisor launches one child only after eligibility. It preserves the
frozen control body and replaces only process inspection plus a reader wrapper
that checks eligibility immediately before/after model initialization and
before each answer call. It forwards every generation argument and result
unchanged. These operational checks add overhead and do not create a controlled
latency comparison with earlier methods.

If competing model work appears, only our child exits gracefully between
calls. Its bound checkpoints remain intact, its shared lock and model memory
are released by process exit, and the supervisor waits again without loaded
weights. Completed checkpoints resume under the frozen recipe; an answer is
never transplanted into another arm. Failures other than resource waiting are
recorded and require inspection rather than silent retries or skipped arms.

The supervisor owns an idle-sleep inhibitor through its lifetime; the frozen
child retains its own inhibitor during answer generation. Neither overrides
closed-lid sleep, power loss or user action. Host sleep and later contention
extend wall-clock time; no calendar finish time is promised.

## Completion and notification

Analyze only after the complete status, 424 unique bound checkpoints, final
output hash, parser replay, reader-weight integrity and exact family coverage
all pass. Inspect the paired summary, update the evidence report with the
used-family local diagnostic, and tell the user what is supported,
contradicted or inconclusive about additional value over disabling memory.
No result is renamed native MemMorph or fresh confirmation.

The accompanying heartbeat checks the supervisor and frozen inputs, recovers
only a genuinely exited instance under the same eligibility rules, and never
duplicates a live job. Healthy waiting and progress are non-actionable;
completion, meaningful failure and required user action are actionable.
After delivering the completed assessment, delete that heartbeat. The prior
original-suite heartbeat remains deleted.
