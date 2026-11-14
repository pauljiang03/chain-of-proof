"""Attempt chronology and explicit revisions never create proof or inferred causality."""
from copy import deepcopy
import json
import unittest

from agent.history import summarize_history, validate_revision


def proposal(fid, status="rejected", claim=None):
    return {"finding_id": fid, "status": status, "question": "Which event?",
            "claim": claim if claim is not None else {"searched": [3100]}}


def event(sequence, row=None, *, claim=None, revises=None, duplicate=False, outcome=None,
          error=None, tool="check"):
    result = None if row is None else {"finding_id": row["finding_id"], "status": row["status"]}
    if result is not None and duplicate:
        result["note"] = "already proposed as " + row["finding_id"]
    arguments = {"question": "Which event?", "claim": claim if claim is not None else (row or {}).get("claim")}
    if revises is not None:
        arguments["revises"] = revises
    outcome = outcome or ("error" if error else "rejected" if (row or {}).get("status") == "rejected" else "success")
    return {"schema_version": 1, "sequence": sequence, "call_id": f"call-{sequence}",
            "started_at": f"2026-11-14T22:00:{sequence:02d}+00:00",
            "completed_at": f"2026-11-14T22:00:{sequence:02d}.001000+00:00", "duration_ns": 1000000,
            "tool": tool, "arguments": arguments, "result": result, "result_sha256": "hash-only-not-verified-here",
            "success": outcome == "success", "outcome": outcome, "error": error,
            "finding_id": (row or {}).get("finding_id"), "previous_sha256": None, "event_sha256": "not-verified-here"}


