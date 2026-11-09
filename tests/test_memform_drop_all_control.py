"""Planning and binding tests. Never initialize a model or execute inference."""
import builtins
import copy
import fcntl
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("drop_all_control", ROOT / "experiments/memform_drop_all_control.py")
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class DropAllControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original_import = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"mlx", "mlx_lm", "torch", "transformers", "sentence_transformers"}:
                raise AssertionError("Planning attempted a model/backend import: " + name)
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded):
            cls.plan = control.build_plan()
        cls.native = control.native_functions()

    def test_plan_has_distinct_actual_arms_for_identical_condition_prompts(self):
        arms = self.plan["arms"]
        self.assertEqual(len(arms), 424)
        self.assertEqual(len({a["arm_id"] for a in arms}), 424)
        self.assertEqual(len({a["family_id"] for a in arms}), 212)
        self.assertEqual(len({a["messages_sha256"] for a in arms}), 212)
        by_family = {}
        for arm in arms:
            by_family.setdefault(arm["family_id"], []).append(arm)
            self.assertEqual(arm["kept_hashes"], [])
            self.assertEqual(arm["flags"], list(range(len(arm["input_hashes"]))))
        for pair in by_family.values():
            self.assertEqual(len(pair), 2)
            self.assertEqual({a["condition"] for a in pair}, {"clean", "poisoned"})
            self.assertEqual(pair[0]["messages_sha256"], pair[1]["messages_sha256"])

    def test_native_empty_history_is_different_from_none_prompt(self):
        families, _, ids = control.load_cases()
        case = families[ids[0]]["P2"]
        task = case["evaluation"]["trigger_tasks"][0]
        self.assertEqual(self.native["build_batch_memory"](None, case, [], "unused", 120), control.FALLBACK)
        self.assertNotEqual(self.native["task_prompt"](case, task, None), self.native["task_prompt"](case, task, control.FALLBACK))

    def checkpoint(self):
        arm = self.plan["arms"][0]
        raw = "FINAL_ANSWER: " + arm["score_labels"]["clean"]
        pred, method = self.native["parse_final_label_details"](raw, arm["valid_labels"])
        value = {k: arm[k] for k in ("arm_id", "family_id", "condition", "task_id", "messages_sha256", "input_hashes", "flags", "kept_hashes", "memory_sha256")}
        value.update(plan_sha256="plan", uncached_actual_call=True, call_id="a" * 32,
                     formatted_prompt_sha256="b" * 64, raw_response_sha256=control.sha(raw),
                     resp=raw, answer_seconds=1., generation_started_utc="2026-11-03T00:00:00+00:00",
                     prediction=pred, parse_method=method, correct=True,
                     endorsed=pred == arm["score_labels"]["poisoned"])
        return arm, value

    def test_checkpoint_binds_recipe_arm_input_and_actual_raw_score(self):
        arm, value = self.checkpoint()
        parser = self.native["parse_final_label_details"]
        control.validate_checkpoint(value, arm, "plan", parser)
        corruptions = {"condition": "other", "plan_sha256": "different", "messages_sha256": "wrong",
                       "raw_response_sha256": "wrong", "correct": False, "uncached_actual_call": False,
                       "call_id": "copied-answer", "answer_seconds": float("nan")}
        for key, wrong in corruptions.items():
            changed = copy.deepcopy(value); changed[key] = wrong
            with self.subTest(key=key), self.assertRaises(AssertionError):
                control.validate_checkpoint(changed, arm, "plan", parser)

    def test_frozen_plan_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            self.assertEqual(control.save_plan({"x": 1}, path), control.save_plan({"x": 1}, path))
            with self.assertRaises(AssertionError):
                control.save_plan({"x": 2}, path)
            self.assertEqual(json.loads(path.read_text()), {"x": 1})

    def test_known_qwen_worker_and_unknown_python_fail_closed(self):
        inventory = "100 99 S /project/.venv/bin/python control.py --execute\n99 1 S /bin/zsh\n39334 39325 R /project/.venv-qwen35/bin/python /work/qwen_epistemic_weight_repair_v2/final_evaluate.py --run final_001\n300 1 S /usr/bin/python mystery.py\n"
        self.assertEqual({r["pid"] for r in control.process_blockers(inventory, 100)}, {39334, 300})
        with self.assertRaises(RuntimeError):
            control.process_blockers("unreadable process inventory", 100)
        with self.assertRaises(RuntimeError):
            control.process_blockers("99 1 S /bin/zsh\n", 100)

    def test_process_inspection_failure_cannot_proceed(self):
        with patch.object(control.subprocess, "run", side_effect=PermissionError("inspection denied")):
            with self.assertRaises(RuntimeError):
                control.inspect_processes()

    def test_busy_shared_lock_prevents_every_execution_step(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "results").mkdir()
            with (root / "results/remaining_queue.lock").open("a+") as owner:
                fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with patch.object(control, "ROOT", root), patch.object(control, "inspect_processes", side_effect=AssertionError("must not inspect or load")):
                    with self.assertRaises(RuntimeError):
                        control.execute({}, "unneeded")


if __name__ == "__main__":
    unittest.main()
