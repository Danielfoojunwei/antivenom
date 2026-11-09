# AntiVenom: Question-Scoped False Claims as Portable Antibodies Against Swarm Memory Poisoning

Apart Research Swarm Alignment Hackathon, 6–8 November 2026 · Track 4: Multi-Agent Oversight and Control · Daniel Foo (NTU Singapore)

- **Report:** [paper/report/antivenom_report.pdf](paper/report/antivenom_report.pdf) · **Slides:** [paper/deck/ANTIVENOM_5slide.pdf](paper/deck/ANTIVENOM_5slide.pdf)
- **Sprint work (judged), 6–8 Nov:** frozen protocol [docs/SPRINT_PLAN_FINAL.md](docs/SPRINT_PLAN_FINAL.md), Phase 2 swarm experiment code [experiments/sprint/](experiments/sprint/), results [results/sprint/](results/sprint/) (`analysis.json`, `raw.jsonl`, human and LLM-judge validation), figures, report and deck.
- **Preexisting work (before 6 Nov):** the AntiVenom detector and its calibration (`src/antivenom/`), the packaged tool (`tool/`), development runs, and Phase 1, the pre-registered single-receiver comparison with CoordGuard and TrustRAG (`results/e29_*`, `e31_*`, `e26_*`, `e35_*`). Everything below this header documents that earlier work.
- **Reproduce Phase 2:** `bash experiments/sprint/go.sh` (Apple-silicon Mac, local MLX models; see report Appendix E), then `python experiments/sprint/score.py` and `python experiments/sprint/figures.py`.

---

# ANTIVENOM

Research code for a captured-claim and attention-based defence against
retrieval poisoning. Runs use released PoisonedRAG passages, local MLX
readers, Contriever retrieval and CPU NLI/baselines.

**4 November publication preparation:** [manuscript and evidence tables](paper/README.md),
[current readiness](docs/PUBLICATION_READINESS.md), the matched-comparison
design and blinded review v2 are prepared. The exact 424-call empty-history
control is complete: clean correctness favors entailment by 12.26 points and
OR by 10.38 points over disabling memory. Extra poisoned-history protection
and abstraction benefit remain unestablished. No fresh confirmation or native
MemMorph case has run, no human labels passed, and no paper was submitted.

Read the [final automated evidence assessment](docs/EVIDENCE_REPORT.md) first.
[The evidence and handoff history](docs/PROJECT_STATUS.md) retains earlier claims
and corrections.
[The remaining-runs queue](docs/REMAINING_RUNS_STATUS.md) tracks the newly
authorized Llama/Mistral, composite, cached-gate and final-check batch.
[The lab notebook](docs/LAB_NOTEBOOK.md) preserves the experimental history;
older design documents contain superseded proposals.

The confirmatory test did **not demonstrate primary superiority** over the
implemented CoordGuard baseline. Parity/equivalence was not established.
The gate and continuation controls are exploratory. Human validation is
pending. See the status document for corrected statistical claims.

**3 November completion:** all original automated tests, the 212-family
MemForm diagnostic and E45's 480 actual untreated-clean receiver calls finished;
all required integrity and reader-weight checks passed. Swarm shared OR clean
accuracy was 33.33%, versus 52.50% untreated and 50.83% cosine. Attack blocking
beats distinct-ID blocklists, but added benefit over cosine and the joint
zero-clean-loss claim remain inconclusive. MemForm supports a local poisoned-action
benefit over cosine; it is not powered fresh primary confirmation. Human
scoring and interpretability validation remain deferred, not passed.

## AntiVenom tool (preexisting, written 4 November 2026)

`tool/` is a dependency-free Python package that packages the method for use in any harness: a two-call API, adapters for any retriever, a JSON CLI, an MCP server and a signed signature registry. See [tool/README.md](tool/README.md). It was written before the 6–8 November sprint and is preexisting work.

## Environment and data

The existing `.venv` uses Python 3.12 on Apple silicon. `pyproject.toml` and
`uv.lock` describe the environment. GPU experiments use MLX and require the
cached Qwen model; CPU scoring also needs cached retriever/NLI/auditor models.
See [data instructions](data/README.md) and
[third-party notices](THIRD_PARTY_NOTICES.md). External data/model weights are
not redistributed. Run commands from this repository directory.

## Reproduce or resume the passage-slot control

