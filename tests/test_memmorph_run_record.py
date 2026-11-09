"""Inert record-binding tests; no native MemMorph/model efficacy is measured."""
import copy
import json
import unittest

from antivenom.memmorph_run_record import (
    RecordError, build_case_request, canonical_sha256, create_run_manifest,
    execute_inert_case, record_observation, text_sha256, validate_observation,
    validate_run_manifest,
)


def fixtures():
    plan = {"candidate_methods": ["none", "tool_policy_entail", "tool_policy_OR", "raw_sample_semantic"],
            "capture_controls": ["confirmed_capture", "unrelated_capture", "mistaken_capture"]}
    config = {"operating_point": "synthetic-only", "threshold": .5, "refill": False}
    capture = {"capture_id": "CAPTURE_ID_SENTINEL", "raw_memory": "Synthetic raw capture.",
               "stored_memory": "Synthetic stored capture."}
    for stage in ("raw", "stored"):
        capture[stage + "_sha256"] = text_sha256(capture[stage + "_memory"])
    case = {"case_id": "CASE_ID_SENTINEL", "condition": "SCORER_CONDITION_SENTINEL", "pair_id": "PAIR_ID_SENTINEL",
        "state": "Synthetic ordinary task.",
        "tools": [{"name": "inspect", "description": "Inspect a fixture", "parameters": {}},
                  {"name": "change", "description": "Change a fixture", "parameters": {}}],
        "memories": [{"record_id": "MEMORY_ID_SENTINEL" + str(i), "text": text,
                      "raw_sha256": text_sha256("raw " + text), "stored_sha256": text_sha256(text)}
                     for i, text in enumerate(["Synthetic first record.", "Synthetic second record."])],
        "scoring": {"safe_tools": ["GOLD_SENTINEL"], "risky_tools": ["RISKY_SENTINEL"],
                    "poison_record_ids": ["POISON_SENTINEL"]}}
    signature = {"asserted_condition": "Synthetic condition", "asserted_rationale": "Synthetic rationale",
                 "induced_tool_preference": "Synthetic preference", "scope_limitations": "Synthetic scope"}
    return plan, config, capture, case, signature


class BoundRecordTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.config, self.capture, self.case, self.signature = fixtures()
        self.run = self.manifest()
        self.request = self.request_for()
        self.times = {"extraction_s": .1, "filter_s": .2, "selection_s": .3, "total_s": .6}

    def manifest(self, **kw):
        args = dict(plan=self.plan, config=self.config, method="tool_policy_entail",
            capture_control="confirmed_capture", model_config={"model": "inert-fixture", "revision": "test"},
            parser_identity={"name": "fixture-json-parser", "revision": "test"})
        args.update(kw)
        return create_run_manifest(**args)

    def request_for(self, run=None, case=None, capture=None, **kw):
        args = dict(kept_indices=[1], extraction_status="valid", signature=self.signature,
                    extraction_raw_output=json.dumps(self.signature))
        args.update(kw)
        return build_case_request(run or self.run, case or self.case, capture or self.capture, **args)

    def observation(self, **kw):
        args = dict(status="selected", selected_tool="inspect", raw_response='{"tool":"inspect"}', timings=self.times)
        args.update(kw)
        return record_observation(self.run, self.request, **args)

    def validate(self, observation, **kw):
        args = dict(case=self.case, capture=self.capture)
        args.update(kw)
        return validate_observation(self.run, self.request, observation, **args)

    def test_manifest_pins_plan_config_model_parser_and_control(self):
        checked = validate_run_manifest(self.run, plan=self.plan, config=self.config)
        self.assertEqual(checked, self.run)
        self.assertFalse(checked["execution_verified"])
        self.assertFalse(checked["native_efficacy_established"])
        self.assertIn("do not authenticate", checked["warning"])
        for changes in ({"capture_control": "mistaken_capture"}, {"method": "raw_sample_semantic"},
                        {"model_config": {"model": "different"}},
                        {"parser_identity": {"name": "other", "revision": "other"}}):
            self.assertNotEqual(self.manifest(**changes)["manifest_sha256"], self.run["manifest_sha256"])

    def test_stale_plan_or_config_cannot_validate(self):
        plan = copy.deepcopy(self.plan)
        plan["untouched_campaigns"] = ["new"]
        for plan, config in [(plan, self.config), (self.plan, {**self.config, "threshold": .6})]:
            with self.assertRaisesRegex(RecordError, "expected plan/config"):
                validate_run_manifest(self.run, plan=plan, config=config)

    def test_undeclared_method_control_and_nonfinite_config_rejected(self):
        for changes in ({"method": "invented"}, {"capture_control": "gold_tool"},
                        {"config": {"threshold": float("nan")}}, {"parser_identity": {"name": "parser"}},
                        {"plan": {**self.plan, "candidate_methods": "tool_policy_entail"}},
                        {"plan": {**self.plan, "capture_controls": ["confirmed_capture", "confirmed_capture"]}}):
            with self.subTest(changes=changes), self.assertRaises(RecordError):
                self.manifest(**changes)

    def test_actual_runtime_input_is_whitelisted_and_order_preserved(self):
        view = self.request["model_input"]
        self.assertEqual(set(view), {"state", "tools", "memories"})
        self.assertEqual(view["memories"], [{"text": self.case["memories"][1]["text"]}])
        serialized = json.dumps(view)
        for hidden in ["GOLD_SENTINEL", "RISKY_SENTINEL", "POISON_SENTINEL", "CASE_ID_SENTINEL",
                       "PAIR_ID_SENTINEL", "CAPTURE_ID_SENTINEL", "SCORER_CONDITION_SENTINEL", "MEMORY_ID_SENTINEL",
                       "signature", "stored_sha256", "raw_sha256"]:
            self.assertNotIn(hidden, serialized)
        self.assertEqual(self.request["model_input_sha256"], canonical_sha256(view))
        self.assertEqual(self.request["post_filter_memory_hashes"], [self.case["memories"][1]["stored_sha256"]])

    def test_scorer_changes_do_not_change_runtime_input(self):
        altered = copy.deepcopy(self.case)
        altered.update(case_id="another", condition="clean")
        altered["scoring"] = {"safe_tools": ["change"], "risky_tools": ["inspect"], "poison_record_ids": []}
        other = self.request_for(case=altered)
        self.assertEqual(other["model_input"], self.request["model_input"])
        self.assertNotEqual(other["case_sha256"], self.request["case_sha256"])

    def test_callbacks_cannot_mutate_bound_input(self):
        def select(view):
            self.assertNotIn("scoring", view)
            view["memories"].clear()
            return "inspect"
        result = execute_inert_case(self.run, self.request, select,
            lambda raw: {"status": "selected", "selected_tool": raw})
        self.assertEqual(len(self.request["model_input"]["memories"]), 1)
        self.assertEqual(self.validate(result), result)
        self.assertFalse(result["native_efficacy_established"])

    def test_filter_cannot_reorder_duplicate_invent_or_overflow_memories(self):
        for indices in ([1, 0], [1, 1], [2], [-1], [True], "1"):
            with self.subTest(indices=indices), self.assertRaises(RecordError):
                self.request_for(kept_indices=indices)

    def test_none_baseline_cannot_hide_filtering_or_signature(self):
        run = self.manifest(method="none")
        request = self.request_for(run=run, kept_indices=[0, 1], extraction_status="not_requested",
                                   signature=None, extraction_raw_output=None)
        self.assertEqual(len(request["model_input"]["memories"]), 2)
        for changes in ({"kept_indices": [1]}, {"signature": self.signature}):
            args = dict(kept_indices=[0, 1], extraction_status="not_requested", signature=None, extraction_raw_output=None)
            args.update(changes)
            with self.assertRaises(RecordError):
                self.request_for(run=run, **args)

    def test_invalid_extraction_and_revocation_keep_context(self):
        for method in ("tool_policy_entail", "tool_policy_OR"):
            run = self.manifest(method=method)
            request = self.request_for(run=run, kept_indices=[0, 1], extraction_status="malformed_json",
                signature=None, extraction_raw_output="broken")
            self.assertEqual(request["extraction_raw_output_sha256"], text_sha256("broken"))
            with self.assertRaisesRegex(RecordError, "pass all memories"):
                self.request_for(run=run, extraction_status="malformed_json", signature=None, extraction_raw_output="broken")
            revoked = self.request_for(run=run, kept_indices=[0, 1], signature_state="revoked")
            self.assertEqual(revoked["signature_state"], "revoked")
            with self.assertRaisesRegex(RecordError, "pass all memories"):
                self.request_for(run=run, signature_state="revoked")

    def test_invalid_extraction_needs_raw_evidence_and_no_valid_signature(self):
        for changes in ({"extraction_raw_output": None}, {"signature": self.signature}):
            args = dict(kept_indices=[0, 1], extraction_status="malformed_json", signature=None, extraction_raw_output="broken")
            args.update(changes)
            with self.assertRaises(RecordError):
                self.request_for(**args)

    def test_gold_signature_fields_and_tool_metadata_are_rejected(self):
        with self.assertRaisesRegex(RecordError, "four"):
            self.request_for(signature={**self.signature, "safe_tool": "inspect"})
        case = copy.deepcopy(self.case)
        case["tools"][0]["gold_tool"] = True
        with self.assertRaisesRegex(RecordError, "scorer"):
            self.request_for(case=case)

    def test_input_hashes_are_not_trusted_declarations(self):
        case = copy.deepcopy(self.case)
        case["memories"][0]["text"] = "changed"
        with self.assertRaisesRegex(RecordError, "stored memory hash"):
            self.request_for(case=case)
        capture = copy.deepcopy(self.capture)
        capture["stored_memory"] = "changed"
        with self.assertRaisesRegex(RecordError, "capture stored hash"):
            self.request_for(capture=capture)

    def test_observation_round_trip_binds_raw_response_and_timings(self):
        result = self.observation()
        self.assertEqual(self.validate(result), result)
        self.assertEqual(result["raw_response_sha256"], text_sha256(result["raw_response"]))
        self.assertEqual(result["timings"], self.times)
        self.assertEqual(result["extraction_status"], "valid")

    def test_other_case_capture_or_context_is_rejected(self):
        result = self.observation()
        for field in ("case_id", "state"):
            case = copy.deepcopy(self.case)
            case[field] = "changed"
            with self.assertRaisesRegex(RecordError, "case changed"):
                self.validate(result, case=case)
        case = copy.deepcopy(self.case)
        case["memories"][1]["text"] = "changed context"
        case["memories"][1]["stored_sha256"] = text_sha256("changed context")
        with self.assertRaisesRegex(RecordError, "case changed"):
            self.validate(result, case=case)
        capture = copy.deepcopy(self.capture)
        capture["capture_id"] = "different"
        with self.assertRaisesRegex(RecordError, "capture changed"):
            self.validate(result, capture=capture)

    def test_stale_config_parser_or_control_cannot_reuse_observation(self):
        result = self.observation()
        for changes in ({"config": {**self.config, "threshold": .6}},
                        {"capture_control": "mistaken_capture"},
                        {"parser_identity": {"name": "parser", "revision": "different"}}):
            other = self.manifest(**changes)
            request = self.request_for(run=other)
            with self.assertRaises(RecordError):
                validate_observation(other, request, result, case=self.case, capture=self.capture)

    def test_resealed_mismatched_result_bindings_are_rejected(self):
        for key, value in [("case_id", "another"), ("method", "none"), ("capture_control", "mistaken_capture"),
                           ("model_input_sha256", "0" * 64), ("post_filter_memory_hashes", []),
                           ("parser_identity_sha256", "0" * 64), ("model_config_sha256", "0" * 64),
                           ("raw_response_sha256", "0" * 64), ("native_efficacy_established", True)]:
            result = self.observation()
            result[key] = value
            result.pop("observation_sha256")
            result["observation_sha256"] = canonical_sha256(result)
            with self.subTest(key=key), self.assertRaisesRegex(RecordError, "differs from expected"):
                self.validate(result)

    def test_resealed_request_metadata_or_filter_outcome_is_rejected(self):
        for changes in ({"method": "none"}, {"capture_control": "mistaken_capture"},
                        {"signature_sha256": "0" * 64}, {"extraction_raw_output_sha256": "0" * 64},
                        {"signature": {**self.signature, "safe_tool": "inspect"}}):
            request = copy.deepcopy(self.request)
            request.update(changes)
            request.pop("request_sha256")
            request["request_sha256"] = canonical_sha256(request)
            result = record_observation(self.run, request, status="selected", selected_tool="inspect",
                                        raw_response="inspect", timings=self.times)
            with self.subTest(changes=changes), self.assertRaises(RecordError):
                validate_observation(self.run, request, result, case=self.case, capture=self.capture)

    def test_parser_replay_can_verify_reported_choice_and_false_failures(self):
        parser = lambda raw: {"status": "selected", "selected_tool": json.loads(raw)["tool"]}
        result = self.observation()
        self.assertEqual(self.validate(result, parser_callback=parser), result)
        altered = self.observation(selected_tool="change")
        with self.assertRaisesRegex(RecordError, "parser replay"):
            self.validate(altered, parser_callback=parser)
        false_failure = self.observation(status="parse_failure", selected_tool=None, error="reported error")
        with self.assertRaisesRegex(RecordError, "parser replay"):
            self.validate(false_failure, parser_callback=parser)
        invalid = self.observation(status="parse_failure", selected_tool=None, raw_response="invalid", error="reported error")
        self.assertEqual(self.validate(invalid, parser_callback=parser), invalid)

    def test_unsealed_or_invented_results_are_rejected(self):
        result = self.observation()
        result["selected_tool"] = "change"
        with self.assertRaisesRegex(RecordError, "observation_sha256"):
            self.validate(result)
        for args in (dict(status="selected", selected_tool="invented"),
                     dict(status="abstained", selected_tool="inspect"),
                     dict(status="selected", selected_tool=[]),
                     dict(status="parse_failure", selected_tool=None, error=None)):
            with self.subTest(args=args), self.assertRaises(RecordError):
                self.observation(**args)

    def test_callback_and_parser_failures_are_saved_once(self):
        calls = []
        def fail(view):
            calls.append(view)
            raise RuntimeError("fixture failure")
        selected = execute_inert_case(self.run, self.request, fail, lambda _: self.fail("parser called"))
        self.assertEqual(selected["status"], "selection_failure")
        self.assertIsNone(selected["raw_response"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.validate(selected), selected)
        parsed = execute_inert_case(self.run, self.request, lambda _: "exact malformed output",
                                    lambda raw: json.loads(raw))
        self.assertEqual(parsed["status"], "parse_failure")
        self.assertEqual(parsed["raw_response"], "exact malformed output")
        self.assertIsNone(parsed["selected_tool"])
        self.assertEqual(self.validate(parsed), parsed)

    def test_abstention_not_converted_to_selection(self):
        result = execute_inert_case(self.run, self.request, lambda _: "abstain",
            lambda _: {"status": "abstained", "selected_tool": None})
        self.assertEqual(result["status"], "abstained")
        self.assertIsNone(result["selected_tool"])
        self.assertEqual(self.validate(result), result)

    def test_bad_parser_results_are_failures_not_repaired(self):
        for returned in ([], {"status": "selected", "selected_tool": "invented"},
                         {"status": "abstained", "selected_tool": "inspect"},
                         {"status": "selected", "selected_tool": "inspect", "gold_tool": "inspect"}):
            result = execute_inert_case(self.run, self.request, lambda _: "raw", lambda _: returned)
            self.assertEqual(result["status"], "parse_failure")
            self.assertEqual(result["raw_response"], "raw")

    def test_negative_nonfinite_or_missing_timing_is_rejected(self):
        for changes in ({"filter_s": -1}, {"total_s": .01}, {"selection_s": float("nan")}, {"filter_s": True}):
            with self.subTest(changes=changes), self.assertRaisesRegex(RecordError, "tim"):
                self.observation(timings={**self.times, **changes})
        with self.assertRaisesRegex(RecordError, "timings need"):
            self.observation(timings={"total_s": 1})

    def test_inert_runner_cannot_be_labelled_native_evidence(self):
        native = self.manifest(evidence_scope="reported_native")
        request = self.request_for(run=native)
        with self.assertRaisesRegex(RecordError, "synthetic"):
            execute_inert_case(native, request, lambda _: "inspect", lambda raw: {"status": "selected", "selected_tool": raw})
        with self.assertRaisesRegex(RecordError, "synthetic"):
            record_observation(native, request, status="selected", selected_tool="inspect", raw_response="inspect", timings=self.times)
        with self.assertRaisesRegex(RecordError, "relabelled"):
            self.observation(execution_kind="reported_native")

    def test_returned_validation_copy_does_not_mutate_original(self):
        result = self.observation()
        checked = self.validate(result)
        checked["timings"]["filter_s"] = 100
        self.assertEqual(result["timings"]["filter_s"], .2)

    def test_reported_native_and_local_port_declarations_stay_distinct(self):
        # These are fabricated declarations testing bindings, not actual runs.
        for scope, kind in [("reported_native", "reported_native"),
                            ("reported_author_validated_local_port", "reported_local_port")]:
            run = self.manifest(evidence_scope=scope)
            request = self.request_for(run=run)
            result = record_observation(run, request, status="selected", selected_tool="inspect",
                raw_response="fixture raw output", timings=self.times, execution_kind=kind)
            checked = validate_observation(run, request, result, case=self.case, capture=self.capture)
            self.assertFalse(checked["execution_verified"])
            self.assertFalse(checked["native_efficacy_established"])
        local = self.manifest(evidence_scope="reported_author_validated_local_port")
        request = self.request_for(run=local)
        with self.assertRaisesRegex(RecordError, "relabelled"):
            record_observation(local, request, status="selected", selected_tool="inspect",
                raw_response="fixture", timings=self.times, execution_kind="reported_native")


if __name__ == "__main__":
    unittest.main()
