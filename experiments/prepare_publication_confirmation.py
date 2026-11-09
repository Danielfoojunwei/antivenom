"""Prepare only publication-study software/design readiness; never infer.

Missing independent data is an explicit blocked state. This command creates
no executable run manifest, launches no process and loads no model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from antivenom.publication_study import assess_readiness

ROOT = Path(__file__).resolve().parents[1]
PREPARED_FILES = (
    'src/antivenom/publication_study.py',
    'experiments/prepare_publication_confirmation.py',
    'tests/test_publication_study.py',
    'src/antivenom/memmorph_matched_sources.py',
    'src/antivenom/tool_policy_signature.py',
    'src/antivenom/memmorph_eval.py',
    'analysis/publication_power.py',
    'tests/test_publication_power.py',
    'docs/PUBLICATION_CONFIRMATION_PROTOCOL_V1.md',
    'results/publication_power_v1.json',
    'uv.lock',
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path,
                        default=ROOT / 'data/external/publication_confirmation/cohort.json')
    parser.add_argument('--review', type=Path,
                        default=ROOT / 'data/external/publication_confirmation/provenance_review.json')
    parser.add_argument('--artifact-root', type=Path,
                        default=ROOT / 'data/external/publication_confirmation')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'results/publication_confirmation_readiness_v1.json')
    args = parser.parse_args()
    report = assess_readiness(ROOT, args.cohort, args.review, args.artifact_root)
    report['prepared_software_only'] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in PREPARED_FILES
    }
    report['prepared_software_is_not_empirical_confirmation'] = True
    previous = ROOT / 'results/provenance/publication_readiness_v1_pre_review.json'
    if previous.is_file():
        report['preexecution_review_corrections'] = [{
            'preserved_previous_readiness': str(previous.relative_to(ROOT)),
            'previous_readiness_sha256': hashlib.sha256(previous.read_bytes()).hexdigest(),
            'correction': 'Apply historical, cross-campaign capture and shared-source exclusions to raw_sha256 as well as stored text/hash. A rewritten record cannot erase its captured-source lineage.',
            'regression_tests': [
                'test_rewritten_memory_raw_source_cannot_reuse_historical_capture',
                'test_rewritten_memory_raw_source_cannot_leak_other_campaign_capture'],
            'timing': 'preexecution software review; no executable freeze or fresh model outcomes existed',
            'original_scientific_inputs_changed': False,
            'confirmation_protocol_and_power_v1_changed': False,
        }]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': report['status'], 'model_calls': 0,
                      'missing': report['missing'], 'errors': report['errors'],
                      'executable_freeze_written': False,
                      'output': str(args.output)}, indent=2))


if __name__ == '__main__':
    main()
