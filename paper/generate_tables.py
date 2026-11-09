#!/usr/bin/env python3
"""Export completed ANTIVENOM evidence; never perform inference or change results.

Only formatting/aggregation already present in frozen completed summaries occurs
here. The manifest records JSON pointers and hashes so every exported value can
be traced to a source. Run from any directory with Python 3.12+.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
LABELS = {
    "none": "Untreated", "cosine": "Captured-sample cosine",
    "entail": "Claim entailment", "OR": "Claim + attention OR",
    "gated_OR": "Gated OR", "coordguard_gate": "CoordGuard geometry gate",
    "trustrag_filter": "TrustRAG document filter", "drop_all": "Exact empty history",
}
SOURCES: dict[str, dict] = {}


def read(name: str):
    path = ROOT / name
    body = path.read_bytes()
    SOURCES[name] = {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    return json.loads(body)


def write_table(stem: str, headers: list[str], rows: list[list]):
    directory = OUT / "tables"
    directory.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    (directory / f"{stem}.csv").write_text(stream.getvalue())
    md = "| " + " | ".join(headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n"
    md += "".join("| " + " | ".join(str(x) for x in row) + " |\n" for row in rows)
    (directory / f"{stem}.md").write_text(md)


def pct(x: float):
    return f"{100*x:.2f}"


def interval(xs):
    return f"[{100*xs[0]:+.2f}, {100*xs[1]:+.2f}]"


def pvalue(p):
    return f"{p:.6g}"


def figure(rates):
    """Standalone SVG, common 0--100% axis; no implied CI for rates."""
    methods = ["entail", "OR", "drop_all"]
    colors = {"entail": "#237e87", "OR": "#6b61ab", "drop_all": "#9aa2ad"}
    chunks = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="430" viewBox="0 0 1000 430">',
              '<rect width="1000" height="430" fill="white"/>',
              '<style>text{font-family:Arial,sans-serif;fill:#1d2938} .small{font-size:14px} .label{font-size:16px} .title{font-size:19px;font-weight:700}</style>']
    for facet, (condition, metric, title, direction) in enumerate([
        ("clean", "correct", "Clean-task accuracy", "Higher is better"),
        ("poisoned", "endorsed", "Poisoned-action endorsement", "Lower is better"),
    ]):
        left = 78 + facet * 490
        chunks.append(f'<text x="{left}" y="34" class="title">{title}</text>')
        chunks.append(f'<text x="{left}" y="56" class="small">{direction}</text>')
        for tick in range(0, 101, 20):
            y = 315 - tick * 2.4
            chunks.append(f'<line x1="{left}" y1="{y}" x2="{left+365}" y2="{y}" stroke="#e0e5eb"/>')
            chunks.append(f'<text x="{left-10}" y="{y+5}" text-anchor="end" class="small">{tick}%</text>')
        for j, method in enumerate(methods):
            v = rates[condition][method][metric]
            h = v * 240
            x = left + 24 + j * 117
            y = 315 - h
            chunks.append(f'<rect x="{x}" y="{y:.4f}" width="75" height="{h:.4f}" fill="{colors[method]}"/>')
            chunks.append(f'<text x="{x+37.5}" y="{y-10:.4f}" text-anchor="middle" class="label">{100*v:.2f}%</text>')
            label = {"entail":"Entailment", "OR":"OR", "drop_all":"Empty history"}[method]
            chunks.append(f'<text x="{x+37.5}" y="342" text-anchor="middle" class="small">{label}</text>')
    chunks += [
        '<text x="78" y="383" class="small">212 already-used local MemForm families per condition. All targets and parse failures retained.</text>',
        '<text x="78" y="406" class="small">Paired uncertainty and Holm8 tests: Table 2. Equal observed poisoned OR/control rates do not establish equivalence.</text>',
        '</svg>',
    ]
    (OUT / "figures").mkdir(exist_ok=True)
    (OUT / "figures" / "exact_control.svg").write_text("\n".join(chunks))


def main():
    control = read("results/memform_drop_all_summary_v1.json")
    audit = read("results/memform_drop_all_completion_audit_v1.json")
    memform = read("results/incident_memform_summary.json")
    swarm = read("results/swarm_track4_summary.json")
    read("results/incident_memform_integrity.json")
    read("results/incident_integrity.json")
    read("results/swarm_clean_reference_integrity.json")
    read("results/component_utility_audit_v1.json")
    read("results/human_validation_status.json")
    read("results/performance_choice_frozen.json")
    assert audit["all424_complete"] and audit["summary_recomputed_matches"]
    assert control["actual_answer_calls"] == 424
    assert control["all_target"]["families"] == 212
    assert memform["all_tasks"]["families"] == 212
    assert swarm["primary"]["independent_incidents"] == 80
    summary_path = ROOT / "results/memform_drop_all_summary_v1.json"
    assert hashlib.sha256(summary_path.read_bytes()).hexdigest() == audit["summary_file_sha256"]
    rates = control["all_target"]["rates"]
    rows = []
    for method in ["none", "cosine", "entail", "OR", "gated_OR", "coordguard_gate", "trustrag_filter", "drop_all"]:
        if method == "drop_all":
            clean, poisoned = rates["clean"][method], rates["poisoned"][method]
        else:
            def simple(condition):
                old = memform["all_tasks"]["rates"][f"{condition}:{method}"]
                return {"correct": old["correct"]["mean"], "endorsed": old["endorsed"]["mean"], "parse_failure_rate": old["parse_failure_rate"]}
            clean, poisoned = simple("clean"), simple("poisoned")
        rows.append([LABELS[method], 212, pct(clean["correct"]), pct(poisoned["correct"]), pct(poisoned["endorsed"]), pct(clean["parse_failure_rate"]), pct(poisoned["parse_failure_rate"])])
    write_table("table1_memform_rates", ["Method", "Families", "Clean correct (%)", "Poisoned correct (%)", "Poisoned endorsement (%)", "Clean parse failures (%)", "Poisoned parse failures (%)"], rows)
    rows = []
    for key, cmp in control["all_target"]["comparisons"].items():
        condition, pair, endpoint = key.split(":")
        method = pair.split("-")[0]
        rows.append([condition, LABELS[method], endpoint, pct(cmp["difference"]), interval(cmp["paired95_ci"]), interval(cmp["simultaneous95_bound"]), cmp["discordant_signature_one_drop_zero"], cmp["discordant_signature_zero_drop_one"], pvalue(cmp["holm8_p"]), cmp["directional_advantage"]])
    write_table("table2_exact_control_effects", ["Condition", "Signature method", "Endpoint", "Method minus empty (pp)", "Paired descriptive 95% CI (pp)", "Simultaneous Hoeffding 95% bounds (pp)", "Method=1 empty=0", "Method=0 empty=1", "Holm8 p", "Directional verdict"], rows)
    rows = []
    for key, cmp in swarm["primary"]["comparisons"].items():
        rows.append([key, pct(cmp["difference"]), interval(cmp["paired_ci95"]), interval([cmp["simultaneous_lower"], cmp["simultaneous_upper"]]), pvalue(cmp["holm_p"])])
    write_table("table3_swarm_primary", ["Comparison", "Favorable effect (pp)", "Paired descriptive 95% CI (pp)", "Simultaneous 95% bounds (pp)", "Holm5 p"], rows)
    rows = []
    for method, values in swarm["primary"]["rates"].items():
        rows.append([method, 80, 3, pct(values["clean"]["correct"]["mean"]), pct(values["attacked"]["endorsed"]["mean"]) if "attacked" in values else "Not run"])
    write_table("table4_swarm_rates", ["Method", "Incidents", "Receivers per incident", "Clean correct (%)", "Attacked endorsement (%)"], rows)
    figure(rates)
    mapping = {
        "schema": "antivenom.paper-evidence-export.v1",
        "classification": "formatting of completed existing evidence; no new inference or statistical family",
        "sources": SOURCES,
        "table_source_pointers": {
            "table1_memform_rates": ["results/incident_memform_summary.json#/all_tasks/rates", "results/memform_drop_all_summary_v1.json#/all_target/rates"],
            "table2_exact_control_effects": ["results/memform_drop_all_summary_v1.json#/all_target/comparisons"],
            "table3_swarm_primary": ["results/swarm_track4_summary.json#/primary/comparisons"],
            "table4_swarm_rates": ["results/swarm_track4_summary.json#/primary/rates"],
            "figures/exact_control.svg": ["results/memform_drop_all_summary_v1.json#/all_target/rates"],
        },
        "units": {"MemForm": "212 declared families", "swarm": "80 incidents; average 3 receivers within incident"},
        "limits": ["descriptive bootstrap intervals are not simultaneous", "no fresh confirmation or native MemMorph", "human review pending", "zero discordance is not equivalence"],
    }
    (OUT / "evidence_index.json").write_text(json.dumps(mapping, indent=2) + "\n")
    manuscript = OUT / "manuscript.md"
    if manuscript.exists():
        body = manuscript.read_text()
        for stem in ["table1_memform_rates", "table2_exact_control_effects", "table3_swarm_primary"]:
            start = f"<!-- BEGIN GENERATED {stem} -->"
            end = f"<!-- END GENERATED {stem} -->"
            replacement = start + "\n" + (OUT / "tables" / f"{stem}.md").read_text().rstrip() + "\n" + end
            body, count = re.subn(re.escape(start) + r".*?" + re.escape(end), lambda _: replacement, body, flags=re.S)
            assert count == 1, f"Expected one table region for {stem}"
        manuscript.write_text(body)
    print("Exported 4 tables (CSV/Markdown), 1 SVG figure and evidence hash index from complete saved results.")


if __name__ == "__main__":
    main()
