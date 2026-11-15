"""Source/contract regressions; copied-key submissions are synthetic, not scores."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from agent.answer_projection import catalog
from agent.answer_requirements import KEY, check, inspect
from eval import benchmark
from eval.hacking_case.validate import HERE, validate


def load(name):
    return json.loads((HERE / name).read_text())


def synthetic_submission(reference, *, from_end=False):
    rows = []
    for question in reference["questions"]:
        answer = deepcopy(question["expected"])
        for path, rule in question["match"].get("list_rules", {}).items():
            key = path.removeprefix("/")
            pool = answer[key]
            answer[key] = pool[-rule["count"]:] if from_end else pool[:rule["count"]]
        rows.append({"question_id": question["id"], "status": "answered", "answer": answer})
    return {"schema_version": 2, "case_id": reference["case_id"], "answers": rows}


class HackingReference(unittest.TestCase):
    def setUp(self):
        self.reference = load("reference.json")
        self.public = load("questions.json")

    def test_all_official_questions_and_every_answer_leaf_have_source_bindings(self):
        result = validate(self.reference, self.public)
        self.assertTrue(result["passed"])
        self.assertEqual(result["question_count"], 31)
        self.assertEqual(result["annotated_answer_leaves"], 38)
        self.assertFalse(result["system_accuracy_measured"])
        self.assertFalse(result["independent_semantic_review"])
        self.assertEqual({q["evaluation_status"] for q in result["questions"]}, {"scorable"})

    def test_synthetic_contract_self_check_accepts_different_requested_subsets(self):
        for from_end in (False, True):
            result = benchmark.score(self.reference, synthetic_submission(self.reference, from_end=from_end))
            self.assertEqual(result["question_counts"]["fully_correct"], 31)
            self.assertTrue(result["perfect_submission"])
            self.assertEqual(result["atomic"]["missing"], 0)
            self.assertEqual(result["atomic"]["wrong"], 0)

    def test_unrequested_pool_members_are_not_missing_but_shotgun_answers_are_extra(self):
        correct = synthetic_submission(self.reference)
        for qid, field, count in ((16, "programs", 6), (20, "newsgroups", 5), (22, "channels", 3)):
            with self.subTest(question=qid):
                result = benchmark.score(self.reference, correct)
                self.assertEqual(result["questions"][qid - 1]["atomic"]["true_positive"], count)
                changed = deepcopy(correct)
                changed["answers"][qid - 1]["answer"][field] = deepcopy(self.reference["questions"][qid - 1]["expected"][field])
                result = benchmark.score(self.reference, changed)
                self.assertNotEqual(result["questions"][qid - 1]["status"], "fully_correct")
                self.assertGreater(result["questions"][qid - 1]["atomic"]["wrong"], 0)

    def test_duplicate_subset_items_do_not_satisfy_distinct_required_examples(self):
        submitted = synthetic_submission(self.reference)
        values = submitted["answers"][15]["answer"]["programs"]
        values[-1] = values[0]
        result = benchmark.score(self.reference, submitted)
        self.assertGreater(result["questions"][15]["atomic"]["missing"], 0)
        self.assertGreater(result["questions"][15]["atomic"]["wrong"], 0)

    def test_omission_false_and_unknown_remain_distinct(self):
        submitted = synthetic_submission(self.reference)
        submitted["answers"][30]["answer"]["viruses_found"] = not submitted["answers"][30]["answer"]["viruses_found"]
        result = benchmark.score(self.reference, submitted)
        self.assertEqual(result["questions"][30]["status"], "incorrect")
        self.assertEqual(result["questions"][30]["atomic"]["wrong"], 1)
        submitted["answers"][30] = {"question_id": "Q31", "status": "unknown"}
        result = benchmark.score(self.reference, submitted)
        self.assertEqual(result["questions"][30]["status"], "unanswered")
        self.assertEqual(result["questions"][30]["atomic"]["wrong"], 0)

    def test_display_times_accept_same_instant_but_no_unpublished_tolerance(self):
        submitted = synthetic_submission(self.reference)
        for index, field in ((2, "installed_at"), (7, "shutdown_at")):
            value = datetime.fromisoformat(submitted["answers"][index]["answer"][field])
            submitted["answers"][index]["answer"][field] = value.astimezone(timezone.utc).isoformat()
        self.assertTrue(benchmark.score(self.reference, submitted)["perfect_submission"])
        value = datetime.fromisoformat(submitted["answers"][2]["answer"]["installed_at"])
        submitted["answers"][2]["answer"]["installed_at"] = (value + timedelta(seconds=1)).isoformat()
        self.assertEqual(benchmark.score(self.reference, submitted)["questions"][2]["status"], "incorrect")

    def test_appendices_do_not_change_agreement_but_unrequested_answer_fields_do(self):
        submitted = synthetic_submission(self.reference)
        baseline = benchmark.score(self.reference, submitted)
        submitted["appendices"] = {"evidence": [{"synthetic_test_only": True}]}
        self.assertEqual(benchmark.score(self.reference, submitted)["atomic"], baseline["atomic"])
        submitted["answers"][30]["answer"]["unrequested_assertion"] = True
        self.assertEqual(benchmark.score(self.reference, submitted)["questions"][30]["atomic"]["wrong"], 1)

    def test_wrong_source_value_or_conversion_is_detected_without_source_repair(self):
        for index, field, value in ((1, "operating_system", "SYNTHETIC_WRONG_VALUE"),
                                    (2, "installed_at", "2099-01-01T00:00:00+00:00")):
            changed = deepcopy(self.reference)
            changed["questions"][index]["expected"][field] = value
            with self.assertRaisesRegex(ValueError, "source"):
                validate(changed, self.public)

    def test_source_snapshot_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "hacking_case"
            shutil.copytree(HERE, package, ignore=shutil.ignore_patterns("__pycache__"))
            path = package / "sources/TestAnswers.pdf"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "source snapshot"):
                validate(package=package)

    def test_private_key_value_cannot_be_inserted_in_public_instructions(self):
        changed = deepcopy(self.public)
        changed["instructions"].append(self.reference["questions"][0]["expected"]["image_hash"]["digest"])
        with self.assertRaisesRegex(ValueError, "leaked"):
            validate(self.reference, changed)

    def test_missing_question_or_requirement_cannot_silently_shrink_contract(self):
        changed = deepcopy(self.public)
        changed["questions"].pop()
        with self.assertRaisesRegex(ValueError, "31"):
            validate(self.reference, changed)
        changed = deepcopy(self.public)
        del changed["questions"][0]["answer_schema"]["properties"]["image_hash"]["properties"]["digest"][KEY]
        with self.assertRaisesRegex(ValueError, "unannotated"):
            validate(self.reference, changed)

    def test_stronger_semantics_remain_required_even_without_catalog_support(self):
        forms = catalog()["forms"]
        unsupported = set()
        for question in self.public["questions"]:
            result = inspect(question["answer_schema"], forms)
            self.assertFalse(any(row["status"] == "invalid" for row in result["requirements"]))
            if any(row["status"] == "no_catalog_support" for row in result["requirements"]):
                unsupported.add(question["id"])
        self.assertEqual(unsupported, {"Q10", "Q15", "Q24"})
        requirement = self.public["questions"][9]["answer_schema"]["properties"]["account_name"][KEY]
        self.assertEqual(check(requirement, "accountRecorded", "account", "account")["status"], "incompatible")
        requirement = self.public["questions"][15]["answer_schema"]["properties"]["programs"]["items"][KEY]
        self.assertEqual(check(requirement, "programRan", "program", "program")["status"], "incompatible")
        self.assertEqual(check(requirement, "programInstalledAt", "program", "program")["status"], "compatible")

    def test_computed_hash_can_be_partial_without_inventing_acquisition_agreement(self):
        from checker.catalog import ROLES
        properties = self.public["questions"][0]["answer_schema"]["properties"]
        algorithm = properties["image_hash"]["properties"]["algorithm"][KEY]
        digest = properties["image_hash"]["properties"]["digest"][KEY]
        comparison = properties["acquisition_verification_match"][KEY]
        self.assertEqual(check(algorithm, "attributeRecorded", "algorithm", "asserted_digest_algorithm")["status"], "compatible")
        logical = ROLES["image.logical.md5"].semantic_type
        retained = ROLES["image.acquisition.md5"].semantic_type
        self.assertEqual(check(digest, "attributeRecorded", "value", logical)["status"], "compatible")
        self.assertEqual(check(digest, "attributeRecorded", "value", retained)["status"], "incompatible")
        self.assertEqual(check(comparison, "attributeRecorded", "value", "recorded_attribute_scanner_detections_found_boolean")["status"], "incompatible")


if __name__ == "__main__":
    unittest.main()
