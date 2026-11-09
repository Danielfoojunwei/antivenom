"""Check experimental identity/coverage from independent stored benchmark IDs.

No models loaded. Default requires full coverage; --allow-partial audits only
completed rows without claiming full coverage.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from antivenom.poisonedrag import load
from antivenom.qa import correct, endorses


def rows(name):
    return [json.loads(l) for l in open(f"results/{name}.jsonl")]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


ap = argparse.ArgumentParser()
ap.add_argument("--allow-partial", action="store_true", help="check completed rows without claiming full coverage")
args = ap.parse_args()
ent = rows("e11a_flag_scores_nq_k10")
expected = [r["id"] for r in ent[20:]]
att = {r["id"]: r for r in rows("e11c_attention_scores_nq_k10")}
rot = {r["id"]: r for r in rows("e21_capture_rotation_nq_k10")}
new = rows("e34_fixed_slots_nq_k10")
base = {r["id"]: r for r in rows("e32_backfill_placebo_nq_k10")}
assert len(new) == len({r["id"] for r in new})
assert set(expected) == set(base) and {r["id"] for r in new} <= set(expected)
assert (args.allow_partial and 0 < len(new) <= 80) or len(new) == 80
for path, expected_hash in json.load(open("results/e34_manifest.json"))["hashes"].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected_hash, path
targets, corpus = load("nq")
by = {t.id: t for t in targets}
rel = json.load(open("data/external/poisonedrag/nq-contriever.json"))
by_ent = {r["id"]: r for r in ent}
true_poison_count = 0
for r in new:
    tid = r["id"]
    t = by[tid]
    clean_ids = sorted(t.clean_ids, key=lambda i: -rel[tid][i])
    clean_iter = iter(clean_ids)
    original = []
    for p in rot[tid]["poison_index"]:
        if p >= 0:
            original.append(t.poison[p])
        else:
            c = corpus[next(clean_iter)]
            original.append(c["title"] + " " + c["text"])
    assert [sha(s) for s in original] == r["original_passage_hashes"], tid
    a = np.array(att[tid]["attn"]["21"]["per_token"])
    z = (a - a.mean()) / (a.std() + 1e-9)
    expected_flags = [i for i, (e, v) in enumerate(zip(by_ent[tid]["entail_qa"], z)) if e >= .01 or v >= 0]
    assert expected_flags == r["flags"] and len(expected_flags) == base[tid]["n_flags"], tid
    donor = by[expected[(expected.index(tid) + 1) % 80]]
    assert r["placebo_from"] == donor.id == base[tid]["placebo_from"]
    donor_ids = sorted(donor.clean_ids, key=lambda i: -rel[donor.id][i])[10:10 + len(expected_flags)]
    donor_hashes = [sha(corpus[i]["title"] + " " + corpus[i]["text"]) for i in donor_ids]
    assert r["placebo_inplace"]["replacement_hashes"] == donor_hashes, tid
    for name in ("true_inplace", "placebo_inplace"):
        arm = r[name]
        assert arm["n_passages"] == 10
        assert len(arm["replacement_hashes"]) == len(arm["replacement_labels"]) == len(expected_flags)
        assert not set(arm["replacement_hashes"]) & set(r["original_passage_hashes"]), tid
        assert arm["correct"] == bool(correct(arm["resp"], t.correct)), tid
        assert arm["endorsed"] == bool(endorses(arm["resp"], t.incorrect)), tid
        assert arm["prompt_tokens"] > 0
    assert all(l == "clean" for l in r["placebo_inplace"]["replacement_labels"])
    true_poison_count += sum(l != "clean" for l in r["true_inplace"]["replacement_labels"])
assert any(r["repeatability_checked"] for r in new)
print(f"PASS: {len(new)}/80 unique targets, frozen inputs, original passage identities, flags, donor identities, replacement counts, and all {len(new) * 2} response scores. True-backfill poison replacements: {true_poison_count}.")
