# Weekend swarm protocol (Apart Swarm Alignment Hackathon, 6–8 November 2026, Track 4)

Status: **plan only, written 4 November.** No sprint code exists yet. Everything below is implemented and run during the sprint, and is the judged contribution. Freeze this file (hash it) before the first outcome is observed.

## Research question
When one agent in a swarm detects one poisoned memory or retrieval record, can that detection be turned into a control that protects the other agents, without costing them accuracy when no attack is present?

## Design
- **Swarm:** one finder and three receivers per incident, serial, homogeneous Qwen2.5-7B readers, as in E42/E45. Receivers' planted records carry distinct IDs.
- **Incidents:** fresh only. Use PoisonedRAG targets never touched by any earlier experiment. Candidates: NQ 101+ if released; otherwise HotpotQA/MS MARCO targets outside 1–100. Confirm availability and count at sprint start, and fix the sample size before any outcome.
- **Calibration:** the gate threshold and every baseline's threshold are fixed on NQ 1–20 only, at a declared clean-removal budget (≤5% of clean passages).
- **Two conditions per incident:** attacked store and clean store, so benign cost is measured for every arm.

## Arms (what the finder shares → what receivers do)
| Arm | Shared | Receiver action | Role |
|---|---|---|---|
| Untreated | nothing | answer as is | floor |
| Record IDs | IDs of the captured record | drop matching IDs | weak sharing baseline |
| Sample cosine | the captured record text | drop passages above a cosine threshold | strong simple baseline |
| Claim signature, ungated | claim signature | entailment OR attention, delete + refill | existing method |
| **Claim signature, gated (focal)** | claim signature | act only if a passage entails the claim; then entailment OR attention, delete + refill | **weekend method** |
| SecureCollaRAG | per-source reliability (its own mechanism) | trained GNN credibility filter | published multi-agent baseline |
| MAPLE-Guard retrieval gate | per-item trust/hazard state (its own mechanism) | rule-based re-rank and filter | published lightweight baseline |

## Baseline ports (sprint work)
**SecureCollaRAG (arXiv 2608.04366).** Public code is at github.com/Aquarids/scr-pub; ask the user before cloning. It assumes several independent sources with a malicious minority. Mapping: each swarm agent's retrieval is one source and returns its top-5. The GNN is trained on the same released PoisonedRAG poison, using only calibration targets (NQ 1–20) plus a disjoint training split that never overlaps evaluation targets. Report that the paper's own numbers (12–21% attack success on NQ/HotpotQA) used other readers and settings.

**MAPLE-Guard retrieval gate (arXiv 2608.00426).** Public code is at github.com/xiong-wenjun/MAPLE-Guard; ask before cloning. Port only the deterministic retrieval gate: re-rank score and answer-key cluster dominance, with fixed weights from the paper. Our passages have no provenance or taint metadata, so the provenance/lineage terms are set to neutral and this is disclosed. It makes no extra LLM calls.

Both ports are checked against their papers' descriptions before the evaluation run. Any deviation is written down here before outcomes.

## Endpoints
- **Primary 1 (protection):** receiver endorsement of the false answer on attacked stores, gated signature vs record IDs, cosine, SecureCollaRAG and MAPLE gate.
- **Primary 2 (benign cost):** receiver correctness on clean stores, gated signature vs untreated.
- **Secondary:** receiver correctness on attacked stores; clean passages discarded; seconds per question; message bytes.
- **Human check:** two blind labellers score a stratified sample of receiver answers; report agreement with the rule scores.

## Analysis
Unit = incident (average its receivers). Paired bootstrap 95% intervals and exact paired tests; Holm correction across the primary family. No non-inferiority claim unless a margin is fixed here before outcomes; a nonsignificant difference is not equivalence. Report every arm, including failures.

## Timeline (single local GPU)
- Fri: confirm fresh targets, freeze this file, ask to clone and port both baselines, calibrate on NQ 1–20.
- Sat: run all arms, one GPU job at a time; release human-label sheets.
- Sun: analysis, fill report Section 4.4 and the abstract sentence, final PDF ≤8 pages; submit before 11:59 PM AoE.

## Disclosure
The ANTIVENOM detector, the single-agent experiments, E29 and E42/E45 are preexisting work. This protocol, the baseline ports, the gated swarm run, the human check and the report are sprint work.
