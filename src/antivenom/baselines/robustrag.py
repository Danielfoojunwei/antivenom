"""RobustRAG keyword aggregation (Xiang et al., 2024), ported for our reader.

Follows ``KeywordAgg.query`` in inspire-group/RobustRAG ``src/defense.py``
(no licence file in that repository; cited, algorithm and prompts reused for
comparison). The two prompts (``QA_PROMPT_TMPL``, ``QA_PROMPT_HINTS_TMPL``) were
extracted verbatim from ``src/prompt_template.py`` with ``ast`` into
data/baselines/robustrag_prompts.json. Parameters as released: alpha=0.3,
beta=3, abstention_threshold=1, short-form QA.
"""
from __future__ import annotations

import functools
import json
from collections import defaultdict
from pathlib import Path

import spacy
from nltk.corpus import stopwords

_PROMPTS = json.load(open(Path(__file__).resolve().parents[3] / "data" / "baselines" / "robustrag_prompts.json"))
IGNORE = {"VERB", "INTJ", "ADP", "AUX", "CCONJ", "DET", "PART", "PRON", "SCONJ", "PUNCT", "SPACE"}
PUNCT = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
STOP = set(stopwords.words("english"))


@functools.lru_cache(maxsize=1)
def _nlp():
    return spacy.load("en_core_web_sm")


def _ask(llm, prompt, max_tokens=64):
    return llm.generate([{"role": "user", "content": prompt}], temp=0.0, max_tokens=max_tokens).strip()


def keyword_agg(llm, question, docs, alpha=0.3, beta=3, abstention_threshold=1):
    raw = [_ask(llm, _PROMPTS["QA_PROMPT_TMPL"].format(query_str=question, context_str=d)) for d in docs]
    responses = [x for x in raw if "I don't" not in x]
    if len(responses) < abstention_threshold:
        return "I don't know.", {"separate": raw, "hints": ""}
    counter = defaultdict(int)
    for response in responses:
        phrases, tmp = [response.strip()], []
        for token in _nlp()(response):
            if token.pos_ in IGNORE:
                if tmp:
                    phrases.append("".join(x.lemma_ + x.whitespace_ for x in tmp).strip())
                    phrases += [x.lemma_ for x in tmp]
                    tmp = []
            else:
                tmp.append(token)
        phrases.append("".join(x.lemma_ + x.whitespace_ for x in tmp).strip())
        phrases += [x.lemma_ for x in tmp]
        for p in set(phrases):
            counter[p] += 1
    threshold = min(beta, alpha * len(responses))
    for tok, c in list(counter.items()):
        if c < threshold or tok in PUNCT or tok in STOP:
            del counter[tok]
    hints = ", ".join(t for t, _ in sorted(counter.items(), key=lambda x: (len(x[0]), x[0]), reverse=True))
    final = _ask(llm, _PROMPTS["QA_PROMPT_HINTS_TMPL"].format(query_str=question, hints=hints), max_tokens=48)
    return final, {"separate": raw, "hints": hints}
