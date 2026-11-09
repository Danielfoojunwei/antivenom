"""Workload accounting and coarse planning ranges; no inference or tuning."""
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

from antivenom.continuation import read_rows, save


def main():
    completed = len(read_rows("results/e36_Mistral-7B-Instruct-v0.3-4bit_msmarco_k10.jsonl"))
    text = Path("results/remaining_mistral.log").read_text()
    durations = [float(m.group(1)) for m in re.finditer(r"msmarco target complete \d+/50 ([\d.]+)s", text)]
    remaining = 50-completed
    reader_low = remaining*statistics.mean(durations[-10:])*.8/3600
    reader_high = remaining*max(statistics.mean(durations)*2, statistics.quantiles(durations[-20:], n=10)[8])/3600
    e34 = [float(m.group(1)) for m in re.finditer(r"\d+/80 ([\d.]+)s", Path("results/e34_run.log").read_text())]
    phases = {
        "remaining_mistral": {"remaining_targets": remaining, "generation_calls_upper": remaining*17,
                              "planning_hours": [reader_low, reader_high]},
        "composite_and_gate": {"generation_calls_upper": 80*(5+7+3)+6, "planning_hours": [3., 8.]},
        "incident_calibrations": {"generation_calls_upper": 20+2*(6+2), "planning_hours": [.3, 1.]},
        "ablation_and_mistaken_capture": {"generation_calls_upper": 80*(2*11+2+2*2+2), "planning_hours": [4., 8.]},
        "prefixfree_ablation": {"generation_calls_upper": 80*(2*9+2*2+1), "planning_hours": [3., 6.]},
        "recurrence": {"generation_calls_upper": 160*(2*7+2*2), "planning_hours": [4., 9.]},
        "e5_retriever_transfer": {"generation_calls_upper": 80*(2*11+2*2), "planning_hours": [4., 10.]},
        "swarm": {"generation_calls_upper": 80*(2+2*3*2*6), "planning_hours": [8., 18.]},
        "memform": {"generation_calls_upper": 212*(1+2*7*2)+232, "planning_hours": [10., 24.]},
        "final_analysis_integrity": {"generation_calls_upper": 0, "planning_hours": [.2, 1.]}}
    result = {
        "estimated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "All currently queued tests; not human review or an unimplemented future fresh confirmation",
        "measured_mistral_complete_targets": completed,
        "measured_mistral_ms_seconds_mean": statistics.mean(durations),
        "measured_mistral_ms_seconds_recent10_mean": statistics.mean(durations[-10:]),
        "mistral_hours_at_recent10_rate": (50-completed)*statistics.mean(durations[-10:])/3600,
        "historical_qwen_two_answer_target_seconds_mean": statistics.mean(e34),
        "historical_qwen_two_answer_target_seconds_last40_mean": statistics.mean(e34[-40:]),
        "phases": phases,
        "generation_calls_upper": sum(p["generation_calls_upper"] for p in phases.values()),
        "planning_hours_sum": [sum(p["planning_hours"][i] for p in phases.values()) for i in (0,1)],
        "method": "Call counts from frozen loop cardinalities, including TrustRAG's three generative stages, signature extraction and MemForm memory compilation. Per-phase time bands are engineering planning ranges, not confidence intervals or measured future phase durations.",
        "limitations": ["Upper counts include calls skipped for empty filtered MemForm histories and do not credit every partially saved current-target arm",
                        "Native MemForm 256-token memory compilation has not yet been timed on this host",
                        "CPU detector/retriever time, attention extraction, prompt lengths, host load and paging add substantial variability",
                        "Update estimates after the first complete incident and external-memory cases; avoid a precise finish-time promise"],
        "performance_assessment": {"host": "Apple M5, 16 GiB RAM",
            "observed_allocated_swap_gib_approx": 7.3,
            "paging_caveat": "A five-second observation showed 56 swapins and zero swapouts. Allocated swap alone does not establish current sustained thrashing or its causal runtime contribution.",
            "already_enabled": ["Per-arm checkpoint resume", "Calibration-verified ordinary greedy decoder", "One Torch CPU thread", "Cached captured-sample embeddings", "One model experiment at a time"],
            "candidate_speedups_requiring_validation": ["More RAM and independent target shards on another compatible host", "Exact prompt/feature caching with separate uncached timing measurements", "Batch generation only after calibration fidelity and memory checks"],
            "not_changed": ["No frozen inference/analysis code or recipes changed", "No extra model worker launched", "No libraries, precision, token limits, models, sample sizes or statistical thresholds changed"]}}
    save("results/runtime_estimate.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
