"""The product CLI uses synthetic jobs and existing render/verify interfaces."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from app import cli


RUN = {"version": 1, "case": {"name": "Synthetic CLI case"},
       "stats": {"verified": 0, "rejected": 0, "proposals": 0},
       "findings": [], "rejections": [], "conclusions": []}


class AppCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_path = self.root / "run.json"
        self.run_path.write_text(json.dumps(RUN))

    def manager(self, statuses, *, report=True, error=None):
        manager = Mock()
        manager.start.return_value = {"name": "dev/fixture", "status": "running"}
        manager.get_run.side_effect = [{"name": "dev/fixture", "status": status,
                                        "run": RUN if report and status != "running" else None,
                                        "events": [], "error": error if status != "running" else None}
                                       for status in statuses]

        def save_report(name, fmt):
            if fmt == "html":
                return b"<!doctype html><title>Synthetic report</title>", "text/html; charset=utf-8", "report.html"
            path = self.root / "runs" / name / "report.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Synthetic report\n")
            return b"Synthetic report\n", "text/markdown; charset=utf-8", "report.md"

        manager.report.side_effect = save_report
        return manager

    def invoke(self, args):
        with contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = cli.main(args, root=self.root)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_investigate_passes_explicit_public_options_and_waits_for_report(self):
        manager = self.manager(["running", "completed"])
        with patch("app.cli._job_manager", return_value=manager) as factory, patch("app.cli.time.sleep") as sleep:
            code, stdout, stderr = self.invoke([
                "investigate", "--name", "dev/fixture", "--facts", "facts.json",
                "--backend", "deepagents", "--model", "explicit-model", "--minutes", "7",
                "--title", "Public title", "--brief", "Public brief", "--question", "First?",
                "--question", "Second?", "--case-profile", "case.json", "--questions", "questions.json"])
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        factory.assert_called_once_with(self.root)
        manager.start.assert_called_once_with({
            "name": "dev/fixture", "facts": "facts.json", "questions": ["First?", "Second?"],
            "backend": "deepagents", "model": "explicit-model", "minutes": 7,
            "title": "Public title", "brief": "Public brief"},
            case_profile="case.json", question_profile="questions.json")
        sleep.assert_called_once_with(2)
        manager.report.assert_called_once_with("dev/fixture", "html")
        self.assertIn(str(self.root.resolve() / "runs/dev/fixture/report.html"), stdout)
        manager.close.assert_called_once_with()

    def test_unset_options_are_left_to_shared_backend_aware_defaults(self):
        manager = self.manager(["completed"])
        with patch("app.cli._job_manager", return_value=manager):
            code, _, _ = self.invoke(["investigate", "--name", "dev/fixture", "--facts", "facts.json"])
        self.assertEqual(code, 0)
        manager.start.assert_called_once_with({"name": "dev/fixture", "facts": "facts.json", "questions": []},
                                              case_profile=None, question_profile=None)

    def test_failed_partial_and_cancelled_runs_keep_truthful_report_paths(self):
        for status in ("failed", "partial", "cancelled"):
            with self.subTest(status=status):
                manager = self.manager([status], error="Safe job explanation")
                with patch("app.cli._job_manager", return_value=manager):
                    code, stdout, stderr = self.invoke(["investigate", "--name", "dev/fixture", "--facts", "facts.json"])
                self.assertEqual(code, 1)
                self.assertIn(f"Status: {status}", stdout)
                self.assertIn("report.html", stdout)
                self.assertIn("Safe job explanation", stderr)
                manager.close.assert_called_once_with()

    def test_failure_without_run_does_not_print_an_invented_report_path(self):
        manager = self.manager(["failed"], report=False, error="The job could not start")
        with patch("app.cli._job_manager", return_value=manager):
            code, stdout, stderr = self.invoke(["investigate", "--name", "dev/fixture", "--facts", "facts.json"])
        self.assertEqual(code, 1)
        self.assertNotIn("Report:", stdout)
        self.assertIn("No report is available", stderr)
        manager.report.assert_not_called()

    def test_ctrl_c_stops_owned_job_closes_manager_and_preserves_partial_report(self):
        manager = self.manager(["running", "cancelled"])
        with patch("app.cli._job_manager", return_value=manager), patch("app.cli.time.sleep", side_effect=KeyboardInterrupt):
            code, stdout, _ = self.invoke(["investigate", "--name", "dev/fixture", "--facts", "facts.json"])
        self.assertEqual(code, 130)
        manager.stop.assert_called_once_with("dev/fixture")
        manager.close.assert_called_once_with()
        self.assertIn("report.html", stdout)

    def test_start_validation_failure_still_closes_manager(self):
        for error in (ValueError("run already exists"), RuntimeError("backend unavailable")):
            with self.subTest(error=type(error).__name__):
                manager = self.manager([])
                manager.start.side_effect = error
                with patch("app.cli._job_manager", return_value=manager), \
                     contextlib.redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit) as raised:
                    cli.main(["investigate", "--name", "dev/fixture", "--facts", "facts.json"], root=self.root)
                self.assertEqual(raised.exception.code, 2)
                self.assertIn(str(error), stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())
                manager.close.assert_called_once_with()

    def test_missing_html_renderer_falls_back_to_saved_markdown(self):
        manager = self.manager(["completed"])
        original_report = manager.report.side_effect

        def without_html(name, fmt):
            if fmt == "html":
                raise ImportError("renderer not installed")
            return original_report(name, fmt)

        manager.report.side_effect = without_html
        with patch("app.cli._job_manager", return_value=manager):
            code, stdout, _ = self.invoke(["investigate", "--name", "dev/fixture", "--facts", "facts.json"])
        self.assertEqual(code, 0)
        self.assertIn("report.md", stdout)
        self.assertFalse((self.root / "runs/dev/fixture/report.html").exists())

    def test_invalid_time_limit_is_rejected_before_manager_creation(self):
        for minutes in ("0", "-1", "1.5", "invalid"):
            with self.subTest(minutes=minutes), patch("app.cli._job_manager") as factory, \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                cli.main(["investigate", "--name", "new", "--facts", "facts.json", "--minutes", minutes])
            self.assertEqual(raised.exception.code, 2)
            factory.assert_not_called()

    def test_serve_uses_loopback_server_contract_and_browser_flags(self):
        server = types.ModuleType("app.server")
        server.serve = Mock()
        with patch.dict("sys.modules", {"app.server": server}):
            self.assertEqual(self.invoke(["serve"])[0], 0)
            server.serve.assert_called_with(root=self.root, port=8765, open_browser=True)
            for flag in ("--no-open", "--no-browser"):
                self.assertEqual(self.invoke(["serve", "--port", "9876", flag])[0], 0)
                server.serve.assert_called_with(root=self.root, port=9876, open_browser=False)

    def test_report_renders_html_through_public_api_and_preserves_input(self):
        renderer = types.ModuleType("app.report")
        renderer.render_html = Mock(return_value="<!doctype html><title>Fixture</title>")
        original = self.run_path.read_bytes()
        output = self.root / "new" / "report.html"
        with patch.dict("sys.modules", {"app.report": renderer}):
            code, stdout, _ = self.invoke(["report", "--run", str(self.run_path), "--out", str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(output.read_text(), "<!doctype html><title>Fixture</title>")
        renderer.render_html.assert_called_once_with(RUN)
        self.assertEqual(self.run_path.read_bytes(), original)
        self.assertIn(str(output.resolve()), stdout)

    def test_report_markdown_and_json_can_write_to_stdout(self):
        code, markdown, _ = self.invoke(["report", "--run", str(self.run_path), "--format", "md"])
        self.assertEqual(code, 0)
        self.assertIn("Synthetic CLI case", markdown)
        code, raw, _ = self.invoke(["report", "--run", str(self.run_path), "--format", "json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(raw), RUN)

    def test_report_refuses_existing_files_inputs_and_dangling_symlinks(self):
        existing = self.root / "existing.md"
        existing.write_text("preserve")
        target = self.root / "not-created"
        link = self.root / "link.md"
        link.symlink_to(target)
        original = self.run_path.read_bytes()
        for output in (existing, self.run_path, link):
            with self.subTest(output=output), contextlib.redirect_stderr(io.StringIO()) as stderr, \
                 self.assertRaises(SystemExit) as raised:
                cli.main(["report", "--run", str(self.run_path), "--format", "md", "--out", str(output)])
            self.assertEqual(raised.exception.code, 2)
            self.assertIn("refusing to overwrite", stderr.getvalue())
        self.assertEqual(existing.read_text(), "preserve")
        self.assertEqual(self.run_path.read_bytes(), original)
        self.assertTrue(link.is_symlink())
        self.assertFalse(target.exists())

    def test_report_racing_writer_is_preserved(self):
        output = self.root / "race.md"
        original_open = Path.open

        def competitor(path, mode="r", *args, **kwargs):
            if path == output and mode == "x":
                with original_open(path, "x") as stream:
                    stream.write("other writer")
            return original_open(path, mode, *args, **kwargs)

        with patch.object(Path, "open", competitor), contextlib.redirect_stderr(io.StringIO()), \
             self.assertRaises(SystemExit) as raised:
            cli.main(["report", "--run", str(self.run_path), "--format", "md", "--out", str(output)])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(output.read_text(), "other writer")

    def test_invalid_report_input_has_a_clean_error_and_no_output(self):
        output = self.root / "not-created.json"
        for text in ("malformed", "[]", "{}", '{"findings": [], "findings": []}',
                     '{"findings": [], "bad": NaN}'):
            with self.subTest(text=text):
                self.run_path.write_text(text)
                with contextlib.redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit) as raised:
                    cli.main(["report", "--run", str(self.run_path), "--format", "json", "--out", str(output)])
                self.assertEqual(raised.exception.code, 2)
                self.assertNotIn("Traceback", stderr.getvalue())
                self.assertFalse(output.exists())

    def test_verify_and_package_preserve_delegated_arguments_and_statuses(self):
        with patch("verifier.verify.main", return_value=1) as verify:
            args = ["--run", "run.json", "--facts", "facts.json", "--out", "verification.json"]
            self.assertEqual(cli.main(["verify", *args]), 1)
            verify.assert_called_once_with(args)
        with patch("verifier.package.main", return_value=0) as package:
            args = ["build", "--run", "run.json", "--facts", "facts.json", "--out", "bundle"]
            self.assertEqual(cli.main(["package", *args]), 0)
            package.assert_called_once_with(args)

    def test_help_does_not_start_a_job(self):
        with patch("app.cli._job_manager") as factory, contextlib.redirect_stdout(io.StringIO()) as output, \
             self.assertRaises(SystemExit) as raised:
            cli.main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        for command in ("investigate", "serve", "report", "verify", "package"):
            self.assertIn(command, output.getvalue())
        factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
