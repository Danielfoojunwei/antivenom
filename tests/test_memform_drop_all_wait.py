"""CPU-only runtime contracts: no models, external signals or real waiting."""
import builtins
import copy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("drop_all_wait_runtime", ROOT / "experiments/run_memform_drop_all_wait.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

def identity(pid, command, ppid=1):
    return dict(pid=pid, ppid=ppid, state="SN", rss_kib=32, cpu_time="0:01.25", start="Sun Nov 1 16:22:31 2026", command=command)

def fixtures():
    target = identity(200, "/project/.venv-qwen/bin/python final_evaluate.py")
    spawn = identity(300, "/project/python -c from multiprocessing.spawn import spawn_main; spawn_main(8) --multiprocessing-fork")
    names = ["/project/lib/numpy/_core.so", "/project/native/cpu.log", "/usr/lib/libSystem.B.dylib"]
    config = dict(schema=runtime.SCHEMA, wait_targets=[target], poll_seconds=30, clear_confirmations=2,
        exemptions=[dict(identity=spawn, classification="dormant_cpu_spawn", lsof_names=names,
                        lsof_sha256=runtime.names_sha256(names), cpu_time=spawn["cpu_time"], rss_kib=32)])
    inventory = {100: identity(100, "/project/python run_memform_drop_all_wait.py --supervise", 99),
                 99: identity(99, "/bin/zsh"), 300: spawn}
    return config, inventory, names

class WaitingRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.config, self.inventory, self.names = fixtures()

    def assess(self, config=None, inventory=None, names=None):
        return runtime.assess_inventory(config or self.config, inventory or self.inventory, 100,
            lambda pid: self.names if names is None else names)

    def test_import_has_no_model_or_scientific_module_import(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"mlx", "mlx_lm", "torch", "transformers", "antivenom"}:
                self.fail("Unexpected import: " + name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

    def test_inventory_parsing_is_complete_and_command_exact(self):
        line = "100 99 S 32 0:01.25 Sun Nov  1 16:22:31 2026 /project/python -c a;  b\n"
        self.assertEqual(runtime.parse_inventory(line)[100]["start"], "Sun Nov 1 16:22:31 2026")
        self.assertEqual(runtime.parse_inventory(line)[100]["command"], "/project/python -c a;  b")
        for bad in ("", "100 99 incomplete", line + line):
            with self.subTest(bad=bad), self.assertRaises(runtime.ResourceBusy):
                runtime.parse_inventory(bad)

    def test_priority_identity_and_pid_reuse_both_block(self):
        inventory = copy.deepcopy(self.inventory)
        target = self.config["wait_targets"][0]
        inventory[200] = target
        self.assertEqual(self.assess(inventory=inventory)["blockers"][0]["reason"], "priority_target_alive")
        inventory[200] = {**target, "start": "changed", "command": "/usr/bin/true"}
        self.assertEqual(self.assess(inventory=inventory)["blockers"][0]["reason"], "priority_target_identity_changed")

    def test_unknown_python_or_model_and_new_spawn_are_not_exempted(self):
        self.assertTrue(self.assess()["clear"])
        for command in ("/other/python mystery.py", "/usr/local/bin/ollama serve", self.inventory[300]["command"]):
            self.assertFalse(self.assess(inventory={**self.inventory, 400: identity(400, command)})["clear"])

    def test_every_dormant_witness_change_blocks(self):
        for changed in (dict(cpu_time="0:01.26"), dict(rss_kib=33), dict(ppid=2), dict(start="changed"), dict(command="/other/python worker.py")):
            inventory = copy.deepcopy(self.inventory); inventory[300].update(changed)
            with self.subTest(changed=changed):
                self.assertFalse(self.assess(inventory=inventory)["clear"])
        self.assertFalse(self.assess(names=self.names + ["/usr/lib/Metal.framework/Metal"])["clear"])
        self.assertFalse(self.assess(names=self.names[:-1])["clear"])
        def denied(pid):
            raise PermissionError("No inspection")
        self.assertFalse(runtime.assess_inventory(self.config, self.inventory, 100, denied)["clear"])

    def test_corrupt_gpu_marked_or_unbounded_exemptions_are_rejected(self):
        for changed in (dict(lsof_sha256="0" * 64), dict(rss_kib=999999), dict(classification="all_python")):
            config = copy.deepcopy(self.config); config["exemptions"][0].update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                runtime.validate_config(config)
        config = copy.deepcopy(self.config); item = config["exemptions"][0]
        item["lsof_names"] = ["/lib/Metal.framework/Metal"]
        item["lsof_sha256"] = runtime.names_sha256(item["lsof_names"])
        with self.assertRaises(ValueError):
            runtime.validate_config(config)

    def test_lsof_is_complete_matching_pid_and_deduplicated(self):
        self.assertEqual(runtime.parse_lsof_names("p300\nn/a\nn/b\nn/a\n", 300), ["/a", "/b"])
        self.assertEqual(runtime.parse_lsof_names("p300\nn\nn/a\n", 300), ["", "/a"])
        for output in ("p301\nn/a\n", "p300\n", "n/a\n", "p300\np301\nn/a\n"):
            with self.subTest(output=output), self.assertRaises(runtime.ResourceBusy):
                runtime.parse_lsof_names(output, 300)

    def test_unnamed_descriptor_is_retained_in_frozen_witness(self):
        config = copy.deepcopy(self.config)
        item = config["exemptions"][0]
        item["lsof_names"] = ["", *self.names]
        item["lsof_sha256"] = runtime.names_sha256(item["lsof_names"])
        runtime.validate_config(config)
        self.assertTrue(self.assess(config=config, names=item["lsof_names"])["clear"])

    def test_stdlib_helpers_are_exact_identity_only(self):
        config, inventory = copy.deepcopy(self.config), copy.deepcopy(self.inventory)
        for pid, kind, command in [(500, "stdlib_http_server", "/usr/bin/python3 -m http.server 8766"),
                                  (501, "stdlib_resource_tracker", "/usr/bin/python3 -c from multiprocessing.resource_tracker import main;main(8)")]:
            item = identity(pid, command)
            config["exemptions"].append(dict(identity=item, classification=kind)); inventory[pid] = item
        self.assertTrue(self.assess(config=config, inventory=inventory)["clear"])
        inventory[500] = {**inventory[500], "start": "changed"}
        self.assertFalse(self.assess(config=config, inventory=inventory)["clear"])

    def test_eligibility_requires_two_clear_observations_and_resets(self):
        count = runtime.next_clear_count(0, dict(clear=True))
        self.assertLess(count, self.config["clear_confirmations"])
        self.assertEqual(runtime.next_clear_count(count, dict(clear=False)), 0)
        self.assertEqual(runtime.next_clear_count(count, dict(clear=True)), 2)

    def test_own_lock_prevents_duplicate_supervisors(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lock"
            with runtime.supervisor_lock(path):
                with self.assertRaises(RuntimeError):
                    with runtime.supervisor_lock(path):
                        self.fail("Duplicate acquired own lock")

    def test_reader_boundary_forwards_exact_args_results(self):
        calls, checks, sentinel = [], [], object()
        class Reader:
            def __init__(self, *args, **kwargs):
                calls.append(("init", args, kwargs))
                self.llm = SimpleNamespace(generate=lambda *a, **k: calls.append(("generate", a, k)) or sentinel)
        continuation = SimpleNamespace(Reader=Reader)
        self.assertIs(runtime.install_reader_guard(continuation, lambda: checks.append(True)), Reader)
        reader = continuation.Reader("frozen-model", 21)
        messages = [dict(role="user", content="Inert fixture")]
        self.assertIs(reader.llm.generate(messages, temp=0., top_p=0., max_tokens=128), sentinel)
        self.assertEqual(checks, [True, True, True])
        self.assertEqual(calls[1], ("generate", (messages,), dict(temp=0., top_p=0., max_tokens=128)))

    def test_busy_init_or_pre_call_never_generates(self):
        def busy():
            raise runtime.ResourceBusy("Other model")
        continuation = SimpleNamespace(Reader=lambda *a, **k: self.fail("Loaded while busy"))
        runtime.install_reader_guard(continuation, busy)
        with self.assertRaises(runtime.ResourceBusy):
            continuation.Reader("model", 21)
        checks = [True, True, False]
        def changing():
            if not checks.pop(0):
                raise runtime.ResourceBusy("Other model appeared")
        continuation = SimpleNamespace(Reader=lambda *a, **k: SimpleNamespace(llm=SimpleNamespace(generate=lambda *a, **k: self.fail("Generated while busy"))))
        runtime.install_reader_guard(continuation, changing)
        reader = continuation.Reader("model", 21)
        with self.assertRaises(runtime.ResourceBusy):
            reader.llm.generate([], temp=0.)

    def test_inspection_unavailable_fails_closed(self):
        with patch.object(runtime, "read_inventory", side_effect=runtime.ResourceBusy("Denied")):
            self.assertFalse(runtime.inspect_guard(self.config)["clear"])

if __name__ == "__main__":
    unittest.main()
