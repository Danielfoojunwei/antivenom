"""Synthetic operational checks; not empirical clean recovery or a network."""
import copy
import hashlib
import json
import unittest
from dataclasses import replace

from antivenom.signature_lifecycle import MAX_REVISION, SignatureRegistry
from antivenom.tool_policy_signature import CaptureView, parse_extraction


def extraction(name="alpha", *, capture_name="capture-alpha"):
    capture = CaptureView(capture_name, "Synthetic source " + capture_name,
                          "Synthetic stored " + capture_name)
    return parse_extraction(capture, json.dumps({
        "asserted_condition": "synthetic condition " + name,
        "asserted_rationale": "synthetic rationale " + name,
        "induced_tool_preference": "synthetic preference " + name,
        "scope_limitations": "synthetic scope only " + name,
    }))


def rehash(snapshot):
    """Rebind a synthetic altered snapshot to test replay beyond hash checks."""
    canonical = lambda obj: json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                       separators=(",", ":"), allow_nan=False)
    sha = lambda obj: hashlib.sha256(canonical(obj).encode()).hexdigest()
    content = {key: snapshot[key] for key in ("schema", "active", "tombstones")}
    snapshot["content_sha256"] = sha(content)
    snapshot["history_sha256"] = sha(snapshot["history"])
    snapshot["snapshot_sha256"] = sha({k: v for k, v in snapshot.items() if k != "snapshot_sha256"})
    return snapshot


