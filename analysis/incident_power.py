"""Paired development-based planning. Does not run or certify a fresh test."""
import math

import numpy as np
from scipy.stats import norm

from antivenom.continuation import read_rows, save


def required_n(variance, slack, power, alpha=.0125):
    if slack <= 0: return None
    # A zero observed discordance must not imply zero required sample size.
    return max(2, math.ceil((norm.ppf(1-alpha) + norm.ppf(power)) ** 2 * max(variance, .0125) / slack ** 2))


def main():
    rows = read_rows("results/incident_base_contriever.jsonl")
    assert len(rows) == 80
    estimates = {}
    for comparator in ("coordguard_gate", "trustrag"):
        for endpoint, condition, metric in (("utility_superiority", "clean", "correct"), ("endorsement_NI", "attacked", "endorsed")):
            x = np.array([int(r["answers"][condition + ":gated_OR"][metric]) -
                          int(r["answers"][condition + ":" + comparator][metric]) for r in rows])
            d, v = float(x.mean()), float(x.var(ddof=1))
            slack = d if endpoint == "utility_superiority" else .05-d
            estimates[comparator + ":" + endpoint] = {"paired_difference": d, "paired_disagreement_rate": float(np.mean(x != 0)),
                "paired_variance": v, "slack_to_null": slack,
                "individual_80_percent_n": required_n(v, slack, .8), "individual_90_percent_n": required_n(v, slack, .9),
                "joint_80_percent_conservative_n": required_n(v, slack, .95),
                "joint_90_percent_conservative_n": required_n(v, slack, .975)}
    joint = {}
    for power in (80, 90):
        ns = [e[f"joint_{power}_percent_conservative_n"] for e in estimates.values()]
        joint[str(power)] = max(ns) if all(n is not None for n in ns) else None
    sensitivity = [{"paired_variance": v, "clean_accuracy_gain": gain, "endorsement_difference": d,
                    "joint_80_percent_conservative_n": max(required_n(v, gain, .95), required_n(v, .05-d, .95))}
                   for v in (.05, .1, .2, .4) for gain in (.03, .05, .10) for d in (0., .02, .04)]
    save("results/incident_power.json", {"margin_absolute": .05, "development_targets": 80,
        "alpha_per_component": .0125, "method": "Normal approximation for paired differences; conservative Bonferroni planning across four conditions. Joint power bound uses union bound on component failure probabilities.",
        "estimates": estimates, "maximum_required_independent_targets": joint, "sensitivity": sensitivity,
        "limitations": ["Planning approximation, not an empirical confirmation or guarantee of power",
                       "Estimates from 80 used targets have substantial uncertainty; inspect sensitivity",
                       "Repeated tasks per incident/family do not add independent samples",
                       "A null sample size means the estimated effect does not support the chosen alternative",
                       "Freeze one fresh-set method, endpoints, eligibility, family unit, margins and sample size before fresh model outcomes"]})
    print("Power planning saved; required independent units:", joint)


if __name__ == "__main__": main()
