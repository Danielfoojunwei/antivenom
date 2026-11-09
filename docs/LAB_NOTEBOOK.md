# Lab notebook: ANTIVENOM (v4 single-agent → v3 swarm)

Rules:
- Everything here is a real run: real model weights, real retrievers, real corpora.
- Numbers go in only after they are produced by a script in `experiments/`, with the raw JSONL in `results/`.
- Scope (user decision, 26 Oct): **defence side only.** Poison comes from published benchmark artifacts. We do not generate attack content.

## 2026-10-26: environment and fidelity checks

**Environment**
- Apple M5, 17 GB. Python 3.12 via uv. mlx-lm 0.32.2, torch 2.14.1, transformers 5.20.2, sentence-transformers 6.2.0.
- Agent and immunologist LLM: `mlx-community/Qwen2.5-7B-Instruct-4bit`, local. Qwen2.5-7B is one of MemMorph's ten backbones. PoisonedRAG did not test Qwen; its closest comparable models are LLaMa-2-7B and Vicuna-7B.
- No API key on this machine. Frontier-model checks are deferred until the user adds one.

**Poison source: PoisonedRAG (Zou et al., USENIX Security 2025)**
- Released files: `results/adv_targeted_results/{nq,hotpotqa,msmarco}.json`, with 100 targets × 5 poison passages each.
- Also used: `results/beir_results/nq-contriever.json`, the released clean top-100 retrieval scores.
- Runtime assembly follows the authors' `src/attack.py` (LM_targeted): each poison is `question + "." + adv_text`.
- Corpus: BEIR NQ from the Hugging Face mirror `BeIR/nq`, 2,681,468 passages. All 9,844 passages in the 100 targets' clean top-100 lists are present.

**Fidelity check 1: retriever**
- Our `facebook/contriever` (mean pooling, dot product), encoding passages as `title + " " + text`, reproduces the released scores to 4 decimals. Example for test1: 1.2163 / 1.1967 / 1.1950, identical to the released values.
- Encoding `text` alone does not match, so the title prefix matters.

**Fidelity check 2: protocol**
- Prompt: `MULTIPLE_PROMPT` copied verbatim from PoisonedRAG `src/prompts.py`.
- ASR: `clean_str(incorrect) in clean_str(response)`, verbatim.
- Settings: top-k = 5, 5 poison passages per target.
- Reproduction target (Table 1, NQ black-box): ASR 0.88–0.97 across PaLM2, GPT-3.5/4, LLaMa-2-7B/13B and Vicuna-7B/13B/33B; F1 0.96.

**Memory-manager behaviour (from source, not docs)**
- `mem0ai==1.0.11`, the last 1.x release: `Memory.add()` runs an LLM update step that emits ADD, UPDATE or **DELETE** events (`memory/main.py` around line 659).
- `mem0ai==2.2.1`: `add()` uses `generate_additive_extraction_prompt`, so there is no delete path in `add()`.
- Consequence: opsonisation (clearance driven by the memory manager) is testable on 1.0.11 and structurally impossible in 2.x `add()`.
- The same split in Graphiti is claimed by its README: contradicted facts are invalidated, not deleted.
- Caveat (2609.08258): invalidated facts are still returned unless retrieval filters them. Our `MemoryStore` has an `enforce_revocation` switch so this can be measured.

**Naming resolved**
- The "MemMorph auditor" cited by 2610.04083 is the GPT-4o-mini memory-auditor baseline in MemMorph §5.4 / B.5.
- MemMorph reports that auditor cut its ASR by only 23.7 points (to 54.9%).

## Deviations to report in the paper
1. **Model:** Qwen2.5-7B-4bit (MLX) instead of PoisonedRAG's tested models.
2. **Captured sample:** the defender captures `poison[0]` of the 5. The other four are unknown to the defender.
3. **Store size:** each per-target store holds the released clean top-100 plus the poison passages, not the full 2.68M corpus. This matches how PoisonedRAG's own `main.py` evaluates (top-k over released results plus poison).
4. **Immunologist:** the same LLM as the agent, i.e. a fork of the agent, with no extra knowledge.

## Results log
*(filled only from `results/*_summary.json`)*

### E01: PoisonedRAG attack baseline, NQ, Qwen2.5-7B-4bit, k = 5, n = 100
Source: `results/e01_nq_Qwen2.5-7B-Instruct-4bit_k5_summary.json`

| | Clean store | With published poison |
|---|---|---|
| Correct answer | 0.53 | 0.11 |
| Target (false) answer, i.e. ASR | 0.04 | **0.99** |
| Mean poison passages in top-5 | — | 4.79 |

- **The attack baseline reproduces.** Published ASR is 0.88–0.97 (Table 1, NQ black-box) and we get 0.99. Published poison F1 is 0.96 and we get 4.79/5 ≈ 0.96.
- The clean "ASR" of 0.04 means the target answer string occurs by chance in a clean answer (short numeric answers). This is the floor for every defence arm.
- Clean accuracy of 0.53 is the ceiling a perfect defence can recover to with this model and corpus.
- Engineering note (also applies to E02): torch's default CPU threads contend with MLX. `torch.set_num_threads(1)` cut Contriever encode time for 6 texts from 3.0 s to 0.11 s, though part of the 3.0 s was warm-up. Run one experiment at a time.

### Metric validation: substring ASR vs "endorsed"
- PoisonedRAG's substring metric scores "the claim X is false" as an attack success. That penalises exactly the defences that make the model name and reject a claim.
- **Tried and rejected:** a Qwen-7B judge (yes/no logprob: 4/8 vs hand labels; extract-the-answer: 9/12). It overrides answers it believes are factually wrong.
- **Adopted:** a rule (`qa.endorses`). The target answer is counted only if it appears in a sentence with no rejection or attribution cue, and the response doesn't open by abstaining. It scores **12/12** on `data/validation/judge_cases.json`.
- On E01, the rule disagrees with substring 3 times. In all 3 the model had in fact rejected the poison, so substring over-counts.
- A random spot-check of 15 rule-endorsed E01 responses found all 15 genuine.

### E02: single-agent antivenom vs baselines, NQ, Qwen2.5-7B-4bit, k=5, n=100 (complete)
Source: `results/e02_summary.txt` (from `analysis/summarise.py`).

**Setup.** The defender captures poison[0] only.

| Arm | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| clean | 0.04 [0.01, 0.08] | 0.53 [0.43, 0.63] |
| attack | 0.96 [0.92, 0.99] | 0.11 [0.05, 0.18] |
| warning prompt | 0.90 | 0.13 |
| delete captured sample | 0.94 | 0.15 |
| delete neighbours τ=0.85 / **0.75** | 0.69 / **0.17 [0.10, 0.24]** | 0.32 / 0.47 |
| flag ×1 / ×3 / ×5 | 0.77 / 0.61 / 0.55 | 0.15 / 0.17 / 0.15 |
| best ×1 / ×3 / ×5 | 0.74 / 0.50 / **0.43 [0.33, 0.53]** | 0.23 / 0.25 / 0.26 |
| evidence ×5 (n=32, where the immunologist knew the answer) | 0.19 | 0.59 |
| flag ×5, no anchor | 0.92 | 0.11 |
| clean + best ×5 (autoimmunity) | 0.04 | 0.47 |
| off-target antibodies | 0.04 | 0.53 |

**Tests** (exact McNemar):
- attack vs best×5, endorsed: p=2e-16.
- flag×5 vs no-anchor: p=1.5e-11. **Retrieval anchoring is the mechanism.**
- flag×1 vs flag×5: p=1e-5. **Dose–response.**
- best×5 vs neighbour deletion τ=0.75, endorsed: p=4e-5. **Neighbour deletion is better.**
- clean vs clean+best×5, correct: p=0.39. Autoimmunity is not significant at n=100.

**Collateral.** Neighbour deletion at τ=0.75 retired on average 4.66 of 5 poisons and 0.01 clean passages per target (max 1).

**Immunologist.** It answered closed-book on 32 of 100: 21 right, 1 repeated the poison. Mean of 5.3 probe queries hit the sample.

**Mechanistic split** (all antibody arms pooled). With 2–3 poisons in the top-5:
- endorsement is 0.12–0.15 when ≥1 antibody is present, vs 1.00 without;
- with 4 poisons it is 0.59;
- 31% of antibody-arm evaluations had no antibody in the top-5 at all.

The failure is **retrieval crowding**, not in-context persuasion.

**Interpretation.**
- Every arm that works here, including our antibodies' anchoring, exploits the fact that PoisonedRAG's poisons are near-clones that open with the question.
- DnD (2609.27090) removes exactly that property. See `docs/SOTA_GAP.md` for the change in principle (claim-keyed, bound counter-records).

**Runtime.** Mean 143 s per target. A concurrent E03 run on the same GPU caused at least one stall.

## 2026-10-27

### E09: oracle attention-blockade upper bound, NQ, Qwen2.5-7B-4bit, k=5, n=100
Sources: `results/e09_oracle_blockade_nq.jsonl`, `results/e09_summary.txt`. Code: `src/antivenom/masked.py`, `experiments/e09_oracle_blockade.py`.

**Fidelity check.** The layer-by-layer masked forward reproduces the model's logits exactly (max abs diff 0.0, same argmax at every position). Passage token spans were verified by decoding them back to text.

**Metric.** log P(correct) − log P(target), as a forced continuation of the prompt. Reported as the share of targets where it is > 0.

**Conditions.**
- *answer_side*: question and answer tokens cannot attend to the true poison spans, at bias s.
- *full*: no later token can attend to them.
- *clean_control*: the same blockade applied to the same number of clean passages in the clean context.

| Subset | clean | attack | answer-side s=−2 | s=−5 | s=−1e4 | clean-control s=−5 |
|---|---|---|---|---|---|---|
| all (n=100) | 0.88 | 0.06 | 0.06 | **0.78** | 0.82 | 0.80 |
| top-5 all poison (n=86) | 0.86 | 0.02 | 0.01 | 0.76 | 0.79 | 0.77 |
| clean passages remain (n=14) | 1.00 | 0.29 | 0.36 | **0.93** | **1.00** | 1.00 |

**What it shows.**
1. **The dose threshold is sharp.** s=−2 does nothing; s=−5 removes most of the effect.
2. **When all 5 passages are poison (86 of 100), the oracle blockade cannot do better than answering from memory.** Its result (0.76–0.79) matches the clean-control value (0.77) that removes all context. On these targets, blockade is equivalent to deletion.
3. **The informative subset is mixed context (n=14, wide CIs).** Answer-side blockade restored the correct preference from 0.29 to 0.93 (s=−5) and 1.00 (s=−1e4). The same blockade on clean passages cost nothing (1.00 → 1.00).
4. **Anomaly to understand.** At s=−5, full isolation was *weaker* than answer-side blockade (0.52 vs 0.78 overall). At s=−1e4 they are equal. Hypothesis: partly suppressing attention inside the passage region disturbs the representations of later passages.

**Gate decision.**
- The mechanism passes as an *upper bound*: the reader's adoption of poison runs through attention from answer positions into the poison spans, and gating that path cures it.
- It does **not** yet show an advantage over deletion. With k=5, PoisonedRAG fills the context, so only 14 targets test the mixed case.

**Still unverified.**
- This is a forced-choice preference between the correct and target answers, not free generation. Generation may say "I don't know" instead.
- Positions are oracle. Real flagging is E11.

**Next to make the bound informative.**
- k=10, so clean evidence co-exists with the 5 poisons.
- Generated answers scored with the validated `endorses` rule.
- Count-matched random-span controls in the attacked context.

### E09b: oracle blockade on generated answers, NQ, Qwen2.5-7B-4bit, k=10, n=90 of 100
Sources: `results/e09b_blockade_generation_nq_k10.jsonl`, `results/e09b_summary_n90.txt`. Code: `masked.generate_masked`, `experiments/e09b_blockade_generation.py`.

