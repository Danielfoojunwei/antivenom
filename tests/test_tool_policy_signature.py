"""Software contracts only; synthetic fixtures are not MemMorph results."""
import hashlib
import json
import unittest

from antivenom.tool_policy_signature import (
    CaptureView, MAX_OUTPUT_CHARS, build_extraction_prompt, build_nli_hypothesis,
    filter_raw_sample_memories, filter_stored_memories, parse_extraction,
    project_capture, raw_sample_hypothesis, select_flags,
)


class SignatureTests(unittest.TestCase):
    def setUp(self):
        self.capture = CaptureView("opaque-capture", "A synthetic raw record.", "A synthetic stored record.")
        self.fields = {
            "asserted_condition": "a test-only condition",
            "asserted_rationale": "a test-only rationale",
            "induced_tool_preference": "a test-only preference",
            "scope_limitations": "the stated test-only scope",
        }

    def result(self, fields=None):
        return parse_extraction(self.capture, json.dumps(self.fields if fields is None else fields))

    def test_prompt_projects_only_source_text_and_never_gold_metadata(self):
        capture = {"capture_id": "ID_SENTINEL", "raw_memory": "RAW_SENTINEL", "stored_memory": "STORED_SENTINEL",
                   "safe_tool": "GOLD_SENTINEL", "gold_action": "ACTION_SENTINEL", "campaign_id": "CAMPAIGN_SENTINEL"}
        prompt = build_extraction_prompt(capture)
        self.assertIn("RAW_SENTINEL", prompt)
        self.assertIn("STORED_SENTINEL", prompt)
        for hidden in ["ID_SENTINEL", "GOLD_SENTINEL", "ACTION_SENTINEL", "CAMPAIGN_SENTINEL"]:
            self.assertNotIn(hidden, prompt)
        self.assertIn("do not assume that every fact is false", prompt)
        self.assertEqual(project_capture(capture).capture_id, "ID_SENTINEL")

    def test_missing_or_oversized_capture_does_not_get_repaired(self):
        with self.assertRaises(ValueError):
            project_capture({"capture_id": "x", "stored_memory": "stored"})
        with self.assertRaises(ValueError):
            CaptureView("x", "raw", " ")

    def test_valid_extract_retains_exact_raw_and_source_hashes(self):
        raw = " \n" + json.dumps(self.fields) + "\n"
        result = parse_extraction(self.capture, raw)
        self.assertTrue(result.valid)
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.raw_output, raw)
        self.assertEqual(result.raw_output_sha256, hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(result.stored_memory_sha256, hashlib.sha256(self.capture.stored_memory.encode()).hexdigest())
        self.assertEqual(result.as_dict()["signature"], self.fields)
        for value in self.fields.values():
            self.assertIn(value, build_nli_hypothesis(result.signature))

    def test_bad_outputs_preserve_evidence_without_repair(self):
        cases = ["", "  ", '{"asserted_condition":', "[]", "null", "```json\n{}\n```",
                 json.dumps({**self.fields, "safe_tool": "oracle"}),
                 json.dumps({k: v for k, v in self.fields.items() if k != "asserted_condition"}),
                 json.dumps({**self.fields, "asserted_condition": " "}),
                 json.dumps({**self.fields, "asserted_rationale": 4}),
                 json.dumps(self.fields)[:-1] + ', "asserted_condition": "duplicate"}',
                 "[" * 1200 + "]" * 1200,
                 "x" * (MAX_OUTPUT_CHARS + 1)]
        for raw in cases:
            with self.subTest(raw=raw[:60]):
                result = parse_extraction(self.capture, raw)
                self.assertFalse(result.valid)
                self.assertIsNone(result.signature)
                self.assertEqual(result.raw_output, raw)
                self.assertEqual(result.raw_output_sha256, hashlib.sha256(raw.encode()).hexdigest())
                self.assertTrue(result.errors)

    def test_invalid_capture_passthrough_does_not_score_or_use_attention(self):
        result = parse_extraction(self.capture, "malformed")
        def forbidden(_):
            self.fail("invalid extraction invoked the scorer")
        decision = filter_stored_memories(["native record one", "native record two"], result,
            forbidden, entailment_threshold=.01, attention_scores=[4., 4.])
        self.assertEqual(decision.flags, ())
        self.assertEqual(decision.kept_memories, ("native record one", "native record two"))
        self.assertEqual(decision.status, "invalid_extraction_passthrough")

    def test_callback_receives_actual_stored_text_and_claim_only(self):
        observed = []
        def scorer(pairs):
            observed.extend(pairs)
            return [.01, .009]
        decision = filter_stored_memories(["native stored A", "native stored B"], self.result(),
                                          scorer, entailment_threshold=.01)
        self.assertEqual([p[0] for p in observed], ["native stored A", "native stored B"])
        self.assertNotIn("opaque-capture", observed[0][1])
        self.assertEqual(decision.flags, (0,))
        self.assertEqual(decision.kept_memories, ("native stored B",))

    def test_raw_semantic_baseline_uses_same_stored_capture_without_extraction(self):
        seen = []
        def scorer(pairs):
            seen.extend(pairs)
            return [.1, .9]
        result = filter_raw_sample_memories(["stored A", "stored B"], self.capture, scorer,
                                           entailment_threshold=.8)
        self.assertEqual(raw_sample_hypothesis(self.capture), self.capture.stored_memory)
        self.assertEqual(seen, [("stored A", self.capture.stored_memory), ("stored B", self.capture.stored_memory)])
        self.assertEqual(result.flags, (1,))

    def test_score_contract_rejects_nan_wrong_count_and_invalid_threshold(self):
        for scores in [[float("nan"), .2], [.3], [True, .2], [1.1, .2]]:
            with self.subTest(scores=scores), self.assertRaises(ValueError):
                filter_stored_memories(["A", "B"], self.result(), lambda _: scores,
                                       entailment_threshold=.01)
        with self.assertRaises(ValueError):
            select_flags([.2], entailment_threshold=-.1)

    def test_optional_OR_is_explicit_and_uses_inclusive_threshold(self):
        self.assertEqual(select_flags([.009, .1], entailment_threshold=.01), (1,))
        self.assertEqual(select_flags([.009, .1], entailment_threshold=.01,
                                      attention_scores=[0., -1.]), (0, 1))

    def test_empty_memory_list_never_calls_scorer(self):
        result = filter_stored_memories([], self.result(), lambda _: self.fail("unexpected callback"),
                                       entailment_threshold=.01)
        self.assertEqual(result.flags, ())
        self.assertEqual(result.kept_hashes, ())


if __name__ == "__main__":
    unittest.main()
