# Data

Nothing in `data/external/`, `data/cache/` or `data/baselines/` is redistributed. Regenerate it locally with the commands below.

| Path | Source | How to regenerate |
|---|---|---|
| `external/poisonedrag/{nq,hotpotqa,msmarco}.json` | PoisonedRAG released adversarial texts (MIT), `results/adv_targeted_results/` | `curl -sL -o data/external/poisonedrag/nq.json https://raw.githubusercontent.com/sleeepeer/PoisonedRAG/main/results/adv_targeted_results/nq.json` (likewise for hotpotqa and msmarco) |
| `external/poisonedrag/*-contriever.json` | PoisonedRAG released Contriever retrieval results, `results/beir_results/` | the same pattern, with `results/beir_results/<dataset>-contriever.json` |
| `external/poisonedrag/*_target_corpus.json` | Subsets of the BEIR NQ, HotpotQA and MS-MARCO corpora (BeIR Hugging Face mirror) | `uv run python experiments/prep_corpus.py <dataset>`. NQ was prepared by the same procedure, inline. |
| `external/metatool_plugin_des.json` | MetaTool tool descriptions (not used in the current pipeline) | `curl -sL -o data/external/metatool_plugin_des.json https://raw.githubusercontent.com/HowieHwong/MetaTool/master/dataset/plugin_des.json` |
| `baselines/robustrag_prompts.json` | RobustRAG `src/prompt_template.py` (no licence file) | `uv run python experiments/prep_robustrag_prompts.py` |
| `cache/` | Local Contriever vectors | Rebuilt automatically by the experiments |

`validation/judge_cases.json` holds 12 author-written test cases for the `endorses` rule. They are synthetic, not human labels of real responses.
