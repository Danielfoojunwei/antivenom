# Third-party notices

This repository adapts code and prompts from the projects below. Each upstream licence text is reproduced verbatim.

## PoisonedRAG (sleeepeer/PoisonedRAG): MIT
Used: `MULTIPLE_PROMPT` (src/antivenom/qa.py) and `clean_str` (src/antivenom/poisonedrag.py), copied verbatim; released adversarial texts and retrieval results, loaded as data and **not** redistributed here (see data/README.md).

```
MIT License

Copyright (c) 2024 Runpeng Geng

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## TrustRAG (HuichiZhou/TrustRAG): MIT
Used: `group_n_gram_filtering`, `k_mean_filtering` and the three `conflict_query` prompts (src/antivenom/baselines/trustrag.py), adapted from `defend_module.py`.

```
MIT License

Copyright (c) 2025 Dawn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## RobustRAG (inspire-group/RobustRAG): no licence file
The repository declares no licence. We re-implement the keyword-aggregation algorithm (`KeywordAgg.query`) for comparison and load its two QA prompts from data/baselines/robustrag_prompts.json, extracted from `src/prompt_template.py`. Cited: Xiang et al., *Certifiably Robust RAG against Retrieval Corruption*, 2024. Permission to redistribute those prompt strings has not been obtained, so data/baselines/robustrag_prompts.json is regenerated locally (see data/README.md) rather than redistributed.

## CoordGuard (Li, Guo, Xu; arXiv 2610.24834)
No code released. src/antivenom/baselines/coordguard.py is our own implementation from the paper's Section 3 and Algorithm 1.

## Models and datasets
- Qwen2.5-7B-Instruct (Apache-2.0), via mlx-community 4-bit conversion.
- facebook/contriever, intfloat/e5-large-v2, princeton-nlp/sup-simcse-bert-base-uncased, cross-encoder/nli-deberta-v3-base: see each model card for its licence.
- BEIR NQ, HotpotQA and MS-MARCO corpora: downloaded from the BeIR Hugging Face mirror by experiments/prep_corpus.py, **not redistributed**. MS-MARCO is for non-commercial research use under its own terms.

## MemForm evaluation release (MIT)

Source: https://github.com/opanhw/memform-code, pinned to commit
0565117042a31a5f78576f89ff6b8a77c393ee09. The original MIT license is retained
locally at `data/external/memform/LICENSE` alongside the pinned records and
reviewed reference source; external data are not redistributed by this repo.
`src/antivenom/memform_port.py` extracts the named native prompt, formatting,
memory-consolidation and multiple-choice-parser functions verbatim through
an explicit AST allowlist. See `docs/MEMFORM_DIAGNOSTIC_PROTOCOL.md` for the
local port's scope and departures. MemForm is distinct from MemMorph.
