"""Case context, scoring boundaries and run preservation without model API calls."""
import contextlib
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agent import run
from agent.brief import BRIEF, investigator_brief
from agent.case import LEGACY_NAME, read_profile, select_case


class CaseProfiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.facts = self.root / "other.json"
        self.write_facts(self.facts, {"case": "Missing Recipe", "pc": {"time_zone": "America/Los_Angeles"}})
        self.profile = self.root / "public.json"
        self.profile.write_text(json.dumps({
            "name": "Missing Recipe",
            "brief": "A recipe disappeared from a workstation. Establish what the records support.",
            "questions": ["Which recipe files were accessed?", "Which accounts appear in the records?"],
            "time_zone": "America/Los_Angeles",
        }))

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def write_facts(path, meta):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"_meta": meta, "strings": {}, "facts": []}))

    @staticmethod
    def finished(*args, **kwargs):
        return {"summary": "No relevant findings.", "turns": 1, "tool_calls": 0,
                "seconds": 0, "ended": "success"}

    def assert_no_legacy_context(self, prompt):
        for value in ("Iaman", "informant", "Spy Conspirator", "RM#1", "RM#2", "RM#3",
                      "New York", "America/New_York", "confidential files", "security checkpoint"):
            self.assertNotIn(value, prompt)
        for kind in ("fileRemoved", "fileCreationRecorded", "volumeRecorded"):
            self.assertIn(kind, prompt)
        self.assertIn("do not by themselves imply a reformat", prompt)

    def call_main(self, argv):
        with patch.object(run, "ROOT", self.root), \
             patch.object(run, "run_claude_code", side_effect=self.finished) as claude, \
             patch.object(run, "run_deepagents", side_effect=self.finished) as deep, \
             patch.object(run.scorer, "main", return_value=0) as score, \
             contextlib.redirect_stdout(io.StringIO()):
            result = run.main(argv)
        return result, claude, deep, score

    def test_metadata_and_missing_metadata_do_not_inherit_case_assumptions(self):
        profile, source = select_case(self.facts)
        self.assertEqual((profile.name, profile.time_zone, source),
                         ("Missing Recipe", "America/Los_Angeles", "metadata"))
        prompt = investigator_brief(profile)
        self.assertIn("America/Los_Angeles", prompt)
        self.assert_no_legacy_context(prompt)
        self.write_facts(self.facts, {})
        profile, source = select_case(self.facts)
        self.assertIsNone(profile.time_zone)
        self.assertEqual(source, "generic")
        self.assertIn("No local time zone is supplied", investigator_brief(profile))
        self.assert_no_legacy_context(investigator_brief(profile))

    def test_both_backends_receive_selected_public_context_without_auto_scoring(self):
        for backend in ("claude-code", "deepagents"):
            with self.subTest(backend=backend):
                result, claude, deep, score = self.call_main([
                    "--facts", str(self.facts), "--case-profile", str(self.profile),
                    "--backend", backend, "--name", f"dev/{backend}",
                ])
                self.assertEqual(result, 0)
                selected = claude if backend == "claude-code" else deep
                prompt = selected.call_args.kwargs["prompt"]
                self.assertIn("Which recipe files were accessed?", prompt)
                self.assertIn("America/Los_Angeles", prompt)
                self.assert_no_legacy_context(prompt)
                score.assert_not_called()
                directory = self.root / "runs" / "dev" / backend
                bundle = json.loads((directory / "run.json").read_text())
                self.assertEqual(bundle["case"]["name"], "Missing Recipe")
                self.assertEqual(bundle["case"]["time_zone"], "America/Los_Angeles")
                self.assertEqual((directory / "prompt.md").read_text(), prompt)
                self.assertFalse((directory / "results.json").exists())

    def test_nondefault_evidence_never_implicitly_scores(self):
        _, claude, _, score = self.call_main(["--facts", str(self.facts), "--name", "generic"])
        self.assert_no_legacy_context(claude.call_args.kwargs["prompt"])
        score.assert_not_called()

    def test_original_default_remains_compatible_but_explicit_profile_opts_out(self):
        original = self.root / "evidence" / "case_facts.json"
        self.write_facts(original, {"case": LEGACY_NAME, "pc": {"time_zone": "America/New_York"}})
        _, claude, _, score = self.call_main(["--name", "original"])
        self.assertEqual(claude.call_args.kwargs["prompt"], BRIEF)
        score.assert_called_once()
        self.assertNotIn("--reference", score.call_args.args[0])
        _, claude, _, score = self.call_main([
            "--name", "profile-on-original", "--case-profile", str(self.profile)])
        self.assert_no_legacy_context(claude.call_args.kwargs["prompt"])
        score.assert_not_called()
        _, _, _, score = self.call_main(["--name", "original-unscored", "--no-score"])
        score.assert_not_called()

    def test_explicit_scoring_inputs_stay_out_of_prompt_and_cwd_is_restored(self):
        reference, labeled = self.root / "answerkey.json", self.root / "gate.json"
        reference.write_text('{"private_answer": "NEVER_EXPOSE_THIS_REFERENCE"}')
        labeled.write_text('{}')
        cwd = Path.cwd()
        _, claude, _, score = self.call_main([
            "--facts", str(self.facts), "--case-profile", str(self.profile), "--name", "scored",
            "--reference", str(reference), "--labeled-claims", str(labeled),
        ])
        argv = score.call_args.args[0]
        for option, value in (("--reference", str(reference)), ("--labeled-claims", str(labeled)),
                              ("--time-zone", "America/Los_Angeles")):
            self.assertEqual(argv[argv.index(option) + 1], value)
        self.assertNotIn("NEVER_EXPOSE_THIS_REFERENCE", claude.call_args.kwargs["prompt"])
        self.assertNotIn(str(reference), claude.call_args.kwargs["prompt"])
        self.assertEqual(Path.cwd(), cwd)
        _, _, _, score = self.call_main([
            "--facts", str(self.facts), "--name", "explicitly-unscored", "--reference", str(reference),
            "--no-score",
        ])
        score.assert_not_called()

    def test_profile_schema_and_invalid_timezones_fail_before_backend_or_run_creation(self):
        data = json.loads(self.profile.read_text())
        for changed in (dict(data, answer_key="private.json"), dict(data, time_zone="Pacific/Made_Up"),
                        dict(data, time_zone="UTC-8"), dict(data, questions=[]),
                        dict(data, questions=[{"answer": "secret"}]), dict(data, brief="")):
            with self.subTest(changed=changed):
                self.profile.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    read_profile(self.profile)
                with patch.object(run, "ROOT", self.root), \
                     patch.object(run, "run_claude_code") as backend, \
                     contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    run.main(["--facts", str(self.facts), "--case-profile", str(self.profile), "--name", "bad"])
                backend.assert_not_called()
                self.assertFalse((self.root / "runs").exists())
        self.write_facts(self.facts, {"time_zone": "not/a/zone"})
        with self.assertRaises(ValueError):
            select_case(self.facts)

    def test_old_runs_and_unsafe_paths_are_preserved(self):
        directory = run.prepare_run_dir("dev/nested", self.root)
        sentinel = directory / "original.txt"
        sentinel.write_text("keep this run")
        for name in ("dev/nested", "../escape", "dev/../escape", "/tmp/outside", ".", "", "a//b", "C:\\temp\\x"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                run.prepare_run_dir(name, self.root)
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "runs" / "alias").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            run.prepare_run_dir("alias/new", self.root)
        self.assertFalse((outside / "new").exists())
        self.assertEqual(sentinel.read_text(), "keep this run")
        with patch.object(run, "ROOT", self.root), patch.object(run, "run_claude_code") as backend, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run.main(["--facts", str(self.facts), "--name", "dev/nested"])
        backend.assert_not_called()
        self.assertEqual(sentinel.read_text(), "keep this run")

    def test_deepagents_uses_selected_prompt_and_exposes_conclusions(self):
        backend = Mock()
        backend.invoke.return_value = {"messages": [types.SimpleNamespace(content="done")]}
        create = Mock(return_value=backend)
        deep_module = types.ModuleType("deepagents")
        deep_module.create_deep_agent = create
        tools_module = types.ModuleType("langchain_core.tools")
        tools_module.tool = lambda function: function
        with patch.dict("sys.modules", {"deepagents": deep_module, "langchain_core.tools": tools_module}), \
             patch("agent.tools.Workbench") as bench:
            bench.return_value.conclude.return_value = {"status": "accepted"}
            run.run_deepagents("test", self.root, str(self.facts), prompt="PUBLIC CASE ONLY")
            toolset = {t.__name__: t for t in create.call_args.kwargs["tools"]}
            self.assertEqual(set(toolset), set(run.INVESTIGATOR_TOOLS))
            toolset["conclude"]("uncertain inference", ["A001"])
            bench.return_value.conclude.assert_called_once_with("uncertain inference", ["A001"])
        self.assertEqual(backend.invoke.call_args.args[0]["messages"][0]["content"], "PUBLIC CASE ONLY")


if __name__ == "__main__":
    unittest.main()
