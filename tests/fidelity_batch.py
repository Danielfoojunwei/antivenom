"""Does mlx_lm.batch_generate reproduce unbatched greedy generation exactly?

Uses real prompts: RobustRAG's per-passage QA prompt for each of the top-10
attacked passages of the first N NQ targets. Compares byte-for-byte with
LocalLLM.generate (greedy) and reports timing. Writes results/fidelity/batch.txt.
"""
import json
import sys
import time
from pathlib import Path

from mlx_lm import batch_generate

from antivenom.baselines.robustrag import _PROMPTS
from antivenom.llm import LocalLLM
from antivenom.poisonedrag import load
from antivenom.retriever import Contriever

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2
targets, corpus = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
R = Contriever()
llm = LocalLLM()

prompts = []
for t in targets[:N]:
    pool = [(corpus[i]["title"] + " " + corpus[i]["text"], released[t.id][i]) for i in t.clean_ids]
    q = R.encode([t.question])[0]
    pool += [(p, float(v @ q)) for p, v in zip(t.poison, R.encode(t.poison))]
    for d, _ in sorted(pool, key=lambda x: -x[1])[:10]:
        prompts.append(_PROMPTS["QA_PROMPT_TMPL"].format(query_str=t.question, context_str=d))

msgs = [[{"role": "user", "content": p}] for p in prompts]
t0 = time.time()
ref = [llm.generate(m, temp=0.0, max_tokens=64).strip() for m in msgs]
t_seq = time.time() - t0

ids = [llm.tok.encode(llm.tok.apply_chat_template(m, add_generation_prompt=True, tokenize=False),
                      add_special_tokens=False) for m in msgs]
t0 = time.time()
batched = [x.strip() for x in batch_generate(llm.model, llm.tok, ids, max_tokens=64).texts]
t_bat = time.time() - t0

same = sum(a == b for a, b in zip(ref, batched))
lines = [f"prompts={len(prompts)} identical={same}/{len(prompts)} sequential={t_seq:.1f}s batched={t_bat:.1f}s "
         f"speedup={t_seq / max(t_bat, 1e-9):.2f}x"]
lines += [f"  DIFF: {a!r} | {b!r}" for a, b in zip(ref, batched) if a != b]
Path("results/fidelity").mkdir(parents=True, exist_ok=True)
Path("results/fidelity/batch.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
