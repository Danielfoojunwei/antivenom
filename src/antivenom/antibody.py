"""Antivenom: defensive counter-records synthesised from one captured sample.

The defender holds a single poisoned record ``sample``. It does not know the
other poison records, where they are, or (necessarily) the true answer.

Pipeline (all real LLM / retriever calls):
  1. ``analyse``     -- extract the false claim and the question it targets.
  2. ``epitope``     -- the query region that retrieves the sample. We use the
                        sample's own leading sentence plus paraphrased probes
                        and keep probes whose top-k actually contains the sample.
  3. ``synthesise``  -- write counter-records ("antibodies") that open with the
                        epitope sentence, so the same queries retrieve them,
                        followed by a neutralising body.
  4. ``negative_selection`` -- drop antibodies that change answers on a
                        "self" set of unrelated questions (autoimmunity check).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

ANALYSE_PROMPT = """You are a memory-integrity analyst. The passage below was identified as tampered: it was inserted into a knowledge base to make an assistant give a false answer.

Passage:
\"\"\"{sample}\"\"\"

Return JSON with two keys:
"question": the question this passage is trying to influence, as a short question.
"false_claim": the specific answer or fact the passage asserts, as a short phrase.
Return only the JSON object."""

CLOSED_BOOK_PROMPT = """Answer the question from your own knowledge in a few words. If unsure, say "unknown".

Question: {question}
Answer:"""

FLAG_PROMPT = """Write a short correction notice (2 sentences, plain prose) for a knowledge base. It must say that the claim "{claim}" in answer to "{question}" comes from tampered records and is false, and that answers should not rely on records making that claim. Do not state any other answer. Vary the wording; this is variant {i}."""

EVIDENCE_PROMPT = """Write a short factual knowledge-base passage (2-3 sentences, plain prose) that answers "{question}" with "{truth}". It should also note that the claim "{claim}" circulating in some records is false. Vary the wording; this is variant {i}."""

PROBE_PROMPT = """Rewrite the question below in {n} different natural ways a user might ask it. One per line, no numbering.

Question: {question}"""


@dataclass
class Analysis:
    question: str
    false_claim: str
    epitope_sentence: str
    probes: list[str] = field(default_factory=list)
    truth: str | None = None


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


class Immunologist:
    def __init__(self, llm):
        self.llm = llm

    def _ask(self, prompt: str, temp: float = 0.0, max_tokens: int = 160) -> str:
        return self.llm.generate([{"role": "user", "content": prompt}], temp=temp,
                                 top_p=0.95 if temp else 0.0, max_tokens=max_tokens).strip()

    def analyse(self, sample: str) -> Analysis:
        d = _json(self._ask(ANALYSE_PROMPT.format(sample=sample)))
        first = re.split(r"(?<=[.?!])\s*", sample.strip(), maxsplit=1)[0]
        return Analysis(question=d.get("question", first), false_claim=d.get("false_claim", ""),
                        epitope_sentence=first)

    def map_epitope(self, a: Analysis, store, sample_id: str, k: int, n: int = 5) -> Analysis:
        lines = self._ask(PROBE_PROMPT.format(question=a.question, n=n), temp=0.7).splitlines()
        cands = [a.question] + [l.strip(" -") for l in lines if l.strip()]
        a.probes = [q for q in cands if any(r.id == sample_id for r, _ in store.search(q, k))]
        return a

    def closed_book(self, a: Analysis) -> Analysis:
        ans = self._ask(CLOSED_BOOK_PROMPT.format(question=a.question), max_tokens=24)
        a.truth = None if "unknown" in ans.lower() else ans.rstrip(".")
        return a

    def synthesise(self, a: Analysis, kind: str, n: int, anchor: bool = True) -> list[str]:
        out = []
        for i in range(n):
            if kind == "flag":
                body = self._ask(FLAG_PROMPT.format(claim=a.false_claim, question=a.question, i=i + 1),
                                 temp=0.7 if i else 0.0)
            elif kind == "evidence":
                if not a.truth:
                    return []
                body = self._ask(EVIDENCE_PROMPT.format(question=a.question, truth=a.truth,
                                                        claim=a.false_claim, i=i + 1),
                                 temp=0.7 if i else 0.0)
            else:
                raise ValueError(kind)
            # Same retrieval geometry as the captured sample: lead with its epitope sentence.
            out.append((a.epitope_sentence + " " + body) if anchor else body)
        return out
