"""Meaningful checks for blind review coverage, immutability and human gates."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication_review", ROOT / "analysis/prepare_publication_review_v2.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class PublicationReviewV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates, cls.key = review.build(ROOT)

    def test_all_families_and_all_method_conditions_mapped(self):
        self.assertEqual(len(self.templates["extraction"]), 212)
        self.assertEqual(len(self.templates["policy"]), 212)
        observations = [x for value in self.key["outcome"].values() for x in value["observations"]]
        self.assertEqual(len(observations), 2120)
        by = {}
        for value in self.key["outcome"].values():
            by.setdefault(value["family_id"], []).extend(value["observations"])
        self.assertEqual(len(by), 212)
        for rows in by.values():
            self.assertEqual({(r["condition"], r["method"]) for r in rows},
                             {(c, m) for c in ("clean", "poisoned") for m in (*review.METHODS, "drop_all")})

    def test_blind_content_has_no_keys_flags_methods_or_automated_labels(self):
        forbidden = {"family_id", "task_id", "condition", "method", "removed_by", "rule_prediction",
                     "benchmark_clean_answer", "benchmark_poisoned_answer", "clean_answer", "poisoned_answer"}
        for kind, rows in self.templates.items():
            for row in rows:
                self.assertFalse(forbidden & set(row))
                self.assertTrue(all(row[field] == "" for field in row if field.startswith("human_")))
                self.assertNotIn("F0", row["uid"])
                if kind != "extraction":
                    self.assertNotIn("extracted_claim", row)
        self.assertNotIn("reference_policy", self.templates["extraction"][0])
        self.assertNotIn("reference_policy", self.templates["outcome"][0])

    def test_deduplication_retains_context_specific_full_mapping(self):
        self.assertLess(len(self.templates["outcome"]), 2120)
        self.assertEqual(set(self.key["memory"]), {r["uid"] for r in self.templates["memory"]})
        total = sum(len(value["observations"]) for value in self.key["memory"].values())
        self.assertEqual(total, 212 * 8)
        self.assertEqual({value["family_id"] for value in self.key["memory"].values()},
                         {value["family_id"] for value in self.key["extraction"].values()})

    def expected(self, kind):
        return {r["uid"]: review.digest(review.canonical(review.immutable(r)).encode()) for r in self.templates[kind]}

    def test_missing_duplicate_and_changed_content_rejected(self):
        rows = copy.deepcopy(self.templates["extraction"])
        expected = self.expected("extraction")
        for bad in (rows[:-1], rows + [rows[0]]):
            with self.assertRaises(AssertionError):
                review.validate_rows("extraction", bad, expected)
        rows[0]["captured_text"] += " modified"
        with self.assertRaises(AssertionError):
            review.validate_rows("extraction", rows, expected)

    def test_invalid_labels_rejected_but_uncertainty_allowed(self):
        rows = copy.deepcopy(self.templates["extraction"])
        expected = self.expected("extraction")
        rows[0]["human_claim_faithful"] = "uncertain"
        review.validate_rows("extraction", rows, expected)
        rows[0]["human_claim_faithful"] = "model says yes"
        with self.assertRaises(AssertionError):
            review.validate_rows("extraction", rows, expected)
        outcomes = copy.deepcopy(self.templates["outcome"])
        outcomes[0]["human_committed_label"] = "AMBIGUOUS"
        review.validate_rows("outcome", outcomes, self.expected("outcome"))

    def test_preparation_never_overwrites_human_labels_and_stays_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            result = review.prepare(ROOT, target)
            self.assertEqual(result["status"], "pending_independent_human_labels")
            self.assertFalse(result["human_validation_passed"])
            path = target / "phase_1_extraction/reviewer_a.csv"
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["human_claim_faithful"] = "yes"
            review.write_csv(path, rows)
            review.prepare(ROOT, target)
            with path.open(newline="") as stream:
                preserved = list(csv.DictReader(stream))
            self.assertEqual(preserved[0]["human_claim_faithful"], "yes")
            self.assertFalse(review.verify_frozen(ROOT, target)["human_validation_passed"])

    def test_complete_synthetic_labels_do_not_automatically_pass(self):
        # Synthetic labels remain inside this isolated test directory only.
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            review.prepare(ROOT, target)
            for index, kind in enumerate(review.FIELDS):
                for reviewer in ("a", "b"):
                    path = target / f"phase_{index + 1}_{kind}" / f"reviewer_{reviewer}.csv"
                    with path.open(newline="") as stream:
                        rows = list(csv.DictReader(stream))
                    for row in rows:
                        for field, options in review.FIELDS[kind].items():
                            row[field] = options[0] if options is not None else json.loads(row["choices"])[0]["label"]
                    review.write_csv(path, rows)
            result = review.assess(target)
            self.assertEqual(result["status"], "complete_labels_missing_human_attestation")
            self.assertFalse(result["human_validation_passed"])
            attestations = {r: {"reviewer_name_or_private_code": "test_human_" + r,
                               "is_independent_human": True, "signed_utc": "test only",
                               "did_not_consult_other_reviewer_or_rule_key": True,
                               "no_model_generated_labels": True} for r in ("a", "b")}
            (target / "attestations.json").write_text(review.canonical(attestations))
            result = review.assess(target)
            self.assertEqual(result["status"], "independent_labels_complete_adjudication_required")
            self.assertFalse(result["human_validation_passed"])

    def test_categorical_agreement_handles_degenerate_labels(self):
        self.assertEqual(review.agreement(["yes", "no"], ["yes", "no"])["cohen_kappa"], 1)
        self.assertIsNone(review.agreement(["yes"], ["yes"])["cohen_kappa"])
        self.assertIsNone(review.agreement([], [])["agreement"])

    def make_disagreement(self, target):
        review.prepare(ROOT, target)
        uid = None
        for reviewer, selected in (("a", "yes"), ("b", "no")):
            path = target / f"phase_1_extraction/reviewer_{reviewer}.csv"
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            if uid is None:
                uid = rows[0]["uid"]
            row = next(r for r in rows if r["uid"] == uid)
            row["human_claim_faithful"] = selected
            review.write_csv(path, rows)
        review.assess(target)
        path = target / "PRIVATE_admin_only/adjudication_pending.json"
        entries = json.loads(path.read_text())
        self.assertEqual(len(entries), 1)
        return path, entries

    def test_regression_signed_judgment_survives_reassessment_and_prepare(self):
        # Never writes fixture labels into the real review package.
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            path, entries = self.make_disagreement(target)
            entries[0].update(adjudicated_human_label="uncertain", human_reason="Isolated test fixture: limiting condition unclear.",
                              adjudicator_name_or_private_code="fixture_adjudicator", signed_utc="2026-11-04T00:00:00+00:00")
            path.write_text(review.canonical(entries))
            before = path.read_bytes()
            for operation in (review.assess, lambda t: review.prepare(ROOT, t), review.assess):
                status = operation(target)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(status["signed_adjudication_fields_preserved"], 1)
                self.assertFalse(status["human_validation_passed"])

    def test_unsigned_partial_reason_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            path, entries = self.make_disagreement(target)
            entries[0]["human_reason"] = "Fixture note to complete later."
            path.write_text(review.canonical(entries))
            before = path.read_bytes()
            status = review.assess(target)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(status["unsigned_adjudication_fields_with_saved_work"], 1)
            self.assertFalse(status["human_validation_passed"])

    def test_mutated_mapping_or_adjudication_binding_is_rejected_without_loss(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            path, entries = self.make_disagreement(target)
            entries[0]["reviewer_a"] = "no"
            entries[0]["human_reason"] = "Fixture work must not disappear."
            path.write_text(review.canonical(entries))
            before = path.read_bytes()
            with self.assertRaisesRegex(AssertionError, "Changed adjudication review binding"):
                review.assess(target)
            self.assertEqual(path.read_bytes(), before)
            mapping = target / "PRIVATE_admin_only/mapping.json"
            mapping.write_text(mapping.read_text() + " ")
            with self.assertRaisesRegex(AssertionError, "Private mapping changed"):
                review.assess(target)
            self.assertEqual(path.read_bytes(), before)

    def test_invalid_signed_decisions_and_changed_review_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            path, entries = self.make_disagreement(target)
            entries[0].update(adjudicated_human_label="invalid", human_reason="Fixture work.",
                              adjudicator_name_or_private_code="fixture", signed_utc="2026-11-04T00:00:00+00:00")
            path.write_text(review.canonical(entries))
            with self.assertRaisesRegex(AssertionError, "Invalid adjudicated label"):
                review.assess(target)
            entries[0]["adjudicated_human_label"] = "uncertain"
            entries[0]["signed_utc"] = "not-a-time"
            path.write_text(review.canonical(entries))
            with self.assertRaisesRegex(AssertionError, "timestamp"):
                review.assess(target)
            entries[0]["signed_utc"] = "2026-11-04T00:00:00+00:00"
            path.write_text(review.canonical(entries))
            before = path.read_bytes()
            reviewer_path = target / "phase_1_extraction/reviewer_a.csv"
            with reviewer_path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            next(r for r in rows if r["uid"] == entries[0]["uid"])["human_claim_faithful"] = "no"
            review.write_csv(reviewer_path, rows)
            with self.assertRaisesRegex(AssertionError, "no longer matches"):
                review.assess(target)
            self.assertEqual(path.read_bytes(), before)

    def test_duplicate_adjudication_entry_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            path, entries = self.make_disagreement(target)
            path.write_text(review.canonical(entries + entries))
            before = path.read_bytes()
            with self.assertRaisesRegex(AssertionError, "Duplicate adjudication"):
                review.assess(target)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
