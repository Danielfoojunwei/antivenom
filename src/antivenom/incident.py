"""Incident-response experiments. No benchmark labels enter a filter prompt."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder

from .antibody import Immunologist
from .baselines.coordguard import _e5, _embed, audit
from .baselines.trustrag import _simcse, trustrag
from .continuation import Reader, save
from .poisonedrag import load
from .qa import contains, correct, endorses
from .retriever import Contriever

FULL_METHODS = ["none", "entail", "attention", "OR", "avidity", "cosine", "exact_hash",
                "coordguard_af", "coordguard_gate", "trustrag", "gated_OR"]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def e5_embeddings(texts):
    return np.concatenate([_embed(texts[i:i + 12]) for i in range(0, len(texts), 12)])


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


class IncidentLab:
    def __init__(self, engine="contriever"):
        started = time.perf_counter()
        self.engine = engine
        self.targets, self.corpus = load("nq")
        self.by = {t.id: t for t in self.targets}
        self.rel = json.load(open("data/external/poisonedrag/nq-contriever.json"))
        self.retriever = Contriever()
        self.reader = Reader("mlx-community/Qwen2.5-7B-Instruct-4bit", 21)
        self.immunologist = Immunologist(self.reader.llm)
        self.nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")
        self.clean_vectors = None
        self.sample_vectors = {}
        self.sample_setup_seconds = {}
        self.initialization_seconds = time.perf_counter() - started

    def prewarm(self):
        # Load CPU baselines before timing; report setup separately.
        started = time.perf_counter()
        _e5()
        _simcse()
        # Execute real calibration-only CPU forward passes before per-method timing.
        _embed(["query: calibration warmup", "passage: calibration warmup"])
        from .baselines.trustrag import embed
        embed(["calibration warmup"])
        self.retriever.encode(["calibration warmup"])
        self.nli.predict([("calibration warmup", "This is calibration.")], apply_softmax=True)
        return time.perf_counter() - started

    def artifact(self, sample, incident_id):
        digest = sha(sample)
        self.prepare_sample(sample)
        path = Path(f"results/checkpoints/incident_artifacts/{digest}.json")
        if path.exists():
            value = json.load(path.open())
            assert value["sample_sha256"] == digest
            return {**value, "cosine_setup_seconds": self.sample_setup_seconds[digest]}
        started = time.perf_counter()
        an = self.immunologist.analyse(sample)
        payload = {"schema": 1, "incident_id": incident_id, "question": an.question,
                   "claim": an.false_claim, "sample_sha256": digest}
        value = {**payload, "extraction_seconds": time.perf_counter() - started,
                 "payload_bytes": len(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()),
                 "sample_bytes": len(sample.encode()), "extraction_valid": bool(an.question.strip() and an.false_claim.strip())}
        save(path, value)
        return {**value, "cosine_setup_seconds": self.sample_setup_seconds[digest]}

    def prepare_sample(self, sample):
        digest = sha(sample)
        if digest not in self.sample_vectors:
            started = time.perf_counter()
            vectors = e5_embeddings(["passage: " + sample]) if self.engine == "e5" else normalize(self.retriever.encode([sample]))
            self.sample_vectors[digest] = vectors[0]
            self.sample_setup_seconds[digest] = time.perf_counter() - started
        return self.sample_vectors[digest]

    def retrieve(self, target, question=None, clean_ids=None, poison_indices=(1, 2, 3, 4), clean=False):
        q = target.question if question is None else question
        ids = list(target.clean_ids if clean_ids is None else clean_ids)
        pool = [{"text": self.corpus[i]["title"] + " " + self.corpus[i]["text"], "label": "clean",
                 "doc_id": i, "poison_index": -1} for i in ids]
        if not clean:
            pool += [{"text": target.poison[j], "label": "poison", "doc_id": f"{target.id}:poison:{j}",
                      "poison_index": j} for j in poison_indices]
        if self.engine == "e5":
            query = e5_embeddings(["query: " + q])[0]
            vectors = e5_embeddings(["passage: " + p["text"] for p in pool])
            scores = vectors @ query
        else:
            query = self.retriever.encode([q])[0]
            if q == target.question:
                clean_scores = np.array([self.rel[target.id][i] for i in ids])
            else:
                if self.clean_vectors is None:
                    self.clean_vectors = dict(np.load("data/cache/nq_clean_vecs.npz"))
                assert all(i in self.clean_vectors for i in ids)
                clean_scores = np.stack([self.clean_vectors[i] for i in ids]) @ query
            poison_scores = self.retriever.encode([p["text"] for p in pool[len(ids):]]) @ query if len(pool) > len(ids) else np.array([])
            scores = np.concatenate([clean_scores, poison_scores])
        for p, score in zip(pool, scores):
            p["score"] = float(score)
        return sorted(pool, key=lambda p: -p["score"])

    def entail(self, texts, artifact):
        h = f'The answer to the question "{artifact["question"]}" is {artifact["claim"]}.'
        return self.nli.predict([(p, h) for p in texts], apply_softmax=True)[:, 1].astype(float)

    def cosine(self, texts, sample):
        captured = self.prepare_sample(sample)
        if self.engine == "e5":
            vectors = e5_embeddings(["passage: " + p for p in texts])
        else:
            vectors = normalize(self.retriever.encode(texts))
        return (vectors @ captured).astype(float)

    def filter(self, method, question, pool, artifact, sample, fit):
        texts = [p["text"] for p in pool[:10]]
        info = {}
        if artifact is None and method in ("OR", "gated_OR"):
            method = "attention"
            info["revoked_signature_fallback"] = True
        if method == "record_blocklist":
            flags = [i for i, p in enumerate(pool[:10]) if p["doc_id"] in fit["record_blocklist"]]
        elif method in ("none", "exact_hash"):
            flags = [] if method == "none" else [i for i, p in enumerate(texts) if sha(p) == sha(sample)]
        elif method in ("coordguard_af", "coordguard_gate"):
            comp, score = audit(question, texts)
            info.update(coordguard_component=sorted(comp), coordguard_score=score)
            flags = sorted(comp) if method == "coordguard_af" or score is not None and score > fit["geometry_gate"] else []
        elif method == "cosine":
            cosine = self.cosine(texts, sample)
            info["cosine"] = cosine.tolist()
            flags = np.flatnonzero(cosine >= fit["cosine_threshold"]).tolist()
        else:
            e = self.entail(texts, artifact) if method in ("entail", "OR", "avidity", "gated_OR") else None
            if e is not None:
                info["entail"] = e.tolist()
            if method == "gated_OR" and max(e) < fit["nli_gate"]:
                info["gate_fired"] = False
                return [], info
            if method == "gated_OR":
                info["gate_fired"] = True
            z = self.reader.attention(question, texts) if method != "entail" else None
            if z is not None:
                info["attention_z"] = z.tolist()
            if method == "entail":
                flags = np.flatnonzero(e >= .01).tolist()
            elif method == "attention":
                flags = np.flatnonzero(z >= 0).tolist()
            elif method in ("OR", "gated_OR"):
                flags = np.flatnonzero((e >= .01) | (z >= 0)).tolist()
            elif method == "avidity":
                p = np.clip(e, 1e-6, 1 - 1e-6)
                logits = fit["coef"][0] * np.log(p / (1 - p)) + fit["coef"][1] * z + fit["intercept"]
                score = 1 / (1 + np.exp(-np.clip(logits, -700, 700)))
                info["avidity"] = score.tolist()
                flags = np.flatnonzero(score >= fit["avidity_threshold"]).tolist()
            else:
                raise ValueError(method)
        return flags, info

    def run_method(self, method, target, question, pool, artifact, sample, fit):
        began = time.perf_counter()
        texts = [p["text"] for p in pool[:10]]
        filter_begin = time.perf_counter()
        if method == "trustrag":
            response, kept = trustrag(self.reader.llm, question, texts)
            pipeline_seconds = time.perf_counter() - began
            flags = [i for i, text in enumerate(texts) if text not in kept]
            result = {"resp": response, "correct": bool(correct(response, target.correct)),
                      "endorsed": bool(endorses(response, target.incorrect)),
                      "pipeline_seconds": pipeline_seconds,
                      "filter_seconds": None, "answer_seconds": None,
                      "timing_note": "Includes TrustRAG filtering and all three generative stages"}
            final = [p for p in pool[:10] if p["text"] in kept]
            info = {}
        else:
            flags, info = self.filter(method, question, pool, artifact, sample, fit)
            filter_seconds = time.perf_counter() - filter_begin
            final = [p for i, p in enumerate(pool[:10]) if i not in flags] + pool[10:10 + len(flags)]
            answer_begin = time.perf_counter()
            result = self.reader.answer(replace(target, question=question), [p["text"] for p in final])
            answer_seconds = time.perf_counter() - answer_begin
            result.update(filter_seconds=filter_seconds, answer_seconds=answer_seconds,
                          pipeline_seconds=time.perf_counter() - began)
        result.update(flags=flags, detection=info, final_context_hashes=[sha(p["text"]) for p in final],
            clean_in=sum(p["label"] == "clean" for p in pool[:10]),
            poison_in=sum(p["label"] != "clean" for p in pool[:10]),
            clean_removed=sum(pool[i]["label"] == "clean" for i in flags),
            poison_removed=sum(pool[i]["label"] != "clean" for i in flags),
            poison_after_refill=sum(p["label"] != "clean" for p in final),
            gold_token_clean_before=sum(p["label"] == "clean" and contains(p["text"], target.correct) for p in pool[:10]),
            gold_token_clean_after=sum(p["label"] == "clean" and contains(p["text"], target.correct) for p in final))
        return result
