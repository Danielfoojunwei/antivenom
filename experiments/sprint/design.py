"""Sprint design: arms, one-factor tests, incidents and blocks. Pure Python, no models.

Every arm is a config record. Each test names ONE field; `check_one_factor`
asserts the test arm and its reference differ in exactly that field and
nowhere else, and the runner refuses to start otherwise.
"""
from __future__ import annotations

import hashlib
import json
import random

SPRINT_SEED = 20261108
K_BLOCKS = 5
DATASETS = ("hotpotqa", "msmarco")
SPRINT_RANGE = range(0, 100)          # released targets 1-100 per dataset (file order)

# Frozen detector settings (docs/V2_DETECTOR_FROZEN.md; results/v2_calibration.json; e27 offsets).
V2 = {"coef_entail": 0.9382, "coef_attn": 2.3472, "intercept": 4.9740, "threshold": 0.09886, "gate": 0.975,
      "slot_offsets": [0.596, -0.097, -0.214, -0.337, 0.235, 0.135, -0.432, -0.323, -0.187, 0.624],
      "layer": 21, "tail": 8, "nli_model": "cross-encoder/nli-deberta-v3-base",
      "cosine_threshold": 0.665714567899704,
      "entail_only_threshold": 0.002167,
      # B3 BinaryShield-style fingerprint (results/sprint_fingerprint_calibration.json)
      "fp_alpha": 2.0, "fp_tau": 254.95,
      # B2 Stealth Lens AV filter (authors' code defaults: delta, alpha = all tokens, max 1 removal)
      "av_delta": 26.20711906167185, "av_max_removed": 1}   # results/sprint_entail_only_calibration.json (5% clean removal, NQ 1-20)   # NQ 1-20 calibration (results/incident_calibration_contriever.json)

BASE = {"payload": "none", "signature_source": "real", "hypothesis_form": "question_claim",
        "attention_input": "off", "gate": "off", "refill": "on", "neutralise": "delete", "prompt_suffix": "none", "local_filter": "none"}


def arm(**kw):
    c = dict(BASE); c.update(kw)
    assert set(c) == set(BASE)
    return c


ARMS = {
    "A0_untreated":     arm(),
    "A1_ids":           arm(payload="ids"),
    "A2_sample":        arm(payload="sample"),
    "A3_signature":     arm(payload="signature"),
    "A4_sham":          arm(payload="signature", signature_source="sham"),
    "A5_sig_attention": arm(payload="signature", attention_input="on"),
    "A6_gated":         arm(payload="signature", attention_input="on", gate="on"),
    "A7_no_refill":     arm(payload="signature", attention_input="on", refill="off"),
    "A8_warn":          arm(payload="signature", attention_input="on", neutralise="warn"),
    "A9_forged":        arm(payload="signature", attention_input="on", signature_source="forged"),
    "A10_bare_claim":   arm(payload="signature", hypothesis_form="claim_only"),
    "B1_self_check":    arm(prompt_suffix="self_check"),          # benchmark only, not in any test
    "B2_stealth_av":    arm(local_filter="stealth_av", refill="off"),   # benchmark: Stealth Lens AV filter (no sharing)
    "B3_fingerprint":   arm(payload="fingerprint"),               # benchmark: BinaryShield-style shared fingerprint
}

# test id -> (arm, reference, the one factor, assumption, primary endpoint, family)
TESTS = {
    "T1":  ("A3_signature", "A1_ids", "payload", "Sharing the claim signature protects receivers more than sharing record IDs", "attacked_endorsed", "primary"),
    "T1b": ("A2_sample", "A1_ids", "payload", "Sharing the raw record protects receivers more than sharing record IDs", "attacked_endorsed", "secondary"),
    "T2":  ("A3_signature", "A4_sham", "signature_source", "Protection comes from the signature's content, not from sharing anything", "attacked_endorsed", "secondary"),
    "T3":  ("A5_sig_attention", "A3_signature", "attention_input", "The attention signal adds protection beyond the signature", "attacked_endorsed", "secondary"),
    "T4":  ("A6_gated", "A5_sig_attention", "gate", "The gate restores clean accuracy, at a stated protection cost", "clean_correct", "secondary"),
    "T5":  ("A5_sig_attention", "A7_no_refill", "refill", "Refilling with next-ranked evidence restores accuracy beyond deleting alone", "attacked_correct", "secondary"),
    "T6":  ("A5_sig_attention", "A8_warn", "neutralise", "Removing poison protects more than warning the reader about the claim", "attacked_endorsed", "secondary"),
    "T7":  ("A9_forged", "A5_sig_attention", "signature_source", "A forged signature (true answer as claim) deletes good evidence and costs accuracy", "clean_correct", "secondary"),
    "T8":  ("A3_signature", "A10_bare_claim", "hypothesis_form", "The signature needs the question, not just the claim", "attacked_endorsed", "secondary"),
}
MANIPULATION_CHECK = ("A0_untreated", "attack on vs off", "attacked_endorsed vs clean_endorsed")


def check_one_factor():
    diffs = {}
    for tid, (a, ref, factor, *_rest) in TESTS.items():
        d = sorted(k for k in BASE if ARMS[a][k] != ARMS[ref][k])
        if d != [factor]:
            raise AssertionError(f"{tid}: {a} vs {ref} differ in {d}, expected only [{factor}]")
        diffs[tid] = {"arm": a, "reference": ref, "factor": factor, a: ARMS[a][factor], ref: ARMS[ref][factor]}
    return diffs


def sha(x: str) -> str:
    return hashlib.sha256(x.encode()).hexdigest()


def draw_incidents(target_ids: dict[str, list[str]], excluded: set[str]):
    """Stratified random assignment of sprint incidents to K blocks, with per-block seeds."""
    rng = random.Random(SPRINT_SEED)
    rows = []
    for d in DATASETS:
        ids = [target_ids[d][i] for i in SPRINT_RANGE]
        assert not (set(ids) & excluded), "sprint incidents overlap excluded sets"
        rng.shuffle(ids)
        for n, tid in enumerate(ids):
            rows.append({"dataset": d, "id": tid, "block": n % K_BLOCKS})
    blocks = {b: {"catch_seed": SPRINT_SEED * 10 + b, "assign_seed": SPRINT_SEED * 100 + b,
                  "order_seed": SPRINT_SEED * 1000 + b, "sham_seed": SPRINT_SEED * 10000 + b} for b in range(K_BLOCKS)}
    for r in rows:
        bs = blocks[r["block"]]
        rr = random.Random(f"{bs['catch_seed']}:{r['dataset']}:{r['id']}")
        catch = rr.randrange(5)
        others = [j for j in range(5) if j != catch]
        random.Random(f"{bs['assign_seed']}:{r['dataset']}:{r['id']}").shuffle(others)
        r["caught_copy"], r["receiver_copies"] = catch, others[:3]
    for b in range(K_BLOCKS):                      # sham: claim from another incident in the same block (derangement)
        members = [r for r in rows if r["block"] == b]
        perm = list(range(len(members)))
        rs = random.Random(blocks[b]["sham_seed"])
        while True:
            rs.shuffle(perm)
            if all(i != p for i, p in enumerate(perm)):
                break
        for i, r in enumerate(members):
            r["sham_from"] = f"{members[perm[i]]['dataset']}:{members[perm[i]]['id']}"
    return rows, blocks


if __name__ == "__main__":
    print(json.dumps(check_one_factor(), indent=1))
