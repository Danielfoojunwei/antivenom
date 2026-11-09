"""Loader for the published PoisonedRAG benchmark artifacts (Zou et al.,
USENIX Security 2025). Poison passages are read from the authors' released
``results/adv_targeted_results/*.json``; we never generate attack text.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "external" / "poisonedrag"


@dataclass
class Target:
    id: str
    question: str
    correct: str
    incorrect: str
    poison: list[str]
    clean_ids: list[str]      # clean top-100 doc ids by released Contriever score


def clean_str(s) -> str:
    """Verbatim from PoisonedRAG src/utils.py."""
    s = str(s).strip()
    if len(s) > 1 and s[-1] == ".":
        s = s[:-1]
    return s.lower()


def load(dataset: str = "nq", prefix: bool = True) -> tuple[list[Target], dict]:
    """prefix=False omits the attack.py question prefix (M0 control; text otherwise verbatim)."""
    adv = json.load(open(ROOT / f"{dataset}.json"))
    res = json.load(open(ROOT / f"{dataset}-contriever.json"))
    corpus = json.load(open(ROOT / f"{dataset}_target_corpus.json"))
    # PoisonedRAG src/attack.py (LM_targeted): adv = question + "." + released text
    targets = [Target(v["id"], v["question"], v["correct answer"], v["incorrect answer"],
                      [(v["question"] + "." if prefix else "") + a for a in v["adv_texts"]], list(res[v["id"]].keys()))
               for v in adv.values()]
    return targets, corpus
