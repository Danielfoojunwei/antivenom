"""Prospective focused E42/E45 analysis; incidents are the independent units."""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta

from antivenom.continuation import freeze, read_rows, save
from continuation_stats import holm, interval

METHODS = ("isolated_attention", "shared_record_ids", "shared_sample_cosine",
           "shared_claim_entail", "shared_claim_OR", "coordguard_gate", "untreated")
LAYOUTS = ("distinct_ids", "shared_ids")


def verify_manifest(path):
    manifest = json.loads(Path(path).read_text())
    for filename, digest in manifest["inputs"].items():
        assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, (path, filename)


def bounded_comparison(values, family_size=5):
    x = np.asarray(values, dtype=float)
    assert len(x) >= 2 and np.isfinite(x).all() and (np.abs(x) <= 1).all()
    alpha = .05 / (2 * family_size)  # Simultaneous bounds across comparisons and tails.
    radius = (np.sqrt(2 * x.var(ddof=1) * np.log(2 / alpha) / len(x))
              + 14 * np.log(2 / alpha) / (3 * (len(x) - 1)))
    rng = np.random.default_rng(0)
    null = (rng.choice([-1, 1], (20000, len(x))) * x).mean(axis=1)
    return {"difference": float(x.mean()), "paired_ci95": interval(x),
            "simultaneous_lower": max(-1., float(x.mean() - radius)),
            "simultaneous_upper": min(1., float(x.mean() + radius)),
            "one_sided_p": float((1 + (null >= x.mean() - 1e-12).sum()) / 20001),
            "independent_incidents": len(x)}


def harm_estimate(events):
    n, k = len(events), int(sum(events))
    return {"incidents_with_any_receiver_loss": k, "independent_incidents": n,
            "rate": k / n, "exact_one_sided_upper95":
            1. if k == n else float(beta.ppf(.95, k + 1, n - k))}


def assemble(swarm, references):
    ids = [r["id"] for r in swarm]
    assert len(set(ids)) == len(ids)
    refs = {r["id"]: r for r in references}
    assert len(refs) == len(references) and set(refs) == set(ids)
    assembled = []
    for row in swarm:
        ref = refs[row["id"]]
        assert set(row["receivers"]) == set(ref["receivers"])
        layouts = {}
        for layout in LAYOUTS:
            agents = []
            for agent in (1, 2, 3):
                rid = f"{layout}:agent{agent}"
                receiver, reference = row["receivers"][rid], ref["receivers"][rid]
                assert receiver["captured"] is False
                hashes = [r["sha256"] for r in receiver["clean_context_metadata"][:10]]
                assert reference["final_context_hashes"] == hashes
                assert reference["flags"] == []
                answers = {m: {c: receiver["answers"][c + ":" + m] for c in ("clean", "attacked")}
                           for m in METHODS if m != "untreated"}
                answers["untreated"] = {"clean": reference}
                agents.append(answers)
            layouts[layout] = agents
        art = row["publisher"]["artifact"]
        assembled.append({"id": row["id"], "nonblank_capture":
            bool(art["question"].strip() and art["claim"].strip()), "layouts": layouts})
    return assembled