E34 is complete: 80/80 targets. Its real-vs-placebo accuracy difference is
55.0% vs 51.25% (raw paired p=0.629); the evidence-content explanation is not
established. Original raw outputs and frozen inputs are preserved.

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false .venv/bin/python -u experiments/e34_fixed_slots.py
.venv/bin/python analysis/e32_e34_summary.py
.venv/bin/python tests/continuation_integrity.py
```

E34 resumes by target ID and checks its input/code manifest. Start only one
GPU experiment at a time. Do not start a second copy while it is running.
The raw E34 output is separate from E32 and the frozen confirmatory results.
Its protocol is [CONTINUATION_PROTOCOL.md](docs/CONTINUATION_PROTOCOL.md).

## Reproduce continuation analyses without loading models

```sh
.venv/bin/python analysis/e33_score_aware.py
.venv/bin/python analysis/e35_confirmatory_audit.py
.venv/bin/python analysis/e32_e34_summary.py
.venv/bin/python analysis/remaining_progress.py
```

E33 evaluates stored-context detection only. E35 audits E29 without replacing
the historical confirmatory analysis. Structured JSON, target-level E33 rows,
and readable summaries are under `results/` and `results/rescored/summaries/`.
The analyses verify target identity and score consistency; a successful
code-level audit does not constitute independent human validation.
`results/continuation_environment.json` records the current dependencies and
cached model snapshots, separately from historical run provenance.

## Incident-response continuation (29 October 2026)

Independent blind reviews are deferred at the user's request and do not block
automated runs. Current text-answer results remain rule-scored. The user chose
a 0.05 absolute endorsement non-inferiority margin for a future fresh
confirmation; this does not change earlier pre-registrations.

The E36–E38 queue was resumed from its saved Llama checkpoints after both old
processes stopped. It runs in a detached session. A second, frozen, detached
queue waits for its successful completion and the same exclusive model lock.
See live machine-readable states in `results/remaining_queue_status.json` and
`results/incident_queue_status.json`; confirm process liveness as well as status.

The extension covers captured-excluded detector ablations, mistaken captures,
strong recurrence comparators, candidate-pool retriever transfer, actual
separate agent states and shared updates, latency/setup/weight/revocation
audits, and development-based power planning. Its protocol is
[INCIDENT_RESPONSE_PROTOCOL.md](docs/INCIDENT_RESPONSE_PROTOCOL.md).

A separately frozen [MemForm P2 diagnostic](docs/MEMFORM_DIAGNOSTIC_PROTOCOL.md)
uses 20 calibration and 212 held-out families from released records. It is a
local memory-formation port, not MemMorph or the powered primary confirmation.
An author-released MemMorph record archive has not been located in the source
search. No attack generator is used. The diagnostic is complete; see the final
evidence assessment for paired effects, corrected tests and limitations.

## Track 4 swarm extension (30 October 2026)

The [Track 4 protocol](docs/SWARM_TRACK4_PROTOCOL.md) fixes shared OR as the focal
method against E42's shared record-ID blocklist and captured-sample cosine. Its
480-call E45 supplement supplies untreated clean receiver answers, after the
original incident queue succeeds and releases the same model lock. Original
scientific source files, method recipes and queues remain unchanged.

The focused analysis pairs by incident, includes failed captures in its main
denominator, and separately reports a nonblank-capture sensitivity. It tests
attack reduction and clean performance, with conservative uncertainty that
does not turn zero observed losses or a nonsignificant difference into proof
of no harm. The zero clean-loss criterion here does not change the user's .05
endorsement margin for a future fresh confirmation. Human reviews are deferred.

```sh
.venv/bin/python tests/swarm_track4_preflight.py
.venv/bin/python experiments/freeze_swarm_track4.py
.venv/bin/python -u experiments/run_swarm_track4.py
```

Inspect `results/swarm_track4_status.json` and actual process liveness before
starting or resuming; do not start a second supervisor. Final focused outputs
are `results/swarm_track4_summary.json` and the corresponding text summary.
This is shared protection among homogeneous serial local agents, not a test
of autonomous contagion or network authentication.

**Preexisting-work disclosure:** the ANTIVENOM code, data preparation, analyses
and this extension developed before the 6–8 November 2026 sprint are preexisting
work. The eventual report must distinguish them from work performed during the
hackathon. Track 4 is the intended anchor; no submission has been made.

## Native MemMorph alignment (new preparation, 3 November)

The [MemMorph alignment protocol](docs/MEMMORPH_ALIGNMENT_PROTOCOL.md) adds a
separate conditional tool-policy signature adapter, captured-sample semantic
control, saved native-fixture contract and actual tool-choice scorer. It does
not rename MemForm results or modify the completed scientific experiments.
Software checks use synthetic fixtures only; they do not establish MemMorph
effectiveness. Native evaluation is blocked until the official saved memories,
harness/prompts/scorer, reproduction references and source review are available.
See `results/memmorph_alignment_status.json` for the machine-readable gate.
