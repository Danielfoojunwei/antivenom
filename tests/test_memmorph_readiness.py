"""Synthetic software readiness tests; no official or empirical results."""
import json
import tempfile
import unittest
from pathlib import Path

from experiments.prepare_memmorph import (
    REQUIRED, SOURCES, freeze_software, inspect_artifacts, sha_file,
)
from test_memmorph_eval import synthetic_bundle


class ReadinessTests(unittest.TestCase):
    def make_test_only_package(self, root):
        bundle = synthetic_bundle()
        (root / "upstream.txt").write_text("Synthetic immutable test input")
        bundle["provenance"] = {
            "kind": "author_verified_native", "author_verified": True,
            "source_url": "https://example.invalid/synthetic-test-only", "revision": "test-only",
            "verification_note": "Artificial metadata for contract tests, not an actual author attestation",
            "verified_by": "software-test",
            "inputs": [{"path": "upstream.txt", "sha256": sha_file(root / "upstream.txt")}],
            "native_pipeline": {k: "test-only" for k in (
                "harness_revision", "memory_writer", "retriever", "agent_model", "prompt_manifest",
                "tool_schema_manifest", "scorer_revision", "baseline_reproduction")}}
        (root / "native_bundle.json").write_text(json.dumps(bundle))
        for name in REQUIRED[1:-1]:
            (root / name).write_text(json.dumps({"scope": "synthetic test only"}))
        review = {"classification": "author_verified_native_export", "reviewer": "software-test",
                  "reviewed_utc": "test-only", "author_linkage_evidence": "synthetic test only",
                  "native_prompt_and_scorer_review": "synthetic test only",
                  "campaign_independence_review": "synthetic test only",
                  "bound_files": {name: sha_file(root / name) for name in REQUIRED[:-1]}}
        (root / "provenance_review.json").write_text(json.dumps(review))
        return bundle, review

    def test_absent_native_data_blocks_and_never_claims_validation(self):
        with tempfile.TemporaryDirectory() as d:
            report = inspect_artifacts(Path(d))
        self.assertEqual(report["status"], "blocked_native_artifacts_missing")
        self.assertEqual(set(report["missing"]), set(REQUIRED))
        self.assertFalse(report["native_empirical_validation"])
        self.assertEqual(report["model_calls"], 0)

    def test_software_cannot_turn_declared_provenance_into_efficacy(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_test_only_package(root)
            report = inspect_artifacts(root)
        self.assertEqual(report["status"], "saved_contract_verified_native_integration_pending")
        self.assertFalse(report["native_empirical_validation"])
        self.assertFalse(report["native_harness_executed"])

    def test_stale_review_rejects_changed_native_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundle, _ = self.make_test_only_package(root)
            bundle["campaigns"][0]["campaign_id"] = "changed"
            (root / "native_bundle.json").write_text(json.dumps(bundle))
            report = inspect_artifacts(root)
        self.assertEqual(report["status"], "blocked_native_artifacts_invalid")
        self.assertIn("not bound", report["errors"][0])

    def test_frozen_native_source_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_test_only_package(root)
            (root / "upstream.txt").write_text("changed test input")
            report = inspect_artifacts(root)
        self.assertEqual(report["status"], "blocked_native_artifacts_invalid")

    def test_synthetic_fixture_cannot_pass_native_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_test_only_package(root)
            (root / "native_bundle.json").write_text(json.dumps(synthetic_bundle()))
            report = inspect_artifacts(root)
        self.assertEqual(report["status"], "blocked_native_artifacts_invalid")
        self.assertIn("synthetic", report["errors"][0])

    def test_local_port_classification_cannot_be_erased(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundle, review = self.make_test_only_package(root)
            review["classification"] = "author_validated_local_port"
            (root / "provenance_review.json").write_text(json.dumps(review))
            report = inspect_artifacts(root)
            self.assertEqual(report["status"], "blocked_native_artifacts_invalid")
            bundle["provenance"]["kind"] = "author_validated_local_port"
            (root / "native_bundle.json").write_text(json.dumps(bundle))
            review["bound_files"]["native_bundle.json"] = sha_file(root / "native_bundle.json")
            (root / "provenance_review.json").write_text(json.dumps(review))
            report = inspect_artifacts(root)
        self.assertEqual(report["status"], "saved_contract_verified_native_integration_pending")
        self.assertEqual(report["classification"], "author_validated_local_port")
        self.assertFalse(report["native_empirical_validation"])

    def test_software_freeze_detects_changes_without_overwriting(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in SOURCES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("synthetic source " + name)
            manifest = root / "freeze.json"
            original = freeze_software(manifest, root)
            saved = manifest.read_bytes()
            self.assertEqual(original, freeze_software(manifest, root))
            (root / SOURCES[0]).write_text("changed")
            with self.assertRaisesRegex(ValueError, "changed after pinning"):
                freeze_software(manifest, root)
            self.assertEqual(saved, manifest.read_bytes())


if __name__ == "__main__":
    unittest.main()
