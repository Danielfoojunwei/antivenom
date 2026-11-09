"""End-to-end check with the real NLI model on released PoisonedRAG data.

Rebuilds the top-10 context for NQ question test363 exactly as in the paper
(research package and cached data required), runs the tool, and checks it
reproduces the paper's entailment-only decisions: 4 of 5 planted passages
flagged by the claim check, all clean passages kept. Then runs the CLI.
Run from antivenom/tool with the project venv:
    HF_HUB_OFFLINE=1 ../.venv/bin/python tests/integration_real.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
os.chdir(os.path.join(HERE, "..", ".."))            # research repo root (data paths)

from antivenom.poisonedrag import load  # noqa: E402
from antivenom.retriever import Contriever  # noqa: E402
from antivenom_tool import Defender, Signature  # noqa: E402

targets, corpus = load("nq")
t = {x.id: x for x in targets}["test363"]
rel = json.load(open("data/external/poisonedrag/nq-contriever.json"))
R = Contriever()
q = R.encode([t.question])[0]
pool = [(corpus[i]["title"] + " " + corpus[i]["text"], rel[t.id][i], "clean") for i in t.clean_ids]
pool += [(p, float(v @ q), "planted") for p, v in zip(t.poison, R.encode(t.poison))]
pool.sort(key=lambda x: -x[1])
top, rest = pool[:10], pool[10:]

sig = Signature.manual("What is the main industry in the Canadian Shield?", "its primary income sector is not mining but rather fishing")
rep = Defender([sig]).check([p for p, _, _ in top], t.question, refill=lambda n: [p for p, _, _ in rest[:n]])
labels = [l for _, _, l in top]
flagged = [v.flagged for v in rep.verdicts]
planted_flagged = sum(f for f, l in zip(flagged, labels) if l == "planted")
clean_flagged = sum(f for f, l in zip(flagged, labels) if l == "clean")
print("gate fired:", rep.gate_fired)
print("entailment:", [round(v.entailment, 3) for v in rep.verdicts])
print("labels:    ", labels)
print(f"planted flagged {planted_flagged}/5, clean flagged {clean_flagged}/5, refilled {rep.refilled}")
assert rep.gate_fired and planted_flagged == 4 and clean_flagged == 0, "does not reproduce the paper's decisions"

with tempfile.TemporaryDirectory() as d:
    sp, pp = os.path.join(d, "sig.json"), os.path.join(d, "passages.json")
    open(sp, "w").write(sig.to_json()); json.dump([p for p, _, _ in top], open(pp, "w"))
    env = dict(os.environ, PYTHONPATH=os.path.join(HERE, ".."))
    out = subprocess.run([sys.executable, "-m", "antivenom_tool.cli", "check", "--signatures", sp, "--passages", pp],
                         capture_output=True, text=True, env=env, timeout=300)
    cli = json.loads(out.stdout)
    assert len(cli["removed"]) == 4 and len(cli["kept"]) == 6, out.stdout[:500] + out.stderr[-500:]
    print("CLI: removed", len(cli["removed"]), "kept", len(cli["kept"]))
print("INTEGRATION OK")