def summarize(cases, layout, focal="shared_claim_OR"):
    if len(cases) < 2:
        return {"independent_incidents": len(cases), "status": "insufficient incidents"}

    def outcome(case, method, condition, metric):
        return np.array([float(a[method][condition][metric]) for a in case["layouts"][layout]])

    rates = {}
    for method in METHODS:
        rates[method] = {}
        for condition in (("clean",) if method == "untreated" else ("clean", "attacked")):
            rates[method][condition] = {}
            for metric in ("correct", "endorsed"):
                x = [outcome(c, method, condition, metric).mean() for c in cases]
                rates[method][condition][metric] = {"mean": float(np.mean(x)), "ci95": interval(x)}
    comparisons = {}
    for baseline in ("shared_record_ids", "shared_sample_cosine"):
        x = [float((outcome(c, baseline, "attacked", "endorsed")
                    - outcome(c, focal, "attacked", "endorsed")).mean()) for c in cases]
        comparisons["attack_benefit_vs:" + baseline] = bounded_comparison(x)
    harms = {}
    for baseline in ("shared_record_ids", "shared_sample_cosine", "untreated"):
        differences = [outcome(c, focal, "clean", "correct")
                       - outcome(c, baseline, "clean", "correct") for c in cases]
        comparisons["clean_benefit_vs:" + baseline] = bounded_comparison([float(x.mean()) for x in differences])
        harms[baseline] = harm_estimate([bool((x < 0).any()) for x in differences])
    adjusted = holm({k: v["one_sided_p"] for k, v in comparisons.items()})
    for key, value in comparisons.items():
        value["holm_p"] = adjusted[key]
    supported = all(v["simultaneous_lower"] > 0 if k.startswith("attack")
                    else v["simultaneous_lower"] >= 0 for k, v in comparisons.items())
    contradicted = any(v["simultaneous_upper"] < 0 for v in comparisons.values())
    return {"independent_incidents": len(cases), "receiver_observations_per_incident": 3,
            "rates": rates, "comparisons": comparisons, "clean_receiver_loss": harms,
            "joint_claim": "supported" if supported else "contradicted" if contradicted else "inconclusive",
            "focal_method": focal}


def main():
    verify_manifest("results/swarm_track4_manifest.json")
    swarm = read_rows("results/incident_swarm.jsonl")
    refs = read_rows("results/swarm_clean_reference.jsonl")
    expected = [r["id"] for r in read_rows("results/e11a_flag_scores_nq_k10.jsonl")][20:]
    assert len(swarm) == len(refs) == 80 and {r["id"] for r in swarm} == set(expected)
    assert json.load(open("results/swarm_clean_reference_integrity.json"))["passed"]
    freeze("results/swarm_track4_evaluation_manifest.json", [
        "results/swarm_track4_manifest.json", "results/incident_swarm.jsonl",
        "results/swarm_clean_reference.jsonl", "results/swarm_clean_reference_integrity.json"])
    cases = assemble(swarm, refs)
    nonblank = [c for c in cases if c["nonblank_capture"]]
    result = {"scope": "Used-question exploratory E42/E45, not fresh primary confirmation",
              "capture_counts": {"all": len(cases), "nonblank": len(nonblank), "blank": len(cases) - len(nonblank)},
              "primary": summarize(cases, "distinct_ids"),
              "secondary_shared_ids": summarize(cases, "shared_ids"),
              "secondary_entailment_distinct_ids": summarize(cases, "distinct_ids", "shared_claim_entail"),
              "secondary_nonblank_distinct_ids": summarize(nonblank, "distinct_ids"),
              "statistics": {"unit": "incident; three receivers averaged before pairing",
                  "bootstrap_draws": 2000, "randomization_draws": 20000, "seed": 0,
                  "holm_family": "five focal directional comparisons within each labelled scope",
                  "decision_bounds": "simultaneous empirical Bernstein alpha=.05/(2*5) per tail; zero clean-loss margin",
                  "future_fresh_endorsement_NI_margin": .05},
              "limitations": ["automated QA scoring; human review deferred",
                  "nonblank does not establish semantic extraction validity", "near-clone released poisons",
                  "serial homogeneous agents; no contagion or authenticated publication experiment",
                  "strict no-harm conjunction can remain underpowered; nonsignificance is not equivalence"]}
    save("results/swarm_track4_summary.json", result)
    lines = ["ANTIVENOM Track 4: used-question exploratory shared protection",
             "Primary joint claim: " + result["primary"]["joint_claim"],
             f"Captures: {len(nonblank)}/{len(cases)} nonblank; human semantics unvalidated."]
    for k, v in result["primary"]["comparisons"].items():
        lines.append(f"{k}: difference={v['difference']:.4f}; paired95={v['paired_ci95']}; "
                     f"simultaneous bounds=[{v['simultaneous_lower']:.4f},{v['simultaneous_upper']:.4f}]; Holm p={v['holm_p']:.6g}")
    Path("results/rescored/summaries/swarm_track4_summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
