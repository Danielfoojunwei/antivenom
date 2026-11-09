"""Small inert statistical/gating tests; no real partial outcomes are inspected."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("drop_all_summary", ROOT / "analysis/memform_drop_all_summary.py")
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


def fixtures(n=2):
    arms, rows, checkpoints = [], [], {}
    for i in range(n):
        for condition in summary.CONDITIONS:
            arm = {"arm_id": f"f{i}:{condition}:task", "family_id": f"f{i}", "condition": condition}
            row = {**arm, "call_id": f"{len(rows):032x}", "formatted_prompt_sha256": str(i) * 64,
                   "plan_sha256": "plan", "correct": True, "endorsed": False, "prediction": "A"}
            arms.append(arm); rows.append(row); checkpoints[arm["arm_id"]] = copy.deepcopy(row)
    status = {"status": "complete", "completed_calls": 2*n, "required_calls": 2*n, "plan_sha256": "plan"}
    integrity = {"passed": True, "reader_weights_unchanged": True, "plan_sha256": "plan",
                 "actual_answer_calls": 2*n, "independent_families": n, "output_sha256": "out"}
    return {"arms": arms}, rows, checkpoints, status, integrity


def decision(correct, endorsed):
    return {"correct": correct, "endorsed": endorsed, "prediction": "A"}


class DropAllSummaryTests(unittest.TestCase):
    def validate(self, values):
        return summary.validate_complete(*values, plan_sha="plan", parser=None,
            checkpoint_validator=lambda row, arm, plan, parser: None,
            output_sha="out", expected_families=2)

    def test_exact_paired_binary_p_values(self):
        self.assertEqual(summary.exact_mcnemar(0, 0), 1.)
        self.assertEqual(summary.exact_mcnemar(1, 0), 1.)
        self.assertEqual(summary.exact_mcnemar(5, 0), .0625)
        self.assertEqual(summary.exact_mcnemar(0, 5), .0625)
        self.assertEqual(summary.exact_mcnemar(3, 3), 1.)
        for a, b in ((True, 1), (-1, 2), (1.2, 0)):
            with self.assertRaises(summary.AnalysisError):
                summary.exact_mcnemar(a, b)

    def test_holm_monotonicity_and_full_family(self):
        adjusted = summary.holm_adjust({"a": .001, "b": .01, "c": .03, "d": 1.})
        self.assertEqual(adjusted, {"a": .004, "b": .03, "c": .06, "d": 1.})
        values = summary.holm_adjust({str(i): .01 for i in range(8)})
        self.assertTrue(all(p == .08 for p in values.values()))

    def test_bootstrap_is_paired_reproducible_and_descriptive(self):
        self.assertEqual(summary.paired_interval([0, 0, 0], repeats=50), [0., 0.])
        self.assertEqual(summary.paired_interval([1, -1, 0], repeats=100),
                         summary.paired_interval([1, -1, 0], repeats=100))
        bounds = summary.simultaneous_bound(0., 212)
        self.assertLess(bounds[0], 0); self.assertGreater(bounds[1], 0)

    def test_direction_is_metric_specific_and_zero_is_not_equivalence(self):
        self.assertEqual(summary.endpoint_verdict(.1, .01, "correct"), "supported")
        self.assertEqual(summary.endpoint_verdict(.1, .01, "endorsed"), "contradicted")
        self.assertEqual(summary.endpoint_verdict(-.1, .01, "endorsed"), "supported")
        self.assertEqual(summary.endpoint_verdict(0, 1, "correct"), "inconclusive")
        self.assertEqual(summary.endpoint_verdict(.2, .2, "correct"), "inconclusive")

    def test_complete_exact_pairing_passes(self):
        result = self.validate(fixtures())
        self.assertEqual(set(result), {"f0", "f1"})

    def test_incomplete_integrity_and_missing_outcomes_fail_before_summary(self):
        for item in ("incomplete", "missing", "integrity", "hash", "duplicate", "checkpoint"):
            values = list(copy.deepcopy(fixtures()))
            if item == "incomplete": values[3]["status"] = "running"
            elif item == "missing": values[1].pop()
            elif item == "integrity": values[4]["passed"] = False
            elif item == "hash": values[4]["output_sha256"] = "bad"
            elif item == "duplicate": values[1][1] = values[1][0]
            else: values[2].pop(next(iter(values[2])))
            with self.subTest(item=item), self.assertRaises(summary.AnalysisError):
                self.validate(values)

    def test_reused_call_wrong_checkpoint_and_prompt_are_rejected(self):
        for item in ("call", "checkpoint", "prompt"):
            values = list(copy.deepcopy(fixtures()))
            if item == "call": values[1][1]["call_id"] = values[1][0]["call_id"]
            elif item == "prompt": values[1][1]["formatted_prompt_sha256"] = "x"*64
            else: values[2][values[1][0]["arm_id"]]["correct"] = False
            if item != "checkpoint":
                values[2][values[1][1]["arm_id"]] = copy.deepcopy(values[1][1])
            with self.subTest(item=item), self.assertRaises(summary.AnalysisError):
                self.validate(values)

    def test_fixed_eight_comparisons_and_separate_joint_verdict(self):
        families = []
        for i in range(20):
            families.append({"family_id": str(i), **{condition: {
                "entail": decision(True, False), "OR": decision(True, False),
                "drop_all": decision(False, False)} for condition in summary.CONDITIONS}})
        result = summary.scope_report(families)
        self.assertEqual(len(result["comparisons"]), 8)
        for method in summary.METHODS:
            verdict = result["verdicts"][method]
            self.assertEqual(verdict["clean_correctness_advantage"], "supported")
            self.assertEqual(verdict["poisoned_endorsement_advantage"], "inconclusive")
            self.assertEqual(verdict["joint_strict_superiority"], "inconclusive")
            self.assertIn("untested", verdict["protection_noninferiority"])

    def test_duplicate_family_units_and_empty_scope(self):
        self.assertEqual(summary.scope_report([])["verdict"], "untested")
        with self.assertRaises(summary.AnalysisError):
            summary.scope_report([{"family_id": "x"}, {"family_id": "x"}])

    def test_freeze_prevents_late_registration_or_source_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in summary.INPUTS:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("test fixture")
            frozen = summary.freeze_analysis(root)
            self.assertEqual(summary.verify_analysis(root), frozen)
            self.assertEqual(summary.freeze_analysis(root), frozen)
            (root / summary.INPUTS[0]).write_text("changed")
            with self.assertRaises(summary.AnalysisError): summary.verify_analysis(root)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in summary.INPUTS:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("test fixture")
            (root / "results/memform_drop_all_control_v1.jsonl").write_text("existing answers")
            with self.assertRaises(summary.AnalysisError): summary.freeze_analysis(root)


if __name__ == "__main__":
    unittest.main()
