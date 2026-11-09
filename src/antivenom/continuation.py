"""Resumable experiment support; original frozen implementation is unchanged."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .poisonedrag import load


def read_rows(path):
    path = Path(path)
    return [json.loads(line) for line in path.open() if line.strip()] if path.exists() else []


def keyed(path):
    rows = read_rows(path)
    out = {r["id"]: r for r in rows}
    assert len(out) == len(rows), f"duplicate targets: {path}"
    return out


def append(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def freeze(path, inputs, extra=None):
    payload = {"inputs": {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest()
                           for p in sorted(set(map(str, inputs)))}, "settings": extra or {}}
    if Path(path).exists():
        assert json.loads(Path(path).read_text()) == payload, f"frozen inputs changed: {path}"
    else:
        save(path, payload)
    return payload


def zf(v):
    v = np.asarray(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-9)


def logit(v):
    v = np.clip(np.asarray(v, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(v / (1 - v))


def passage_hashes(pool):
    return [hashlib.sha256(c["text"].encode()).hexdigest() for c in pool]


def clean_pool(t, corpus, rel):
    return sorted([{"text": corpus[i]["title"] + " " + corpus[i]["text"],
                    "score": rel[t.id][i], "label": "clean", "poison_index": -1,
                    "doc_id": i} for i in t.clean_ids], key=lambda c: -c["score"])


def build_pool(t, corpus, rel, retriever, poison_indices=None):
    pool = clean_pool(t, corpus, rel)
    q = retriever.encode([t.question])[0]
    indices = list(range(len(t.poison))) if poison_indices is None else list(poison_indices)
    vectors = retriever.encode([t.poison[j] for j in indices])
    pool += [{"text": t.poison[j], "score": float(v @ q),
              "label": "captured" if j == 0 else "poison", "poison_index": j,
              "doc_id": f"poison:{j}"} for j, v in zip(indices, vectors)]
    return sorted(pool, key=lambda c: -c["score"])


def refill(pool, flags):
    return [c["text"] for i, c in enumerate(pool[:10]) if i not in flags] + [c["text"] for c in pool[10:10 + len(flags)]]


class Reader:
    def __init__(self, model, layer):
        from .llm import LocalLLM
        self.llm = LocalLLM(model)
        self.hf = self.llm.tok._tokenizer
        self.layer = int(layer)
        self.fast = False

    def prompt(self, question, texts):
        from .masked import token_spans
        from .qa import wrap_prompt
        prompt = self.llm.tok.apply_chat_template(
            [{"role": "user", "content": wrap_prompt(question, texts)}],
            add_generation_prompt=True, tokenize=False)
        return token_spans(self.hf, prompt, texts)

    def attention(self, question, texts):
        from .masked import attention_rows
        ids, spans = self.prompt(question, texts)
        a = attention_rows(self.llm.model, ids, list(range(len(ids) - 8, len(ids))),
                           [self.layer])[self.layer].mean(axis=(0, 1))
        return zf([a[s:e].mean() for s, e in spans])

    def answer(self, target, texts, blocked=(), fast=None):
        from .masked import generate_masked
        from .qa import correct, endorses, wrap_prompt
        use_fast = self.fast if fast is None else fast
        if use_fast and not blocked:
            response = self.llm.generate([{"role": "user", "content": wrap_prompt(target.question, texts)}],
                                         temp=0.0, max_tokens=48).strip()
        else:
            ids, spans = self.prompt(target.question, texts)
            response = generate_masked(self.llm.model, self.llm.tok, ids,
                [spans[i] for i in blocked], -5.0 if blocked else 0.0,
                from_row=spans[-1][1] if spans else 0).strip()
        return {"resp": response, "endorsed": bool(endorses(response, target.incorrect)),
                "correct": bool(correct(response, target.correct))}

    def fidelity(self, targets, contexts):
        tests = []
        for t in targets[:3]:
            texts = [c["text"] for c in contexts[t.id]["pool"][:10]]
            regular = self.answer(t, texts, fast=True)
            masked = self.answer(t, texts, fast=False)
            tests.append({"id": t.id, "identical": regular["resp"] == masked["resp"],
                          "regular": regular["resp"], "masked": masked["resp"]})
        self.fast = all(r["identical"] for r in tests)
        return {"use_fast_ordinary": self.fast, "tests": tests}
