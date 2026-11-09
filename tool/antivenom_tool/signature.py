"""Claim signatures: the antibody that one caught record becomes.

A signature is the question a planted record targets and the false claim it
pushes. It is small (about 250 bytes), carries no record identifier and no
attacker text beyond the claim itself, and can be shared with other agents.
Prompts are the ones used in the paper's experiments.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field

from .backends import LLM

EXTRACT_PROMPT = """You are a memory-integrity analyst. The passage below was identified as tampered: it was inserted into a knowledge base to make an assistant give a false answer.

Passage:
\"\"\"{sample}\"\"\"

Return JSON with two keys:
"question": the question this passage is trying to influence, as a short question.
"false_claim": the specific answer or fact the passage asserts, as a short phrase.
Return only the JSON object."""

REWRITE_PROMPT = """Question: {q}
A record claims: "{c}"
Rewrite the record's claim as one self-contained declarative sentence that names every person, place or thing explicitly (no pronouns) and states the claim as a direct answer to the question. Keep the record's position exactly; do not add or correct anything. Return only the sentence."""

YES_NO = re.compile(r"^(are|is|was|were|do|does|did|can|could|has|have|had|will|would|should)\b", re.I)
STRIP = re.compile(r'^\s*the record claims(\s+that)?\s*:?\s*"?', re.I)


class ExtractionError(ValueError):
    """Raised when the LLM does not return a usable question and claim."""


@dataclass
class Signature:
    question: str
    claim: str
    hypothesis: str
    created: float = field(default_factory=time.time)
    expires: float | None = None
    issuer: str = "local"
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(f"{self.question}\n{self.claim}".encode()).hexdigest()[:16]

    def expired(self, now: float | None = None) -> bool:
        return self.expires is not None and (now or time.time()) > self.expires

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_dict(cls, d: dict) -> "Signature":
        return cls(**{k: d[k] for k in ("question", "claim", "hypothesis", "created", "expires", "issuer", "id") if k in d})

    @classmethod
    def manual(cls, question: str, claim: str, **kw) -> "Signature":
        """Build a signature without an LLM, e.g. from an incident report."""
        return cls(question=question, claim=claim, hypothesis=hypothesis_for(question, claim), **kw)


def hypothesis_for(question: str, claim: str) -> str:
    return f'The answer to the question "{question}" is {claim}.'


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def make_signature(caught_record: str, llm: LLM, *, rewrite_yes_no: bool = True,
                   ttl_seconds: float | None = None, issuer: str = "local") -> Signature:
    """Turn one caught poisoned record into a shareable claim signature.

    Raises ``ExtractionError`` if the model returns no question or claim
    (silently using an empty signature would protect nothing).
    """
    d = _json(llm.complete(EXTRACT_PROMPT.format(sample=caught_record), max_tokens=200))
    q, c = str(d.get("question", "")).strip(), str(d.get("false_claim", "")).strip()
    if not q or not c:
        raise ExtractionError("model returned no question or false_claim; try a stronger model or Signature.manual()")
    hyp = hypothesis_for(q, c)
    if rewrite_yes_no and YES_NO.match(q):
        st = llm.complete(REWRITE_PROMPT.format(q=q, c=c), max_tokens=80).strip().strip('"')
        st = STRIP.sub("", st).strip().strip('"')
        if st:
            hyp = st
    now = time.time()
    return Signature(question=q, claim=c, hypothesis=hyp, created=now,
                     expires=now + ttl_seconds if ttl_seconds else None, issuer=issuer)
