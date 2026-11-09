"""R2: explicit invalid-capture fallback; successful parsing is unchanged."""
from __future__ import annotations

import hashlib
import json
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

from .continuation import append, save

CONTEXT = ContextVar("capture_parse_context", default={})


def parser_with_invalid_fallback(original, audit):
    def parse(text):
        try:
            return original(text)
        except json.JSONDecodeError as exc:
            audit(text, exc)
            return {}
    return parse


def install():
    from . import antibody
    original_parser = antibody._json
    original_analyse = antibody.Immunologist.analyse

    def audit(text, exc):
        context = CONTEXT.get()
        raw_hash = hashlib.sha256(text.encode()).hexdigest()
        observed = datetime.now(timezone.utc).isoformat()
        key = hashlib.sha256(json.dumps([context,raw_hash,sys.argv,observed], sort_keys=True).encode()).hexdigest()
        record = {"id": key, "observed_utc": observed,
                  **context, "script_arguments": list(sys.argv), "raw_output_sha256": raw_hash,
                  "error": str(exc), "error_class": "JSONDecodeError", "policy": "R2 invalid capture: existing empty-dictionary fallback"}
        save(f"results/checkpoints/extraction_failures/{key}.json", {**record, "raw_output": text})
        append("results/extraction_failure_events.jsonl", record)
        print("R2 invalid extraction recorded:", context.get("sample_sha256"), str(exc), flush=True)

    def analyse(self, sample):
        token = CONTEXT.set({"sample_sha256": hashlib.sha256(sample.encode()).hexdigest(),
                             "model": self.llm.model_id, "extraction_token_cap": 160, "temperature": 0.0})
        try:
            return original_analyse(self, sample)
        finally:
            CONTEXT.reset(token)

    antibody._json = parser_with_invalid_fallback(original_parser, audit)
    antibody.Immunologist.analyse = analyse
