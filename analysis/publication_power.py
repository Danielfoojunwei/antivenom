"""Outcome-free power planning for independent ANTIVENOM confirmation.

Never reads saved answers, loads a model or generates adversarial text. Exact
paired-superiority power is evaluated on an explicit sample-size grid. Optional
NI numbers are hypothetical normal approximations, not an approved design.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binom, norm

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_COMPONENTS = 4
ALPHA_FAMILY = .05
ALPHA_COMPONENT = ALPHA_FAMILY / PRIMARY_COMPONENTS
SAMPLE_GRID = (100, 150, 200, 250, 300, 400, 500, 750, 1000, 1500,
               2000, 3000, 5000, 7500, 10000, 15000, 20000)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_paired_superiority_power(n: int, gain: float, discordance: float,
                                    alpha: float = ALPHA_COMPONENT) -> float:
    """Exact favourable rejection probability for two-sided McNemar.

    D=+1 for focal-only success and -1 for comparator-only success. Given K
    discordances, focal wins follow Bin(K,(discordance+gain)/(2*discordance)).
    Favourable rejection requires a positive direction and exact p <= alpha.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if not 0 <= gain <= discordance <= 1:
        raise ValueError("require 0 <= gain <= discordance <= 1")
    if discordance == 0:
        return 0.0
    ks = np.arange(n + 1)
    first_win = binom.isf(alpha / 2, ks, .5).astype(np.int64) + 1
    p_win = (discordance + gain) / (2 * discordance)
    probability = binom.sf(first_win - 1, ks, p_win)
    return float(np.sum(binom.pmf(ks, n, discordance) * probability))


def first_adequate_grid_n(gain: float, discordance: float, target_power: float,
                          alpha: float = ALPHA_COMPONENT,
                          grid: tuple[int, ...] = SAMPLE_GRID) -> dict[str, Any]:
    if not 0 < target_power < 1:
        raise ValueError("target power must be in (0, 1)")
    if not grid or tuple(sorted(set(grid))) != grid or grid[0] < 1:
        raise ValueError("grid must be strictly increasing positive integers")
    checked = []
    for n in grid:
        power = exact_paired_superiority_power(n, gain, discordance, alpha)
        checked.append({"n": n, "power": power})
        if power >= target_power:
            return {"first_adequate_grid_n": n, "achieved_power": power,
                    "evaluated_grid": checked, "not_a_minimal_integer_n": True}
    return {"first_adequate_grid_n": None, "achieved_power": None,
            "evaluated_grid": checked, "not_a_minimal_integer_n": True}


def ni_normal_planning_n(discordance: float, endorsement_increase: float,
                         hypothetical_margin: float, target_power: float,
                         alpha: float = ALPHA_COMPONENT) -> int | None:
    """Optional hypothetical sensitivity; not the margin-free primary design."""
    if not 0 <= abs(endorsement_increase) <= discordance <= 1:
        raise ValueError("invalid paired probabilities")
    if not 0 <= hypothetical_margin <= 1:
        raise ValueError("invalid margin")
    if not 0 < target_power < 1 or not 0 < alpha < 1:
        raise ValueError("invalid power or alpha")
    slack = hypothetical_margin - endorsement_increase
    variance = discordance - endorsement_increase ** 2
    if slack <= 0 or variance <= 0:
        return None
    return max(2, math.ceil((norm.ppf(1-alpha) + norm.ppf(target_power)) ** 2
                            * variance / slack ** 2))