class SignatureLifecycleTests(unittest.TestCase):
    def test_publication_revision_duplicate_and_stale_ordering(self):
        registry = SignatureRegistry()
        first, newer = extraction(), extraction("revised")
        self.assertEqual(registry.publish("incident-a", 1, first), "published")
        content = registry.content_sha256
        self.assertEqual(registry.publish("incident-a", 1, first), "duplicate")
        self.assertEqual(registry.content_sha256, content)
        self.assertEqual(registry.publish("incident-a", 2, newer), "updated")
        content = registry.content_sha256
        self.assertEqual(registry.publish("incident-a", 1, first), "stale")
        self.assertEqual(registry.content_sha256, content)
        self.assertEqual(registry.active_ids, ("incident-a",))

    def test_conflicting_revision_and_different_capture_do_not_mutate_state(self):
        registry = SignatureRegistry()
        registry.publish("incident-a", 1, extraction())
        before = registry.snapshot()
        with self.assertRaisesRegex(ValueError, "same revision"):
            registry.publish("incident-a", 1, extraction("different"))
        self.assertEqual(registry.snapshot(), before)
        with self.assertRaisesRegex(ValueError, "new logical ID"):
            registry.publish("incident-a", 2, extraction(capture_name="different-capture"))
        self.assertEqual(registry.snapshot(), before)

    def test_positive_json_integer_revisions_are_required(self):
        registry = SignatureRegistry()
        for revision in (0, -1, True, 1., "1", None, MAX_REVISION + 1):
            with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, "positive"):
                registry.publish("a", revision, extraction())
        self.assertEqual(registry.active_ids, ())
        for identifier in ("", " ", None, 2):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                registry.publish(identifier, 1, extraction())

    def test_tombstone_arriving_first_blocks_delayed_and_higher_revisions(self):
        registry = SignatureRegistry()
        self.assertEqual(registry.revoke("incident-a"), "revoked")
        self.assertEqual(registry.publish("incident-a", 1, extraction()), "tombstoned")
        self.assertEqual(registry.publish("incident-a", 900, extraction("revised")), "tombstoned")
        self.assertEqual(registry.publish("incident-a", 901,
            extraction(capture_name="different-capture")), "tombstoned")
        self.assertEqual(registry.revoke("incident-a"), "already_revoked")
        self.assertEqual(registry.active_ids, ())
        self.assertEqual(registry.tombstone_ids, ("incident-a",))
        self.assertEqual(registry.publish("new-incident", 1,
            extraction(capture_name="different-capture")), "published")

    def test_two_receivers_diverge_temporarily_then_converge_after_revocation(self):
        left, right = SignatureRegistry(), SignatureRegistry()
        item = extraction()
        left.publish("a", 1, item)
        right.revoke("a")
        self.assertNotEqual(left.content_sha256, right.content_sha256)
        left.revoke("a")
        right.publish("a", 1, item)
        right.publish("a", 7, extraction("late revision"))
        self.assertEqual(left.active_ids, right.active_ids)
        self.assertEqual(left.tombstone_ids, right.tombstone_ids)
        self.assertEqual(left.content_sha256, right.content_sha256)
        self.assertNotEqual(left.snapshot()["history_sha256"], right.snapshot()["history_sha256"])

    def test_snapshot_roundtrip_replays_exact_history_and_restart_keeps_tombstone(self):
        registry = SignatureRegistry()
        registry.publish("b", 1, extraction("beta", capture_name="capture-beta"))
        registry.publish("a", 1, extraction())
        registry.publish("a", 1, extraction())
        registry.revoke("a")
        portable = json.loads(json.dumps(registry.snapshot()))
        restored = SignatureRegistry.from_snapshot(portable)
        self.assertEqual(restored.snapshot(), registry.snapshot())
        self.assertEqual(restored.publish("a", 100, extraction()), "tombstoned")
        self.assertEqual(restored.active_ids, ("b",))
        portable["active"][0]["logical_id"] = "changed copy"
        self.assertEqual(registry.active_ids, ("b",))

    def test_snapshot_detects_tampering_and_inconsistent_rehashed_history(self):
        registry = SignatureRegistry()
        registry.publish("a", 1, extraction())
        changed = copy.deepcopy(registry.snapshot())
        changed["active"][0]["revision"] = 2
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            SignatureRegistry.from_snapshot(changed)
        with self.assertRaisesRegex(ValueError, "replay"):
            SignatureRegistry.from_snapshot(rehash(changed))
        changed = copy.deepcopy(registry.snapshot())
        changed["history"][0]["outcome"] = "updated"
        with self.assertRaisesRegex(ValueError, "outcome"):
            SignatureRegistry.from_snapshot(rehash(changed))

    def test_malformed_or_rebound_extraction_cannot_publish(self):
        registry = SignatureRegistry()
        bad = parse_extraction(CaptureView("a", "synthetic raw"), "{malformed")
        with self.assertRaisesRegex(ValueError, "malformed"):
            registry.publish("a", 1, bad)
        good = extraction()
        rebound = replace(good, raw_output_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            registry.publish("a", 1, rebound)
        rebound = replace(good, signature=extraction("different").signature)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            registry.publish("a", 1, rebound)
        self.assertEqual(registry.active_ids, ())
        self.assertEqual(registry.snapshot()["history"], [])

    def test_no_active_signature_is_exact_passthrough_without_callback(self):
        registry = SignatureRegistry()
        original = ["A ", "B", "B"]
        decision = registry.filter(original,
            lambda _: self.fail("passthrough invoked callback"), entailment_threshold=.5)
        self.assertEqual(decision.kept_memories, tuple(original))
        self.assertEqual(decision.flags, ())
        self.assertEqual(decision.input_hashes, decision.kept_hashes)
        self.assertEqual(decision.callback_calls, 0)
        self.assertEqual(decision.scored_pairs, 0)
        self.assertEqual(decision.status, "no_active_signatures_passthrough")

    def test_union_scores_every_active_signature_against_original_evidence(self):
        registry = SignatureRegistry()
        registry.publish("z", 1, extraction("beta", capture_name="capture-beta"))
        registry.publish("a", 2, extraction())
        original = ["first", "second", "third"]
        seen = []
        def scorer(pairs):
            seen.extend(pairs)
            return [.9, .1, .1, .1, .8, .1]
        decision = registry.filter(original, scorer, entailment_threshold=.5)
        self.assertEqual([memory for memory, _ in seen], original + original)
        self.assertEqual(decision.active_signature_ids, ("a", "z"))
        self.assertEqual(decision.per_signature[0].flags, (0,))
        self.assertEqual(decision.per_signature[1].flags, (1,))
        self.assertEqual(decision.flags, (0, 1))
        self.assertEqual(decision.kept_memories, ("third",))
        self.assertEqual(decision.callback_calls, 1)
        self.assertEqual(decision.scored_pairs, 6)
        self.assertEqual(original, ["first", "second", "third"])

    def test_revoking_one_preserves_another_signature_and_original_context(self):
        registry = SignatureRegistry()
        registry.publish("a", 1, extraction())
        registry.publish("b", 1, extraction("beta", capture_name="capture-beta"))
        original = ["first", "second", "third"]
        both = registry.filter(original, lambda _: [.9, .1, .1, .1, .9, .1], entailment_threshold=.5)
        self.assertEqual(both.kept_memories, ("third",))
        registry.revoke("a")
        seen = []
        def only_b(pairs):
            seen.extend(pairs)
            return [.1, .9, .1]
        after = registry.filter(original, only_b, entailment_threshold=.5)
        self.assertEqual([text for text, _ in seen], original)
        self.assertEqual(after.flags, (1,))
        self.assertEqual(after.kept_memories, ("first", "third"))

    def test_mock_decision_recovers_after_mistaken_signature_revoked_software_only(self):
        registry = SignatureRegistry()
        original = ["synthetic legitimate support", "other synthetic memory"]
        mock_reader = lambda context: "fixture-success" if original[0] in context else "fixture-failure"
        self.assertEqual(mock_reader(original), "fixture-success")
        registry.publish("mistaken", 1, extraction())
        filtered = registry.filter(original, lambda _: [.9, .1], entailment_threshold=.5)
        self.assertEqual(mock_reader(filtered.kept_memories), "fixture-failure")
        registry.revoke("mistaken")
        restored = registry.filter(original, entailment_threshold=.5)
        self.assertEqual(restored.kept_memories, tuple(original))
        self.assertEqual(mock_reader(restored.kept_memories), "fixture-success")
        self.assertEqual(restored.callback_calls, 0)

    def test_empty_context_and_malformed_scores_do_not_retry(self):
        registry = SignatureRegistry()
        registry.publish("a", 1, extraction())
        empty = registry.filter([], lambda _: self.fail("empty context scored"), entailment_threshold=.5)
        self.assertEqual(empty.callback_calls, 0)
        self.assertEqual(empty.per_signature[0].scores, ())
        for values in ([], [True], [float("nan")], [1.1], [".5"], None):
            calls = []
            def scorer(pairs):
                calls.append(pairs)
                return values
            with self.subTest(values=values), self.assertRaises(ValueError):
                registry.filter(["actual memory"], scorer, entailment_threshold=.5)
            self.assertEqual(len(calls), 1)
        with self.assertRaises(ValueError):
            registry.filter(["actual memory"], entailment_threshold=.5)

    def test_inflight_decision_is_bound_to_call_entry_state_not_later_revocation(self):
        registry = SignatureRegistry()
        registry.publish("a", 1, extraction())
        before = registry.content_sha256
        def revoke_during_scoring(pairs):
            registry.revoke("a")
            return [.9]
        decision = registry.filter(["original evidence"], revoke_during_scoring,
                                   entailment_threshold=.5)
        self.assertEqual(decision.registry_content_sha256, before)
        self.assertNotEqual(decision.registry_content_sha256, registry.content_sha256)
        self.assertEqual(decision.active_signature_ids, ("a",))
        self.assertEqual(decision.flags, (0,))
        next_decision = registry.filter(["original evidence"], entailment_threshold=.5)
        self.assertEqual(next_decision.kept_memories, ("original evidence",))
        self.assertEqual(next_decision.callback_calls, 0)


if __name__ == "__main__":
    unittest.main()
