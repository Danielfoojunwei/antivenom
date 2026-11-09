# What must change to be SOTA (26 Oct 2026)

*Inputs: our E01/E02 runs, the side chat's novelty check and E03 smoke test, and a verified sweep of current RAG and memory-poisoning defences. "Verified" below means checked against the arXiv abstract page directly.*

## 1. The landscape as of 26 Oct 2026

**The attack that defines SOTA: DnD** (arXiv 2609.27090, N. Z. Gong's group, Duke, 22 Sep 2026; verified)
- **Divide:** four poisons, each in a different document style and framing. A style ledger and ROUGE-L caps stop them clustering.
- **Doubt:** one poison casts doubt on the evidence for the correct answer without naming it.
- **Results** (from the sweep, which read the full paper):
  - TrustRAG: 2.3% → 29–36% ASR; SeCon-RAG: 2.3% → 26–38%; RAGuard: +58–60 pts.
  - **No public code or poison data.**

**The defence that defines SOTA: CoordGuard** (arXiv 2610.24834, 17 Oct 2026; verified)
- Removes a dense, query-anchored component in embedding space.
- NQ, Qwen2.5-7B: ASR_exp 0.576 → 0.167, at a 13.6-pt clean-accuracy cost. A gated mode keeps clean accuracy at 0.315 with ASR 0.331.
- RobustRAG and ReliabilityRAG reach only 0.512.
- Uses **count-matched deletion controls**. No code link.

**Standard comparison set in 2026**
- DnD's eight: InstructRAG, TrustRAG, SeCon-RAG, RAGuard, RobustRAG, Astute-RAG, ReliabilityRAG, RAGDefender. CoordGuard is added from now on.
- Released code exists for RobustRAG, TrustRAG, InstructRAG, ReliabilityRAG, SeCon-RAG and RAGDefender.

**Closest prior art to the swarm idea**
- CAMA 2608.19701: effective independent sources in correlated multi-agent memories, the "false majority" problem.
- Also SecureCollaRAG 2608.04366, Cordon-MAS 2605.26754, SMSR 2606.12703, and "count sources, not votes" (2610.29178).

**Name collision:** GRAD, "Graph-Structured Antibody Defense", 2610.22828.

## 2. Where we stand, honestly

All of our current signals assume that **poisons are near-clones of each other**:
- near-neighbour deletion (E02);
- antibodies anchored on the sample's leading sentence (E02);
- the side chat's n_eff, complement diffusion and danger index (E03).

That holds for PoisonedRAG (our released source) and **not** for DnD. Near-neighbour deletion is essentially a weaker TrustRAG or CoordGuard. A paper that only beats PoisonedRAG clones would be rejected in Nov 2026.

**E02 tells us something more useful than its headline.** It splits by what actually reached the top-5 (final, n=100 targets; the attack arm and all antibody arms pooled):

| Top-5 contents | No antibody in context | ≥1 antibody in context |
|---|---|---|
| 2 poisons | endorse 1.00 (n=11) | **0.12** (n=104) |
| 3 poisons | 1.00 (n=12) | **0.15** (n=91) |
| 4 poisons | 0.96 (n=28) | 0.59 (n=193) |
| 5 poisons | 0.98 (n=305) | no antibody ever reached context |

- **Once one claim-specific counter-record is in context alongside 2–3 poisons, it wins about 85–88% of the time.** That is far stronger than majority-rules evidence integration predicts.
- **Antibodies fail in retrieval, not persuasion.** Of 696 antibody-arm evaluations:
  - only 247 (35%) placed an antibody in the top-5 with at most three poisons;
  - 219 (31%) had all five slots taken by poison.

**E02 headline (n=100, 95% bootstrap CI; endorsed = validated rule):**
- attack 0.96 [0.92, 0.99]
- best×5 antibodies 0.43 [0.33, 0.53]
- near-neighbour deletion τ=0.75: **0.17 [0.10, 0.24]**, which beats antibodies (McNemar p=4e-5), with ≤1 clean passage removed per target.
- Antibodies lost a few points of clean accuracy (0.53 → 0.47, n.s.).
- This is the piece worth keeping. It does **not** depend on poisons being clones.

## 3. The change in principle: key the defence on the attack's invariant

A poisoning attack can vary **style, wording, coordination and cluster structure**. DnD shows this. What it **cannot** vary is the **target claim**: every supporting poison must assert, or make inferable, the target answer for the target question. The Doubt passage is the exception, handled below.

**SOTA requirement → our change:**
1. **Don't rely on near-duplicate signals** (DnD; sweep point f-3).
   - → **Claim signatures.** From one captured sample, extract the *(question, false claim)* pair.
   - At retrieval time, any record that **entails** the false claim for that question gets the bound counter-record attached. Detection is by an NLI or entailment check, not embedding proximity to the sample.
   - Style diversity doesn't help the attacker, because each diverse poison still has to entail the claim.
   - This is IBM's Digital Immune System signature model applied at the *semantic* level, not the byte level.
2. **Fix the bottleneck E02 found (retrieval crowding).**
   - → **Bound delivery.** The counter-record no longer competes for a top-k slot: it is attached to the retrieved poison it neutralises.
   - It costs no clean slot, so it causes no crowding.
3. **Counter the Doubt passage** (DnD's second component).
   - → Doubt passages attack the *correct* answer's evidence, so they never entail the false claim, and claim signatures won't catch them.
   - Pair the signature with a **source-independence check on the doubted evidence**. Doubt aimed at multiple *independent* clean passages is itself the anomaly. This needs a test, not an assumption.
4. **Correlation from structure, not embeddings** (sweep point f-3).
   - → For the swarm (v3), estimate independence from **which records each agent actually retrieved**, i.e. overlapping record IDs and provenance. Embedding similarity of the text is exactly what DnD defeats.
   - Distinguish this explicitly from CAMA.
5. **Beat CoordGuard on the ASR / clean-accuracy frontier, with count-matched controls.**
   - → Re-implement CoordGuard from its paper; it has no code. Run the released-code baselines (TrustRAG, RobustRAG, ReliabilityRAG, InstructRAG, SeCon-RAG).
   - Plot the frontier.
6. **Scale.**
   - 3 PoisonedRAG datasets (NQ, HotpotQA, MS-MARCO; all released).
   - At least 2 retrievers (Contriever plus e5 or ANCE) and at least 3 readers (Qwen2.5-7B, Llama-3-8B, Mistral-7B locally), plus a frontier model if a key is provided.
   - Bootstrap CIs and McNemar tests (`analysis/summarise.py` already does this).
7. **Rename.** "Antibody" collides with GRAD and AgentAntibody. Use **claim signature** / **bound counter-record**.

**Note on corpus splicing (reviewer point d).** For top-k retrieval with k ≤ 100 and a fixed retriever, merging the true clean top-100 with the injected records is *mathematically identical* to indexing them into the full corpus. The full-corpus top-k is always drawn from that union. Our E01 scores match the released full-corpus scores exactly. The one deviation is the immunologist's paraphrased probe queries, whose clean top-100 we don't have. That has to be fixed or disclosed.

## 4. The evaluation gap we cannot close alone

- **Diverse poison that is actually released is scarce.**
  - DnD has no released data.
  - CoordGuard's stress sets (paraphrase, low-coordination, gate-aware) aren't released.
  - SafeRAG releases human-built conflict cases, but it is Chinese and has ~100 cases per task.
- Under the defence-only rule (no attack generation by us), the options are:
  - **(a) Ask DnD's authors for their poison passages.** This is a user action: an email to Gong's group.
  - **(b) Use SafeRAG's released conflict set** with a multilingual retriever. It is real and diverse, but not like-for-like with DnD.
  - **(c) Relax the rule** for one bounded case only: paraphrase the *released* PoisonedRAG poison into diverse styles. This is the minimal stress test reviewers expect, and it creates no new false claims.
- **Adaptive attacks against our own defence**, which reviewers now expect, conflict with the defence-only rule in the same way. The same three options apply.

## 5. Proposed next experiments (in order)

| ID | What | Why |
|---|---|---|
| E04 | Claim signatures plus bound counter-records on NQ (released PoisonedRAG), vs E02's arms and count-matched deletion | Tests whether removing the crowding bottleneck lifts the 0.44 ceiling |
| E05 | Same on HotpotQA and MS-MARCO; second retriever; Llama-3-8B and Mistral-7B readers | Generality and the scale reviewers expect |
| E06 | Baselines: TrustRAG, RobustRAG, ReliabilityRAG, InstructRAG (released code); CoordGuard (re-implemented) | SOTA frontier |
| E07 | Diverse-poison test via 4(a), (b) or (c) | The test that decides whether the invariant claim holds |
| E08 | Swarm (v3): compartmentalised memories, independence from retrieval-ID overlap, plus fleet-shared claim signatures | Builds v3 directly on E04's primitive; distinguish from CAMA |
