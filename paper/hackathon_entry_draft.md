# One Captured Poison, a Protected Swarm: Sharing Claim Signatures Against Memory and Retrieval Poisoning in Agent Swarms

**Daniel Foo** · Nanyang Technological University (NTU), Singapore
Apart Research Swarm Alignment Hackathon, 6–8 November 2026 · Track 4: Multi-Agent Oversight and Control

**Research question:** when one agent in a swarm detects one poisoned memory or retrieval record, can that detection be turned into a control that protects the other agents, without costing them accuracy when no attack is present?

## Abstract

Agents in a swarm read from shared memory and retrieval, so a handful of planted records can mislead many agents at once. Today's defences treat every agent separately: each must detect the poison on its own, and the main way to warn others is to share record identifiers, which fail as soon as copies differ. We ask whether one agent's detection of one poisoned record can protect the rest of the swarm. ANTIVENOM turns a captured record into a claim signature: the reader extracts the question it targets and the false claim it pushes. Receivers flag retrieved passages that entail that claim, combine this with the reader's own attention, and replace flagged passages with the next-ranked evidence. On a pre-registered test of 100 untouched PoisonedRAG questions, ANTIVENOM cut false-answer endorsement from 76% to 7–12%. That matches CoordGuard and TrustRAG, with no difference surviving correction. At its deployed setting it discarded 11% of clean passages against CoordGuard's 21%, and it ran faster than both. In a swarm of serial agents, sharing the signature instead of record IDs cut fooled receivers from 62% to 9%, with clean accuracy unchanged (52% vs 53%). Adding ungated attention blocked almost every attack but lowered clean accuracy to 33%. [WEEKEND: one sentence on the gated swarm test on fresh incidents.] Results are rule-scored, and blind human labels are pending.

*(Word count: ~225 including the placeholder sentence; check after filling it.)*

## 1. Introduction

During the Hugging Face agent incident, agents passed work and information to hundreds of others (METR, 2026). In such a population, a poisoned memory or retrieval record is not one agent's problem. Every agent that retrieves it can be misled, and agents copy what they read into shared state. Track 4 asks what oversight and control still work when the untrusted side is many agents. Here the untrusted side is a set of planted records that many agents read, and the control is a warning one agent can pass to the rest.

We study a narrow, practical version: **when one agent catches one poisoned record, what should it tell the others?** Two obvious answers are weak. Sharing the record's identifier misses renamed or paraphrased copies. Sharing the raw record helps, but leaves each receiver to decide what to remove, and broadcasts the attacker's text.