class RevisionValidation(unittest.TestCase):
    def test_optional_revision_and_prior_refusal_are_valid(self):
        rows = [proposal("A001")]
        self.assertIsNone(validate_revision(None, rows))
        self.assertEqual(validate_revision("A001", rows, current_id="A002"), "A001")

    def test_unknown_self_forward_and_malformed_links_are_refused(self):
        rows = [proposal("A001"), proposal("A002"), proposal("A003")]
        for target in ("A002", "A003", "missing", "", 1, True, {}, "../A001"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_revision(target, rows, current_id="A002")

    def test_ids_do_not_define_chronology(self):
        self.assertEqual(validate_revision("Z999", [proposal("Z999")], current_id="A001"), "Z999")

    def test_conflicting_target_and_scope_are_refused(self):
        rows = [proposal("A001"), proposal("A001", "verified")]
        with self.assertRaisesRegex(ValueError, "conflicting"):
            validate_revision("A001", rows)
        rows = [dict(proposal("A001"), case_id="one"), dict(proposal("A002"), case_id="two")]
        with self.assertRaisesRegex(ValueError, "conflicting"):
            validate_revision("A001", rows)

    def test_identical_repeated_log_row_is_one_target(self):
        row = proposal("A001")
        self.assertEqual(validate_revision("A001", [row, deepcopy(row)]), "A001")

    def test_validator_is_pure(self):
        rows = [proposal("A001")]
        before = deepcopy(rows)
        validate_revision("A001", rows, current_id="A002")
        self.assertEqual(rows, before)


class ClaimHistory(unittest.TestCase):
    def test_refusal_then_explicit_accepted_revision(self):
        old = proposal("A001", claim={"usbConnected": [3100]})
        new = proposal("A002", "verified")
        history = summarize_history([old, new], [event(1, old), event(2, new, revises="A001")])
        self.assertEqual([a["status"] for a in history["attempts"]], ["refused", "accepted"])
        self.assertEqual(history["attempts"][1]["revision_status"], "valid")
        self.assertEqual(history["attempts"][1]["revises"], "A001")
        self.assertEqual(history["counts"]["explicit_revisions"], 1)
        self.assertEqual(history["coverage"]["matched_proposal_rows"], 2)
        self.assertFalse(history["coverage"]["complete"])

    def test_success_after_refusal_never_implies_revision(self):
        old, new = proposal("A001"), proposal("A002", "verified")
        history = summarize_history([old, new], [event(1, old), event(2, new)])
        self.assertEqual(history["counts"]["explicit_revisions"], 0)
        self.assertTrue(all(a["revises"] is None for a in history["attempts"]))

    def test_duplicate_is_separate_attempt_with_no_new_proof(self):
        row = proposal("A001", "verified")
        events = [event(1, row), event(2, row, duplicate=True)]
        history = summarize_history([row], events)
        self.assertEqual(len(history["attempts"]), 2)
        self.assertEqual(history["counts"]["accepted"], 1)
        self.assertEqual(history["counts"]["duplicate"], 1)
        duplicate = history["attempts"][1]
        self.assertEqual(duplicate["duplicate_of"], "A001")
        self.assertFalse(duplicate["new_proposal"])
        self.assertEqual(duplicate["proof_status"], "verified")

    def test_duplicate_refusal_with_explicit_link_is_not_repaired_claim(self):
        row = proposal("A001")
        history = summarize_history([row], [event(1, row), event(2, row, revises="A001", duplicate=True)])
        duplicate = history["attempts"][1]
        self.assertEqual((duplicate["status"], duplicate["proof_status"]), ("duplicate", "rejected"))
        self.assertEqual(duplicate["revision_status"], "valid")
        self.assertFalse(duplicate["new_proposal"])
        self.assertEqual(history["counts"]["accepted"], 0)

    def test_failed_and_malformed_attempts_without_proposals_are_retained(self):
        failed = event(1, error={"type": "RuntimeError"})
        malformed = event(2, claim="{", outcome="rejected")
        malformed["result"] = {"status": "rejected", "reason": "claim is not valid JSON"}
        history = summarize_history([], [failed, malformed])
        self.assertEqual([a["status"] for a in history["attempts"]], ["failed", "refused"])
        self.assertEqual(history["attempts"][0]["error"], "RuntimeError")
        self.assertIsNone(history["attempts"][1]["finding_id"])
        self.assertEqual(history["attempts"][1]["claim"], "{")

    def test_exception_payload_is_not_copied_into_error_field(self):
        failed = event(1, error={"type": "RuntimeError", "message": "SECRET TOKEN"})
        history = summarize_history([], [failed])
        self.assertNotIn("SECRET TOKEN", json.dumps(history))

    def test_hash_only_result_and_missing_arguments_are_unknown(self):
        row = proposal("A001", "verified")
        hashed = event(1, row)
        hashed["result"] = None
        missing = event(2, row)
        missing["arguments"] = None
        history = summarize_history([row], [hashed, missing])
        self.assertEqual([a["status"] for a in history["attempts"]], ["unknown", "unknown"])
        self.assertTrue(all(a["problems"] for a in history["attempts"]))
        self.assertEqual(history["attempts"][1]["revision_status"], "unknown")

    def test_self_forward_and_unknown_revision_attempts_are_diagnostic(self):
        old, new = proposal("A001"), proposal("A002", "verified")
        for target in ("A001", "A002", "unknown", 17):
            first = event(1, old)
            first["arguments"]["revises"] = target
            history = summarize_history([old, new], [first, event(2, new)])
            self.assertEqual(history["attempts"][0]["revision_status"], "invalid")
            self.assertEqual(history["counts"]["explicit_revisions"], 0)

    def test_partial_audit_does_not_invent_positions_for_legacy_rows(self):
        old, new = proposal("A001"), proposal("A002", "verified")
        history = summarize_history([old, new], [event(7, new, revises="A001")])
        self.assertEqual([a["finding_id"] for a in history["attempts"]], ["A002"])
        self.assertEqual([a["finding_id"] for a in history["unmatched_proposals"]], ["A001"])
        self.assertEqual(history["attempts"][0]["revision_status"], "valid")
        self.assertEqual(history["counts"]["attempts"], 1)
        self.assertEqual(history["coverage"]["unmatched_proposal_rows"], 1)
        self.assertIn("unknown", history["coverage"]["unmatched_proposal_placement"])
        self.assertTrue(history["problems"])

    def test_legacy_order_and_unknown_times_are_preserved(self):
        rows = [dict(proposal("Z999"), checked_in_ms=12, revises="A001"), proposal("A001", "verified")]
        history = summarize_history(rows)
        self.assertEqual([a["finding_id"] for a in history["attempts"]], ["Z999", "A001"])
        self.assertTrue(all(a["started_at"] is None and a["completed_at"] is None for a in history["attempts"]))
        self.assertTrue(all(a["revises"] is None for a in history["attempts"]))
        self.assertEqual(history["coverage"]["attempts_without_timestamps"], 2)
        self.assertEqual(history["coverage"]["completeness"], "recorded_events_only")

    def test_audit_only_can_link_an_explicit_prior_proposal(self):
        old, new = proposal("A001"), proposal("A002", "verified")
        history = summarize_history(None, [event(1, old), event(2, new, revises="A001")])
        self.assertEqual(history["attempts"][1]["revision_status"], "valid")
        self.assertIsNone(history["coverage"]["proposal_rows"])

    def test_invalid_integrity_is_visible_and_passed_is_not_completeness(self):
        row = proposal("A001")
        for passed in (False, True):
            history = summarize_history([row], [event(1, row)], {"passed": passed})
            self.assertEqual(history["audit_integrity"]["status"], "passed" if passed else "failed")
            self.assertFalse(history["coverage"]["complete"])
            self.assertEqual(history["coverage"]["interrupted_calls"], "unmeasured")

    def test_conflicting_finding_binding_is_unknown(self):
        row = proposal("A001", "verified")
        audit = event(1, row)
        audit["finding_id"] = "A002"
        history = summarize_history([row], [audit])
        self.assertEqual(history["attempts"][0]["status"], "unknown")
        self.assertTrue(history["attempts"][0]["problems"])

    def test_noncheck_events_do_not_count_as_attempts(self):
        row = proposal("A001")
        history = summarize_history([row], [event(1, tool="sql"), event(2, row)])
        self.assertEqual(history["counts"]["attempts"], 1)
        self.assertEqual(history["attempts"][0]["audit_sequence"], 2)

    def test_unavailable_logs_are_not_zero_observed_activity(self):
        history = summarize_history(None)
        self.assertFalse(history["available"])
        self.assertIsNone(history["counts"]["attempts"])
        empty = summarize_history([], [])
        self.assertTrue(empty["available"])
        self.assertEqual(empty["counts"]["attempts"], 0)

    def test_helpers_preserve_inputs_and_json_serializability(self):
        rows = [proposal("A001")]
        events = [event(1, rows[0])]
        original = deepcopy((rows, events))
        json.dumps(summarize_history(rows, events), allow_nan=False)
        self.assertEqual((rows, events), original)


if __name__ == "__main__":
    unittest.main()
