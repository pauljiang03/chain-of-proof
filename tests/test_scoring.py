"""The matcher the scorer and the memory baseline share, on hand-made rows."""
import unittest

from eval import memory_baseline, score


def row(kind, obj, aux="", utc="2015-03-24T14:00:00", res=1, **prov):
    return {"id": 1, "kind": kind, "t": score._us(utc), "res": res, "obj_text": obj,
            "aux_text": aux, "prov": prov}


class Matchers(unittest.TestCase):
    def test_names_match_exactly_by_ending_or_by_a_distinctive_part(self):
        r = row("programInstalled", "Google Drive (x86)", "1.20")
        self.assertTrue(score.same_entity({"kind": "programInstalled", "obj_contains": "google drive"}, r))
        self.assertFalse(score.same_entity({"kind": "programInstalled", "obj": "Google Drive"}, r))
        self.assertTrue(score.same_entity({"kind": "programInstalled", "obj_contains": "drive",
                                           "aux_contains": "1.2"}, r))
        self.assertFalse(score.same_entity({"kind": "programRun", "obj_contains": "drive"}, r))

    def test_a_time_matches_within_tolerance_or_within_the_rows_own_uncertainty(self):
        e = {"kind": "programInstalled", "utc": "2015-03-24T14:00:01"}
        self.assertEqual(score.time_match(e, row("programInstalled", "x"), 2), "tolerance")
        late = row("programInstalled", "x", utc="2015-03-24T00:00:00", res=86_400_000_000)
        self.assertEqual(score.time_match(e, late, 2), "row uncertainty")
        self.assertIsNone(score.time_match(e, row("programInstalled", "x", utc="2015-03-24T00:00:00"), 2))

    def test_a_date_only_answer_is_compared_in_the_cases_local_zone(self):
        e = {"kind": "programInstalled", "local_day": "2015-03-23"}
        # 02:00 UTC on the 24th is 22:00 on the 23rd in New York
        self.assertEqual(score.time_match(e, row("programInstalled", "x", utc="2015-03-24T02:00:00"), 2), "day")
        self.assertIsNone(score.time_match(e, row("programInstalled", "x", utc="2015-03-24T05:00:00"), 2))

    def test_an_answer_no_kind_can_state_is_counted_not_dropped(self):
        ref = {"tolerance_s": 2, "items": [
            {"id": "Q1-01", "question": 1, "expect": None, "book": "closed"},
            {"id": "Q10-01", "question": 10, "book": "closed",
             "expect": {"kind": "programInstalled", "obj_contains": "drive"}}]}
        out = score.score_extraction(ref, [row("programInstalled", "Google Drive")])
        self.assertEqual([o["status"] for o in out], ["not_expressible", "match"])
        self.assertEqual(out[1]["within"], "untimed")


class Memory(unittest.TestCase):
    def test_remembered_rows_are_scored_for_the_name_and_for_the_time(self):
        answer = ('{"kind": "webSearch", "obj": "anti-forensics", "aux": "", "utc": null, "sure": false}\n'
                  'some prose the model added\n'
                  '{"kind": "usbInsert", "obj": "ABC", "aux": "", "utc": "2015-03-24T13:58:32", "sure": true}\n')
        rows = memory_baseline.parse(answer)
        self.assertEqual(len(rows), 2)
        ref = {"tolerance_s": 2, "items": [
            {"id": "Q16-01", "question": 16, "expect": {"kind": "webSearch", "obj": "anti-forensics",
                                                        "utc": "2015-03-23T18:17:14"}},
            {"id": "Q22-01", "question": 22, "expect": {"kind": "usbInsert", "obj": "abc",
                                                        "utc": "2015-03-24T13:58:33"}},
            {"id": "Q33-01", "question": 33, "expect": {"kind": "cdBurn", "utc": "2015-03-24T19:47:47"}}]}
        result = memory_baseline.score(ref, rows)
        self.assertEqual(result["totals"], {"rows": 2, "entity": 2, "timed": 2, "full": 1})


if __name__ == "__main__":
    unittest.main()
