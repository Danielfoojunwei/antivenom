"""The receiver side: check retrieved passages against shared signatures.

For each active signature, every passage gets an entailment score for the
signature's hypothesis. Optionally, a second, sample-independent signal
(the reader's attention, or any influence score you supply) is combined
with it, as in the paper. A gate makes the defender act only when some
passage actually asserts a signature's claim, so clean traffic is untouched.

Defaults (from the paper's calibration on NQ questions 1-20):
  * flag a passage when entailment >= 0.01 (entailment-only mode), or when the
    combined score >= 0.0989 (with an attention/influence signal);
  * gate: act only if some passage has entailment >= 0.975.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Callable, Iterable, Sequence

from .backends import CrossEncoderEntailment, Entailment
from .signature import Signature

# Logistic weights fitted on calibration data with slot-corrected attention z.
COEF_ENTAIL, COEF_ATTN, INTERCEPT, COMBINED_THRESHOLD = 0.938, 2.347, 4.974, 0.0989

AttentionFn = Callable[[str, Sequence[str]], Sequence[float]]   # (query, passages) -> z-score per passage


@dataclass
class PassageVerdict:
    index: int
    flagged: bool
    signature_id: str | None
    entailment: float
    attention_z: float | None
    score: float
    reason: str


@dataclass
class Report:
    gate_fired: bool
    kept: list[str]
    removed: list[str]
    verdicts: list[PassageVerdict] = field(default_factory=list)
    refilled: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verdicts"] = [asdict(v) for v in self.verdicts]
        return d


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


class Defender:
    """Protects one agent's retrieved context.

    Args:
        signatures: claim signatures to defend against (add more with ``add``).
        entailment: any object with ``scores(passages, hypothesis)``; defaults
            to the paper's local NLI cross-encoder.
        attention: optional ``fn(query, passages) -> z-scores``; enables the
            combined score that catches reworded copies.
        gate: act only when some passage asserts a claim (recommended).
        flag_threshold, gate_threshold: see module docstring.
    """

    def __init__(self, signatures: Iterable[Signature] = (), entailment: Entailment | None = None,
                 attention: AttentionFn | None = None, gate: bool = True,
                 flag_threshold: float = 0.01, gate_threshold: float = 0.975):
        self.signatures: dict[str, Signature] = {s.id: s for s in signatures}
        self.entailment = entailment or CrossEncoderEntailment()
        self.attention, self.gate = attention, gate
        self.flag_threshold, self.gate_threshold = flag_threshold, gate_threshold

    def add(self, sig: Signature) -> None:
        self.signatures[sig.id] = sig

    def remove(self, sig_id: str) -> None:
        self.signatures.pop(sig_id, None)

    def active(self) -> list[Signature]:
        return [s for s in self.signatures.values() if not s.expired()]

    def check(self, passages: Sequence[str], query: str = "",
              refill: Callable[[int], Sequence[str]] | None = None) -> Report:
        """Score passages; remove flagged ones; optionally refill.

        ``refill(n)`` should return up to n replacement passages (for example
        the next-ranked results from your retriever). Replacements are checked too.
        """
        passages = list(passages)
        sigs = self.active()
        if not passages or not sigs:
            return Report(False, passages, [], [PassageVerdict(i, False, None, 0.0, None, 0.0, "no active signature")
                                               for i in range(len(passages))])
        best_e, best_sig = [0.0] * len(passages), [None] * len(passages)
        for s in sigs:
            for i, e in enumerate(self.entailment.scores(passages, s.hypothesis)):
                if e > best_e[i]:
                    best_e[i], best_sig[i] = e, s.id
        fired = (not self.gate) or max(best_e) >= self.gate_threshold
        z = list(self.attention(query, passages)) if (self.attention and fired) else None
        verdicts = []
        for i, e in enumerate(best_e):
            if not fired:
                verdicts.append(PassageVerdict(i, False, best_sig[i], e, None, e, "gate closed: no passage asserts a shared claim"))
                continue
            if z is not None:
                score = 1 / (1 + math.exp(-(COEF_ENTAIL * _logit(e) + COEF_ATTN * z[i] + INTERCEPT)))
                flag = score >= COMBINED_THRESHOLD
                why = ("asserts the shared claim" if e >= self.flag_threshold else "reader's attention fixes on it") if flag else "below threshold"
            else:
                score, flag = e, e >= self.flag_threshold
                why = "asserts the shared claim" if flag else "does not assert any shared claim"
            verdicts.append(PassageVerdict(i, flag, best_sig[i], e, z[i] if z is not None else None, score, why))
        kept = [p for p, v in zip(passages, verdicts) if not v.flagged]
        removed = [p for p, v in zip(passages, verdicts) if v.flagged]
        refilled = 0
        if refill and removed:
            extra = list(refill(len(removed)))
            if extra:
                sub = self.check(extra, query)          # replacements must pass the same check
                kept += sub.kept
                refilled = len(sub.kept)
        return Report(fired, kept, removed, verdicts, refilled)
