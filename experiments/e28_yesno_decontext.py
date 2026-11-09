"""E28: decontextualised claim signature for yes/no-form questions (defender-
observable rule: the extracted question starts with an auxiliary verb).
The reader restates the claim already extracted from the captured poison as
one self-contained declarative sentence naming every entity; no new claim is
introduced. Hypothesis = that sentence. Tier-1 HotpotQA/MS-MARCO yes/no-form
targets (post hoc design data); passages from step2_passages.jsonl."""
import json
import re
from collections import defaultdict

from sentence_transformers import CrossEncoder

from antivenom.llm import LocalLLM

YN = re.compile(r"^(are|is|was|were|do|does|did|can|could|has|have|had|will|would|should)\b", re.I)
PROMPT = """Question: {q}
A record claims: "{c}"
Rewrite the record's claim as one self-contained declarative sentence that names every person, place or thing explicitly (no pronouns) and states the claim as a direct answer to the question. Keep the record's position exactly; do not add or correct anything. Return only the sentence."""
llm = LocalLLM()
nli = CrossEncoder("cross-encoder/nli-deberta-v3-base", device="cpu")
P = defaultdict(list)
for l in open("results/rescored/summaries/step2_passages.jsonl"):
    x = json.loads(l); P[x["id"]].append(x)
out = open("results/e28_yesno_decontext.jsonl", "w")
for d in ("hotpotqa", "msmarco"):
    for l in open(f"results/rescored/e15_cross_dataset_{d}_k10.jsonl"):
        r = json.loads(l)
        if not YN.match(r["question_extracted"].strip()):
            continue
        s = llm.generate([{"role": "user", "content": PROMPT.format(q=r["question_extracted"], c=r["claim"])}],
                         temp=0.0, top_p=0.0, max_tokens=80).strip().strip('"')
        ps = sorted(P[r["id"]], key=lambda x: x["slot"])
        ent = nli.predict([(x["text"], s) for x in ps], apply_softmax=True)[:, 1]
        out.write(json.dumps({"dataset": d, "id": r["id"], "statement": s, "entail_decontext": [round(float(e), 5) for e in ent]}) + "\n")
        print(d, r["id"], "|", s, flush=True)
