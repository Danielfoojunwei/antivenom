"""Download a BEIR corpus from the Hugging Face mirror and keep only the
passages that appear in PoisonedRAG's released top-100 lists for its 100
targets. Usage: python experiments/prep_corpus.py hotpotqa"""
import json
import sys

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

d = sys.argv[1]
root = "data/external/poisonedrag"
path = hf_hub_download(f"BeIR/{d}", "corpus/corpus-00000-of-00001.parquet", repo_type="dataset",
                       local_dir=f"data/external/beir/{d}")
res = json.load(open(f"{root}/{d}-contriever.json"))
targets = json.load(open(f"{root}/{d}.json"))
need = set()
for t in targets.values():
    need |= set(res[t["id"]].keys())
tab = pq.read_table(path, columns=["_id", "title", "text"])
sub = tab.filter(pc.is_in(tab["_id"], value_set=pa.array(list(need))))
out = {r["_id"]: {"title": r["title"], "text": r["text"]} for r in sub.to_pylist()}
json.dump(out, open(f"{root}/{d}_target_corpus.json", "w"))
print(d, "corpus rows", tab.num_rows, "needed", len(need), "found", len(out))
