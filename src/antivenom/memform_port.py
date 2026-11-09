"""Reviewed MIT MemForm functions only; no upstream module initialization.

Source: opanhw/memform-code @ 0565117042a31a5f78576f89ff6b8a77c393ee09.
License: data/external/memform/LICENSE. Native prompt/parser functions are
retained verbatim through an explicit AST allowlist.
"""
import ast
import re
from pathlib import Path


def native_functions():
    source = Path("data/external/memform/reference/memform/eval/core.py").read_text()
    names = {"exp_texts", "format_experiences", "build_batch_memory", "task_prompt", "parse_final_label_details"}
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == names
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
    namespace = {"re": re}
    exec(compile(module, "pinned_memform_selected_functions", "exec"), namespace)
    return {k: namespace[k] for k in names}


def family_split(rows):
    import hashlib
    families = {}
    for r in rows:
        families.setdefault(r["family_id"], {})[r["interface"]] = r
    eligible = []
    for name, cases in families.items():
        if name.startswith("F0001_") or not {"P1", "P2"} <= set(cases): continue
        sample = cases["P1"]["memory_building"]["poisoned_condition"]["memory_text"]
        if any(sample == e["text"] for e in cases["P2"]["candidate_experiences"]): continue
        eligible.append(name)
    eligible.sort(key=lambda k: hashlib.sha256(("incident-memform-17:" + k).encode()).hexdigest())
    return families, eligible[:20], eligible[20:]