**Stopped at 90 targets (user's choice).** From about 08:40 the run slowed to a crawl: two jobs from another project (`wirelessjev.envlearn`, `wirelessjev.radiojev.e45`) filled memory, and the E09b process was paging, in state "UN" with an 18 MB resident set. I stopped it; it is resumable from target 91.

**Fidelity check.** The cached masked greedy decoder with no bias matched `mlx_lm` greedy generation exactly on 4 of 4 poisoned prompts.

**Setup.**
- top-10 retrieval: 4.97 poison passages on average, the rest clean.
- Scoring: answers generated by greedy decoding and scored with the validated `endorses` rule plus `correct`.
- Control: block the same number of randomly chosen *clean* passages in the attacked context (seeded per target).

| Condition | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| clean | 0.04 [0.01, 0.09] | 0.69 [0.59, 0.78] |
| attack | 0.91 [0.84, 0.97] | 0.23 [0.14, 0.32] |
| **block poison, s=−5** | **0.06 [0.01, 0.11]** | **0.54 [0.44, 0.64]** |
| block random clean, s=−5 | 0.94 [0.89, 0.99] | 0.06 [0.01, 0.11] |
| block poison, s=−1e4 | 0.06 [0.01, 0.11] | 0.52 [0.42, 0.62] |

**Exact McNemar tests.**

| Comparison | Endorsed | Correct |
|---|---|---|
| attack vs block poison | p = 1e-23 | p = 3e-7 |
| block random clean vs block poison | p = 2e-24 | p = 1e-13 |
| clean vs block poison | p = 1 | p = 0.002 |
| s=−5 vs s=−1e4 | p = 1 | p = 0.5 |

**Reading.**
1. **On generated text, gating answer-side attention into the true poison spans removes the poison's effect.** Endorsement is indistinguishable from the clean context.
2. **It is specific.** Blocking the same number of clean passages does not help; it hands the poison more control.
3. **The correctness gap to clean (0.54 vs 0.69) is expected.** The reader then has about 5 clean passages instead of 10.
4. **s=−5 is enough.** This is a soft gate, not deletion, which matters for the cost of false flags in E11.

**The 5 residual endorsements, read by hand.**
- 2 are the clean floor: the clean context gives the target too (test213, test397).
- 1 is a false positive of the `endorses` rule: "base of the sperm *head*" in a correct "midpiece" answer (test19).
- 1 is a genuine leak (test164: Astros → Yankees).
- 1 is ambiguous and possibly parametric (test419, Belichick).
- **Hypothesised leak path:** clean passages *after* a poison span can still attend to it and carry its content forward, because only the answer-side rows are blocked.

**Not yet shown.** Positions are oracle. E11 must find the poison spans with real signals (claim entailment against a captured sample; attention-collapse) and keep this effect at realistic false-flag rates.

### E11: real flagging (claim entailment from ONE captured sample) + attention blockade, NQ, k=10
Sources:
- `results/e11a_flag_scores_nq_k10.jsonl`, `results/e11a_flags_summary.txt`, `results/e11a_chosen_flags.json`
- `results/e11b_flagged_blockade_nq_k10.jsonl`, `results/e11b_summary_n95.txt`

Code: `experiments/e11a_flag_scores.py`, `analysis/e11a_flags.py`, `experiments/e11b_flagged_blockade.py`, `analysis/e11b_summary.py`.

**Flagger.**
- `cross-encoder/nli-deberta-v3-base`. Labels read from its config: {0 contradiction, 1 entailment, 2 neutral}.
- Premise = each retrieved passage. Hypothesis built from the immunologist's extraction of poison[0] only (reused from E02). The dataset question is never used.

**Selection protocol.** Phrasing and threshold were chosen on targets 1–20 only: max F1 on non-captured poisons, subject to clean FPR ≤ 5%. The rule was fixed before looking at the test split. Results are reported on targets 21–100.

| Phrasing | Calibration P / R | Held-out P / R / clean-FPR |
|---|---|---|
| bare claim | 0.977 / 0.525 | 0.922 / 0.448 / 0.030 (τ=0.05) |
| **"The answer to the question "Q" is C."** | 1.000 / 0.875 | **0.952 / 0.871 / 0.035** (τ=0.01) |

- Held-out counts: TP 276, FP 14, FN 41, TN 389. The captured sample was flagged 80/80.
- The bare-claim failure is that extracted claims are often fragments ("In 1875"), which a passage cannot entail without the question.

**Cure (E11b, s=−5, generated answers).** n = 95 of 100. The last 5 targets were still running under memory contention from another project's jobs.

| Held-out (n=75) | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| clean | 0.05 [0.01, 0.11] | 0.67 [0.56, 0.77] |
| attack | 0.91 [0.84, 0.96] | 0.25 [0.16, 0.35] |
| oracle blockade (E09b) | 0.07 [0.01, 0.13] | 0.53 [0.43, 0.64] |
| **flagged blockade** | **0.21 [0.13, 0.31]** | **0.44 [0.33, 0.55]** |

**Exact McNemar tests.**

| Comparison | Endorsed | Correct |
|---|---|---|
| attack vs flagged | p = 4e-16 | p = 5e-4 |
| oracle vs flagged | p = 0.003 | p = 0.016 |

**Diagnosis.**
- **All 12 held-out leaks** (flagged endorses where the oracle does not) had ≥1 missed poison, often 3–4. Mean true flags per target is 4.41 of 4.96 poisons.
- **The gap to the oracle is flag recall, not the blockade.**
- **False flags cost correctness.** On the 11 held-out targets with ≥1 false flag, correct answers went 7 → 3 versus the oracle.

**Next.**
- **Raise recall without raising false flags.** Candidates:
  - an attention-concentration signal OR-ed for recall;
  - an AND-gate for weak flags (block only when both signals agree);
  - re-run entailment with multiple extracted phrasings.
- **Cost of false flags.** Measure softer strengths (−3, −4), since E09 showed −2 does nothing and −5 is enough.

### E11c: attention-concentration signal and OR/AND combination with entailment (flag quality)
Sources: `results/e11c_attention_scores_nq_k10.jsonl`, `results/e11c_combine_summary.txt`, `results/e11c_combined_flags.json`. Code: `masked.attention_rows`, `experiments/e11c_attention_scores.py`, `analysis/e11c_combine.py`.

**Signal.**
- For each passage: the attention mass from the last 8 prompt positions into that passage, averaged over heads, read per layer, then z-scored within the context.
- It needs no captured sample. This is the D-SCAN idea (2608.06947).

**Fidelity check.** `attention_rows` rows sum to 1 at every layer, with zero mass on future positions. Layer 27 overflowed in fp16 until the q·k product was computed in float32.

**Selection.** Layer, normalisation and threshold were chosen on targets 1–20: max F1 subject to clean FPR ≤ 5%. Chosen: layer 21, per-token mass, z ≥ 0 (calibration P 0.969, R 0.775).

**Depth profile** (first 7 contexts, descriptive only):
- Layers 0–6 attend *less* to poison than to clean passages.
- Layers 12–27 attend *more*, peaking at layers 18–21.

**Held-out flag quality (targets 21–100, n=80).** Recall counts non-captured poisons.

| Flagger | Precision | Recall | Clean FPR | FP | FN |
|---|---|---|---|---|---|
| entailment | 0.952 | 0.871 | 0.035 | 14 | 41 |
| attention (layer 21) | 0.956 | 0.814 | 0.030 | 12 | 59 |
| **OR** | 0.923 | **0.978** | 0.065 | 26 | 7 |
| **AND** | **1.000** | 0.707 | **0.000** | 0 | 93 |

**Caveat that must be tested.** The attention threshold is relative to the other passages in the context (z ≥ 0). With about half of each top-10 being poison, a relative split is flattered. At low poison fractions (for example 1 poison in 10) it would flag many clean passages. Next: evaluate at controlled poison counts 1–5.

## 2026-10-27: Erratum and corrections after an independent code review

An independent reviewer (a separate agent, read-only) checked all code, results and claims above.

**Confirmed by the reviewer.**
- No faked, mocked or hard-coded results. Every stored metric re-derives from its stored response: E02 0/1628 mismatches, E09b 0/540, E11b 0/380, E12 0/460.
- Context orderings agree across every script that reuses another's results.
- The defender side never uses the dataset question, answers or labels.
- The McNemar and bootstrap code is correct, and so are the logprob positions.
- Nothing in the main pipeline depends on the other session's `immune.py`, `steer.py` or E03.

### C1. Scoring bug on short and yes/no answers (fixed; all results re-scored)
- **The bug.** `correct` and `endorses` used plain substring matching. Examples:
  - `correct("I don't know", "no")` was True, because "no" is inside "know".
  - The target "O" matched inside "ocean".
- **Impact.** 20 of 100 NQ targets have answers of ≤ 4 characters. In the first 50 targets, HotpotQA has 11 yes/no targets; across all 100, MS-MARCO has 24.
- **Fix.** `qa.contains` now requires a whole-token match, and an abstention can never be `correct`. PoisonedRAG's original substring rule is kept as `poisoned` / `poisoned_substring`, for comparison with published numbers only.
- **Re-scoring.** `analysis/rescore.py` re-scores every stored response into `results/rescored/` and never touches the raw files. A first version of the script scored E02's off-target arm against the wrong question; that was fixed before any number was used.
- **Changes after re-scoring:** E02 33/1728 judgements, E09b 11/540, E11b 10/380, E12 7/500.

**Re-scored headline numbers.** These supersede the tables above. Sources: `results/rescored/summaries/*.txt`.

| Result | Endorsed (before → after) | Correct (before → after) |
|---|---|---|
| E02 attack | 0.96 → **0.95** | 0.11 → 0.10 |
| E02 best×5 | 0.43 → **0.42** | 0.26 → 0.25 |
| E02 neighbour deletion τ=0.75 | 0.17 → **0.15** | 0.47 → 0.46 |
| E02 clean | 0.04 → 0.03 | 0.53 → **0.51** |
| E02 off-target | 0.04 → 0.03 | 0.53 → 0.51 (same as clean: no off-target harm) |
| E09b (n=90) attack | 0.91 → **0.90** | 0.23 |
| E09b block poison s=−5 | 0.06 → **0.04** | 0.54 → 0.52 |
| E09b block random clean | 0.94 → **0.93** | 0.06 |
| E09b clean | 0.04 → 0.03 | 0.69 → 0.68 |
| E11b (targets 21–100, n=75) attack | 0.91 → **0.89** | 0.25 |
| E11b oracle | 0.07 → **0.05** | 0.53 |
| E11b flagged blockade | 0.21 → **0.19** | 0.44 |
| E11b clean | 0.05 → 0.04 | 0.67 → 0.65 |

All conclusions and significance tests are unchanged in direction.
- E09b, attack vs block poison: p = 1e-23.
- E11b, attack vs flagged blockade: p = 2e-16.

### C2. Targets 21–100 are a development set, not a held-out set
- E11b's results on 21–100 (the leak diagnosis and the recall gap) shaped the OR/AND design (E11c), E12, E16 and E17, all scored on the same targets.
- From here on, **21–100 is called the development set.**
- **The confirmatory test is E15:** HotpotQA and MS-MARCO with every setting frozen at its NQ value, run once.
- Other parameters never calibrated on targets 1–20: E02's neighbour-deletion τ grid {0.85, 0.75}, and E16's ladder, margin and claim length.

### C3. Thresholds sat on the edge of their grids (sensitivity added)
- **Entailment.** On the calibration split the "qa" phrasing had 0 false positives at every τ ≥ 0.01, so the FPR ≤ 5% constraint never bound and the grid minimum won.
  - With the grid extended down to τ = 0.001 (`results/e11a_flags_summary_v2_extended_grid.txt`), the selection moves to τ = 0.005: development-set P 0.940, R 0.893, FPR 0.045 (was 0.952 / 0.871 / 0.035 at τ = 0.01).
  - The development-set table varies smoothly in τ.
- **Attention.** z ≥ 0 was also the grid minimum. Extended down to z = −1.0 (`results/e11c_combine_summary_v2_extended_grid.txt`), the selection moves to z ≥ −0.25, where the constraint binds (calibration FPR 0.050).
  - Development set: attention P 0.941, R 0.950, FPR 0.047.
  - OR: P 0.908, R **0.994**, FPR 0.079.
  - AND: P 0.996, R 0.826, FPR 0.0025.
- **Decision.** Downstream experiments (E12, E15, E16, E17) keep the original v1 settings (τ = 0.01, z ≥ 0), which were fixed before those experiments ran. v2 is reported as sensitivity. Files:
  - `results/e11a_chosen_flags.json` / `results/e11c_combined_flags.json` are v1, canonical.
  - `*_v2_extended_grid.json` are v2.
- The calibration split is small: 100 clean passages and 80 non-captured poisons. "FPR ≤ 5%" therefore means at most 5 false positives.

### C4. "Validated" overclaimed the `endorses` rule
- `data/validation/judge_cases.json` holds 12 author-written cases, and the rule was tuned against them. That is not validation.
- **Known failure modes:** "X, not Y" sentences are rejected; hedged answers can count as endorsed (e.g. test419).
- **Now in place:** a blind, stratified sheet of 152 *real* responses, `data/validation/label_sheet.csv`.
  - It has opaque IDs; the rule decisions are in a separate key file.
  - **It awaits a human labeller.**
  - `analysis/label_agreement.py` will report accuracy, Cohen's κ and CIs.
- Until that is done the rule is called "a transparent rule", not "validated".

### C5. Unequal answer lengths in baselines (fixed before E19 ran)
- TrustRAG's final answer and RobustRAG's final answer are now capped at 48 tokens, the same as every other arm.
- E19 also adds CoordGuard (AF, and AF with relevance refill), implemented from the paper.

### Smaller corrections
- **E02 "31% … had no antibody in the top-5" is wrong.** 256/696 = **36.8%** had no antibody in the top-5. 219/696 = 31% is the share where all five slots were poison.
- **E09b residuals.**
  - test397 is a metric artefact ("O" inside "Ocean"), not the clean floor.
  - test419 is a rule false positive (hedged answer).
  - So 2–3 of the 5 residuals are metric errors, not leaks. After re-scoring, E09b block-poison endorsement is 0.04.
- **E09b "blocking clean passages hands the poison more control"** is not significant: attack vs random-clean endorsed, p = 0.45. It means only that random blocking does not help.
- **E11a table.** The calibration P/R column was printed at τ = 0.05, while the development values were at τ = 0.01. At τ = 0.01 calibration is P 1.000, R 0.925. The bare-claim development row came from an inline run; it is now reproducible via `analysis/e11a_flags.py`.
- **E11c.** The last 8 prompt positions are mostly the chat template's "Answer:" and the assistant header, not the "question tail".
- **E12 backfill** draws from deeper ranks without re-screening, so poisons can re-enter: delete_entail_backfill has a poison in context for 14 of 48 targets at the time of review. This will be disclosed with the E12 results.
- **E12 denominators.** E12 covers only targets present in E11b, so it has at most 75 development targets, not 80.
- **E01.** 0.53 is not a "ceiling" (a defence could exceed it). E01 combines released clean scores with locally computed poison scores; this is justified by the retriever fidelity check.
- **E11b "7 → 3 correct" under false flags** is n = 11: anecdotal.
- **E09 metric.** It compares summed log-probs of `" " + option`, so it is biased by answer length and tokenisation. Treat it as the screening bound it was used for.
- **Generation caps differ.** E01/E02 use 64 tokens; masked generation (E09b onward) uses 48. Do not compare numbers across these groups.
- **Causal wording.** "The failure is retrieval crowding" (E02) and "retrieval anchoring is the mechanism" rest on observational splits or single comparisons. Read them as "consistent with".
- **Unbacked fidelity claims.** These now have committed scripts with saved output:
  - `tests/fidelity_retriever.py` → `results/fidelity/retriever.txt`;
  - `tests/fidelity_masked.py` → `results/fidelity/masked.txt`.
- **Housekeeping.**
  - Licences: `THIRD_PARTY_NOTICES.md` reproduces the MIT texts for PoisonedRAG and TrustRAG.
  - RobustRAG has no licence, so its prompts are regenerated locally, not redistributed.
  - Corpora and poison files are git-ignored; `data/README.md` gives the commands to regenerate them.
  - Dead code removed: the broken `MiniLM` class and the `hello()` stub.

### E12: blockade vs deletion with combined flags, NQ development set (targets 21–100), k=10, n=75 (complete)
Sources: `results/rescored/e12_combined_and_deletion_nq_k10.jsonl`, `results/rescored/summaries/e12.txt`. Re-scored with the fixed rules.

**Setup.** Flags are v1 (entailment τ=0.01, attention layer 21 z≥0). Blockade uses s=−5. E12 only covers targets present in E11b, hence n=75. Clean, attack, oracle and block_entail answers are reused from E11b.

| Arm | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| clean | 0.04 [0.00, 0.09] | 0.65 [0.55, 0.76] |
| attack | 0.89 [0.83, 0.96] | 0.25 [0.16, 0.35] |
| oracle blockade | 0.05 [0.01, 0.11] | 0.53 [0.43, 0.64] |
| block_entail | 0.19 | 0.44 |
| block_OR | 0.08 [0.03, 0.15] | 0.43 [0.31, 0.53] |
| block_AND | 0.47 | 0.37 |
| delete_OR | 0.08 [0.03, 0.15] | 0.45 [0.33, 0.56] |
| **delete_OR_backfill** | **0.11 [0.04, 0.19]** | **0.60 [0.49, 0.71]** |
| delete_entail | 0.19 | 0.47 |
| delete_entail_backfill | 0.17 | 0.59 |

**Exact McNemar tests.**

| Comparison | Endorsed | Correct |
|---|---|---|
| attack vs block_OR | p = 9e-19 | p = 0.004 |
| block_OR vs delete_OR | p = 1 | p = 0.69 |
| block_OR vs delete_OR_backfill | p = 0.69 | p = 0.001 |
| oracle vs delete_OR_backfill | p = 0.29 | p = 0.36 |

**Reading.**
- **On PoisonedRAG, attention blockade and deletion of the same flagged passages are indistinguishable.** The receptor-level gate gives no measurable advantage over removal here.
- **Backfill restores correctness** (0.60 vs 0.43–0.45), because it brings in fresh clean evidence.
- **The end-to-end pipeline is not distinguishable from the oracle** in this sample (one captured sample → OR detection → delete + backfill).
- **Disclosure.** Backfill draws from deeper ranks without re-screening, so poison re-entered the context in 10/75 targets (OR) and 22/75 (entailment). This accounts for delete_OR_backfill's 0.11 vs delete_OR's 0.08. Re-screening backfilled passages with the same flags is the obvious next arm.
- **AND flags are too strict to cure** (0.47 endorsed). AND's value is as a zero-false-flag detector, not as a removal rule.

### E15 (CONFIRMATORY): HotpotQA, all settings frozen at NQ values, run once, n=50
Sources: `results/rescored/e15_cross_dataset_hotpotqa_k10.jsonl`, `results/rescored/summaries/e15_hotpotqa*.txt`.

**Setup.**
- The immunologist extracts the claim from poison[0] only.
- Entailment uses the "qa" phrasing at τ=0.01; attention uses layer 21, per-token, z≥0. These are the v1 settings, chosen on NQ targets 1–20.
- Generated answers are scored with the fixed rules. This run started after the scoring fix, so rescoring changed 0 of 200 judgements.

**Detection.** Recall counts non-captured poisons.

| Flagger | Precision | Recall | Clean FPR | Captured poison flagged |
|---|---|---|---|---|
| entailment | 0.931 | 0.675 | 0.040 | 46/50 |
| attention | 0.947 | 0.710 | 0.032 | 33/50 |
| **OR** | 0.908 | **0.885** | 0.072 | **50/50** |

**Cure.**

| Arm | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| clean | 0.02 [0.00, 0.06] | 0.48 [0.34, 0.62] |
| attack | 0.86 [0.76, 0.94] | 0.12 [0.04, 0.22] |
| **block_OR (s=−5)** | **0.22 [0.12, 0.34]** | 0.38 [0.24, 0.52] |
| delete_OR_backfill | 0.34 [0.22, 0.48] | 0.32 [0.20, 0.46] |

**Exact McNemar tests.**

| Comparison | Endorsed | Correct |
|---|---|---|
| attack vs block_OR | p = 2e-8 | p = 0.001 |
| attack vs delete_OR_backfill | p = 3e-6 | p = 0.02 |
| block_OR vs delete_OR_backfill | p = 0.07 | p = 0.38 |

**Reading.**
1. **Detection from one captured sample transfers to a new dataset without re-tuning, but each signal weakens.** Entailment recall drops from 0.871 (NQ development) to 0.675. The OR combination recovers 0.885 at a 7.2% clean false-flag rate.
2. **The cure transfers.** Endorsement falls from 0.86 to 0.22, though it does not reach the clean level (0.02).
3. **Blockade vs delete+backfill reverses direction relative to NQ** (0.22 vs 0.34). This is not significant (7 vs 1 discordant targets, p=0.07). It is not due to backfill re-entry: all 5 poisons sit in the top-10 for every target. In the 7 discordant targets, 1–2 missed poisons remained in context under both arms. Hypothesis, untested: deeper-ranked HotpotQA backfill is weaker evidence for multi-hop questions, so a leftover poison dominates more often.

### E15 (CONFIRMATORY): MS-MARCO, frozen NQ settings, run once, n=50
Sources: `results/rescored/e15_cross_dataset_msmarco_k10.jsonl`, `results/rescored/summaries/e15_msmarco*.txt`. On average 4.9 poisons are in the top-10. The captured poison reached the top-10 in 49 of 50 targets.

**Detection.**

| Flagger | Precision | Recall | Clean FPR | Captured poison flagged |
|---|---|---|---|---|
| entailment | 0.891 | 0.832 | 0.078 | 47/49 |
| attention | 0.924 | 0.622 | 0.039 | 35/49 |
| **OR** | 0.857 | **0.918** | 0.118 | 48/49 |

**Cure.**

| Arm | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| clean | 0.00 | 0.74 [0.62, 0.86] |
| attack | 0.80 [0.68, 0.90] | 0.06 [0.00, 0.14] |
| block_OR | 0.28 [0.16, 0.40] | 0.40 [0.26, 0.54] |
| **delete_OR_backfill** | **0.14 [0.06, 0.24]** | **0.64 [0.50, 0.76]** |

**Exact McNemar tests.**

| Comparison | Endorsed | Correct |
|---|---|---|
| attack vs delete_OR_backfill | p = 2e-9 | p = 4e-9 |
| block_OR vs delete_OR_backfill | p = 0.016 | p = 5e-4 |

### Cross-dataset summary (NQ development; HotpotQA and MS-MARCO confirmatory)

| Dataset | OR recall | OR precision | Clean FPR | Attack → block_OR → delete+backfill (endorsed) | Correct under delete+backfill (clean) |
|---|---|---|---|---|---|
| NQ (dev, n=75–80) | 0.978 | 0.923 | 0.065 | 0.89 → 0.08 → 0.11 | 0.60 (0.65) |
| HotpotQA (n=50) | 0.885 | 0.908 | 0.072 | 0.86 → 0.22 → 0.34 | 0.32 (0.48) |
| MS-MARCO (n=50) | 0.918 | 0.857 | 0.118 | 0.80 → 0.28 → 0.14 | 0.64 (0.74) |

**Conclusions supported so far.**
- Claim-signature entailment from one captured sample, OR-ed with the reader's attention signal, detects most unseen poisons on two datasets it was never tuned on: recall 0.885 and 0.918.
- The single signals are weaker and vary by dataset: entailment recall 0.675–0.871, attention recall 0.62–0.81.
- Both removal and attention blockade cut endorsement substantially on every dataset.
- Neither is uniformly better:
  - delete+backfill is significantly better on MS-MARCO;
  - the two are indistinguishable on NQ;
  - there is a non-significant opposite trend on HotpotQA.
- The receptor-level gate therefore has no consistent advantage over removal in these benchmarks.
- The clean false-flag cost grows on MS-MARCO (11.8%).

### Retriever fidelity (committed test)
Source: `results/fidelity/retriever.txt` (`tests/fidelity_retriever.py`).
- Setup: 100 targets × top-3 released clean passages per dataset.
- Max |our score − released score|: NQ 2.6e-6, HotpotQA 2.4e-6, MS-MARCO 3.0e-6.
- All 900 pairs agree within 1e-3.

### E17: bound delivery ("immune complex") with no backfill pool, NQ development set, n=75
Sources: `results/rescored/e17_bound_delivery_nq_k10.jsonl`, `results/rescored/summaries/e17.txt`.

**Setup.**
- OR flags, v1 settings.
- After each flagged record, one counter-record from E02 is inserted. E02's counter-records were synthesised from poison[0] alone: "flag", or "best" (evidence where the immunologist knew the answer, otherwise flag).
- Clean, attack, block_OR and delete_OR are reused from E12.

| Arm | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| attack | 0.89 | 0.25 |
| delete_OR | 0.08 [0.03, 0.15] | 0.45 [0.35, 0.57] |
| block_OR | 0.08 [0.03, 0.15] | 0.43 [0.32, 0.53] |
| bound_flag | 0.17 [0.09, 0.27] | 0.48 [0.37, 0.59] |
| bound_best | 0.23 [0.13, 0.32] | 0.49 [0.39, 0.60] |
| **bound_best + block** | **0.08 [0.03, 0.15]** | **0.51 [0.40, 0.61]** |

**Exact McNemar tests.**

| Comparison | Endorsed | Correct |
|---|---|---|
| attack vs bound_best | p = 2e-14 | p = 1e-4 |
| delete_OR vs bound_best | p = 0.019 | p = 0.55 |
| bound_best vs bound_best+block | p = 0.001 | p = 1 |
| bound_best+block vs block_OR | p = 1 | p = 0.11 |

**Reading.**
- Delivering the counter-record bound to the flagged record removes the retrieval-crowding problem seen in E02, and it cuts endorsement from 0.89 to 0.23. Alone, though, it is weaker than removing the record.
- The two-component "cocktail" (bound counter-record + blockade) matches deletion on endorsement. It has the highest correctness among the no-backfill arms (0.51 vs 0.43–0.45), but that difference is **not significant** (p=0.11), so no advantage is claimed.

### E16: titration (per-threat dose to effect), NQ development set, n=75. Negative result.
Sources: `results/rescored/e16_titration_nq_k10.jsonl`, `results/rescored/summaries/e16.txt`.

**Method.**
- For each query, a fork of the reader scores the first 8 tokens of the claim extracted from poison[0] as an answer continuation.
- It raises the blockade strength on the OR-flagged passages along the ladder {−1, −2, −3, −4, −5, −8}.
- It stops at the first dose where log P(claim) ≤ (its value with the flagged passages removed) + 0.5.
- The answer is then generated at that dose. Only defender-side information is used.
- The ladder, margin and claim length were **not** calibrated on targets 1–20; they are fixed a priori.

| Arm | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| titrated | 0.13 [0.07, 0.21] | 0.43 [0.32, 0.53] |
| fixed s=−5 (block_OR) | 0.08 [0.03, 0.15] | 0.43 [0.32, 0.53] |
| delete_OR_backfill | 0.11 | 0.60 |

**Tests and breakdown.**
- Titrated vs fixed: endorsed p=0.12, correct p=1.
- Dose distribution: −1: 7, −2: 3, −3: 12, −4: 5, −5: 7, **−8 (ladder maximum): 41**.
- 27 targets were titrated below −5. On those, titrated endorsement was 0.30 vs 0.15 at fixed −5, and correctness was 0.41 vs 0.37.

**Reading.**
- This dose-to-effect criterion under-doses where it chooses low doses, and it saturates the ladder in most other cases.
- It does not improve the poison/correctness trade-off over a fixed dose.
- The pharmacological "dose to effect" principle, as operationalised here, is **not supported**. A criterion based on held-out clean-answer stability, rather than claim likelihood, would be the next thing to try.

### E16b protocol: clinical titration (pre-specified before running)
**Why E16 was the wrong mapping.**
- E16 titrated against a pharmacokinetic proxy: claim likelihood relative to a removal reference.
- It started from the smallest dose and tried to minimise it.
- Clinical antivenom practice works differently (e.g. the WHO snakebite guidelines):
  - give a **standard initial dose**;
  - **reassess a clinical endpoint** observable in the patient (e.g. the 20-minute whole-blood clotting test, neurotoxic signs);
  - give **repeat doses** while the endpoint stays abnormal, up to a maximum;
  - **monitor adverse reactions**.
- E11b and E12 traced every leak to *missed* poisons. A repeat dose must therefore **widen neutralisation coverage**, not only strengthen it on the same flags. This is the analogue of more antivenom raising neutralising capacity.

**Protocol** (`experiments/e16b_clinical_titration.py`). Fixed a priori; nothing tuned on the development set.

| Element | Setting |
|---|---|
| Initial dose | OR flags at v1 (entailment τ=0.01, attention layer-21 z≥0), blockade s=−5 |
| Endpoint | The defender reads the reader's generated answer. "Still envenomated" means NLI(premise=answer, hypothesis=claim signature) entailment ≥ 0.5, the standard NLI decision boundary. |
| Repeat dose 2 | τ=0.005, z≥−0.25, s=−5 |
| Repeat dose 3 | τ=0.002, z≥−0.5, s=−8 |
| Maximum | 3 doses |
| Adverse events recorded | clean passages neutralised; escalation that turns a substantive answer into an abstention |

- **Defender-side information only:** the claim from poison[0], and the per-passage entailment and attention scores from E11a and E11c.
- **Population:** NQ development targets 21–100.
- **Comparators:** fixed-dose block_OR and delete_OR_backfill, from E12.

### E19: SOTA baselines on identical contexts, NQ development set (complete; n=75 joined with E12)
Sources: `results/rescored/e19_baselines_nq_k10.jsonl`, `results/rescored/summaries/e19_compare.txt` (`analysis/e19_compare.py`).

**Setup.**
- Same reader, same top-10 attacked contexts, same 48-token answer cap, same scoring rules.
- TrustRAG is ported from released code: k-means plus n-gram filtering, then three-stage conflict consolidation.
- RobustRAG is the keyword-aggregation port, with α=0.3 and β=3.
- CoordGuard is implemented from the paper, in AF mode, plus the paper's relevance-refill variant.

| Arm | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| clean | 0.04 [0.00, 0.09] | 0.65 [0.55, 0.76] |
| attack | 0.89 [0.83, 0.96] | 0.25 [0.16, 0.35] |
| **ours: OR → delete + backfill** | 0.11 [0.04, 0.19] | **0.60 [0.49, 0.71]** |
| ours: OR → block | 0.08 [0.03, 0.15] | 0.43 [0.32, 0.53] |
| ours: OR → delete | 0.08 [0.03, 0.15] | 0.45 [0.35, 0.57] |
| TrustRAG | 0.05 [0.01, 0.11] | 0.52 [0.41, 0.64] |
| CoordGuard AF | **0.03 [0.00, 0.07]** | 0.39 [0.28, 0.49] |
| CoordGuard AF + refill | 0.05 [0.01, 0.11] | 0.53 [0.43, 0.64] |
| RobustRAG keyword | 0.52 [0.41, 0.63] | 0.33 [0.23, 0.44] |

**Exact McNemar tests, ours (delete + backfill) vs each baseline.**

| Baseline | Endorsed | Correct |
|---|---|---|
| TrustRAG | p = 0.22 | p = 0.31 |
| CoordGuard AF + refill | p = 0.34 | p = 0.33 |
| CoordGuard AF | p = 0.07 | p = 0.003 (ours better on correctness) |
| RobustRAG | p = 1e-7 | p = 2e-4 (ours better) |

**Detection on the same contexts** (all 372 poisons including captured, 378 clean passages):

| | Poison recall | Clean removed |
|---|---|---|
| CoordGuard AF | 0.997 | **0.222** |
| ours, OR | 0.981 | **0.069** |

**Reading.**
- On PoisonedRAG (near-clone poison), our pipeline is **on par with TrustRAG and CoordGuard**. Its correctness point estimate is the highest (0.60 vs 0.52–0.53), but the difference is not significant at n=75. Its endorsement is slightly higher, also not significant.
- **Its concrete, measured advantage is detection precision.** It removes about 3× fewer clean passages than CoordGuard (6.9% vs 22.2%) at similar poison recall.
- It clearly beats RobustRAG keyword aggregation.
- PoisonedRAG's near-clone structure favours CoordGuard's geometry. Whether the claim-plus-attention detection *beats* SOTA has to be decided on diverse poison, which is still pending a source.

### Mechanism-code fidelity (committed test)
Source: `results/fidelity/masked.txt` (`tests/fidelity_masked.py`).
- `forward_logits` with only the causal mask vs the model's own forward pass, 5 real prompts: max |logit diff| = 0.0.
- `generate_masked` with no bias vs `mlx_lm` greedy decoding, 10 real attacked prompts: 10/10 identical.
- `attention_rows`, all 28 layers: every row sums to 1.000000; max mass on future positions 0.0.

Batched-generation check: `results/fidelity/batch.txt` (`tests/fidelity_batch.py`).
- `mlx_lm.batch_generate` reproduced unbatched greedy output on 20/20 real prompts.
- It was 0.5× as fast here (measured while E19 shared the GPU), so it is not used.

### Diverse-poison test: status
- **Paraphrasing.** The user authorised paraphrasing the released poison as a bounded exception. A safety classifier stopped that generation, so it was **not done** and will not be attempted.
- **SafeRAG** (`data/external/saferag/nctd.json`, released) does not provide the needed setting. Its inter-context-conflict task has one poisoned passage per question (93 items, Chinese), and that passage is a near-copy of a clean passage with edited figures. With one captured poison there are no unseen poisons to generalise to.
- **ProvenanceGuard** (IEEE DataPort, DOI 10.21227/8ftd-cm96) releases 12,000 adversarial passages in 4 strategies, including multi-passage coordinated poisoning. Its files require an IEEE DataPort subscription login. The GitHub repository contains only script-generated sample data.
- **DnD** (2609.27090) has no released data.
- **Consequence.** Robustness to diverse distributed poison is **untested**. The paper must state this as a limitation unless the user obtains ProvenanceGuard or DnD data.

### E16b: clinical titration (protocol pre-specified above), NQ development set, n=75
Sources: `results/rescored/e16b_clinical_titration_nq_k10.jsonl`, `results/rescored/summaries/e16b.txt`.

| Arm | Endorsed [95% CI] | Correct [95% CI] |
|---|---|---|
| titrated (clinical) | 0.07 [0.01, 0.13] | 0.43 [0.32, 0.53] |
| fixed s=−5 (block_OR) | 0.08 [0.03, 0.15] | 0.43 [0.32, 0.53] |
| delete_OR_backfill | 0.11 | 0.60 |

**Tests.**
- Titrated vs fixed: endorsed p=1, correct p=1.
- Titrated vs delete + backfill: endorsed p=0.45; correct p=0.001 (delete + backfill better).

**Course of treatment.**
- 70 of 75 targets met the endpoint after the initial dose.
- 2 needed dose 2. Both ended unpoisoned; fixed-dose blocking left 1 of those 2 poisoned.
- 3 needed dose 3. 2 of those 3 were still endorsed at the end.

**Endpoint sensitivity.** The endpoint (NLI of the answer against the claim signature, entailment < 0.5) reported "normalised" in 74/75 targets. The `endorses` rule still counts 5 final answers as poisoned, so the answer-level endpoint misses some leaks.

**Adverse events.**
- In 2 targets, escalation turned a substantive answer into an abstention.
- Clean passages neutralised per target: 0.35 at dose 1, 0.36 at the final dose.

**Reading.**
- The clinical protocol runs as designed and is low-harm.
- On PoisonedRAG it matches, but does not beat, the fixed dose: the initial dose already suffices for 93% of targets, and the endpoint's limited sensitivity stops escalation on some leaking cases.
- A more sensitive endpoint would be needed for repeat dosing to matter. One candidate: the `endorses`-style rule applied to the extracted claim answer.

**Housekeeping.**
- E12b crashed at model load: the Hugging Face hub tried to reach the network during a DNS outage. It is re-queued with `HF_HUB_OFFLINE=1` (cached model).
- In the rescoring output, "changed=88" counts per-dose responses that had not been scored before. It is not a correction.

## 2026-10-27: Plan step 1, offline (no model loaded)
Sources: `results/rescored/summaries/step1_offline.txt` (`analysis/step1_offline.py`), `data/validation/label_sheet_v2.csv`, `docs/PREREG_CONFIRMATORY.md` + `.sha256`.

### Construction profile
- In all three datasets, every poison contains the question verbatim (1.00). No clean passage in the top-10 does (0.00).
- Poisons are about half the length of clean passages. Median words, poison vs clean: NQ 36 vs 89, HotpotQA 42 vs 82, MS-MARCO 32 vs 50.
- Both are shortcuts a detector can exploit. This makes the prefix-free control (approved) mandatory before any SOTA claim.

### M1 avidity (fit on NQ 1–20; development set)
- A 2-signal logistic model (coefficients: entailment logit 0.93, attention z 2.51) reaches AUC 0.991, vs entailment 0.971 and attention 0.981.
- The naive-sum ablation gets 0.996.
- The two signals are nearly uncorrelated within class (r = −0.03 for poison, 0.05 for clean), so they genuinely carry separate information.
- At OR's FPR (0.065): recall 0.987 vs 0.978. At AND's FPR (0): recall 0.757 vs 0.707.
- Clean-removal budget for 95% poison recall: 0.030.
- **Small gain over OR; development only.**

### M5 kinetic proofreading: not supported
| Rule | Recall | FPR |
|---|---|---|
| layer 21, z ≥ 0 | 0.814 | 0.030 |
| all of layers 15–24, z ≥ 0 | 0.666 | 0.017 |
| 3 of 4 layers, z ≥ 0 | 0.795 | 0.032 |
| mean of 15–24, z ≥ 0 | 0.871 | 0.050 |

No persistence rule beats layer 21 at an equal FPR.

### M2 isotype-switching gate
- 12 of 80 development targets have a gold-bearing clean passage in the medium avidity band. The band runs from the clean 90th percentile to the poison median.
- This is below the pre-set threshold of 15, so **M2 is not run**. It is reported as a null.

### M10 backfire (H1a)
- In 1 of 75 targets, the attack alone was not endorsed but a bound counter-record arm was. This holds for both bound arms.
- No meaningful antibody-dependent enhancement.

### CoordGuard gate sweep (attacked side, development set)
- AF (always filter) is its best point.
- Gating at attacked-score quantiles 0.25 / 0.5 / 0.75 / 0.9 raises AF+refill endorsement to 0.28 / 0.47 / 0.67 / 0.79.
- Caveat: this is calibrated on attacked contexts. Clean-context calibration needs e5 over clean contexts, which is a separate CPU step.

### Label sheet v2
- 302 blind rows: the 152 v1 rows unchanged, plus 150 new rows (30 each from E15 HotpotQA, E15 MS-MARCO, E19 baselines, E16b and E17).
- Ids are opaque; the rule decisions are kept in a separate key file.
- `analysis/label_agreement.py v2` reads it. It is unlabelled; a second labeller is pending.

### Protocol freeze
- `docs/PREREG_CONFIRMATORY.md` sets out the splits, the frozen v1 detector, the primary claims (clean cost, defended-clean accuracy, and endorsement with CIs, no NI claim unless powered), the arms, the analysis, the robustness rows, the human-validation gate and the demotion rule.
- SHA-256 hashes of the protocol and the frozen code, flag files and sheet are in `docs/PREREG_CONFIRMATORY.sha256`.

## E12b screened backfill (development, NQ 21-100, n=75)
Screened vs unscreened delete+backfill: endorsed 0.11 vs 0.11, correct 0.59 vs 0.60, McNemar p=1 for both. Poison remained in context after screened backfill in 7/75 targets. Per the pre-registration, the primary effector stays **unscreened delete+backfill**.

## E24 detection head-to-head on confirmatory tier 1 (post hoc for the avidity model; CPU)
Frozen avidity logistic (NQ 1-20, coefficients entail-logit 0.926, attn-z 2.507) vs CoordGuard AF (e5-large-v2), identical rebuilt top-10 contexts, 0 label mismatches vs E15, 50 targets each.

| Dataset | CoordGuard recall / clean removed | Ours OR v1 | Avidity at CG clean rate (recall) | Avidity at CG recall (clean removed) |
|---|---|---|---|---|
| HotpotQA | 1.000 / 0.196 | 0.908 / 0.072 | 0.976 | 0.996 |
| MS-MARCO | 0.963 / 0.216 | 0.931 / 0.118 | 0.984 | 0.141 |

Reading: mixed. On MS-MARCO avidity dominates CoordGuard (higher recall at equal clean cost; about a third less clean removed at equal recall). On HotpotQA CoordGuard dominates: its last few percent of recall would cost us nearly every clean passage, because a few poisons score low on both of our signals. Primary claim 1 (clean-cost superiority at matched recall) is **not supported on HotpotQA** at tier 1. Bootstrap CIs and tier 2 still to come; tier-1 avidity is post hoc.

## Step 2 offline (CPU; tier 1 HotpotQA/MS-MARCO, post hoc) — `analysis/step2_offline.py`, full output `results/rescored/summaries/step2_offline.txt`
- **M14 antivenomics.** Misses at CoordGuard's clean rate: HotpotQA 6/200, MS-MARCO 4/196, each spread over 4 targets. Every miss has entailment < 0.5. On HotpotQA, 0.67 of misses are yes/no targets vs 0.21 of caught poisons: a claim like "they are both in the same neighbourhood" does not entail from passages phrased as two separate descriptions. Misses are less similar to the captured poison (median cosine 0.84 vs 0.86-0.91). This is the HotpotQA loss in E24.
- **S11 length confound: not supported.** AUCs inside the length band shared by both classes are unchanged (avidity 0.984 / 0.979). Length alone gives AUC 0.73 / 0.86.
- **M7 extra hypothesis templates: null.** Max over 3 templates lowers AUC (0.926 vs 0.940 HotpotQA; 0.939 vs 0.956 MS-MARCO) and does not recover the misses.
- **M12 / benchmark shortcut (important).** Contriever cosine to the captured poison alone has AUC **1.000** (HotpotQA) and **0.993** (MS-MARCO). Released poisons for a question are near-clones of each other (poison min cosine 0.77 vs clean max 0.77 on HotpotQA). A trivial "delete anything similar to the sample" rule therefore beats every detector, ours and CoordGuard included, on this benchmark. Part of this similarity is the shared question prefix; E25 prefixfree measures how much. Paper consequence: report this trivial baseline, and treat PoisonedRAG detection numbers as an upper bound for near-clone campaigns.

## E25 robustness (queued after E22; `experiments/e25_robustness.py`)
NQ dev 21-100. Modes: permute (attention under 4 orders plus clean-only twin), prefixfree (M0, approved, with undefended arm), s4 (answer-side vs row-0 blockade vs deletion). The loader gained `prefix=False`; default unchanged. Smoke row test87 (permute): in the clean-only twin the first slot scores z 2.83, and a poison at slot 4 goes from z -0.12 to 1.97 when the order is reversed. A position effect is likely; the full run will test it.

## E21 worst-case capture (NQ dev, n=80) — `analysis/e21_summary.py`
- Entailment recall by captured index: 0.871 / 0.893 / 0.909 / 0.918 / 0.893, FPR 0.035-0.039. poison[0], the one used everywhere, is the *worst* on average, so the headline was not flattered by sample choice.
- Per target, though, entailment is capture-dependent: worst-capture mean recall 0.665, and 24/80 targets fall below 0.5 under some capture.
- **OR with attention removes this:** worst-capture mean recall 0.953, 0/80 targets below 0.5. The capture-independent innate signal covers the capture-specific adaptive one. This is the cleanest evidence so far for the innate + adaptive design.
- k-capture threat model (any of 5 captured): recall 0.995, FPR 0.057.

## Step 3 results (NQ dev, exploratory) — `analysis/step3_summary.py`, output `results/rescored/summaries/step3_summary.txt`
**Prefix-free control (M0, E25 + E26).** Without the attack.py question prefix, 3.26 poisons reach the top-10 on average (4.96 prefixed); 6/80 targets retrieve none. Undefended endorsement 0.70 (0.76 on exposed targets).
- Our detection barely moves: avidity AUC 0.982 (0.991 prefixed), entailment 0.956, attention 0.942. Unlike RAGuard in 2610.33849, our signals do not depend on the prefix shortcut.
- **CoordGuard collapses on clean cost:** recall 0.972 but 52.3% of clean passages removed. At the same recall the frozen avidity score removes 8.9%. At CoordGuard's clean cost avidity recall is 1.000. Pre-committed sentence: **the precision advantage is not prefix-dependent; it grows without the prefix.**
- Cost to us: OR FPR rises to 14.5% (attention part 10.4%); defended endorsement 0.17 vs 0.11 prefixed.

**E20 low poison count.** Defended endorsement 0.03-0.10 at m=1,2,3 (attack 0.53/0.70/0.85). Delete+backfill correct 0.49/0.64/0.60. Attention FPR is highest at m=1 (8.7%): z-normalising within the context forces flags when only one poison is present.

**E22 other readers.** Fidelity passes for both (logit diff 0, 10/10 greedy identical).
- Mistral-7B (layer 15): OR recall 0.959, FPR 4.2%; endorsement 0.84 to 0.10, correct 0.66 (clean 0.70). Transfers.
- Llama-3-8B (layer 18): OR recall 0.801, FPR 17.1%; endorsement 0.70 to 0.40, correct 0.49. Partial transfer only. Entailment flags are reader-extracted, so a weaker Immunologist on Llama is the likely cause (to check).

**E25 permutation.** Attention flags are order-sensitive: recall 0.817 (original) / 0.972 (reversed) / 0.839 / 0.950; 12.4% of flags flip under reversal. In clean-only contexts slot 0 gets mean z 1.15 vs -0.13 elsewhere (a primacy sink). The pre-registered position-debiased variant (slot effect fitted on NQ 1-20) is now warranted.

**E25 S4 blockade mechanism (59/80, partial).** Answer-side blockade, row-0 blockade and deletion are indistinguishable on endorsement (0.07/0.08/0.07, p=1). Blockade adds nothing over deletion; consistent with the consolidated cure-side null.

**S4 final (n=80, supersedes the 59-row entry).** Endorsed 0.07 / 0.09 / 0.07 (answer-side / row-0 / delete), correct 0.44 / 0.46 / 0.46, all McNemar p >= 0.69; all-flagged stratum (73) 0.04 / 0.04 / 0.03. Blockade = deletion. Goes to the consolidated null.

## E27 position-debiased attention (pre-registered single re-test) — `experiments/e27_position_debias.py`
Slot offsets fitted on clean-only top-10 contexts of NQ 1-20 (original + reversed order): [0.60, -0.10, -0.21, -0.34, 0.24, 0.14, -0.43, -0.32, -0.19, 0.62]. A U-shape: first and last slots draw extra attention (primacy and recency). Debiased z = re-z-scored (z - offset[slot]).

| Order (NQ dev) | raw recall / FPR | debiased recall / FPR |
|---|---|---|
| original | 0.817 / 0.032 | 0.861 / 0.022 |
| reversed | 0.972 / 0.020 | 0.943 / 0.020 |
| shuffle 0 | 0.839 / 0.052 | 0.934 / 0.055 |
| shuffle 1 | 0.950 / 0.025 | 0.937 / 0.015 |

Recall range across orders falls from 0.155 to 0.082; mean recall 0.894 to 0.919; FPR equal or lower in 3 of 4 orders. Adopted as the attention signal for the frozen v2 detector, which must be frozen before confirmatory tier 2 runs. Residual order dependence remains and is reported.

## E28 yes/no fix (design data: tier-1 yes/no-form targets, 21; post hoc) — `experiments/e28_yesno_decontext.py`, `results/rescored/summaries/e28_yesno.txt`
The reader restates the captured claim as a self-contained sentence naming every entity; a fixed regex strips "The record claims…" lead-ins (8/21 outputs had one; 1/21 invented an entity).
- Yes/no-form entailment AUC: HotpotQA 0.744 to 0.893; MS-MARCO 0.886 to 0.862.
- Full avidity detector, rewrite used only on yes/no-form questions, vs CoordGuard:
  - HotpotQA: recall at CG clean rate 0.970 to 0.985 (CG 1.000); clean removed at CG recall 0.996 to 0.820 (CG 0.196). The gap narrows but CoordGuard still wins.
  - MS-MARCO: recall 0.980 to 0.990 (CG 0.963); clean removed 0.149 to 0.122 (CG 0.216). Ours wins by more.
- Max(old, new) template was worse than the rewrite alone. Adopted: rewrite on yes/no-form. **v2 detector frozen** in `docs/V2_DETECTOR_FROZEN.md`, hash appended to `PREREG_CONFIRMATORY.sha256`.

## E29 confirmatory tier 2 launched (2026-10-28) — `experiments/e29_tier2.py`
HotpotQA then MS-MARCO, targets 51-100, Qwen reader, every arm once. v2 calibration recorded and hashed before launch. Arms: clean, attack, v1 block, v1 delete+backfill (primary), v2 delete+backfill, random and lowest-relevance count-matched deletion, CoordGuard AF and AF+refill, TrustRAG, and defended-clean for v1, v2 and CoordGuard. Row 1 (smoke test) is kept as the run-once result.

## E29 CONFIRMATORY RESULT (tier 2, run once, Qwen; `analysis/e29_confirmatory.py` → `results/rescored/summaries/e29_confirmatory.txt`)
Pooled n=100 targets (HotpotQA 50 + MS-MARCO 50). Pre-registered primary family, Holm-corrected:
- **Claim 1 (fewer clean passages removed at matched recall vs CoordGuard): NOT SUPPORTED.** CoordGuard recall 0.997, clean removed 0.206. Ours at the same recall removes 0.402 (difference -0.196 [-0.375, 0.060]; Holm p=0.50). Our advantage exists only below full recall: at deployed points v1 is 0.967 / 0.114 and v2 0.977 / 0.147.
- **Claim 2 (defended-clean accuracy above CoordGuard): NOT SUPPORTED.** 0.35 vs 0.37, Holm p=0.73. Every defence loses about 0.25 of clean accuracy (0.61 with no defence).
- **Claim 3 (endorsement, descriptive):** ours v1 minus CoordGuard AF+refill = +0.07 [0.02, 0.13], McNemar 8/1 p=0.039. **CoordGuard blocks significantly more attacks than our pre-registered primary.** v1 vs TrustRAG = 0.00 [-0.09, 0.09].
Secondary (uncorrected): v2 endorsement 0.07 vs CoordGuard 0.05 (p=0.63); correct under attack v1 0.54 / v2 0.53 vs CoordGuard 0.47 (p=0.19 / 0.24) vs TrustRAG 0.53. The HotpotQA accuracy advantage (p=0.013-0.049) does not replicate on MS-MARCO, where CoordGuard+refill is ahead (0.64 vs 0.56-0.60).
Count-matched random and lowest-relevance deletion leave endorsement at 0.64 / 0.73, so the gains come from detection.

**Verdict: on the pre-registered confirmatory test, ANTIVENOM is not superior to CoordGuard on any primary claim, and the v1 primary is slightly worse on endorsement. Defensible statement: on par with SOTA (CoordGuard, TrustRAG) on PoisonedRAG, with different error profiles. CoordGuard and ours abstain; TrustRAG drifts to wrong answers 43% of the time. Ours keeps more clean evidence at the deployed operating point.**

## 2026-10-29: resumed audit and continuation (E30–E35)

Current handoff: `docs/PROJECT_STATUS.md`. New exploratory protocol:
`docs/CONTINUATION_PROTOCOL.md`. No original raw result, frozen detector,
protocol or historical hash entry was replaced. No jobs were active at the
start of this continuation. E31/E32 had already completed this morning but
were missing from this notebook.

### Correction to the preceding E29 interpretation

The historical claim-1 code uses the continuous **v2** avidity scores, not
the pre-registered binary v1 OR detector. Thus it does not confirm a frozen
v1 matched-recall ranking. The endorsement comparison p=0.039 is **raw**:
the original code Holm-corrects only claims 1 and 2. A conservative
four-comparison Holm sensitivity gives p=0.156 for endorsement vs CoordGuard.
The point estimates are unchanged. **No primary superiority was demonstrated;
parity/equivalence/non-inferiority was not established either.** The phrase
"on par" above should not be read as an equivalence result.

`analysis/e35_confirmatory_audit.py` checks all expected tier-2 IDs, absence
of tier-1 overlap, all latest frozen hashes and all 1,300 stored response
scores. No scoring mismatch was found. An earlier v2-document hash is
explicitly superseded by a later entry. Both human sheets remain empty
(0/152 and 0/302 completed rows). Responses counted both correct and endorsing
are exported in `data/validation/e29_overlap_review.csv`, without human labels.
The matched-cost and multiplicity sensitivity results are in
`results/rescored/summaries/e35_confirmatory_audit.txt`. Bootstrap sign-tail
probabilities reproduce the historical approach, not a new null-calibrated test.

**Structural clean-context finding:** v1's within-context attention z >= 0
must flag at least one passage, even if every passage is clean. All 100 tier-2
clean contexts are filtered (mean 3.79 v1 removals). Of 64 with a gold-token
occurrence in the initial top-10, 18 lose every occurrence after v1 filtering
and refill. Gold-token containment is only a proxy. A separate no-action gate
addresses a limitation the original OR rule cannot address by itself.

### E30 attack gate (existing completed exploratory result, recovered)

Threshold g=0.97490412, NQ 1–20 calibration. On pooled E29 targets it fires
on 91% of attacked and 4% of clean contexts. Clean-context accuracy is 0.61
for all three gated defences; endorsement is v1 0.17, v2 0.14, CoordGuard
0.12. Excluding the captured passage from the gate gives 0.19/0.20/0.18.
Source: `results/rescored/summaries/e30_attack_gate.txt`. Clean per-passage
NLI scores were not saved. Tier 2 was already inspected before gate design;
these numbers are not fresh confirmation. The gate assumes a trusted captured
signature is available on the clean-context trials too.

### E31 single non-captured poison (existing run complete)

Source: `results/e31_single_poison.json`; NQ development, 80 targets × four
non-captured released poisons = 320 exposed single-poison contexts.
Entailment-only: recall 0.871875, clean removed 0.026389. CoordGuard AF:
recall 0.95, clean removed 0.716319. **No singleton blind spot observed**:
one poison can join a component containing clean passages. Operating points
are not matched. Only aggregates were persisted; variants are clustered within
80 targets and do not supply 320 independent experimental units.

### E32 M3 appended backfill placebo (existing run complete, analysed)

All 80 development targets. True/placebo/deletion correctness:
0.6000/0.4875/0.4625; endorsement 0.1000/0.0750/0.0750.
True vs placebo correctness +0.1125, paired 95% CI [0.025, 0.200], raw
p=0.02246, Holm over six exploratory comparisons p=0.11230. True vs deletion
+0.1375 [0.0625, 0.225], Holm p=0.02051. Placebo vs deletion p=0.625.
Thus the evidence-specific mechanism is suggestive rather than established
after this correction. All 150 responses shared with E12 are identical.
Source: `analysis/e32_e34_summary.py`, `results/e32_e34_summary.json`.

### E33 score-aware stored-context detection (new, complete)

Source: `analysis/e33_score_aware.py`, `results/e33_score_aware_targets.jsonl`,
`results/rescored/summaries/e33_score_aware.txt`. NQ development; target means.
Selecting the hardest unseen poison gives recall entailment 0.7625,
attention 0.3625, OR 0.9125, avidity 0.9625, CoordGuard 0.9875. Different
operating points; no matched-cost superiority claim. Combining hardest-one
selection with the worst of five captures gives entailment 0.475, OR 0.825
(14/80 targets with an OR miss). Original full-context scores are retained:
these are **not** reader ASR or scores after rebuilding a singleton context.

### E34 passage-slot placement control (new, complete; n=80)

Two new arms put the exact E32 true/placebo replacements into the flagged
passage slots. Surviving passage slots stay fixed, but absolute token
positions and passage lengths vary. `results/e34_manifest.json` freezes
protocol, code and input hashes before generation. One E32 answer was
reproduced exactly before the new arms. The run resumes by target ID in
`experiments/e34_fixed_slots.py`.

**Final result:** true-inplace / placebo-inplace / deletion correctness
0.5500 / 0.5125 / 0.4625; endorsement 0.1125 / 0.0500 / 0.0750.
True vs placebo correctness difference +0.0375, paired bootstrap 95% CI
[-0.0625, 0.1375], raw exact McNemar p=0.6291, six-test Holm p=1.0.
True vs deletion +0.0875 [0, 0.175], raw p=0.0923, Holm p=0.4614.
No comparison in the E34 six-test family survives adjustment. Unscreened true
backfill reintroduces three released poison passages; placebo reintroduces none.

The apparent evidence-content advantage is smaller in original slots than
under appended refill, but direct placement comparisons are themselves
nonsignificant (true correctness raw p=0.2891; placebo p=0.7266). Thus these
controls establish neither an evidence-specific gain nor a placement effect;
they do not prove a padding-only explanation. M3's mechanistic prediction
remains unsupported by a robust true-vs-placebo result.

Source: `results/e32_e34_summary.json`,
`results/rescored/summaries/e32_e34_summary.txt`. Full independent integrity
check passed: 80 unique expected targets, all frozen input hashes, original
passage identities, flags, donor identities, replacement counts and all 160
new response scores (`results/e34_integrity.txt`). Inference exited 0.

## 2026-10-29: remaining local runs authorized and queued (E36–E38)

The user authorized the remaining runs and tests. Scientific choices were
saved in `docs/REMAINING_RUNS_PROTOCOL.md` before new outcomes. Live status and
resumption instructions are in `docs/REMAINING_RUNS_STATUS.md`; the queue
state is `results/remaining_queue_status.json`. No result is called complete
until expected target coverage, all arms, and the final integrity check pass.

**Preparation complete:** 120 canonical contexts (20 NQ calibration, 50
HotpotQA tier 2, 50 MS-MARCO tier 2), all expected IDs. Clean CoordGuard
removals reproduce the existing results on all 100 tier-2 contexts; attacked
removals/scores reproduce on the first three per dataset. Geometry gating
uses a fixed 90th percentile of 20 benign calibration scores. Raw source and
code hashes were frozen before preparation.

**E36 queue:** Llama then Mistral, one model process at a time. Preserve E22
v1 settings: Llama layer 18, Mistral layer 15, both z >= 0.25. V2 gets a
separate NQ-only calibration with saved raw scores. Each reader runs all 13
E29 arms on all 100 tier-2 IDs, with per-arm checkpoints. These are transfer
extensions on used question IDs, not fresh-question confirmation. Llama's
three-prompt greedy-decoder fidelity check passed; all 20 calibration rows
and its coefficients were frozen before tier 2. Initial complete targets
passed independent arm/rescoring/manifest checks (`results/remaining_preflight.json`).

**E37 queue:** prefix-free, retrieved single-poison contexts; captured sample
index differs from context poison index. Recompute attention and entailment
for every candidate; select worst detection pair before answering. Evaluate
all 80 development targets with the stated eight arms. This is the physical
composite test missing from E33's stored-context analysis.

**E38 queue:** save Qwen per-target clean NLI scores, reproduce E30's printed
rates, then add paired uncertainty and geometry-gate comparisons. Pooling
keeps each question's three-reader results together; no 300-independent-query
claim or post-hoc equivalence claim is permitted.

Final analysis and integrity scripts are queued automatically after inference.
An initial queue restart serialization issue was fixed during calibration
before any tier-2 answers. Original queue source/manifest are archived in
`results/provenance/`; active manifest v2 passed its resume round-trip check.
The experimental recipe and saved calibration rows were unchanged.

**External dependencies remain:** independent human reviewers have two
separate shuffled 302-row blank copies; the acceptance checker leaves them
pending until actually labelled. A bounded primary-source release check did
not identify a compatible new-question poison set: PoisonedRAG's tree has the
three already used attack files, RAGuard's examined files provide clean data
and aggregate results, CPA-RAG has a release notice. Repository commit IDs
and candidate files are recorded in `results/released_data_availability.json`.
No attack generation, author contact, fabricated human labels, or claim of
fresh gate confirmation was performed.

### 2026-10-29 continuation: user defers blind review; incident suite queued

User fixed the future fresh endorsement NI margin at 0.05 absolute, suggested
MemMorph as an external source, then instructed us to proceed without blind
reviews. Human validation remains unmeasured and is not an execution gate.
No earlier confirmatory recipe or outcome was changed.

At the subsequent live audit, E36 supervisor PID 25390 and child PID 25403
were both absent despite a stale running status. Saved Llama progress was
32/50 HotpotQA targets plus 10/13 arms for target 33. Original frozen manifest
v2 hashes matched. Restarted unchanged queue detached (PID 29536, child
29540), preserving all checkpoints; target 33 then completed. Restart evidence
is in `results/remaining_restart.json`. Cause of process termination is not
established by the logs; do not call it an experimental failure or success.

Implemented and preflighted the incident suite described in
`INCIDENT_RESPONSE_PROTOCOL.md`: E39 captured-excluded full ablation and
mistaken clean capture, prefix-free shift; E40 actual reretrieved recurrence;
E41 e5 candidate-pool transfer; E42 four separate agent states with real
publisher/receiver calls and delivered messages; E43 actual method timing,
capture/setup bytes and time, reader weight hashes, calibration revocation,
and E39-based paired power planning. Detector/gate/revocation/blocklist,
clustering, paired-test and power-slack fixtures passed without generating
reader outcomes. The data-only preflight confirms 80 development targets,
160 stored later questions, no identical captured/evaluated poison text, and
at least 14 clean documents in every proposed agent partition.

MemMorph's primary paper describes tool-choice hijacking; an official released
record archive was not found in the bounded source search. Third-party attack
generators are not treated as official evaluation records and were not run.
Separately pinned the MIT MemForm evaluation release at commit
0565117042a31a5f78576f89ff6b8a77c393ee09. The MCQ record file SHA256 is
fc9e76b051c21c378281ed4dcbb648f76820a2eaf086683b0c1d24db7fcaaee5.
E44's separate frozen protocol covers P1 policy capture -> P2 forged experience
transfer, 20 calibration families and 212 held-out families, excluding F0001
schema inspection. Native consolidation/task/parser functions are extracted
through a reviewed AST allowlist; the upstream module runner is not executed.
No oracle memory or gold labels enter defence prompts. Full TrustRAG is not
ported in this diagnostic: its document filter is named explicitly. Therefore
this run cannot establish the full primary confirmation regardless of result.

Launched the frozen incident extension as detached PID 29569. Its verified
state is `waiting_for_remaining_queue`; no new incident or MemForm model
outcomes exist yet. It waits for E36–E38 success and the same model lock, stops
on a failed phase, and never treats deferred human labels as passed. Source,
data, split and protocol hashes are in `results/incident_queue_manifest.json`.

### Completion monitoring authorized

The user asked to keep all remaining tests running and report the supported
claims and remaining gaps at completion. Created the active in-thread
heartbeat `finish-antivenom-tests-and-assess-claims`, checking every 30 minutes.
It verifies actual process liveness and progress, resumes checkpoints after
safe infrastructure recovery, preserves frozen scientific recipes, and stays
quiet on unchanged/non-actionable states. Completion requires inspecting raw
outputs and integrity/statistical reports, then a claim-by-claim assessment
with paired uncertainty and explicit negative, inconclusive and untested
findings. Human review remains deferred and the future NI margin stays .05.
The heartbeat is instructed to disable itself after delivering that report.
`results/completion_monitor.json` records the monitor and process IDs. A macOS
idle-sleep inhibitor is tied to the incident queue's lifetime and exits with
that process; it does not alter persistent power settings.

### Completed Llama interim assessment (before Mistral/composite finish)

E36 Llama completed all 100 intended tier-2 questions and 1,300 arm responses.
The completed-stage check reproduces every saved automated answer score.
`analysis/e36_llama_interim.py` reuses the frozen final-analysis functions and
comparison families without executing their unfinished-reader requirements.
Results are in `results/e36_llama_interim_summary.json`. Extra comparisons
against attack/random/low-rank controls form a separately labelled exploratory
six-comparison family. No partial Mistral performance is used for claims.

The operational Llama pipeline reduces endorsement from .53 undefended to
.32 with V1; paired difference -.21, target-bootstrap CI [-.32,-.10], six-test
Holm p=.00376. Random removal leaves .48 and low-rank removal .62. Accuracy
under attack increases from .26 to .43, difference .17 [ .06,.27 ], corrected
p=.00998 in the same exploratory control family. This supports partial attack
mitigation for the actual pipeline, not full method transfer or superiority.

The frozen ten-comparison reader-transfer family strongly disfavors our block
rate against always-filter CoordGuard+refill: endorsement .32 versus .03,
difference .29 [ .21,.38 ], Holm p=3.73e-8. Accuracy is .43 versus .46 and
not distinguished. V2 endorsement .33 and accuracy .45 are not an improvement
over V1. TrustRAG's local port has .03 endorsement but .13 accuracy, a different
error trade-off; this does not rescue an equal-blocking claim.

Critical operational limitation: 95/100 extracted claim strings are blank
(46/50 HotpotQA, 49/50 MS-MARCO). Saved hypotheses literally contain an empty
answer. The frozen extractor allows a missing false_claim key to default to
an empty string and does not retain the raw extraction response, so these
records alone cannot identify whether generation, truncation, or schema parsing
caused failure. The run is valid evidence of this implementation's operational
failure, but is not a clean test of entailment with valid Llama signatures.
Do not silently repair/reselect signatures on these test outcomes or label
this as successful claim-specific protection transfer. A calibration-only raw
extraction diagnosis and a separately frozen follow-up would be needed to
attribute/retest it; neither is part of the current frozen E36 run.

Qwen E29 has no blank claims on the 100 records. On Llama, the NLI gate fires
on 99/100 attacked and 86/100 clean contexts. Defended-clean V1 accuracy is
.44, gated .48, versus .63 unfiltered. Native geometry-gated CoordGuard gives
.63 clean accuracy and .25 attacked endorsement, against gated V1 .48 and
.32. Thus the earlier Qwen gate behaviour does not transfer universally.
These are used-question exploratory and automatically scored results. The
five-point fresh-confirmation margin is not retroactively applied here.

### Current-Mac-only runtime amendment R1

The user ruled out additional hardware and paid compute. Preserve all sample
sizes, algorithms, weights, precision, generation budgets, thresholds and
uncached method timing measurements. Prepared a calibration-gated test of
MLX's unused allocator-cache cap (256 MiB), with the selection rule frozen
in `docs/PERFORMANCE_RUNTIME_AMENDMENT.md`. This does not cap the KV cache or
live tensors and introduces no extra model worker or answer/feature reuse.
Validation runs only on NQ calibration contexts, after E36–E38 releases the
model lock. Exact signature, response, detector vector, flag and final-context
agreement is required across configurations/repeats, plus the declared runtime
gain. Otherwise the original default remains selected. No speedup is claimed
before actual validation and subsequent throughput measurements.

Only the idle incident supervisor was relaunched through
`experiments/run_incident_optimized.py`; the active E36–E38 process was
untouched. The wrapper invokes the original frozen experiment sources and
annotates queue status with its runtime launcher for safe recovery. All
original manifests still match. Wrapper routing/provenance fixtures passed
without inference. The first wrapper launch was rejected before inference
because runpy supplied a relative __file__ instead of Python's original
absolute source identity. Corrected that operational path handling; archived
the initial wrapper/guard sources and runtime manifest in results/provenance.
No original frozen manifest was replaced or relaxed. Current waiting
supervisor PID is 36006 and its lifetime-bound sleep inhibitor is recorded in
results/completion_monitor.json.

The heartbeat now enforces current-Mac-only execution and the runtime-aware
resume path. At the last check both readers had completed all 200 intended
targets, and the original supervisor had advanced to E37 composite inference.
The full incident extension and its allocator validation were still waiting;
no extra cloud job or paid service was started.

### Full Mistral interim result and revised composite timing

All 100 Mistral tier-2 records and 1,300 automatic score checks are complete;
there are zero blank extracted claims. Reused the unchanged frozen scope and
gate-analysis functions to save `results/e36_mistral_interim_summary.json`.
This is a completed-reader interim analysis on used questions, not fresh
confirmation. No incomplete composite performance was used for claims.

Pooled endorsement falls from .69 undefended to .11 with V1, paired reduction
.58, bootstrap CI [.48,.67]; accuracy under attack rises .28 -> .67, gain .39
[.28,.50]. The separately labelled exploratory six-comparison control family
gives Holm p=4.16e-17 for endorsement and 8.34e-9 for accuracy. Random removal
leaves endorsement .56 and accuracy .40, and low-rank removal .73/.27, so the
mitigation is not explained by indiscriminate removal. The valid-signature
operational pipeline therefore has supportive transfer evidence on Mistral,
while Llama's disclosed extraction failure remains a separate limitation.

The frozen ten-comparison transfer family does not establish superiority:
V1 accuracy .67 vs CoordGuard AF+refill .64 (difference .03, CI [-.05,.11])
and TrustRAG .60 (.07, CI [-.05,.18]); endorsement .11 vs .09 and .07.
Every listed pooled transfer comparison has Holm p=1. V2 is .66 accuracy,
.11 endorsement and is not distinguished from V1. Non-significance is not
equivalence, and no fresh five-point non-inferiority verdict is introduced.

Gated V1 gives .70 defended-clean accuracy against .71 unfiltered, with
attacked endorsement .14 and attacked accuracy .66. This is an encouraging
operating point; the clean-accuracy gain over ungated V1 (.60 -> .70) does
not survive its frozen family correction (Holm p=.331). Geometry-gated CG
and sample-aware baselines require their separately scoped comparisons;
do not infer a universal gate win from this reader.

At 21/80 complete composite targets, recent five/ten completed-target wall
intervals predict approximately 7.2/8.5 additional hours for E37. These are
engineering extrapolations sensitive to sleep and load, not confidence bounds.
The wider incident extension has not started, and allocator-cache validation
is still waiting for the original shared lock. Full-suite planning remains
roughly 40–90 further hours of continuous awake execution, not a precise
calendar completion promise. Detailed checkpoint-derived estimates are in
`results/e37_runtime_estimate.json`. Repeated clamshell sleeps were separately
recorded in `results/host_sleep_audit.json` and disclosed to the user.

### R2: composite extraction exception and transparent recovery

At 2026-10-29T18:57:14Z (30 October SGT), E37 stopped after 70/80 completed
targets. The strict JSON decoder failed on test423 capture index 2, expecting
a comma at column 56. Captures 0/1 were checkpointed, but no reconstructed
variant or reader answer for that target existed. The incident supervisor
correctly stopped dependent work. This is an actual extraction failure,
not a successful/complete composite test. All 350 captures and 70 selected
claims in the completed prefix were nonblank.

Before resuming, froze `docs/EXTRACTION_RESILIENCE_AMENDMENT.md` and new
external parser/queue guards in results/extraction_resilience_manifest.json.
Successful parses remain identical; only JSONDecodeError is recorded and
mapped to the pre-existing empty-dictionary/no-claim fallback. No claim text
is repaired or inferred, no alternative reader/signature is substituted,
and no threshold, prompt, budget or target set is changed. The original
scientific source files and all original manifests still match. This is a
post-start exception-handling amendment and must be disclosed as such.

The first malformed reply had not been saved by the original failing process.
The unchanged greedy replay reproduced the same column-56 error, saved its
raw output and hashes, and recorded the blank capture. The failing sample SHA
is 2b3b0032cae5223035bea33f3075932f4ca80cb3122f0347ac68e84bd6575084;
raw-output SHA is ae2d107cf18eaa3d57f60cad59fadfaec638e719b2b3b4ed41465ad29d8797e9.
The event and ignored raw checkpoint are in results/extraction_failure_events.jsonl
and results/checkpoints/extraction_failures/. Target 71 then advanced through
new singleton scoring. No failed capture was silently replaced by a valid one.

Parser fixtures passed for unchanged valid/no-object/missing-field behavior,
recorded malformed JSON, and propagation of unrelated exceptions. Original
first-70 result rows and their hash are preserved under results/provenance/.
Resumed original remaining supervisor as PID 75348 and composite child 75453;
incident supervisor PID 75351 waits normally, with lifetime-bound sleep
inhibitor. Both recover through experiments/run_resilient_queue.py plus role
argument (remaining or incident), retaining R1 on incident GPU children.
The heartbeat was updated with the R2 policy, launcher arguments and failure
reporting requirements.

Final reporting keeps every planned target in operational results, counts
invalid/blank and selected captures, and adds the separately labelled paired
nonblank-selected-capture sensitivity specified in R2. The same subset must
be applied to every comparator and never replace the all-target report.
Nonblank syntax is not independently verified semantic correctness. The
70/80 prefix and incomplete downstream results establish no new robustness
claim; human review remains deferred and future fresh NI margin remains .05.

### E36–E38 automated batch complete; incident suite begins

The original remaining batch completed at 2026-10-29T20:19:48Z. It includes
200 reader-target evaluations, 80 rebuilt composite targets and 100 cached
Qwen gate targets. Full integrity passed 3,240 raw answer-score checks,
identities, contexts, masks, candidate selection and frozen source manifests.
The gate replay reproduced the historical printed rates. Human labels remain
pending/deferred, not passed. The incident supervisor automatically acquired
the shared lock, hashed reader weights, and began its calibration phase.

Composite all80: endorsement .4875 undefended -> .05 OR+refill; accuracy
.4625 -> .4625. The extra exploratory paired control gives endorsement
difference -.4375, CI [-.55,-.325], Holm p=1.16e-10; no accuracy gain.
CoordGuard AF+refill is .0375 endorsement/.4875 accuracy; TrustRAG .1375/.5375.
No comparison in the frozen composite six-test family establishes an OR
advantage. Defended-clean OR accuracy .425 vs .65 unfiltered retains the
false-alarm cost. Among 73 originally poison-exposed targets, OR endorsement
is .0548 and accuracy .4521; this subset is reported separately.

R2 audit confirms 1/400 blank capture attempts and one blank selected capture
(test423). The all80 report retains it. The prespecified secondary nonblank
selected-capture analysis uses the same 79 targets for every comparator and
72 originally exposed targets. `analysis/e37_capture_sensitivity.py` reproduces
the all80 frozen-analysis rates/comparisons exactly and verifies the original
first70 byte prefix. Outputs and frozen audit sources are saved under
results/e37_capture_sensitivity*. Nonblank does not establish semantic validity.

R1 calibration validation found exact signatures, responses, NLI/attention
vectors, masks and final contexts across all selected cases/repeats, with
nonblank signatures. However median capped/default runtime ratio was .9940
and aggregate ratio 1.0383. It failed the prespecified performance rule, so
the cap was **not adopted**. The incident suite retains original default
allocator settings; no measured speedup is claimed. Choice and raw paired
validation are frozen in results/performance_validation.json and
results/performance_choice_frozen.json. Neither KV settings nor precision,
batching, sample sizes or method timings were changed.

### Completed composite fixed-gate replay

Completed the gate replay planned in the original E37 protocol, using the
unchanged E30 NLI threshold (.974904...) and stored answer arms only. The
original final-summary script had saved E37 gate inputs but did not produce
this composite-gate summary; the additional data-only analysis is
analysis/e37_gate_replay.py. Its input/code hashes and results are in
results/e37_gate_replay_manifest.json and results/e37_gate_replay.json.
The six-pair/two-endpoint comparison family is explicitly exploratory.
No threshold was recalibrated or selected from composite outcomes.

The fixed NLI gate fires on 35% of changed attacked contexts and 3.75% of
clean contexts. Gated OR endorsement is .25 versus .05 always-filter OR:
difference .20, paired CI [.1125,.2875], Holm p=.000305 in the 12-test family.
Clean accuracy improves .425 -> .6125 (unfiltered .65), but the clean gain's
Holm p=.0732 does not survive this family correction. The corresponding
attack-correctness change is only .4625 -> .475. This demonstrates a real
blocking/utility trade-off in this stress regime; the gate is not a universal
false-alarm solution. The degradation persists on the R2-prespecified 79
nonblank-selected-capture sensitivity and is not explained solely by the
malformed extraction.

With this fixed benign-calibration geometry threshold, native geometry-gated
CoordGuard leaves the attacked endpoints at undefended values (.4875
endorsement/.4625 accuracy). NLI-gated CG gives .25/.4875, with .625 clean
accuracy; geometry-gated clean accuracy is .65. These are results for this
implementation/calibration and cannot establish a general statement about
every CoordGuard gate or superiority to sample-aware cosine. Keep always-
filter and gated comparators distinct, and retain the earlier original-gate
replay on the 100 original Qwen contexts as a separate used-question scope.

The active incident ablation remains unfinished and its partial performance
has not been used for claims. A checkpoint-derived planning snapshot is
results/current_runtime_forecast.json: approximately 4–6 more hours for the
current phase and 35–80 hours for all remaining queued work on the awake Mac.
Those are engineering ranges, not confidence bounds or a guaranteed deadline.

### 30 October: Track 4 swarm extension authorized and frozen

The user authorized ANTIVENOM's Track 4 swarm extension, keeping all remaining
tests running and comparing shared signatures with blocklists and cosine
without clean-performance harm. The base incident ablation has now completed
80/80 cases (1,920 saved result arms), followed by its frozen power analysis.
The original supervisor PID 75351 is running prefix-free evaluation through
the existing R1/R2 launcher, child PID 23608. No original scientific source,
recipe, calibration, queue manifest or saved result was changed for this work.

E42 already supplies the one-publisher/three-non-capturing-receiver sharing
experiment and both shared-ID/distinct-ID poison layouts. Before any E42
receiver outcomes, froze `docs/SWARM_TRACK4_PROTOCOL.md` and 25 source/input
hashes in `results/swarm_track4_manifest.json`. Shared OR and the distinct-ID
layout are focal; entailment and shared-ID layouts remain secondary. This is
prospective analysis of previously used questions, not fresh confirmation.

Identified a clean-utility control gap: E42's isolated/no-update arm still
filters with attention. Added separate E45 untreated clean receiver responses
on the exact saved contexts: 80 incidents x two layouts x three receivers =
480 actual calls. Identical contexts are still answered independently; no
response substitution. The same reader/prompt/fidelity/allocator settings are
retained. E45 extracts no signatures, fits no thresholds, generates no attacks,
and makes no randomized latency claim against earlier E42 timings.

The focused analysis pairs by incident, averaging receivers first. It reports
paired bootstrap intervals, five Holm-corrected directional tests, conservative
simultaneous bounded-mean intervals and exact upper bounds for any receiver
clean-answer loss. Strict clean loss margin is zero; the user's .05 endorsement
margin remains reserved for a future fresh confirmation. Equal observed scores
or nonsignificance cannot establish no harm. Include all captures in main
results, with identically paired nonblank sensitivity separately.

Synthetic preflight verifies incident clustering, context-pairing rejection,
effect direction and nonzero finite-sample uncertainty even with zero observed
losses. Sources compile and all original frozen hashes still match. No swarm
effectiveness claim has yet been supported by outcomes.

Detached Track 4 supervisor PID 24377 waits for the entire original incident
queue and integrity to succeed before taking the same model lock. Its lifetime
sleep inhibitor is PID 24381; no second GPU model child was started. Status is
`results/swarm_track4_status.json`. The existing heartbeat now includes E45,
its integrity and focused analysis before final reporting/completion.

All work produced now predates the Nov 6–8 sprint and is explicitly identified
as preexisting work in README/protocol. This tests shared protection among
homogeneous serial local agents, not autonomous contagion, authenticated
publication, heterogeneous fleets or a swarm-wide false-warning/revocation
experiment. The sprint report must separate later weekend contributions.

### 30 October: completed incident base ablation audited on CPU

Added a separate completed-scope analysis, `analysis/incident_base_interim.py`,
without changing the frozen suite or any GPU recipe. It invokes the original
`incident_summary.summarize` comparisons and original integrity answer checker.
All 80 used NQ targets, 1,920 answers, saved contexts, exclusion rules and
mistaken-capture source selections pass base-only checks. All 80 selected
signatures are nonblank; semantic correctness remains unvalidated. Full suite
integrity, later context-shift scopes and swarm results remain pending.

| Method | Attacked endorsement | Attacked correct | Clean correct |
| --- | --- | --- | --- |
| None | .8750 | .2750 | .6500 |
| Attention | .1750 | .5625 | .4250 |
| Entailment | .1625 | .6000 | .6375 |
| OR | .0500 | .6000 | .4125 |
| Avidity | .0500 | .6125 | .4250 |
| Captured-sample cosine | .0250 | .6500 | .6500 |
| Exact captured-text hash | .8750 | .2750 | .6500 |
| CoordGuard always-filter | .0500 | .5250 | .4625 |
| CoordGuard native geometry gate | .6375 | .3125 | .6500 |
| Full local TrustRAG | .0625 | .5625 | .5750 |
| NLI-gated OR | .1000 | .5750 | .6125 |
| Mistaken-capture OR | .1750 | .5500 | .4000 |

OR versus none: endorsement difference -.825, paired bootstrap 95% interval
[-.900,-.7375], Holm p=4.07e-18; attacked-correctness difference +.325, interval
[.2122,.4375], Holm p=.000345. These support blocking known-campaign variants
on this used-question scope. Captured text itself is excluded throughout;
the exact-hash baseline consequently cannot block distinct released variants.

OR versus cosine: endorsement difference +.025, interval [-.025,.075], Holm
p=1; attacked-correctness difference -.050, interval [-.1125,0], Holm p=1.
Clean-correctness difference -.2375, interval [-.3625,-.1125], raw p=.000878,
Holm p=.1045 in the original broad 152-comparison family. The pairwise interval
is not multiplicity-adjusted; no superiority or equivalence follows. Cosine's
point estimates are better on all three endpoints, and the added complexity
of OR has not earned a demonstrated advantage here. Do not replace the frozen
swarm focal method or recalibrate it after this observation.

NLI-gated OR versus this calibrated geometry-gated CoordGuard has less
endorsement (-.5375, interval [-.6625,-.4125], Holm p=2.26e-9) and higher
attacked correctness (+.2625, interval [.1375,.375], Holm p=.0238), but clean
correctness is -.0375 (interval [-.0875,0], Holm p=1). No broad gate or SOTA
superiority claim follows, especially given the stronger cosine comparator.

The completed development power calculation has no finite recommended sample
for the proposed conjunction under its estimated effects: gated OR's clean
utility point estimate is below native geometry-gated CoordGuard. Against
TrustRAG alone, the estimated endorsement difference is +.0375, leaving only
.0125 slack inside the user's .05 margin. The planning approximation requires
8,428 independent targets for conservative joint 80% power for that component.
These noisy development estimates are not a fresh NI result or a reason to
change the margin; the 212-family MemForm diagnostic cannot become the primary
confirmation by relabelling it.

Outputs: `results/incident_base_interim_summary.json`, its readable summary and
`results/incident_base_interim_manifest.json`; no original result overwritten.
Prefix-free evaluation continues under the existing model lock (52/80 complete
at this audit). Swarm and E45 supervisors remain queued as specified.

### 30 October: prefix-free incident scope complete; recurrence started

Prefix-free evaluation finished all 80 targets (1,440 arms) at 14:36 UTC.
The original supervisor automatically started recurrence child PID 38263.
A separate CPU-only `analysis/incident_prefixfree_interim.py` audit checks
all 1,440 raw responses/context masks against the unchanged full-suite checker,
captured exclusion, saved checkpoint identity and original frozen hashes.
All pass this scope's checks; full-suite integrity is still pending. All 80
selected captures are nonblank, which is not human-verified semantic validity.

| Method | Attacked endorsement | Attacked correct | Clean correct |
| --- | --- | --- | --- |
| None | .6750 | .3500 | .6500 |
| Attention | .1500 | .5625 | .4250 |
| Entailment | .1625 | .5625 | .6250 |
| OR | .1125 | .5750 | .4125 |
| Avidity | .0875 | .5250 | .4125 |
| Captured-sample cosine | .1500 | .5875 | .6375 |
| CoordGuard native geometry gate | .6125 | .3750 | .6500 |
| Full local TrustRAG | .0875 | .5000 | .5750 |
| NLI-gated OR | .2375 | .5250 | .6250 |

Original frozen analysis uses 104 comparisons in this scope. OR versus none
endorsement difference is -.5625, paired bootstrap 95% interval [-.6875,-.4375],
Holm p=7.05e-9. Thus blocking survives this prefix-free, captured-excluded
context shift on used questions. Its attacked accuracy difference +.225 has
interval [.10,.35] but Holm p=.1829, so it does not survive this broad family.

OR versus cosine endorsement difference is -.0375, interval [-.1375,.0625],
Holm p=1: no demonstrated superiority. Their attacked accuracy difference is
-.0125, interval [-.10,.075], Holm p=1. OR's clean accuracy is lower by .225,
interval [-.35,-.10], raw p=.00210, Holm p=.1829; the pairwise interval is not
multiplicity-adjusted. Compared with the base scope, cosine's near-clone
advantage weakens after removing prefixes, but OR's complexity and clean-utility
cost still have no demonstrated joint advantage. Do not infer equivalence.

Fixed NLI gating restores clean accuracy to .625 from .4125, while endorsement
rises to .2375 from .1125; both comparisons fail the scope-wide correction.
No universal gate benefit, no-harm result, swarm superiority or fresh primary
confirmation is established. No model recipe, threshold or swarm focal method
was changed after inspecting these outcomes.

Results are in `results/incident_prefixfree_interim_summary.json`, its readable
summary and `results/incident_prefixfree_interim_manifest.json`. Recurrence,
second-retriever, swarm and MemForm scopes and E45 remain in the serial queue.

### 31 October: explicit cross-chat temporary resource priority

At 02:12:47 UTC, the recurrence worker PID 38263 was suspended (process state
T) by a resource guard for another local experiment. This was investigated
before attempting recovery. The actual human reply in the chat titled
`Assess Qwen Bit Changes in Swarms` explicitly approved temporarily pausing
the Antivenom and Qwen v5.2 workers, with automatic resumption when that
peer-review run finishes. The approval was verified from `read_thread`, not
inferred merely from a local `human_authorized` flag.

Honor that priority: no forced SIGCONT, restart or duplicate model job while
the approved priority process remains alive. Recurrence is preserved at 156
of 160 complete cases, 2,187 saved arms. Both original/supplement supervisors
and their sleep inhibitors are alive. All frozen hashes and E37's saved prefix
still match; no scientific recipe or saved outcome changed.

The existing external watcher PID 76314 checks priority process PID 65858's
identity, then sends SIGCONT to the exact suspended workers when it exits.
Verified its config, state, identities and liveness. Local evidence is recorded
in `results/external_resource_pause.json`; the heartbeat now respects the
explicit priority override. This is an operational suspension, not an
experimental failure, canceled task or scientific amendment. Calendar ETA is
extended by the as-yet unknown remaining priority-run duration.

The priority process subsequently exited. Its existing watcher resumed the
same recurrence worker automatically at 02:40:11 UTC (10:40 Singapore) on
31 October; no local restart or duplicate job was needed. At 02:55 UTC,
recurrence had reached 158/160 cases with fresh checkpoint progress. The
watcher then exited normally. A priority process exit is not evidence that
the other experiment completed successfully; only the resume condition and
ANTIVENOM continuation have been verified here.

### 31 October: recurrence completes; E5 calibration starts

All 160 later-session cases (two per independent incident, 80 incidents) finished
at 02:59 UTC. The original queue automatically started E5 calibration, child
PID 84348. Its first 3/20 calibration cases are saved at the 03:25 UTC check.
The swarm and E45 controls remain queued; no receiver outcome exists yet.

`analysis/incident_recurrence_interim.py` audits 2,240 raw answers with the
unchanged original integrity checker, exact stored later questions, checkpoint
identity, actual changed context hashes and captured-passage exclusion.
Scope checks pass; full suite integrity remains pending. Every incident has
two sessions and one consistent nonblank selected signature. Nonblank does not
establish semantically correct extraction. Statistics average the two sessions
within each incident before paired uncertainty; the denominator is 80, not 160.

| Method | Attacked endorsement | Attacked correct | Clean correct |
| --- | --- | --- | --- |
| None | .7500 | .3000 | .5750 |
| Attention | .25625 | .4375 | .4500 |
| Stored OR | .0500 | .48125 | .4500 |
| Captured-sample cosine | .03125 | .54375 | .5375 |
| Native geometry-gated CoordGuard | .6500 | .29375 | .5750 |
| Full local TrustRAG | .0250 | .4875 | .53125 |
| NLI-gated OR | .1125 | .4375 | .5500 |

With the frozen 72-comparison family and incident-level 20,000-draw paired
sign randomization, stored OR versus attention endorsement difference is
-.20625, paired bootstrap 95% interval [-.29375,-.125], Holm p=.00360.
Versus none the difference is -.70, interval [-.7875,-.60625], Holm p=.00360.
This supports reusable known-campaign protection against the attention-only
ablation and undefended recurrence on this development scope.

It does not establish superiority over simple sample similarity: OR minus
cosine endorsement is +.01875, interval [0,.05], Holm p=1; attacked accuracy
-.0625, interval [-.13125,0], Holm p=1; clean accuracy -.0875, interval
[-.18125,0], Holm p=1. OR minus TrustRAG endorsement is +.025, interval
[-.025,.08125], Holm p=1; clean accuracy -.08125, interval [-.18125,.01875],
Holm p=1. Nonsignificance does not establish equivalence or clean no-harm.

Stored OR's clean accuracy is below untreated by .125, interval [-.225,-.03125],
but Holm p=1 in this broad family; the interval is not multiplicity-adjusted.
The NLI gate improves clean accuracy by .10 in point estimate while raising
endorsement by .0625; neither survives the family correction. No threshold,
method or swarm focal analysis changed based on these outcomes.

Raw/audited outputs: `results/incident_recurrence_interim_summary.json`, its
readable summary and `results/incident_recurrence_interim_manifest.json`.
These actual-reretrieval results are separate from historical E18's stored
contexts. They cannot establish receiver protection, official MemMorph results,
heterogeneous swarm transfer or the fresh powered primary confirmation.

At 04:25:44 UTC, a new resource guard in the personality-activation chat
suspended the E5 worker PID 84348 and incident supervisor PID 75351 at 18/20
calibration cases. Its state explicitly applies the previously verified user
temporary-pause approval to successor workers/queue. The latest human steering
in that chat focuses the work on personality activation interventions. This
records the other chat's application of the earlier authorization, not a new
human approval invented from a local flag.

Verified matching process identities, active priority screen PID 3048 and
resume watcher PID 3187, config under
`/var/folders/kx/80_lxpgd2r78xfgmv2__lnrc0000gn/T/personality_activation_3048_y7u_2ivo/`.
The watcher resumes the exact queue and child when its screen exits. Do not
interfere with that intentional priority or launch a duplicate. Original and
supplemental hashes still match. Updated `results/external_resource_pause.json`
and archived the completed earlier pause separately; scientific recipes and
checkpoints are unchanged. ETA now also includes this screening pause.
