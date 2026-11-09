"""Inert end-to-end lifecycle/record checks; zero native or model efficacy."""
import copy
import json
import unittest

from antivenom.memmorph_matched_sources import (
    build_matched_extraction_prompt, filter_matched_sources, project_source_views,
)
from antivenom.memmorph_run_record import (
    RecordError, build_case_request, create_run_manifest, execute_inert_case,
    text_sha256, validate_observation, validate_run_manifest,
)
from antivenom.signature_lifecycle import SignatureRegistry
from antivenom.tool_policy_signature import parse_extraction


class ExtensionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.capture = {"capture_id": "PRIVATE_CAPTURE_ID", "raw_memory": "Synthetic captured raw view.",
                        "stored_memory": "Synthetic captured stored view.", "safe_tool": "HIDDEN_GOLD_LABEL"}
        for stage in ("raw", "stored"):
            self.capture[stage + "_sha256"] = text_sha256(self.capture[stage + "_memory"])
        self.fields = {"asserted_condition": "Synthetic fixture condition",
                       "asserted_rationale": "Synthetic fixture rationale",
                       "induced_tool_preference": "Synthetic fixture preference",
                       "scope_limitations": "No empirical applicability claim"}
        self.raw_extraction = json.dumps(self.fields)
        self.extraction = parse_extraction(self.capture, self.raw_extraction)
        self.memories = ("Ordinary fixture record A", "Ordinary fixture record B")
        self.case = {"case_id": "PRIVATE_CASE_ID", "condition": "clean", "state": "A synthetic task.",
                     "tools": [{"name": "inspect", "description": "Inert choice only", "parameters": {}},
                               {"name": "change", "description": "Inert choice only", "parameters": {}}],
                     "memories": [{"text": text, "stored_sha256": text_sha256(text)} for text in self.memories],
                     "scoring": {"safe_tools": ["inspect"], "risky_tools": ["change"]}}
        self.plan = {"candidate_methods": ["tool_policy_entail"], "capture_controls": ["mistaken_capture"]}
        self.config = {"threshold": .5, "execution": "inert_fixture_only", "refill": False}
        self.run = create_run_manifest(plan=self.plan, config=self.config, method="tool_policy_entail",
            capture_control="mistaken_capture", model_config={"name": "INERT_CALLBACK_NOT_A_MODEL"},
            parser_identity={"name": "fixture-parser", "revision": "1"})

    @staticmethod
    def scorer(pairs):
        return [.9 if text.endswith(" A") else .1 for text, _ in pairs]

    def request(self, registry, decision, *, state):
        return build_case_request(self.run, self.case, self.capture,
            kept_indices=[i for i in range(len(self.memories)) if i not in decision.flags],
            extraction_status="valid", signature=self.fields,
            extraction_raw_output=self.raw_extraction, signature_state=state)

    @staticmethod
    def parser(raw):
        return {"status": "selected", "selected_tool": json.loads(raw)["tool"]}

    @staticmethod
    def inert_selector(view):
        # This deliberately defined function checks state plumbing, not an LLM.
        return json.dumps({"tool": "inspect" if len(view["memories"]) == 2 else "change"})

    def test_mistaken_share_revoke_restart_binds_exact_contexts(self):
        sender, receiver = SignatureRegistry(), SignatureRegistry()
        for registry in (sender, receiver):
            registry.publish("mistaken-fixture", 1, self.extraction)
        before = receiver.filter(self.memories, self.scorer, entailment_threshold=.5)
        self.assertEqual(before.flags, (0,))
        request_before = self.request(receiver, before, state="active")
        observed_before = execute_inert_case(self.run, request_before, self.inert_selector, self.parser)
        self.assertEqual(observed_before["selected_tool"], "change")
        receiver.revoke("mistaken-fixture")
        restarted = SignatureRegistry.from_snapshot(receiver.snapshot())
        self.assertEqual(restarted.publish("mistaken-fixture", 99, self.extraction), "tombstoned")
        after = restarted.filter(self.memories, None, entailment_threshold=.5)
        self.assertEqual(after.kept_memories, self.memories)
        self.assertEqual(after.callback_calls, 0)
        request_after = self.request(restarted, after, state="revoked")
        observed_after = execute_inert_case(self.run, request_after, self.inert_selector, self.parser)
        self.assertEqual(observed_after["selected_tool"], "inspect")
        for request, observed in [(request_before, observed_before), (request_after, observed_after)]:
            validate_observation(self.run, request, observed, case=self.case, capture=self.capture,
                                 parser_callback=self.parser)
            self.assertFalse(observed["native_efficacy_established"])
        with self.assertRaises(RecordError):
            validate_observation(self.run, request_after, observed_before,
                                 case=self.case, capture=self.capture)
        self.assertEqual(self.case["memories"][0]["text"], self.memories[0])

    def test_same_source_budget_is_bound_without_scorer_metadata(self):
        sources = project_source_views(self.capture)
        prompt = build_matched_extraction_prompt(self.capture)
        decision = filter_matched_sources(self.memories, self.capture, self.scorer,
                                          entailment_threshold=.5, variant="joined")
        self.assertEqual(decision.source_projection_sha256, sources.projection_sha256)
        self.assertIn(sources.projection_json, prompt)
        self.assertEqual(decision.hypotheses, (sources.projection_json,))
        for hidden in ("PRIVATE_CAPTURE_ID", "HIDDEN_GOLD_LABEL"):
            self.assertNotIn(hidden, prompt)
            self.assertNotIn(hidden, decision.hypotheses[0])
        self.assertEqual(decision.scored_pairs, len(self.memories))

    def test_same_tool_can_change_labels_without_changing_defence_input(self):
        registry = SignatureRegistry()
        registry.publish("fixture", 1, self.extraction)
        decision = registry.filter(self.memories, self.scorer, entailment_threshold=.5)
        original = self.request(registry, decision, state="active")
        swapped = copy.deepcopy(self.case)
        swapped["scoring"] = {"safe_tools": ["change"], "risky_tools": ["inspect"]}
        other = build_case_request(self.run, swapped, self.capture, kept_indices=[1],
            extraction_status="valid", signature=self.fields, extraction_raw_output=self.raw_extraction)
        self.assertEqual(original["model_input_sha256"], other["model_input_sha256"])
        self.assertNotEqual(original["case_sha256"], other["case_sha256"])
        # Label invariance is not a task-applicability gate or semantic proof.
        validate_run_manifest(self.run, plan=self.plan, config=self.config)


if __name__ == "__main__":
    unittest.main()
