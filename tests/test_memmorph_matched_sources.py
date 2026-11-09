"""Synthetic software contracts only; no native MemMorph efficacy evidence."""
import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError

from antivenom.memmorph_matched_sources import (
    SCHEMA_VERSION, build_matched_extraction_prompt, filter_matched_sources,
    project_source_views,
)
from antivenom.tool_policy_signature import CaptureView, MAX_MEMORY_CHARS


class MatchedSourcesTests(unittest.TestCase):
    def setUp(self):
        self.capture = {
            "capture_id": "BOOKKEEPING_ONLY", "raw_memory": "RAW_SOURCE",
            "stored_memory": "STORED_SOURCE", "gold_tool": "GOLD_ONLY",
            "scoring": {"safe_tools": ["SCORER_ONLY"]},
            "campaign_id": "CAMPAIGN_ONLY",
        }

    def test_projection_and_extraction_exclude_bookkeeping_and_scorer_fields(self):
        source = project_source_views(self.capture)
        prompt = build_matched_extraction_prompt(self.capture)
        payload = json.loads(source.projection_json)
        self.assertEqual(payload["schema"], SCHEMA_VERSION)
        self.assertEqual(payload["captured_views"], [
            {"stages": ["raw"], "text": "RAW_SOURCE"},
            {"stages": ["stored"], "text": "STORED_SOURCE"},
        ])
        self.assertEqual(prompt.split("SOURCE_PROJECTION_JSON:\n", 1)[1], source.projection_json)
        for forbidden in ("BOOKKEEPING_ONLY", "GOLD_ONLY", "SCORER_ONLY", "CAMPAIGN_ONLY"):
            self.assertNotIn(forbidden, source.projection_json)
            self.assertNotIn(forbidden, prompt)
        changed = {**self.capture, "capture_id": "OTHER_ID", "gold_tool": "OTHER_GOLD"}
        self.assertEqual(project_source_views(changed), source)
        self.assertIn("Do not supply a corrected policy", prompt)

    def test_projection_is_stable_nonmutating_and_immutable(self):
        original = dict(self.capture)
        source = project_source_views(self.capture)
        reversed_order = dict(reversed(list(self.capture.items())))
        self.assertEqual(source, project_source_views(reversed_order))
        self.assertEqual(source.projection_sha256,
                         hashlib.sha256(source.projection_json.encode()).hexdigest())
        self.assertEqual(self.capture, original)
        with self.assertRaises(FrozenInstanceError):
            source.views[0].text = "changed"

    def test_joined_baseline_receives_exact_focal_source_projection(self):
        seen = []
        def scorer(pairs):
            seen.append(pairs)
            return [.01, .009]
        decision = filter_matched_sources(["actual memory A", "actual memory B"],
            self.capture, scorer, entailment_threshold=.01, variant="joined")
        projection = project_source_views(self.capture).projection_json
        self.assertEqual(seen, [[("actual memory A", projection), ("actual memory B", projection)]])
        self.assertEqual(decision.hypotheses, (projection,))
        self.assertEqual(decision.flags, (0,))
        self.assertEqual(decision.kept_memories, ("actual memory B",))
        self.assertEqual(decision.entailment_threshold, .01)
        self.assertEqual(decision.callback_calls, 1)
        self.assertEqual(decision.scored_pairs, 2)
        self.assertIsNone(decision.per_view_scores)

    def test_max_variant_scores_all_views_once_before_fixed_aggregation(self):
        seen = []
        def scorer(pairs):
            seen.append(pairs)
            return [.1, .8, .7, .2]
        decision = filter_matched_sources(["A", "B"], self.capture, scorer,
            entailment_threshold=.75, variant="max_over_views")
        self.assertEqual(seen, [[("A", "RAW_SOURCE"), ("A", "STORED_SOURCE"),
                                 ("B", "RAW_SOURCE"), ("B", "STORED_SOURCE")]])
        self.assertEqual(decision.entailment_scores, (.8, .7))
        self.assertEqual(decision.per_view_scores, ((.1, .8), (.7, .2)))
        self.assertEqual(decision.flags, (0,))
        self.assertEqual(decision.kept_memories, ("B",))
        self.assertEqual(decision.callback_calls, 1)
        self.assertEqual(decision.scored_pairs, 4)
        self.assertEqual(decision.source_projection_sha256,
                         project_source_views(self.capture).projection_sha256)

    def test_exact_duplicate_views_are_deduplicated_with_both_stage_labels(self):
        capture = CaptureView("opaque", "same source", "same source")
        source = project_source_views(capture)
        self.assertEqual(len(source.views), 1)
        self.assertEqual(source.views[0].stages, ("raw", "stored"))
        self.assertEqual(source.views[0].text, "same source")
        seen = []
        def scorer(pairs):
            seen.extend(pairs)
            return [.9, .1]
        decision = filter_matched_sources(["A", "B"], capture, scorer,
            entailment_threshold=.5, variant="max_over_views")
        self.assertEqual(seen, [("A", "same source"), ("B", "same source")])
        self.assertEqual(decision.scored_pairs, 2)
        self.assertEqual(decision.source_view_stages, (("raw", "stored"),))
        self.assertEqual(decision.flags, (0,))

    def test_absent_stored_view_is_a_one_view_comparison_not_repair(self):
        capture = {"capture_id": "opaque", "raw_memory": "raw only"}
        source = project_source_views(capture)
        self.assertEqual(source.views[0].stages, ("raw",))
        self.assertEqual(len(source.views), 1)
        decision = filter_matched_sources(["A"], capture, lambda pairs: [.5],
            entailment_threshold=.5, variant="max_over_views")
        self.assertEqual(decision.flags, (0,))
        self.assertEqual(decision.scored_pairs, 1)
        with self.assertRaises(ValueError):
            project_source_views({**capture, "stored_memory": " "})

    def test_whitespace_is_preserved_and_not_semantically_deduplicated(self):
        capture = CaptureView("opaque", "record ", "record")
        source = project_source_views(capture)
        self.assertEqual(tuple(v.text for v in source.views), ("record ", "record"))
        self.assertNotEqual(source.views[0].sha256, source.views[1].sha256)
        changed = CaptureView("opaque", "record", "record")
        self.assertNotEqual(source.projection_sha256,
                            project_source_views(changed).projection_sha256)

    def test_empty_context_never_scores_and_retains_explicit_variant_config(self):
        for variant in ("joined", "max_over_views"):
            with self.subTest(variant=variant):
                decision = filter_matched_sources([], self.capture,
                    lambda _: self.fail("empty context invoked callback"),
                    entailment_threshold=.8, variant=variant)
                self.assertEqual(decision.callback_calls, 0)
                self.assertEqual(decision.scored_pairs, 0)
                self.assertEqual(decision.flags, ())
                self.assertEqual(decision.kept_hashes, ())
                self.assertEqual(decision.entailment_scores, ())
                self.assertEqual(decision.variant, variant)

    def test_invalid_operating_points_fail_before_callback(self):
        for threshold in [-.1, 1.1, 10 ** 1000, float("nan"), float("inf"), True, "0.5", None]:
            for variant in ("joined", "max_over_views"):
                with self.subTest(threshold=threshold, variant=variant), self.assertRaises(ValueError):
                    filter_matched_sources(["A"], self.capture,
                        lambda _: self.fail("invalid threshold scored"),
                        entailment_threshold=threshold, variant=variant)
        for variant in ("best", "JOINED", None, []):
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                filter_matched_sources(["A"], self.capture,
                    lambda _: self.fail("invalid variant scored"),
                    entailment_threshold=.5, variant=variant)
        with self.assertRaisesRegex(ValueError, "callable"):
            filter_matched_sources([], self.capture, None, entailment_threshold=.5)

    def test_malformed_callback_scores_are_rejected_without_retry(self):
        malformed = [[], [.1, .2], [True], [float("nan")], [float("inf")],
                     [-.1], [1.1], [10 ** 1000], [".1"], None, "0.1", {"score": .1}]
        for scores in malformed:
            calls = []
            def scorer(pairs):
                calls.append(pairs)
                return scores
            with self.subTest(scores=scores), self.assertRaises(ValueError):
                filter_matched_sources(["A"], self.capture, scorer,
                    entailment_threshold=.5, variant="joined")
            self.assertEqual(len(calls), 1)
        with self.assertRaisesRegex(ValueError, "pair count"):
            filter_matched_sources(["A"], self.capture, lambda _: [.5],
                entailment_threshold=.5, variant="max_over_views")

    def test_callback_exception_propagates_once_without_retry_or_fallback(self):
        calls = []
        def failure(pairs):
            calls.append(pairs)
            raise RuntimeError("synthetic scorer failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic scorer failure"):
            filter_matched_sources(["A"], self.capture, failure, entailment_threshold=.5)
        self.assertEqual(len(calls), 1)

    def test_invalid_memory_and_capture_fail_before_scoring(self):
        for memories in ("one string", b"bytes", {"record": "A"}, {"A", "B"}, [None], [" "],
                         ["x" * (MAX_MEMORY_CHARS + 1)], None):
            with self.subTest(memories=str(memories)[:30]), self.assertRaises(ValueError):
                filter_matched_sources(memories, self.capture,
                    lambda _: self.fail("invalid input scored"), entailment_threshold=.5)
        with self.assertRaises(ValueError):
            filter_matched_sources(["A"], {"capture_id": "opaque"},
                lambda _: self.fail("missing capture scored"), entailment_threshold=.5)

    def test_audit_hashes_bind_actual_inputs_hypotheses_and_retained_context(self):
        memories = ["A", "B", "B"]
        decision = filter_matched_sources(memories, self.capture, lambda _: (0., 1., 0.),
                                          entailment_threshold=.5)
        sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
        self.assertEqual(decision.input_hashes, tuple(map(sha, memories)))
        self.assertEqual(decision.hypothesis_sha256, tuple(map(sha, decision.hypotheses)))
        self.assertEqual(decision.flags, (1,))
        self.assertEqual(decision.kept_memories, ("A", "B"))
        self.assertEqual(decision.kept_hashes, (sha("A"), sha("B")))
        self.assertEqual(memories, ["A", "B", "B"])
        record = decision.as_dict()
        self.assertEqual(record["schema"], SCHEMA_VERSION)
        self.assertEqual(record["entailment_threshold"], .5)
        self.assertNotIn("gold_tool", record)


if __name__ == "__main__":
    unittest.main()