def audit_available_family_pool() -> dict[str, Any]:
    """Input-only inventory; deliberately never opens saved answers."""
    source = ROOT / "data/external/memform/accepted_mcq.jsonl"
    if not source.exists():
        return {"status": "source_missing", "fresh_usable_family_count": 0}
    from antivenom.memform_port import family_split
    rows = [json.loads(line) for line in source.read_text().splitlines() if line]
    families, calibration, diagnostic = family_split(rows)
    assigned = set(calibration) | set(diagnostic)
    unassigned = []
    for fid, interfaces in sorted(families.items()):
        if fid in assigned:
            continue
        reason = ("schema_inspection_family_not_fresh" if fid.startswith("F0001_")
                  else "missing_P1_capture_or_P2_case")
        unassigned.append({"family_id": fid, "interfaces": sorted(interfaces),
                           "reason": reason})
    return {"status": "no_untouched_eligible_P1_to_P2_families",
            "source": str(source.relative_to(ROOT)),
            "source_sha256": sha256_file(source),
            "input_rows": len(rows), "all_family_ids": len(families),
            "previously_assigned_calibration_families": len(calibration),
            "previously_assigned_diagnostic_families": len(diagnostic),
            "unassigned": unassigned, "fresh_usable_family_count": 0,
            "other_interfaces_are_not_independent_new_families": True,
            "saved_outcomes_opened": False}


def planning_report() -> dict[str, Any]:
    superiority = []
    for gain in (.03, .05, .10):
        for discordance in (.10, .20, .40):
            powers = {str(target): first_adequate_grid_n(gain, discordance, target)
                      for target in (.80, .90, .95, .975)}
            superiority.append({"assumed_gain": gain,
                                "assumed_discordance": discordance,
                                "powers": powers})
    ni = [{"assumed_discordance": q, "assumed_endorsement_increase": d,
           "hypothetical_margin_not_accepted": margin,
           "approximate_n_for_95_percent_component_power":
           ni_normal_planning_n(q, d, margin, .95)}
          for q in (.10, .20, .40) for d in (.00, .01, .02)
          for margin in (.01, .02, .03, .05)]
    return {"schema": "antivenom-publication-power-v1",
            "status": "design_frozen_execution_blocked",
            "uses_saved_model_outcomes": False, "model_calls": 0,
            "primary_components": PRIMARY_COMPONENTS,
            "family_alpha": ALPHA_FAMILY, "conservative_component_alpha": ALPHA_COMPONENT,
            "primary_margin": 0, "primary_tests": "strict superiority; no NI",
            "sample_grid": SAMPLE_GRID,
            "exact_superiority_method": "Sum over Binomial discordance counts of conditional exact two-sided McNemar favourable-tail rejection probability",
            "superiority_grid": superiority,
            "joint_power_note": "Four components each at power .95 give union-bound joint power >= .80; .975 gives >= .90. Joint power .80 for either two-component claim needs each at .90. Final N requires explicit accepted planning assumptions.",
            "ni_sensitivity_method": "Optional hypothetical normal paired-difference approximation Var(D)=discordance-E[D]^2; not part of primary design",
            "ni_sensitivity": ni, "selected_ni_margin": None,
            "selected_sample_size": None,
            "available_input_audit": audit_available_family_pool(),
            "execution_blockers": [
                "No untouched eligible MemForm family pool remains in the accepted release",
                "No author-native MemMorph bundle and reviewed native harness are available",
                "Independent campaign-family provenance and overlap review are missing",
                "Fresh calibration/test IDs and content hashes are not available",
                "Final calibration, reader/parser bindings and accepted planning assumptions/N are not frozen"],
            "bound_planning_files": {p: sha256_file(ROOT / p) for p in (
                "analysis/publication_power.py", "tests/test_publication_power.py",
                "docs/PUBLICATION_CONFIRMATION_PROTOCOL_V1.md")},
            "limitations": [
                "Hypothetical distributions are not estimates of efficacy",
                "Exact numerical power assumes independent incident-family units",
                "File hashes cannot establish semantic independence or author provenance",
                "No new adversarial text, target skipping, thresholds or answers are generated",
                "The old .05 future NI margin and original zero-loss swarm criterion remain scoped to their original studies"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/publication_power_v1.json")
    args = parser.parse_args()
    report = planning_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "selected_sample_size": None,
                      "primary_margin": 0, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
