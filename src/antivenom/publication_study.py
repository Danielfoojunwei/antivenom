"""Model-free publication-study contracts, calibration and matched filters.

No reader, model loader, network client or inference launcher is imported.
Callbacks receive only memory/capture text projections. Hash bindings and
review declarations never authenticate authorship or semantic independence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from numbers import Real
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from antivenom.memmorph_eval import (ContractError, canonical_sha256,
    validate_fixture_bundle, verify_input_files)
from antivenom.memmorph_matched_sources import (project_source_views,
    build_matched_extraction_prompt, filter_matched_sources)
from antivenom.tool_policy_signature import (MAX_MEMORY_CHARS, build_nli_hypothesis,
    filter_stored_memories, parse_extraction)

SCHEMA = 'antivenom.publication.confirmation.v1'
METHODS = ('tool_policy_entail', 'raw_nli_joined', 'raw_nli_max_over_views',
           'cosine', 'drop_all', 'none')
SCORED_METHODS = METHODS[:4]
CALIBRATION_FPR = .05
MODEL_ROLES = ('extraction', 'nli', 'embedding', 'reader', 'parser')


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _require(test: bool, message: str) -> None:
    if not test:
        raise ContractError(message)


def _text(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), label + ' must be nonblank text')
    return value


def _digest(value: Any, label: str) -> str:
    _require(isinstance(value, str) and len(value) == 64 and
             all(c in '0123456789abcdef' for c in value), label + ' needs lowercase SHA256')
    return value


def _number(value: Any, lo: float, hi: float, label: str) -> float:
    _require(isinstance(value, Real) and not isinstance(value, bool) and
             math.isfinite(value) and lo <= value <= hi, label + ' outside finite score bounds')
    return float(value)


def _memories(memories: Sequence[str]) -> tuple[str, ...]:
    _require(isinstance(memories, Sequence) and not isinstance(memories, (str, bytes)),
             'memories must be a sequence')
    result = tuple(memories)
    _require(all(isinstance(x, str) and x.strip() and len(x) <= MAX_MEMORY_CHARS for x in result),
             'memory texts must be nonblank and within common source limit')
    return result


@dataclass(frozen=True)
class Calibration:
    method: str
    threshold: float
    observed_fpr: float
    benign_records: int
    failed_extraction_records: int
    flagged_records: int
    score_vector_sha256: str
    budget: float = CALIBRATION_FPR
    tie_rule: str = 'inclusive_score_ge_threshold; nextafter_above_first_disallowed_score'

    def as_dict(self) -> dict:
        return asdict(self)


def calibrate_clean_scores(method: str, scores: Sequence[float | None]) -> Calibration:
    """Fit only benign-record detector scores, including invalid extraction.

    None is allowed only for focal unusable extraction and denotes a record
    passed through without a detector score. It remains in the denominator.
    A bounded threshold cannot silently move above one to evade tied scores.
    """
    _require(method in SCORED_METHODS, 'unknown scored method')
    _require(isinstance(scores, Sequence) and not isinstance(scores, (str, bytes)) and bool(scores),
             'nonempty benign record score vector required')
    lo = -1. if method == 'cosine' else 0.
    values = []
    failures = 0
    for score in scores:
        if score is None:
            _require(method == 'tool_policy_entail', 'missing score only allowed for unusable focal extraction')
            failures += 1
        else:
            values.append(_number(score, lo, 1., 'calibration score'))
    allowed = math.floor(CALIBRATION_FPR * len(scores))
    descending = sorted(values, reverse=True)
    if len(descending) <= allowed:
        threshold = lo
    else:
        threshold = math.nextafter(descending[allowed], math.inf)
    _require(threshold <= 1., 'calibration impossible in bounded inclusive threshold range')
    flagged = sum(value >= threshold for value in values)
    _require(flagged <= allowed, 'calibration tie handling exceeded fixed budget')
    return Calibration(method, threshold, flagged / len(scores), len(scores), failures,
                       flagged, canonical_sha256(list(scores)))


def run_filter(method: str, memories: Sequence[str], capture: Mapping[str, Any], *,
               threshold: float | None = None, extraction_output: str | None = None,
               nli_callback: Callable | None = None,
               cosine_callback: Callable | None = None) -> dict:
    """One callback batch, fixed aggregation, exact failure retention.

    Extraction is supplied as an exact decoder string; this function does not
    generate or retry it. An adapter must use extraction_prompt(capture).
    Callback exceptions/invalid scores become explicit operational failures
    with original memory retained. No synthetic callback is an efficacy test.
    """
    _require(method in METHODS, 'unknown method')
    texts = _memories(memories)
    sources = project_source_views(capture)
    projection = sources.projection_json
    base = {'schema': SCHEMA, 'method': method, 'status': 'complete',
            'source_projection_sha256': sources.projection_sha256,
            'source_projection_json': projection,
            'source_view_sha256': [view.sha256 for view in sources.views],
            'source_characters': sum(len(view.text) for view in sources.views),
            'input_hashes': [sha(text) for text in texts], 'threshold': threshold,
            'callback_calls': 0, 'scored_pairs': 0, 'pair_characters': 0,
            'actual_token_counts': None, 'token_counts_note': 'must be measured by pinned runtime adapter; characters are not tokens',
            'scores': [], 'extraction': None, 'failure': None}
    flags: tuple[int, ...] = ()
    if method == 'drop_all':
        flags = tuple(range(len(texts)))
    elif method != 'none':
        lo = -1. if method == 'cosine' else 0.
        _number(threshold, lo, 1., 'threshold')
        try:
            if method == 'tool_policy_entail':
                _require(isinstance(extraction_output, str), 'exact extraction decoder output required')
                result = parse_extraction(capture, extraction_output)
                base['extraction'] = result.as_dict()
                if result.valid:
                    _require(callable(nli_callback), 'NLI callback required')
                    hypothesis = build_nli_hypothesis(result.signature)
                    base['scored_pairs'] = len(texts)
                    base['pair_characters'] = sum(len(text) + len(hypothesis) for text in texts)
                    base['callback_calls'] = int(bool(texts))
                decision = filter_stored_memories(texts, result, nli_callback,
                                                 entailment_threshold=threshold)
                flags = decision.flags
                base['scores'] = list(decision.entailment_scores)
                base['status'] = decision.status
            elif method.startswith('raw_nli_'):
                _require(callable(nli_callback), 'NLI callback required')
                variant = 'joined' if method == 'raw_nli_joined' else 'max_over_views'
                hypotheses = [projection] if variant == 'joined' else [view.text for view in sources.views]
                base['callback_calls'] = int(bool(texts))
                base['scored_pairs'] = len(texts) * len(hypotheses)
                base['pair_characters'] = sum(len(text)+len(hypothesis) for text in texts for hypothesis in hypotheses)
                decision = filter_matched_sources(texts, capture, nli_callback,
                                                 entailment_threshold=threshold, variant=variant)
                flags = decision.flags
                base['scores'] = list(decision.entailment_scores)
            else:
                _require(callable(cosine_callback), 'cosine callback required')
                pairs = [(text, view.text) for text in texts for view in sources.views]
                base['callback_calls'] = int(bool(pairs))
                base['scored_pairs'] = len(pairs)
                base['pair_characters'] = sum(len(a)+len(b) for a, b in pairs)
                raw_scores = tuple(cosine_callback(pairs)) if pairs else ()
                _require(len(raw_scores) == len(pairs), 'cosine pair count mismatch')
                values = tuple(_number(v, -1., 1., 'cosine score') for v in raw_scores)
                width = len(sources.views)
                scores = tuple(max(values[i:i+width]) for i in range(0, len(values), width))
                base['scores'] = list(scores)
                flags = tuple(i for i, score in enumerate(scores) if score >= threshold)
        except Exception as exc:
            # No retry or omitted arm; enclosing runtime must checkpoint this
            # explicit failure alongside any subsequent reader decision.
            flags = ()
            base['status'] = 'operational_failure_passthrough'
            base['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
    keep = tuple(text for i, text in enumerate(texts) if i not in set(flags))
    base.update(flags=list(flags), kept_memories=list(keep), kept_hashes=[sha(x) for x in keep])
    return base


def extraction_prompt(capture: Mapping[str, Any]) -> str:
    return build_matched_extraction_prompt(capture)


def historical_input_index(root: Path) -> dict:
    """Conservative input-only exclusion index, not a semantic independence proof."""
    ids, hashes, files = set(), set(), {}
    path = root / 'data/external/memform/accepted_mcq.jsonl'
    _require(path.is_file(), 'historical MemForm input unavailable: cannot certify exact nonoverlap')
    files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for line in path.read_text().splitlines():
        row = json.loads(line)
        ids.add(row['family_id'])
        for condition in ('clean_condition', 'poisoned_condition'):
            text = row.get('memory_building', {}).get(condition, {}).get('memory_text')
            if isinstance(text, str):
                hashes.add(sha(text))
        for experience in row.get('candidate_experiences', []):
            hashes.add(sha(experience['text']))
    for name in ('nq', 'hotpotqa', 'msmarco'):
        path = root / f'data/external/poisonedrag/{name}.json'
        _require(path.is_file(), 'historical released QA input unavailable: ' + name)
        files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        for key, row in json.loads(path.read_text()).items():
            ids.update((key, name + ':' + key))
            hashes.update(sha(text) for text in row.get('adv_texts', []))
    return {'family_ids': ids, 'text_hashes': hashes, 'input_files': files}


def primary_pair(campaign: Mapping[str, Any]) -> str:
    pairs = {case['pair_id'] for case in campaign['cases']}
    cid = campaign['campaign_id']
    return min(pairs, key=lambda p: sha('publication-confirmation-v1:' + cid + ':' + p))


def validate_candidate(bundle: Mapping[str, Any], *, used_family_ids: set[str],
                       used_text_hashes: set[str]) -> dict:
    _require(isinstance(bundle, Mapping) and bundle.get('schema') == SCHEMA, 'unknown cohort schema')
    checked = copy.deepcopy(dict(bundle))
    provenance = checked.get('provenance', {})
    _require(provenance.get('kind') in {'independent_local', 'native_memmorph'},
             'synthetic fixtures and author flags do not constitute independent/native data')
    for field in ('source_url', 'revision', 'license'):
        _text(provenance.get(field), 'provenance.'+field)
    _require(provenance['source_url'].startswith('https://'), 'source URL must be HTTPS')
    # Reuse strict paired case/input/capture-leak validation without making an
    # author-native declaration. The temporary fixture schema is internal only.
    contract = {'schema': 'antivenom.memmorph.native.v1',
                'provenance': {'kind': 'synthetic_fixture', 'inputs': provenance.get('inputs', [])},
                'campaigns': checked.get('campaigns')}
    validate_fixture_bundle(contract, allow_synthetic=True)
    _require(bool(provenance.get('inputs')), 'provenance needs hash-bound source files')
    groups, capture_hashes, memory_hashes, task_hashes = set(), set(), {}, {}
    split_counts = {'calibration': 0, 'test': 0}
    for campaign in checked['campaigns']:
        cid = campaign['campaign_id']
        group = _text(campaign.get('independence_group'), 'independence_group')
        _require(cid not in used_family_ids and group not in used_family_ids, 'used family cannot become fresh by relabelling')
        _require(group not in groups, 'duplicate independence group / cross-split campaign')
        groups.add(group)
        split = campaign.get('split')
        _require(split in split_counts, 'each group needs calibration or test split')
        split_counts[split] += 1
        capture = project_source_views(campaign['capture'])
        current_hashes = {view.sha256 for view in capture.views}
        _require(not current_hashes & used_text_hashes, 'historical captured source reused')
        _require(not current_hashes & capture_hashes, 'capture reused across independent groups')
        capture_hashes.update(current_hashes)
        for case in campaign['cases']:
            # A common task/state reused across campaigns cannot count as new
            # independent incidents merely because family/task IDs differ.
            task_hash = canonical_sha256({'state': case['state'], 'tools': case['tools']})
            _require(task_hash not in task_hashes or task_hashes[task_hash] == cid,
                     'same primary task input reused across campaign groups')
            task_hashes[task_hash] = cid
            for memory in case['memories']:
                # Stored text is validated against stored_sha256 by the
                # strict paired-case contract above. Its raw source digest
                # must also participate in every exclusion: a rewrite with
                # new bytes does not make an old/shared source independent.
                source_hashes = {memory['raw_sha256'], memory['stored_sha256'],
                                 sha(memory['text'])}
                _require(not source_hashes & used_text_hashes,
                         'historical raw or stored memory source reused')
                for digest in source_hashes:
                    _require(digest not in memory_hashes or memory_hashes[digest] == cid,
                             'raw or stored memory source shared across independent groups; group it before split')
                    memory_hashes[digest] = cid
        if split == 'test':
            _require(campaign.get('primary_pair_id') == primary_pair(campaign),
                     'primary task pair does not match fixed input-only selection')
    _require(all(split_counts.values()), 'separate calibration and test groups required')
    _require(not capture_hashes & set(memory_hashes), 'any capture source leaked into a test/calibration memory')
    execution = checked.get('execution', {})
    _require(execution.get('methods') == list(METHODS), 'six fixed methods required in order')
    n = execution.get('minimum_test_families')
    _require(type(n) is int and n > 0 and split_counts['test'] >= n,
             'test groups below explicit selected minimum N')
    planning = execution.get('planning', {})
    _digest(planning.get('power_report_sha256'), 'power_report_sha256')
    for field in ('assumed_gain', 'assumed_discordance', 'component_power'):
        _number(planning.get(field), 0., 1., 'planning.' + field)
    _require(0 < planning['assumed_gain'] <= planning['assumed_discordance'] <= 1,
             'invalid accepted paired planning envelope')
    _require(planning['component_power'] in (.9, .95, .975), 'joint planning power must be explicit')
    _text(planning.get('justification'), 'planning.justification')
    models = execution.get('models', {})
    _require(set(models) == set(MODEL_ROLES), 'all fixed model/parser identities required')
    for role in MODEL_ROLES:
        _text(models[role].get('revision'), role+'.revision')
        _digest(models[role].get('artifact_sha256'), role+'.artifact_sha256')
    _digest(execution.get('harness_sha256'), 'harness_sha256')
    _digest(execution.get('protocol_sha256'), 'protocol_sha256')
    _require(execution.get('calibration_fpr_budget') == CALIBRATION_FPR, 'common fixed calibration budget required')
    _require(isinstance(execution.get('decoding'), Mapping) and bool(execution['decoding']), 'frozen decoding required')
    return checked


def verify_review(review: Mapping[str, Any], cohort_sha256: str, artifact_root: Path) -> dict:
    """Validate real evidence bindings; local declarations do not prove truth."""
    _require(review.get('schema') == 'antivenom.publication.provenance-review.v1', 'unknown review schema')
    _require(review.get('cohort_sha256') == cohort_sha256, 'review not bound to exact cohort')
    _require(review.get('decision') == 'accepted', 'independent provenance review is pending/rejected')
    reviewer = _text(review.get('reviewed_by'), 'reviewed_by')
    creator = _text(review.get('cohort_prepared_by'), 'cohort_prepared_by')
    _require(reviewer != creator, 'reviewer must be distinct from cohort preparer')
    for field in ('independence_assessment', 'development_overlap_assessment', 'same_tool_memory_dependence_assessment'):
        _text(review.get(field), field)
    inputs = review.get('evidence_files')
    _require(isinstance(inputs, list) and bool(inputs), 'review needs actual evidence files, not flags alone')
    verified = verify_input_files({'provenance': {'inputs': inputs}}, artifact_root)
    return {'reviewer': reviewer, 'verified_evidence_files': verified,
            'authorship_or_semantic_independence_authenticated_by_software': False}


def assess_readiness(project_root: Path, candidate_path: Path, review_path: Path,
                     artifact_root: Path) -> dict:
    report = {'schema': SCHEMA, 'status': 'blocked', 'model_calls': 0,
              'executable_freeze_written': False, 'native_empirical_validation': False,
              'native_authorship_authenticated_by_software': False,
              'errors': [], 'missing': [], 'verified_input_files': {}}
    for label, path in (('cohort', candidate_path), ('provenance_review', review_path)):
        if not path.is_file():
            report['missing'].append(label + ': ' + str(path))
    if report['missing']:
        return report
    try:
        used = historical_input_index(project_root)
        bundle = validate_candidate(json.loads(candidate_path.read_text()),
                                    used_family_ids=used['family_ids'],
                                    used_text_hashes=used['text_hashes'])
        report['cohort_sha256'] = canonical_sha256(bundle)
        review = verify_review(json.loads(review_path.read_text()), report['cohort_sha256'], artifact_root)
        report['verified_input_files'] = verify_input_files(bundle, artifact_root)
        protocol_path = project_root / 'docs/PUBLICATION_CONFIRMATION_PROTOCOL_V1.md'
        power_path = project_root / 'results/publication_power_v1.json'
        execution = bundle['execution']
        _require(hashlib.sha256(protocol_path.read_bytes()).hexdigest() == execution['protocol_sha256'],
                 'protocol changed after execution binding')
        _require(hashlib.sha256(power_path.read_bytes()).hexdigest() == execution['planning']['power_report_sha256'],
                 'power report changed after execution binding')
        # Import the exact outcome-free planner only after checking the report's
        # source bindings as well as its own digest. A changed planner cannot
        # certify N against an old report.
        power_report = json.loads(power_path.read_text())
        for name, digest in power_report['bound_planning_files'].items():
            target = (project_root / name).resolve(strict=True)
            _require(target.is_relative_to(project_root.resolve()), 'planning binding escapes project')
            _require(hashlib.sha256(target.read_bytes()).hexdigest() == digest,
                     'frozen planning file changed: ' + name)
        import importlib.util
        spec = importlib.util.spec_from_file_location('publication_planner', project_root / 'analysis/publication_power.py')
        planner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(planner)
        planning = execution['planning']
        power = planner.exact_paired_superiority_power(execution['minimum_test_families'],
                                                      planning['assumed_gain'], planning['assumed_discordance'])
        _require(power >= planning['component_power'], 'selected N does not attain declared power assumptions')
        report.update(status='input_contracts_reviewed_runtime_and_calibration_still_required',
                      provenance_kind=bundle['provenance']['kind'], review=review,
                      historical_exclusion_inputs=used['input_files'], planned_minimum_N=execution['minimum_test_families'],
                      planned_component_power=power,
                      remaining_gates=['pinned actual model/artifact bodies and common token limits',
                                       'fresh calibration scores and frozen thresholds',
                                       'reviewed native or local runtime and actual baseline reproduction',
                                       'single-job resource guard and complete uncached execution'])
    except (ContractError, ValueError, KeyError, TypeError, OSError) as exc:
        report['errors'].append(type(exc).__name__ + ': ' + str(exc))
    return report
