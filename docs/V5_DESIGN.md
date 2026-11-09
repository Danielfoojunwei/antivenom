# ANTIVENOM v5: a hardened, biology-grounded design with new maths

*26 Oct 2026. This revision follows the devil's-advocate review, a prior-art sweep on deep defences, and a negative steering experiment (§0).*

## 0. What the evidence already tells us

- **Text antibodies (E02, interim, 10/100 targets).** They only work when anchored for co-retrieval: endorsement 0.80 without the anchor vs 0.10–0.20 with it at ×5. They also crowd out real passages (clean accuracy 0.60 → 0.50), and flag antibodies yield "I don't know", not a cure.
- **Near-neighbour deletion (τ=0.75)** is the strongest arm so far, because PoisonedRAG's poisons are near-duplicates.
- **Naive single-sample steering failed.**
  - Method: v = h(clean top-4 + sample) − h(clean top-5) at the last token, projected out at layers 14/18/22 with α ∈ {1, 2}.
  - Result: 0 of 6 targets cured, and 1 made worse.
  - Diagnosis: a single difference vector is dominated by content change, not by "deferring to injected context", and it never sees the other four poisons.
  - Consequence: steering is demoted to a stretch goal and only comes back in the denoised form of §3.6.

**Design consequence.** The strongest available signal is **structural**, not semantic. Poison is *many correlated copies of one voice*. Biology has a precise answer to that: immune systems discriminate self from non-self by *pattern* and *context*, not by reading the "argument" of the pathogen.

## 1. Biology → mechanism map (what we learn that we hadn't used)

| Immunology | What it really does | Agent analogue (new) |
|---|---|---|
| **Clonal expansion of pathogens** | A pathogen replicates into near-identical copies | Poison = one claim replicated into k near-duplicate passages. Detect **correlated support**, not content |
| **Complement cascade (opsonisation)** | One binding event tags neighbours with decaying amplification | Flag mass diffuses from the captured sample over the similarity graph (§3.2) |
| **Danger theory** (Matzinger) | Respond to *damage signals*, not to foreignness alone | Intervene only when evidence is **concentrated in one correlated cluster** *and* the action is consequential (§3.3) |
| **Tolerance / anergy** | Ignore self-antigens; require co-stimulation (signal 2) to activate | A passage needs *independent corroboration* (signal 2) before it can drive an answer (§3.1) |
| **Affinity maturation** (germinal centre) | Mutate, select by binding, discard self-reactive clones | Robust minimax optimisation of antibodies against a drift neighbourhood, with negative selection (§3.4) |
| **Polyclonal antivenom** | A mixture covers venom variability | Submodular coverage of the variant space with a greedy (1−1/e) guarantee (§3.5) |
| **Dose–response / therapeutic index** | Potency (EC50) vs toxicity (TD50) | Hill fits for venom and antibody; report TI = TD50_autoimmunity / EC50_neutralisation (§3.7) |
| **Idiotypic network** (Jerne) | Antibodies regulate antibodies, preventing runaway | Self-limiting antibody titre caps crowding (§3.8) |
| **Herd immunity** | Protect the population once immune fraction > 1 − 1/R0 | Swarm thresholds using effective independence (§4) |
| **Trained immunity / memory cells** | Faster, stronger secondary response | Fingerprint cache plus stored antibody; re-read blocking (§3.9) |

## 2. The unifying idea: count *independent* voices, not voices

One quantity serves the passages inside one agent and the agents inside a swarm: the **effective number of independent sources** supporting an answer.

## 3. The maths

### 3.1 Co-stimulation via effective independent support (core, novel combination)

Let passages i = 1..k in the retrieved context support candidate answers. Let s_i(y) ∈ [0, 1] be the support of passage i for answer y, and let ρ_ij be the similarity between passages i and j (cosine of retriever embeddings, clipped at 0). The **correlation-aware effective support** is

$$
n_{\text{eff}}(y) \;=\; \frac{\big(\sum_i s_i(y)\big)^2}{\sum_i\sum_j s_i(y)\,s_j(y)\,\rho_{ij}}\qquad(\rho_{ii}=1)
$$

This is Kish's design effect generalised to correlated sources.
- Five near-duplicate poisons (ρ ≈ 1) collapse to **n_eff ≈ 1**.
- Three genuinely different passages give n_eff ≈ 3.

**Co-stimulation rule (tolerance):** an answer may be asserted only if n_eff(y) ≥ m, or if it agrees with the model's closed-book prior. Otherwise the agent abstains, or gathers more evidence (signal 2).

*Why it hardens the weak spots:*
- Refutation in context doesn't help the attacker, because more correlated copies add ~0 effective support.
- Crowding is irrelevant.
- No captured sample is needed for this layer.
- The attacker's counter is to make the poisons *diverse*. That costs retrieval, since diverse passages are less similar to the query, so we get a **retrieval–diversity trade-off** we can measure.

### 3.2 Complement diffusion from the captured sample (replaces threshold deletion)

Instead of "delete all with cos ≥ τ", diffuse a tag from the captured sample p₀ over the passage similarity graph W (row-normalised):

$$
\mathbf f \;=\; (1-\beta)\,(I-\beta W)^{-1}\,\mathbf e_{p_0}
$$

This is personalised PageRank. f_i is the "opsonin mass" on passage i. Down-weight each passage's retrieval score by score_i · exp(−γ f_i), rather than deleting.
- β controls how far the cascade spreads, and decays with graph distance.
- Benign passages that are only *topically* close receive little mass, because they don't sit in the dense near-duplicate cluster.
- Down-weighting can be undone, unlike deletion.

### 3.3 Danger signal: influence concentration

Let Δ_i = KL(π(·|C) ‖ π(·|C∖{i})) be the leave-one-out influence of passage i on the answer distribution. Group passages into similarity clusters c and define

$$
D \;=\; \frac{\sum_c \big(\sum_{i\in c}\Delta_i\big)^2}{\big(\sum_i \Delta_i\big)^2}
$$

This is a Herfindahl index over *cluster* influence. The danger response fires when D > θ_D *and* the answer contradicts the closed-book prior (or the action is irreversible).
- Ordinary leave-one-out misses five redundant poisons, because removing one changes nothing.
- Cluster-level influence catches them: removing the *cluster* swings the answer.

Cost: one forward pass per cluster, not per passage.

### 3.4 Affinity maturation as robust