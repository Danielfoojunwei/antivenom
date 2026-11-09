# Dormant platform services in deferred control execution

This operational revision on 4 November 2026 preserves the frozen scientific
control, 424-call plan and analysis. It extends the separately recorded
[waiting-runtime amendment](MEMFORM_DROP_ALL_RUNTIME_AMENDMENT.md); all of
that amendment's restrictions remain in force.

The v1 supervisor started and waited without a child or model. Its broad
`inference` process heuristic also matched long-lived, idle macOS platform
providers. They are operating-system services, rather than the competing
research experiment. Only our waiting supervisor was stopped gracefully for
this replacement. Its code, configuration, tests and manifest are preserved,
with the before/after status in
`results/provenance/memform_drop_all_wait_v1_operational_replacement.json`.
No other process was signalled, and no model answer was generated.

The new wrapper/configuration/manifest have explicit v2 paths. The supervisor
lock, status, logs and checkpoint paths are shared with v1 so a duplicate
cannot run. All scientific and analysis inputs remain unchanged.

The only new exemption classification applies to exact observed identities
of these two executable paths:

- `/System/Library/ExtensionKit/Extensions/TGOnDeviceInferenceProviderService.appex/Contents/MacOS/TGOnDeviceInferenceProviderService`
- `/System/Library/ExtensionKit/Extensions/GenerativeExperiencesSafetyInferenceProvider.appex/Contents/MacOS/GenerativeExperiencesSafetyInferenceProvider`

Each exemption also binds its entire command including launch arguments,
PID, parent, start time, unchanged cumulative CPU time and non-rising baseline
RSS no greater than 64 MiB. The exact executable file hash and strict Apple
code-signing requirement are checked live at every boundary. The saved
signature-verification flag is a declaration, not a substitute for that check.
Protected operating-system process open-file inventories are unavailable;
none is invented or treated as verified. This is a separate code-identity
classification for normal platform providers, not an exemption from a research
worker's missing file witness. The existing CPU-spawn exemptions still require
their complete unchanged file inventories and absence of model backends.
Arbitrary system paths, model servers, Python programs and other experiments
are not exempted. Any bound identity, activity, memory, binary or signature
change blocks our next call and causes only our child to release its allocations.

These are bounded observations of dormant normal platform activity, not an
absolute guarantee of physical GPU idleness. Process polling has races;
ordinary operating-system graphics and services remain outside this experiment's
control. Nothing in this revision authorizes interference with another run.

The exact native fallback, prompts, model weights, precision, generation
parameters, independent uncached calls, checkpoints, failure policy and eight
paired statistical comparisons are unchanged. Runtime inspection overhead is
not a scientific speed comparison. The completion heartbeat must use the
v2 launcher and runtime manifest, preserve the v1 evidence, and deliver the
completed value-over-disabling-memory assessment before deleting itself.
