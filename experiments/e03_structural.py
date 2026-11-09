"""E03: structural defences (n_eff, complement diffusion, danger index) on
published PoisonedRAG poison. Pre-registered settings (from the similarity
distribution only, before any outcome): tau=0.75, rho0=0.54, beta=0.85,
gamma=4, pool=20, k=5. Each target is run on the attacked and the clean
top-k so protection and cost are measured on the same items."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from antivenom.immune import complement, danger, excess, neff_answer, sim_matrix
from antivenom.llm import LocalLLM
from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses, wrap_prompt
from antivenom.retriever import Contriever

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=100)
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--tau", type=float, default=0.75)
ap.add_argument("--rho0", type=float, default=0.54)
ap.add_argument("--beta", type=float, default=0.85)
ap.add_argument("--gamma", type=float, default=4.0)
ap.add_argument("--pool", type=int, default=20)
args = ap.parse_args()

T, C = load("nq")
released = json.load(open("data/external/poisonedrag/nq-contriever.json"))
V = dict(np.load("data/cache/nq_clean_vecs.npz"))
R = Contriever()
llm = LocalLLM()
out = Path(f"results/e03_nq_k{args.k}.jsonl")
done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()


def run_ctx(t, items, sample_vec):
    """items: list of (text, score, origin, vec). Returns metrics for top-k."""
    top = sorted(items, key=lambda x: -x[1])[: args.k]
    texts = [x[0] for x in top]
    vecs = np.stack([x[3] for x in top])
    rho = sim_matrix(vecs)
    r = {"origins": [x[2] for x in top]}
    r["vanilla"] = llm.generate([{"role": "user", "content": wrap_prompt(t.question, texts)}],
                                temp=0.0, max_tokens=64).strip()
    na = neff_answer(llm, t.question, texts, excess(rho, args.rho0))
    r["neff"], r["count"], r["groups"] = na["by_neff"], na["by_count"], na["groups"]
    d = danger(llm, t.question, texts, rho, args.tau)
    r["D"], r["deltas"], r["clusters"] = d["D"], d["deltas"], d["clusters"]
    keep = [p for i, p in enumerate(texts) if i not in d["top_cluster"]]
    r["danger_removed"] = llm.generate([{"role": "user", "content": wrap_prompt(t.question, keep or texts)}],
                                       temp=0.0, max_tokens=64).strip()
    r["removed_origins"] = [top[i][2] for i in d["top_cluster"]]
    # complement diffusion seeded at the captured sample over the top-pool graph
    pool = sorted(items, key=lambda x: -x[1])[: args.pool]
    pv = np.vstack([sample_vec[None], np.stack([x[3] for x in pool])])
    f = complement(sim_matrix(pv), 0, args.beta)[1:]
    f = f / max(f.max(), 1e-9)
    s = np.array([x[1] for x in pool]) * np.exp(-args.gamma * f)
    order = np.argsort(-s)[: args.k]
    r["comp_origins"] = [pool[i][2] for i in order]
    r["complement"] = llm.generate([{"role": "user", "content": wrap_prompt(t.question, [pool[i][0] for i in order])}],
                                   temp=0.0, max_tokens=64).strip()
    for m in ("vanilla", "neff", "count", "danger_removed", "complement"):
        r[m + "_end"] = endorses(r[m], t.incorrect)
        r[m + "_cor"] = correct(r[m], t.correct)
    return r


with out.open("a") as fh:
    for t in T[: args.limit]:
        if t.id in done:
            continue
        t0 = time.time()
        q = R.encode([t.question])[0]
        pv = R.encode(t.poison)
        clean = [(C[i]["title"] + " " + C[i]["text"], released[t.id][i], "corpus", V[i]) for i in t.clean_ids]
        pois = [(p, float(v @ q), "poison", v) for p, v in zip(t.poison, pv)]
        row = {"id": t.id, "attack": run_ctx(t, clean + pois, pv[0]),
               "clean": run_ctx(t, clean, pv[0])}
        row["secs"] = round(time.time() - t0, 1)
        fh.write(json.dumps(row) + "\n"); fh.flush()
        a = row["attack"]
        print(t.id, row["secs"], "attack end:", {m: int(a[m + "_end"]) for m in
              ("vanilla", "neff", "count", "danger_removed", "complement")}, "D=%.2f/%.2f" % (a["D"], row["clean"]["D"]),
              flush=True)
