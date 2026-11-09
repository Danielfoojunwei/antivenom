"""Meaningful checks for blind review coverage, immutability and human gates."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication_review", ROOT / "analysis/prepare_publication_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class PublicationReviewTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
