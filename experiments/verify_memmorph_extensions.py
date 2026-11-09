"""Verify new local software separately from frozen studies; never load a model."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

OLD_TESTS = ("test_memmorph_eval.py", "test_memmorph_readiness.py", "test_tool_policy_signature.py")
NEW_TESTS = ("test_memmorph_matched_sources.py", "test_memmorph_run_record.py",
             "test_signature_lifecycle.py", "test_memmorph_extension_integration.py",
             "test_memform_drop_all_control.py")
NEW_SOURCES = (
    "src/antivenom/memmorph_matched_sources.py", "src/antivenom/memmorph_run_record.py",
    "src/antivenom/signature_lifecycle.py", "experiments/verify_memmorph_extensions.py",
    "experiments/memform_drop_all_control.py", "docs/MEMMORPH_EXTENSION_PROTOCOL.md",
    "docs/MEMFORM_DROP_ALL_CONTROL.md", *("tests/" + name for name in NEW_TESTS),
)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text())


def save(name, data):
    path = ROOT / name
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def verify_previous():
    baseline = read("results/heartbeat_integrity_check.json")
    manifests = ["results/" + name for name in sorted(baseline["checked_inputs"])]
    manifests.append("results/memmorph_alignment_software_manifest.json")
    checks, cache = {}, {}
    for name in manifests:
        inputs = read(name)["inputs"]
        for filename, expected in inputs.items():
            path = Path(filename)
            path = path if path.is_absolute() else ROOT / path
            if path not in cache:
                cache[path] = sha(path)
            if cache[path] != expected:
                raise RuntimeError(f"Frozen input changed: {name}: {filename}")
        checks[name] = {"inputs_checked": len(inputs), "manifest_sha256": sha(ROOT / name)}
    reference = read("results/provenance/e37_original_first70_hash.json")
    prefix = b"".join((ROOT / "results/e37_composite_nq_k10.jsonl").read_bytes().splitlines(keepends=True)[:70])
    preserved = ROOT / "results/provenance/e37_original_first70.jsonl"
    if hashlib.sha256(prefix).hexdigest() != reference["sha256"] or sha(preserved) != reference["sha256"]:
        raise RuntimeError("E37 original prefix changed")
    return {"manifests": checks, "unique_input_files_checked": len(cache),
            "original_scientific_manifest_count": len(manifests) - 1,
            "v1_preparation_unchanged": True, "e37_first70_preserved": True}


def freeze_new():
    payload = {"schema": "antivenom.memmorph.extensions-software.v1",
        "scope": "New engineering checks only; no native scientific execution freeze",
        "inputs": {name: sha(ROOT / name) for name in NEW_SOURCES},
        "v1_preparation_manifest_sha256": sha(ROOT / "results/memmorph_alignment_software_manifest.json")}
    name = "results/memmorph_extensions_software_manifest_v1.json"
    path = ROOT / name
    if path.exists():
        if read(name) != payload:
            raise RuntimeError("New extension source changed after pinning; use a disclosed new version")
    else:
        save(name, payload)
    return payload


def suite(patterns):
    loader = unittest.TestLoader()
    tests = unittest.TestSuite(loader.discover(str(ROOT / "tests"), pattern=name) for name in patterns)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(tests)
    return {"tests_run": result.testsRun, "passed": result.wasSuccessful(),
            "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped)}, stream.getvalue()


def main():
    before = verify_previous()
    freeze = freeze_new()
    original, original_log = suite(OLD_TESTS)
    extension, extension_log = suite(NEW_TESTS)
    after = verify_previous()
    if before != after:
        raise RuntimeError("Frozen inputs changed during CPU checks")
    from experiments.prepare_memmorph import inspect_artifacts
    native = inspect_artifacts(ROOT / "data/external/memmorph")
    report = {"schema": "antivenom.memmorph.extensions-verification.v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "passed": original["passed"] and extension["passed"],
        "original_tests": original, "new_tests": extension,
        "total_software_tests": original["tests_run"] + extension["tests_run"],
        "frozen_integrity": after,
        "extension_manifest_sha256": sha(ROOT / "results/memmorph_extensions_software_manifest_v1.json"),
        "new_sources_pinned": len(freeze["inputs"]), "model_calls": 0, "native_cases_run": 0,
        "native_empirical_validation": False, "human_review_passed": False,
        "native_readiness": native,
        "evidence_scope": "software contracts plus separate completed-record posthoc audit",
        "limits": ["Synthetic scores and toy selectors do not establish semantic or native efficacy",
                   "Hashes do not authenticate publishers, native provenance or real execution",
                   "Local revocation does not undo prior actions or demonstrate network recovery",
                   "Exact drop-all control is prepared separately; no new model answers in these checks"]}
    save("results/memmorph_extensions_verification_v1.json", report)
    (ROOT / "results/memmorph_extensions_tests_v1.log").write_text(original_log + "\n" + extension_log)
    print(json.dumps({k: report[k] for k in ("passed", "original_tests", "new_tests", "total_software_tests", "model_calls", "native_cases_run")}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
