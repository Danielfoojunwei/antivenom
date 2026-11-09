"""Contract tests, never model-accuracy or provenance-authentication evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from antivenom.memmorph_eval import ContractError, canonical_sha256
from antivenom.publication_study import (
    SCHEMA, METHODS, calibrate_clean_scores, extraction_prompt, run_filter,
    validate_candidate, primary_pair, verify_review, assess_readiness, sha,
)

ROOT = Path(__file__).resolve().parents[1]


def source_capture(key='capture'):
    return {'capture_id': key, 'raw_memory': 'raw source ' + key,
            'stored_memory': 'stored source ' + key,
            'raw_sha256': sha('raw source ' + key), 'stored_sha256': sha('stored source ' + key),
            'gold_tool': 'GOLD_SECRET', 'family_id': 'FAMILY_SECRET'}


def signature():
    return json.dumps({'asserted_condition': 'condition', 'asserted_rationale': 'rationale',
                       'induced_tool_preference': 'preference', 'scope_limitations': 'scope'})


def campaign(key, split='test'):
    rows = []
    for condition in ('clean', 'attacked'):
        text = key + ' ' + condition + ' new memory'
        rows.append({'case_id': key + ':' + condition, 'pair_id': key + ':pair',
                     'condition': condition, 'state': 'state ' + key,
                     'tools': [{'name': 'safe', 'description': 'legitimate action'},
                               {'name': 'risky', 'description': 'alternative action'}],
                     'memories': [{'record_id': key + ':record:' + condition,
                                   'text': text, 'raw_sha256': sha(text), 'stored_sha256': sha(text)}],
                     'scoring': {'safe_tools': ['safe'], 'risky_tools': ['risky'],
                                 'poison_record_ids': [] if condition == 'clean' else [key + ':record:attacked']}})
    result = {'campaign_id': key, 'independence_group': key, 'split': split,
              'capture': source_capture(key), 'cases': rows}
    result['primary_pair_id'] = primary_pair(result)
    return result


def fixture_bundle():
    return {'schema': SCHEMA,
            'provenance': {'kind': 'independent_local', 'source_url': 'https://example.invalid/fixture',
                           'revision': 'unit-test-only', 'license': 'fixture',
                           'inputs': [{'path': 'source.txt', 'sha256': sha('source evidence')}]},
            'campaigns': [campaign('new-cal', 'calibration')] + [campaign('new-test-' + str(i)) for i in range(8)],
            'execution': {'methods': list(METHODS), 'minimum_test_families': 8,
                          'planning': {'power_report_sha256': hashlib.sha256((ROOT/'results/publication_power_v1.json').read_bytes()).hexdigest(),
                                       'assumed_gain': 1., 'assumed_discordance': 1., 'component_power': .9,
                                       'justification': 'synthetic boundary-test assumptions only'},
                          'models': {role: {'revision': 'fixture-only', 'artifact_sha256': 'a'*64}
                                     for role in ('extraction','nli','embedding','reader','parser')},
                          'harness_sha256': 'b'*64,
                          'protocol_sha256': hashlib.sha256((ROOT/'docs/PUBLICATION_CONFIRMATION_PROTOCOL_V1.md').read_bytes()).hexdigest(),
                          'calibration_fpr_budget': .05,
                          'decoding': {'temperature': 0, 'max_tokens': 128}}}


class PublicationCalibrationTests(unittest.TestCase):
    def test_tie_cannot_exceed_five_percent_budget(self):
        result = calibrate_clean_scores('raw_nli_joined', [.5, .5] + [.1]*18)
        self.assertGreater(result.threshold, .5)
        self.assertEqual(result.flagged_records, 0)
        self.assertEqual(result.benign_records, 20)

    def test_bounded_maximum_tie_fails_instead_of_infinite_threshold(self):
        with self.assertRaises(ContractError):
            calibrate_clean_scores('raw_nli_joined', [1., 1.] + [.1]*18)

    def test_invalid_extraction_stays_in_denominator(self):
        result = calibrate_clean_scores('tool_policy_entail', [None]*19 + [.5])
        self.assertEqual(result.failed_extraction_records, 19)
        self.assertEqual(result.benign_records, 20)
        self.assertLessEqual(result.observed_fpr, .05)
        with self.assertRaises(ContractError):
            calibrate_clean_scores('raw_nli_joined', [None]*20)

    def test_nonfinite_and_boolean_scores_fail(self):
        for value in (float('nan'), float('inf'), True, -1):
            with self.subTest(value=value), self.assertRaises(ContractError):
                calibrate_clean_scores('tool_policy_entail', [value])


class PublicationFilterTests(unittest.TestCase):
    def test_same_projection_excludes_bookkeeping_and_gold(self):
        capture = source_capture()
        prompt = extraction_prompt(capture)
        got = []
        def score(pairs):
            got.extend(pairs)
            return [.1] * len(pairs)
        result = run_filter('raw_nli_joined', ['memory'], capture, threshold=.5, nli_callback=score)
        self.assertIn(result['source_projection_json'], prompt)
        for secret in ('GOLD_SECRET', 'FAMILY_SECRET', 'gold_tool', 'family_id'):
            self.assertNotIn(secret, prompt + str(got))
        changed = copy.deepcopy(capture); changed['gold_tool'] = 'changed'
        self.assertEqual(extraction_prompt(changed), prompt)
        self.assertEqual(capture['gold_tool'], 'GOLD_SECRET')

    def test_malformed_extraction_passes_through_without_scorer(self):
        def never(_):
            self.fail('invalid extraction must not invoke scorer')
        result = run_filter('tool_policy_entail', ['memory'], source_capture(),
                            threshold=.5, extraction_output='{bad', nli_callback=never)
        self.assertEqual(result['kept_memories'], ['memory'])
        self.assertEqual(result['extraction']['status'], 'malformed_json')
        self.assertEqual(result['callback_calls'], 0)
        self.assertEqual(result['extraction']['raw_output'], '{bad')

    def test_valid_focal_keeps_all_failure_records(self):
        result = run_filter('tool_policy_entail', ['a', 'b'], source_capture(),
                            threshold=.5, extraction_output=signature(), nli_callback=lambda p: [.8,.2])
        self.assertEqual(result['flags'], [0])
        self.assertEqual(result['scored_pairs'], 2)
        self.assertEqual(result['input_hashes'], [sha('a'),sha('b')])

    def test_raw_max_has_fixed_additional_pair_budget(self):
        capture = source_capture()
        result = run_filter('raw_nli_max_over_views', ['a','b'], capture,
                            threshold=.85, nli_callback=lambda p: [.1,.8,.9,.2])
        self.assertEqual(result['scored_pairs'], 4)
        self.assertEqual(result['callback_calls'], 1)
        self.assertEqual(result['flags'], [1])
        capture['stored_memory'] = capture['raw_memory']
        result = run_filter('raw_nli_max_over_views', ['a','b'], capture,
                            threshold=.5, nli_callback=lambda p: [.1,.2])
        self.assertEqual(result['scored_pairs'], 2)

    def test_signed_cosine_scores_and_fixed_max(self):
        result = run_filter('cosine', ['a','b'], source_capture(), threshold=.85,
                            cosine_callback=lambda p: [-.9,.8,.9,-.2])
        self.assertEqual(result['flags'], [1])
        self.assertEqual(result['scored_pairs'], 4)

    def test_model_failure_is_not_retried_or_silently_dropped(self):
        calls = []
        def fail(pairs):
            calls.append(pairs)
            raise RuntimeError('backend unavailable')
        result = run_filter('raw_nli_joined', ['a','b'], source_capture(), threshold=.5, nli_callback=fail)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['status'], 'operational_failure_passthrough')
        self.assertEqual(result['kept_memories'], ['a','b'])
        self.assertEqual(result['failure']['type'], 'RuntimeError')

    def test_bad_score_count_is_explicit_failure(self):
        result = run_filter('raw_nli_joined', ['a','b'], source_capture(), threshold=.5,
                            nli_callback=lambda p: [.1])
        self.assertEqual(result['status'], 'operational_failure_passthrough')
        self.assertEqual(result['flags'], [])

    def test_none_dropall_have_no_scoring_calls(self):
        for method, expected in [('none',['a','b']), ('drop_all',[])]:
            result = run_filter(method, ['a','b'], source_capture())
            self.assertEqual(result['kept_memories'], expected)
            self.assertEqual(result['callback_calls'], 0)
            self.assertEqual(result['scored_pairs'], 0)


class PublicationInputGateTests(unittest.TestCase):
    def validate(self, bundle, ids=None, hashes=None):
        return validate_candidate(bundle, used_family_ids=ids or set(), used_text_hashes=hashes or set())

    def test_valid_shape_is_copied_not_authenticated(self):
        bundle = fixture_bundle(); result = self.validate(bundle)
        result['campaigns'][0]['capture']['raw_memory'] = 'changed'
        self.assertNotEqual(result, bundle)

    def test_old_id_and_relabelled_capture_rejected(self):
        bundle = fixture_bundle()
        with self.assertRaises(ContractError):
            self.validate(bundle, ids={'new-test-0'})
        with self.assertRaises(ContractError):
            self.validate(bundle, hashes={sha('raw source new-test-0')})

    def test_calibration_test_group_overlap_rejected(self):
        bundle = fixture_bundle()
        bundle['campaigns'][1]['independence_group'] = bundle['campaigns'][0]['independence_group']
        with self.assertRaises(ContractError):
            self.validate(bundle)

    def test_duplicate_task_cannot_inflate_families(self):
        bundle = fixture_bundle()
        for row in bundle['campaigns'][2]['cases']:
            row['state'] = bundle['campaigns'][1]['cases'][0]['state']
        with self.assertRaises(ContractError):
            self.validate(bundle)

    def test_source_capture_cannot_leak_into_any_test_memory(self):
        bundle = fixture_bundle(); memory = bundle['campaigns'][1]['cases'][0]['memories'][0]
        memory['text'] = bundle['campaigns'][0]['capture']['raw_memory']
        memory['raw_sha256'] = memory['stored_sha256'] = sha(memory['text'])
        with self.assertRaises(ContractError):
            self.validate(bundle)

    def test_rewritten_memory_raw_source_cannot_reuse_historical_capture(self):
        bundle = fixture_bundle()
        memory = bundle['campaigns'][1]['cases'][0]['memories'][0]
        historical = sha('historical captured source')
        memory['raw_sha256'] = historical
        # Stored bytes differ; changing them cannot erase raw-source lineage.
        self.assertNotEqual(memory['stored_sha256'], historical)
        with self.assertRaisesRegex(ContractError, 'historical raw or stored'):
            self.validate(bundle, hashes={historical})

    def test_rewritten_memory_raw_source_cannot_leak_other_campaign_capture(self):
        bundle = fixture_bundle()
        memory = bundle['campaigns'][1]['cases'][0]['memories'][0]
        other_capture = bundle['campaigns'][0]['capture']['raw_sha256']
        memory['raw_sha256'] = other_capture
        self.assertNotEqual(memory['stored_sha256'], other_capture)
        with self.assertRaisesRegex(ContractError, 'any capture source leaked'):
            self.validate(bundle)

    def test_task_selection_and_missing_model_identity_rejected(self):
        for mutation in ('task', 'model', 'N'):
            bundle = fixture_bundle()
            if mutation == 'task': bundle['campaigns'][1]['primary_pair_id'] = 'chosen_after_outcome'
            if mutation == 'model': del bundle['execution']['models']['parser']
            if mutation == 'N': bundle['execution']['minimum_test_families'] = 9
            with self.subTest(mutation=mutation), self.assertRaises(ContractError): self.validate(bundle)

    def test_fixture_claim_flags_do_not_make_native(self):
        bundle = fixture_bundle()
        bundle['provenance'].update(kind='synthetic_fixture', author_verified=True, human_authorized=True)
        with self.assertRaises(ContractError): self.validate(bundle)

    def test_review_flags_without_evidence_are_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ContractError):
                verify_review({'schema': 'antivenom.publication.provenance-review.v1',
                               'cohort_sha256': 'a'*64, 'decision': 'accepted',
                               'reviewed_by':'b', 'cohort_prepared_by':'a',
                               'independence_assessment':'reviewed', 'development_overlap_assessment':'reviewed',
                               'same_tool_memory_dependence_assessment':'reviewed',
                               'human_authorized':True}, 'a'*64, Path(tmp))

    def test_review_binding_changes_or_file_changes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'review.txt'; path.write_text('review evidence')
            review = {'schema':'antivenom.publication.provenance-review.v1',
                      'cohort_sha256':'a'*64, 'decision':'accepted', 'reviewed_by':'b', 'cohort_prepared_by':'a',
                      'independence_assessment':'reviewed', 'development_overlap_assessment':'reviewed',
                      'same_tool_memory_dependence_assessment':'reviewed',
                      'evidence_files':[{'path':'review.txt','sha256':sha('review evidence')}]}
            result = verify_review(review, 'a'*64, Path(tmp))
            self.assertFalse(result['authorship_or_semantic_independence_authenticated_by_software'])
            with self.assertRaises(ContractError): verify_review(review, 'b'*64, Path(tmp))
            path.write_text('modified')
            with self.assertRaises(ContractError): verify_review(review, 'a'*64, Path(tmp))

    def test_missing_default_inputs_cannot_write_executable_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = assess_readiness(ROOT, Path(tmp)/'missing.json', Path(tmp)/'review.json', Path(tmp))
            self.assertEqual(report['status'], 'blocked')
            self.assertFalse(report['executable_freeze_written'])
            self.assertFalse(report['native_empirical_validation'])
            self.assertEqual(report['model_calls'], 0)
            self.assertEqual(len(report['missing']), 2)

    def test_readiness_validates_frozen_protocol_and_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp); bundle = fixture_bundle()
            (tmp/'source.txt').write_text('source evidence')
            (tmp/'review.txt').write_text('independent unit-test evidence, not actual provenance')
            review = {'schema':'antivenom.publication.provenance-review.v1',
                      'cohort_sha256':canonical_sha256(bundle), 'decision':'accepted',
                      'reviewed_by':'fixture-reviewer', 'cohort_prepared_by':'fixture-preparer',
                      'independence_assessment':'synthetic fixture test', 'development_overlap_assessment':'synthetic fixture test',
                      'same_tool_memory_dependence_assessment':'synthetic fixture test',
                      'evidence_files':[{'path':'review.txt','sha256':sha((tmp/'review.txt').read_text())}]}
            (tmp/'cohort.json').write_text(json.dumps(bundle)); (tmp/'review.json').write_text(json.dumps(review))
            report = assess_readiness(ROOT, tmp/'cohort.json', tmp/'review.json', tmp)
            self.assertEqual(report['errors'], [])
            self.assertIn('runtime_and_calibration_still_required', report['status'])
            self.assertFalse(report['native_authorship_authenticated_by_software'])
            bundle['execution']['protocol_sha256'] = 'c'*64
            review['cohort_sha256'] = canonical_sha256(bundle)
            (tmp/'cohort.json').write_text(json.dumps(bundle)); (tmp/'review.json').write_text(json.dumps(review))
            report = assess_readiness(ROOT, tmp/'cohort.json', tmp/'review.json', tmp)
            self.assertEqual(report['status'], 'blocked')
            self.assertIn('protocol changed', report['errors'][0])


if __name__ == '__main__':
    unittest.main()
