# Completed-record component utility audit

Posthoc descriptive audit. No model calls, no tuned thresholds, no fresh confirmation.

All selected captures are nonblank; each sensitivity uses identical comparator records.

| Scope / condition | Independent units | Contexts | OR extra removals | OR / entail correctness | OR / entail endorsement | Entire input removed (OR / entail) |
|---|---:|---:|---:|---:|---:|---:|
| memform / clean | 212 | 212 | 15.09% | 93.40% / 95.28% | 4.25% / 2.83% | 64 / 48 |
| memform / poisoned | 212 | 212 | 0.59% | 83.02% / 82.08% | 8.02% / 8.96% | 212 / 207 |
| swarm_distinct_ids / clean | 80 | 240 | 29.92% | 33.33% / 51.67% | 0.00% / 1.25% | 0 / 0 |
| swarm_distinct_ids / attacked | 80 | 240 | 6.83% | 42.92% / 47.50% | 0.42% / 9.17% | 0 / 0 |
| swarm_shared_ids / clean | 80 | 240 | 29.92% | 33.33% / 51.67% | 0.00% / 1.25% | 0 / 0 |
| swarm_shared_ids / attacked | 80 | 240 | 7.21% | 43.75% / 48.33% | 0.83% / 7.92% | 0 / 0 |

MemForm poisoned OR removed every input experience in every family and produced the native empty-history fallback. That limits a claim of selectively preserving poisoned-history utility.
The saved actual no-memory prompt has different text from that fallback. It is informative diagnostically, but cannot substitute for an unrun, exact always-drop-history arm on every clean and poisoned input.

The unblinded JSONL inventory covers every context and retains IDs, hashes, flags, labels and outcome metadata for later review; it is not a human-reviewed or blinded evaluation.

See the machine-readable result and frozen manifest for all-target/nonblank tables, exact input hashes, validation details and limitations.