ANTIVENOM shares a *claim signature* instead: the question the record targets and the false claim it pushes. The design borrows from immunology, as AgentAntibody and GRAD also do. One captured antigen yields an antibody, the antibody circulates, and recognition combines a specific signal (entailment of the claim) with a general one (the reader's attention).

**Contributions.**
1. A swarm defence that converts one captured poisoned record into a shareable claim signature, with a gate, an adaptive check, an innate check and a neutralising step. It needs no training and leaves model weights unchanged.
2. A pre-registered confirmatory test showing parity with the strongest published defences on attack blocking, with better precision, speed and failure profile.
3. A swarm experiment showing that sharing claims beats sharing record IDs, and that ungated attention costs clean accuracy.
4. [WEEKEND] A gated swarm test on fresh incidents, with blind human scoring.

## 2. Related work

**Retrieval poisoning.** PoisonedRAG (Zou et al., USENIX Security 2025) plants a few passages that make a reader give a chosen false answer. We use its released poison and never generate attack text.

**Single-agent defences.** TrustRAG filters passages by clustering and self-assessment. RobustRAG aggregates isolated answers. CoordGuard (arXiv 2610.24834) removes coordinated clusters of passages. "Ranking Is Not Deciding" (arXiv 2610.33849) shows that the question prefix PoisonedRAG adds to every poison is a shortcut, and sets a reporting protocol that we follow.

**Multi-agent and immune-inspired defences.** Five recent defences are closest to ours. None shares a claim-level signature derived from one captured record; they share trust or reputation scores, per-item status, or nothing.

| Defence | Threat | What is shared after a detection | Needs | Benchmarks | Code |
|---|---|---|---|---|---|
| MAPLE-Guard (2608.00426) | Poisoned memory items spreading across a multi-agent system | Per-item and per-agent trust, hazard and reputation | Memory provenance metadata; evaluator correctness feedback | MMLU, LongMemEval, AppWorld, CSQA, InjectAgent | Yes |
| PerMIT (2610.28987) | Poisoned persistent memory from tools and web | Per-entry endorsements on exact bytes; freeze or evict | Two-LLM split, confirmation gate, Lean proofs | Trojan Hippo, τ²-bench | On request |
| SecureCollaRAG (2608.04366) | Poisoned documents from a minority of sources | Per-source reliability score | Trained GNN, several independent sources | NQ, HotpotQA (PoisonedRAG), MediNote, Finance | Yes |
| GRAD (2610.22828) | Decomposition and memory attacks in one agent's trace | Nothing between agents | Supervised trace classifier | DecomposedHarm, MCP-SafetyBench, MT-AgentRisk | Supplement only |
| AgentAntibody (2608.04053) | Prompt injection crossing unstated user boundaries | Nothing between agents; one agent reuses abstract "epitope" antibodies | Extra LLM calls; user feedback on misses | AgentDojo, AgentDyn, LatentBoundaryBench | Not checked |
| **ANTIVENOM (ours)** | **Retrieval and memory poisoning read by many agents** | **A ~250-byte claim signature from one captured record** | **No training; weights unchanged** | **PoisonedRAG (NQ, HotpotQA, MS MARCO)** | **Prepared** |

AgentAntibody is the closest idea: it turns one confirmed attack into an abstract antibody and reuses it, and its ablation shows that raw-text memory fails to transfer. We apply the same principle to poisoning, express the antibody as an entailment-checkable false claim, and share it across agents. SecureCollaRAG is the only one evaluated on our benchmark; it relies on majority agreement across independent sources, whereas ANTIVENOM propagates one agent's detection. It reports 12–21% attack success on NQ and HotpotQA under PoisonedRAG with other readers and settings, so its numbers are not directly comparable to ours.

**Benign cost.** "The Price of Safety" (2609.22818) argues that memory defences must be judged on benign traffic too. Our false-alarm analysis and the gate respond to that.

## 3. Method

**Threat model.** An attacker plants k near-duplicate records into a store that several agents read. Each record is written to make a reader give one false answer. One agent, the *finder*, obtains one of these records, for example from an alert or an audit. Receivers do not know which of their records are planted. The attacker does not adapt to the defence in this study.

**Pipeline.**
1. **Capture and signature.** The finder's reader extracts, as JSON, the question the record targets and the false claim. For yes/no questions it restates the claim as a self-contained sentence. The signature is about 250 bytes.
2. **Broadcast.** The signature, not the record or its ID, is sent to receivers.
3. **Gate.** A receiver acts only if some retrieved passage entails the claim (NLI probability at or above a threshold fixed on calibration questions).
4. **Adaptive check.** Each passage is scored for entailment of "The answer to the question Q is C" (DeBERTa-v3 NLI).
5. **Innate check.** The reader's attention from its last prompt tokens to each passage, at one layer, z-scored within the context and corrected for slot position.
6. **Neutralise and answer.** Flagged passages are deleted and replaced by the next-ranked passages. The reader answers with the same prompt and greedy decoding.

**Biology mapping.** Captured antigen → antibody design (signature) → circulation (broadcast) → innate and adaptive recognition (attention and entailment) → neutralisation and clearance (deletion and refill).

**Setup.** PoisonedRAG released poison for NQ, HotpotQA and MS MARCO; Contriever retrieval reproducing released scores to within 3×10⁻⁶; top-10 contexts; Qwen2.5-7B-Instruct (4-bit, MLX) as the main reader, with Mistral-7B and Llama-3-8B for transfer. Thresholds and weights are fitted on NQ questions 1–20 only.

**Baselines and controls.** CoordGuard (always-filter, with and without refill), TrustRAG (ported from released code), captured-sample cosine similarity, shared record-ID blocklists, and deletion of the same number of passages at random or by lowest rank. In the weekend swarm test we add two published multi-agent defences: SecureCollaRAG (each agent's retrieval treated as a source; its graph network trained only on calibration and disjoint training targets) and MAPLE-Guard's deterministic retrieval gate (provenance terms neutral, since our passages carry no provenance). The protocol is in docs/WEEKEND_SWARM_PROTOCOL.md.

**Scoring.** "Endorses" checks whether the answer asserts the target false answer, with rejection and abstention cues. "Correct" checks the gold answer with word boundaries and counts abstention as not correct. Both are rule-based; a blind human labelling sheet of 302 responses is prepared.

**Confirmatory protocol.** Before touching HotpotQA and MS MARCO questions 51–100, we froze and hashed the protocol, primary claims and the detector. Every arm ran once. Statistics: exact McNemar tests, target-level bootstrap intervals and Holm correction over the primary family.

## 4. Results

### 4.1 Capability: parity with the state of the art

Pre-registered test, 100 untouched questions, Qwen reader:

| Arm | Endorses false answer | Correct |
|---|---:|---:|
| No defence | 76% | 19% |
| ANTIVENOM v1 (pre-registered primary) | 12% | 54% |
| ANTIVENOM v2 (frozen improved detector) | 7% | 53% |
| CoordGuard + refill | 5% | 47% |
| TrustRAG | 12% | 53% |
| Random deletion, same count | 64% | 26% |
| Clean context, no attack | 4% | 61% |

Neither pre-registered superiority claim was supported. At the matched recall of CoordGuard, our detector removed more clean passages (Holm p = 0.50). Defended accuracy on clean contexts was 35% against 37% (p = 0.73). Endorsement differences against CoordGuard and TrustRAG do not survive correction. Random and low-rank deletion leave most attacks intact, so the gain comes from detection.

On Mistral-7B the defence transferred (endorsement 69% → 11%, CoordGuard 9%, TrustRAG 7%). On Llama-3-8B, 95 of 100 claim extractions came back blank, so that run does not test the signature.

### 4.2 Beyond parity

| Question | ANTIVENOM | Strongest comparator | Source |
|---|---|---|---|
| Clean passages discarded at the deployed setting | 11.4% | CoordGuard 20.6% | Fresh test |
| Clean discarded, one poison among clean passages | 2.6% (87% of poisons caught) | CoordGuard 71.6% (95% caught) | Development |
| Clean discarded without the question prefix, same recall | 8.9% | CoordGuard 52.3% | Development |
| Seconds per attacked question | 18.4 | CoordGuard 24.6, TrustRAG 35.9 | Timing audit |
| Wrong (non-target) answers under attack | 13% | TrustRAG 43% | Fresh test |
| Abstentions under attack | 27% | CoordGuard 42% | Fresh test |
| Recall under the unluckiest captured record | 95% (signature + attention) | 67% (signature alone) | Development |

Captured-sample cosine similarity shares most of the precision gains in question answering. It is a strong, simple baseline, and we report it everywhere.

### 4.3 Swarm: share the claim, not the ID

80 incidents; one finder and three receivers whose planted records carry different IDs (used development questions):

| What the finder shares | Receivers endorsing false answer | Receivers' clean accuracy |
|---|---:|---:|
| Nothing (untreated clean reference) | — | 52.5% |
| Record IDs | 62.5% | 52.5% |
| The raw sample (cosine filter) | 2.1% | 50.8% |
| Claim signature (entailment only) | 9.2% | 51.7% |
| Claim signature + attention (ungated) | 0.4% | 33.3% |

Sharing the signature beat sharing IDs by 62 points (Holm p = 0.00025). It did not beat cosine (p = 0.50). Adding ungated attention blocked nearly everything but cost 19 points of clean accuracy, because the attention rule always flags at least one passage.

### 4.4 [WEEKEND] Gated signature sharing on fresh incidents

[Placeholder. Planned: freeze the gate threshold from calibration, run gated sharing against record IDs, cosine, SecureCollaRAG and MAPLE-Guard's retrieval gate on fresh incidents, report receiver endorsement and clean accuracy with paired intervals, and report blind human agreement with the scoring rule.]

Exploratory single-agent evidence motivates this test. On the fresh questions, the gate fired on 91% of attacked contexts and 4% of clean ones. It restored clean-context accuracy from 35% to 61%, while endorsement rose from 12% to 17%.

## 5. Discussion

ANTIVENOM does not win on the main objective. It matches the state of the art on blocking. What it adds is a different operating profile: it keeps more good evidence, costs less time, fails by abstaining rather than by inventing answers, and produces a small artefact that can protect other agents. For swarms the practical lesson is simple: **share what the poison says, not where it is**, and only cut once the claim has matched.

Two findings matter beyond this method. First, PoisonedRAG poisons for one question are near-copies, so a trivial similarity rule reaches near-perfect detection (AUC 0.99–1.00). Detection numbers on this benchmark should be read as upper bounds. Second, every defence we tested, including CoordGuard, loses about a quarter of clean accuracy when it runs on unattacked contexts. Benign-case cost needs to be a primary metric.

## 6. Conclusion

One captured record can be turned into a claim signature that protects a swarm. It blocks as well as the best single-agent defences, keeps more good evidence, and transfers across agents where record IDs fail. The open problem is benign-case cost, which a claim-entailment gate appears to solve and which we test on fresh incidents this weekend.

## Prior work disclosure (required by the sprint rules)

This project builds on the author's preexisting ANTIVENOM code and experiments, written before 6 November 2026 and not yet published: the detector, the single-agent experiments (E01–E30 and the incident suite), the confirmatory test in Section 4.1, the analyses in 4.2, and the swarm comparison in 4.3. These are marked as preexisting in the README and here. Work done during the sprint: [LIST — e.g. the gated swarm protocol and its run on fresh incidents (4.4), blind human scoring, this report and slides].

## Appendix A. Limitations

- Answers are rule-scored; human labels are pending.
- One main reader. Mistral transfers; Llama's claim extraction failed.
- Most swarm and robustness results reuse development questions; only Section 4.1 is fresh confirmation.
- Cosine similarity matches ANTIVENOM in question answering, and is cheaper.
- The attacker is not adaptive, and poisons come from one benchmark of near-duplicates.
- The swarm is serial and homogeneous; it does not model autonomous contagion, authentication or transport.
- The defence assumes one agent can obtain one poisoned record.

## Appendix B. Dual-use and ethical considerations

The work is defence-only. All poison comes from the published PoisonedRAG release; no new attack content was generated. Describing which poisons escape detection could help an attacker. We report aggregate patterns, such as yes/no claims and dissimilar paraphrases, but do not release new escaping examples. Shared signatures could themselves be spoofed to make agents delete legitimate evidence. Deployments should authenticate signatures and gate their use, as studied here.

## References

[To complete: SecureCollaRAG 2608.04366 (github.com/Aquarids/scr-pub); MAPLE-Guard code github.com/xiong-wenjun/MAPLE-Guard; PoisonedRAG; TrustRAG; RobustRAG; CoordGuard 2610.24834; Ranking Is Not Deciding 2610.33849; MAPLE-Guard 2608.00426; PerMIT 2610.28987; Byzantine-tolerant collaborative RAG 2608.04366; GRAD 2610.22828; AgentAntibody 2608.04053; The Price of Safety 2609.22818; METR 2026 incident report; Contriever; DeBERTa-v3 NLI; Qwen2.5.]
