"""Pluggable model backends. Nothing here is tied to a framework.

Two roles need a model:
  * an LLM that turns a caught record into a claim signature (``LLM``), and
  * an entailment scorer that says whether a passage asserts that claim (``Entailment``).

Any object with the right method works. Ready-made options:
  * ``OpenAICompatibleLLM``: any OpenAI-style chat endpoint (OpenAI, OpenRouter,
    vLLM, Ollama, LM Studio, ...). Standard library only.
  * ``CallableLLM``: wrap your own ``fn(prompt) -> str``.
  * ``CrossEncoderEntailment``: the DeBERTa-v3 NLI model used in the paper
    (needs ``sentence-transformers``; loaded lazily).
  * ``LLMJudgeEntailment``: ask an LLM "does this passage assert the claim?"
    (works through any API, including closed models).
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Callable, Protocol, Sequence


class LLM(Protocol):
    def complete(self, prompt: str, max_tokens: int = 200) -> str: ...


class Entailment(Protocol):
    def scores(self, passages: Sequence[str], hypothesis: str) -> list[float]: ...


class CallableLLM:
    """Wrap any ``fn(prompt: str) -> str``."""

    def __init__(self, fn: Callable[[str], str]):
        self.fn = fn

    def complete(self, prompt: str, max_tokens: int = 200) -> str:
        return self.fn(prompt)


class OpenAICompatibleLLM:
    """Chat-completions client for any OpenAI-compatible endpoint.

    Examples:
        OpenAICompatibleLLM("openai/gpt-4o-mini")                      # OpenRouter (default base URL)
        OpenAICompatibleLLM("llama3.1", base_url="http://localhost:11434/v1", api_key="ollama")

    The key is read from ``api_key`` or the ``api_key_env`` environment variable
    (default ``OPENROUTER_API_KEY``, falling back to ``OPENAI_API_KEY``).
    Greedy decoding (temperature 0) is used so signatures are reproducible.
    """

    def __init__(self, model: str, base_url: str = "https://openrouter.ai/api/v1",
                 api_key: str | None = None, api_key_env: str = "OPENROUTER_API_KEY", timeout: float = 60.0):
        self.model, self.base_url, self.timeout = model, base_url.rstrip("/"), timeout
        self.api_key = api_key or os.environ.get(api_key_env) or os.environ.get("OPENAI_API_KEY")

    def complete(self, prompt: str, max_tokens: int = 200) -> str:
        body = json.dumps({"model": self.model, "messages": [{"role": "user", "content": prompt}],
                           "temperature": 0, "max_tokens": max_tokens}).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.base_url + "/chat/completions", data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            out = json.loads(r.read())
        return out["choices"][0]["message"]["content"] or ""


class CrossEncoderEntailment:
    """Entailment probability from a local NLI cross-encoder (the paper's default).

    Label order for ``cross-encoder/nli-deberta-v3-base`` is
    (contradiction, entailment, neutral); ``entail_index`` selects entailment.
    """

    def __init__(self, model: str = "cross-encoder/nli-deberta-v3-base", device: str = "cpu", entail_index: int = 1):
        self.model_name, self.device, self.entail_index = model, device, entail_index
        self._m = None

    def scores(self, passages: Sequence[str], hypothesis: str) -> list[float]:
        if not passages:
            return []
        if self._m is None:
            from sentence_transformers import CrossEncoder
            self._m = CrossEncoder(self.model_name, device=self.device)
        p = self._m.predict([(x, hypothesis) for x in passages], apply_softmax=True)
        return [float(row[self.entail_index]) for row in p]


JUDGE_PROMPT = """Does the passage below assert the following claim? Answer with a single number between 0 and 1: 1 if it clearly asserts it, 0 if it does not or says otherwise.

Claim: {h}

Passage: \"\"\"{p}\"\"\"

Number:"""


class LLMJudgeEntailment:
    """Entailment judged by an LLM. Use when no local NLI model is available
    (for example with closed models through OpenRouter). One call per passage."""

    def __init__(self, llm: LLM):
        self.llm = llm

    def scores(self, passages: Sequence[str], hypothesis: str) -> list[float]:
        out = []
        for p in passages:
            txt = self.llm.complete(JUDGE_PROMPT.format(h=hypothesis, p=p), max_tokens=8)
            m = re.search(r"[01](?:\.\d+)?", txt)
            out.append(min(1.0, max(0.0, float(m.group()))) if m else 0.0)
        return out
