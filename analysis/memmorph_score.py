"""Score complete saved native tool choices; does not run tools or a harness."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from antivenom.memmorph_eval import summarize_results, validate_fixture_bundle, verify_input_files

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.prepare_memmorph import freeze_software, inspect_artifacts, sha_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path,
                        help="JSONL exported by the separately reviewed native tool-choice parser")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Refusing to overwrite a previous score report")
    if args.bundle.name != "native_bundle.json":
        raise ValueError("Use the exact native_bundle.json bound by the source-review record")
    manifest = ROOT / "results/memmorph_alignment_software_manifest.json"
    if not manifest.exists():
        raise ValueError("Preparation software must be reviewed and pinned before scoring")
    freeze_software(manifest)
    readiness = inspect_artifacts(args.bundle.parent)
    if readiness["status"] != "saved_contract_verified_native_integration_pending":
        raise ValueError("Native source review is incomplete: " + json.dumps(readiness))
    bundle = validate_fixture_bundle(json.loads(args.bundle.read_text()))
    verified = verify_input_files(bundle, args.bundle.parent)
    observations = [json.loads(line) for line in args.observations.read_text().splitlines() if line.strip()]
    summary = summarize_results(bundle, observations, require_complete=True)
    summary.update(verified_input_files=verified,
                   classification=readiness["classification"],
                   observations_sha256=sha_file(args.observations),
                   software_manifest_sha256=sha_file(manifest),
                   result_type="descriptive rescoring of reviewed exports; not a native harness reproduction",
                   human_semantics="not established by this software check")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Scored {summary['planned_tasks']} planned tool choices in {summary['campaign_groups']} declared campaign groups")


if __name__ == "__main__":
    main()
