"""Requested-size example lists use a declared pool without a model judge."""
import unittest
from copy import deepcopy

from eval.benchmark import score, validate_reference


class SubsetContracts(unittest.TestCase):
    def setUp(self):
        self.ref = {"schema_version": 2, "case_id": "subset-test", "questions": [{
            "id": "Q1", "prompt": "Give two supported examples.",
            "expected": {"examples": ["alpha", "beta", "gamma"]},
            "match": {"strings": "casefold", "list_rules": {"/examples": {"mode": "subset", "count": 2}}}}]}

    def result(self, value=None, *, unanswered=False):
        answers = [] if unanswered else [{"question_id": "Q1", "status": "answered", "answer": value}]
        return score(self.ref, {"schema_version": 2, "case_id": "subset-test", "answers": answers})

    def test_any_requested_size_subset_earns_full_credit(self):
        for items in (["alpha", "beta"], ["gamma", "ALPHA"], ["beta", "gamma"]):
            result = self.result({"examples": items})
            self.assertTrue(result["perfect_submission"])
            self.assertEqual(result["atomic"]["scorable_reference_atoms"], 2)
            self.assertEqual(result["atomic"]["true_positive"], 2)

    def test_missing_subset_uses_requested_count_not_pool_size(self):
        for value, unanswered in ((None, True), ({}, False), ({"examples": []}, False), ([], False)):
            result = self.result(value, unanswered=unanswered)
            self.assertEqual(result["atomic"]["missing"], 2)
            self.assertEqual(result["atomic"]["scorable_reference_atoms"], 2)
        one = self.result({"examples": ["gamma"]})
        self.assertEqual(one["questions"][0]["status"], "partial")
        self.assertEqual(one["atomic"]["missing"], 1)

    def test_duplicates_unknown_and_shotgun_answers_are_not_full_credit(self):
        for items, matched, wrong in ((["alpha", "ALPHA"], 1, 1),
                                      (["alpha", "invented"], 1, 1),
                                      (["alpha", "beta", "gamma"], 2, 1),
                                      (["invented"], 0, 1)):
            result = self.result({"examples": items})
            self.assertFalse(result["perfect_submission"])
            self.assertEqual(result["atomic"]["true_positive"], matched)
            self.assertEqual(result["atomic"]["wrong"], wrong)
            self.assertEqual(result["atomic"]["scorable_reference_atoms"], 2)

    def test_alias_does_not_create_a_second_accepted_member(self):
        self.ref["questions"][0]["match"]["string_aliases"] = {"/examples/*": [["alpha", "first"]]}
        result = self.result({"examples": ["first", "ALPHA"]})
        self.assertEqual(result["atomic"]["true_positive"], 1)
        self.assertEqual(result["atomic"]["wrong"], 1)

    def test_shared_alias_cannot_be_repeated_to_cover_distinct_pool_entries(self):
        self.ref["questions"][0]["match"]["string_aliases"] = {
            "/examples/*": [["alpha", "shared"], ["beta", "shared"]]}
        result = self.result({"examples": ["shared", "SHARED"]})
        self.assertFalse(result["perfect_submission"])
        self.assertEqual(result["atomic"]["true_positive"], 1)
        self.assertEqual(result["atomic"]["wrong"], 1)

    def test_invalid_contracts_fail_closed(self):
        for rule in ({"mode": "subset", "count": 0}, {"mode": "subset", "count": True},
                     {"mode": "subset", "count": 4}, {"mode": "anything", "count": 2}):
            ref = deepcopy(self.ref)
            ref["questions"][0]["match"]["list_rules"]["/examples"] = rule
            with self.assertRaises(ValueError):
                validate_reference(ref)
        for pool in (["alpha", "ALPHA"], [{"name": "alpha"}, {"name": "beta"}]):
            ref = deepcopy(self.ref)
            ref["questions"][0]["expected"]["examples"] = pool
            with self.assertRaises(ValueError):
                validate_reference(ref)
        self.ref["questions"][0]["match"]["list_rules"] = {"/typo": {"mode": "subset", "count": 2}}
        with self.assertRaises(ValueError):
            validate_reference(self.ref)

    def test_no_rule_preserves_exact_list_matching(self):
        del self.ref["questions"][0]["match"]["list_rules"]
        result = self.result({"examples": ["alpha", "beta"]})
        self.assertFalse(result["perfect_submission"])
        self.assertEqual(result["atomic"]["missing"], 1)

    def test_overlapping_prefix_pools_cannot_credit_the_same_answer_twice(self):
        for pool in (["al", "alpha"], ["alpha", "al"]):
            self.ref["questions"][0]["expected"]["examples"] = pool
            self.ref["questions"][0]["match"]["strings"] = "prefix"
            with self.assertRaises(ValueError):
                self.result({"examples": ["alpha", "alpha"]})


if __name__ == "__main__":
    unittest.main()
