"""Regenerate data/baselines/robustrag_prompts.json from RobustRAG's released
src/prompt_template.py. The two prompt strings are extracted with ``ast``
(no repository code is executed). Not redistributed: see THIRD_PARTY_NOTICES.md."""
import ast
import json
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/inspire-group/RobustRAG/main/src/prompt_template.py"
WANT = {"QA_PROMPT_TMPL", "QA_PROMPT_HINTS_TMPL"}

src = urllib.request.urlopen(URL).read().decode()
out = {}
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in WANT:
        out[node.targets[0].id] = ast.literal_eval(node.value)
assert set(out) == WANT, out.keys()
path = Path("data/baselines/robustrag_prompts.json")
path.parent.mkdir(parents=True, exist_ok=True)
json.dump(out, open(path, "w"), indent=1)
print("wrote", path, {k: len(v) for k, v in out.items()})
