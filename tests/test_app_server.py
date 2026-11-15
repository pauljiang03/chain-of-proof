"""Actual loopback HTTP with synthetic jobs; no provider or investigator calls."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from app.server import create_server


class FakeManager:
    def __init__(self):
        self.calls = []
        self.closed = 0
        self.failure = None

    def config(self):
        return {"defaults": {"facts": "facts.json", "backend": "claude-code", "model": "opus", "minutes": 45},
                "backends": [{"id": "claude-code", "label": "Claude Code", "available": True}], "active_run": None}

    def list_runs(self):
        return [{"name": "saved/run1.2", "title": "Saved", "status": "saved", "generated_at": None,
                 "verified": 1, "rejected": 0}]

    def get_run(self, name):
        self.calls.append(("get", name))
        if self.failure:
            raise self.failure
        return {"name": name, "status": "running", "run": getattr(self, "run", None), "events": [
            {"sequence": 1, "tool": "fact", "outcome": "success", "completed_at": "2026-11-14T00:00:00Z",
             "finding_id": None, "arguments": {"fact_id": 1}}], "error": None}

    def start(self, payload):
        self.calls.append(("start", payload))
        if self.failure:
            raise self.failure
        return {"name": payload["name"], "status": "running"}

    def stop(self, name):
        self.calls.append(("stop", name))
        if self.failure:
            raise self.failure
        return {"name": name, "status": "cancelled"}

    def report(self, name, fmt, options=None):
        self.calls.append(("report", name, fmt) if options is None else ("report", name, fmt, options))
        if self.failure:
            raise self.failure
        return b"saved report", "untrusted/mime", '../../secret\r\nX-Leak: yes.' + fmt

    def close(self):
        self.closed += 1


class AppServer(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / "assets"
        self.assets.mkdir()
        for name in ("index.html", "app.js", "graph.js", "report.js", "timeline.js", "overview.js", "evidence.js", "style.css", "icon.svg"):
            (self.assets / name).write_text("synthetic " + name)
        assets_patch = patch("app.server.STATIC_ROOT", self.assets)
        assets_patch.start()
        self.addCleanup(assets_patch.stop)
        self.manager = FakeManager()
        self.server = create_server(self.root, 0, manager=self.manager)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.host = f"127.0.0.1:{self.server.server_port}"

    def stop_server(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def request(self, path, *, method="GET", payload=None, body=None, headers=None, token=True):
        supplied = {"Host": self.host}
        if payload is not None:
            body = json.dumps(payload).encode()
            supplied["Content-Type"] = "application/json"
        if method == "POST" and token:
            supplied["X-COP-Token"] = self.server.token
        supplied.update(headers or {})
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=supplied)
            response = connection.getresponse()
            raw = response.read()
            return response.status, dict(response.getheaders()), raw
        finally:
            connection.close()

    def duplicate_headers(self, path, headers, body=b""):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.putrequest("POST", path, skip_host=True)
            for key, value in [("Host", self.host), ("X-COP-Token", self.server.token),
                               ("Content-Type", "application/json"), ("Content-Length", str(len(body)))] + headers:
                connection.putheader(key, value)
            connection.endheaders(body)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def assert_error(self, status, response):
        code, headers, body = response
        self.assertEqual(code, status, body)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(set(json.loads(body)), {"error"})
        self.assertNotIn(b"provider-secret", body)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_bound_loopback_config_token_and_no_job_start(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, body = self.request("/api/config")
        self.assertEqual(status, 200)
        config = json.loads(body)
        self.assertEqual(set(config), {"token", "defaults", "backends", "active_run"})
        self.assertEqual(config["token"], self.server.token)
        self.assertGreaterEqual(len(config["token"]), 32)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.manager.calls, [])
        other = create_server(self.root, 0, manager=FakeManager())
        try:
            self.assertNotEqual(other.token, self.server.token)
        finally:
            other.server_close()

    def test_runs_live_state_and_valid_nested_name(self):
        self.assertEqual(json.loads(self.request("/api/runs")[2])["runs"], self.manager.list_runs())
        status, _, body = self.request("/api/run?name=saved%2Frun1.2")
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertIsNone(result["run"])
        self.assertEqual(result["events"][0]["arguments"], {"fact_id": 1})
        self.assertEqual(self.manager.calls, [("get", "saved/run1.2")])

    def test_explicit_start_and_stop_only_forward_public_fields(self):
        payload = {"name": "user/run1.2", "facts": "/selected/facts.json", "title": "Case",
                   "brief": "Investigate", "questions": ["What happened?"], "backend": "deepagents",
                   "model": "model-id", "minutes": 2}
        response = self.request("/api/investigations", method="POST", payload=payload,
                                headers={"Origin": "http://" + self.host})
        self.assertEqual(response[0], 200)
        self.assertEqual(self.manager.calls, [("start", payload)])
        stopped = self.request("/api/stop", method="POST", payload={"name": payload["name"]})
        self.assertEqual(json.loads(stopped[2])["status"], "cancelled")

    def test_host_origin_and_write_token_protections(self):
        for headers in ({"Host": "attacker.test"}, {"Host": "127.0.0.1:1"},
                        {"Origin": "https://attacker.test"}, {"Origin": "null"},
                        {"Origin": f"http://localhost:{self.server.server_port}"}):
            with self.subTest(headers=headers):
                self.assert_error(403, self.request("/api/config", headers=headers))
        payload = {"name": "new", "facts": "facts.json"}
        self.assert_error(403, self.request("/api/investigations", method="POST", payload=payload, token=False))
        self.assert_error(403, self.request("/api/investigations", method="POST", payload=payload,
                                           headers={"X-COP-Token": "wrong"}))
        host = f"localhost:{self.server.server_port}"
        self.assertEqual(self.request("/api/config", headers={"Host": host, "Origin": "http://" + host})[0], 200)
        self.assertEqual(self.manager.calls, [])

    def test_duplicate_security_headers_and_lengths_are_rejected(self):
        for headers, expected in (([("Host", self.host)], 403),
                                  ([("Origin", "http://" + self.host)] * 2, 403),
                                  ([("X-COP-Token", self.server.token)], 403),
                                  ([("Content-Length", "2")], 400)):
            with self.subTest(headers=headers):
                status, result = self.duplicate_headers("/api/stop", headers, b"{}")
                self.assertEqual(status, expected)
                self.assertEqual(set(result), {"error"})

    def test_invalid_json_lengths_content_types_and_nonfinite_numbers(self):
        for body in (b"{", b"\xff", b'{"name":"a","name":"b"}', b'{"minutes":NaN}'):
            self.assert_error(400, self.request("/api/investigations", method="POST", body=body,
                                                headers={"Content-Type": "application/json"}))
        for length in ("-1", "nonsense", "1, 1"):
            self.assert_error(400, self.request("/api/stop", method="POST", body=b"{}",
                                                headers={"Content-Length": length, "Content-Type": "application/json"}))
        self.assert_error(413, self.request("/api/stop", method="POST", body=b"{}",
                                            headers={"Content-Length": str(64 * 1024 + 1)}))
        self.assert_error(415, self.request("/api/stop", method="POST", body=b"{}"))
        self.assert_error(400, self.request("/api/stop", method="POST", payload={"name": "a"},
                                            headers={"Transfer-Encoding": "chunked"}))
        self.assertEqual(self.manager.calls, [])

    def test_start_validation_blocks_cli_only_inputs_before_manager(self):
        base = {"name": "new", "facts": "facts.json"}
        variants = [{field: "private.json"} for field in ("reference", "case_profile", "question_profile", "answers", "api_key")]
        variants += [{"name": "sample"}, {"minutes": True}, {"minutes": 1.5}, {"minutes": 0},
                     {"backend": "claude"}, {"questions": [""]}, {"questions": "text"},
                     {"questions": ["x" * 8193]}, {"model": "m" * 257}, {"facts": ""}, {"title": None}]
        for changes in variants:
            with self.subTest(changes=changes):
                self.assert_error(400, self.request("/api/investigations", method="POST", payload={**base, **changes}))
        self.assert_error(400, self.request("/api/stop", method="POST", payload={"name": "a", "force": True}))
        self.assertEqual(self.manager.calls, [])

    def test_paths_queries_and_private_routes_are_rejected(self):
        bad_paths = ("/../app.js", "/%2e%2e/app.js", "/app%2ejs", "/api/config?extra=x",
                     "/api/run?name=a&name=b", "/api/run?name=../private", "/api/run?name=%2Fabsolute",
                     "/api/run?name=a%5Cb", "/api/run?name=a%00b", "/api/run?name=", "/api/run?name=a//b",
                     "/api/report?name=a&format=pdf", "/api/report?name=a&download=2")
        for path in bad_paths:
            with self.subTest(path=path):
                self.assert_error(400, self.request(path))
        for path in ("/api/credentials", "/api/transcript?name=a", "/runs/a/run.json", "/app/server.py", "/.env"):
            with self.subTest(path=path):
                self.assert_error(404, self.request(path))
        self.assertEqual(self.manager.calls, [])

    def test_run_symlinks_are_rejected_for_reads_and_writes(self):
        runs = self.root / "runs"
        runs.mkdir()
        (runs / "linked").symlink_to(self.assets, target_is_directory=True)
        self.assert_error(400, self.request("/api/run?name=linked/child"))
        self.assert_error(400, self.request("/api/report?name=linked"))
        self.assert_error(400, self.request("/api/stop", method="POST", payload={"name": "linked"}))
        self.assert_error(400, self.request("/api/investigations", method="POST", payload={"name": "linked/new", "facts": "facts.json"}))
        self.assertEqual(self.manager.calls, [])

    def test_static_allowlist_and_asset_symlinks(self):
        for route, mime in (("/", "text/html"), ("/index.html", "text/html"), ("/app.js", "text/javascript"),
                            ("/style.css", "text/css"), ("/static/app.js", "text/javascript"),
                            ("/static/graph.js", "text/javascript"), ("/static/report.js", "text/javascript"),
                            ("/static/timeline.js", "text/javascript"), ("/static/overview.js", "text/javascript"), ("/static/evidence.js", "text/javascript"),
                            ("/static/icon.svg", "image/svg+xml"),
                            ("/static/style.css", "text/css")):
            status, headers, body = self.request(route)
            self.assertEqual(status, 200)
            self.assertTrue(headers["Content-Type"].startswith(mime))
            self.assertTrue(body.startswith(b"synthetic"))
        (self.assets / "app.js").unlink()
        (self.assets / "app.js").symlink_to(self.assets / "index.html")
        self.assert_error(404, self.request("/app.js"))
        linked = self.root / "linked-assets"
        linked.symlink_to(self.assets, target_is_directory=True)
        with patch("app.server.STATIC_ROOT", linked):
            self.assert_error(404, self.request("/"))

    def test_report_formats_and_download_filenames(self):
        for fmt, mime in (("html", "text/html"), ("md", "text/markdown"), ("json", "application/json")):
            status, headers, body = self.request(f"/api/report?name=saved/run1.2&format={fmt}&download=1")
            self.assertEqual(status, 200)
            self.assertEqual(body, b"saved report")
            self.assertEqual(headers["Content-Type"], mime + "; charset=utf-8")
            self.assertEqual(headers["Content-Disposition"], f'attachment; filename="saved-run1.2.{fmt}"')
            self.assertNotIn("X-Leak", headers)
        self.assertNotIn("Content-Disposition", self.request("/api/report?name=sample")[1])

    def test_a_run_arrives_with_a_brief_counted_from_its_own_records(self):
        status, _, body = self.request("/api/run?name=saved")
        self.assertEqual(status, 200)
        self.assertNotIn("brief", json.loads(body))          # nothing saved yet: nothing to count
        self.manager.run = {"findings": [{"finding_id": "F1", "status": "verified", "cited_facts": [
            {"id": 1, "kind": "usbInsert", "t": 1427135470000000, "obj_text": "S1", "prov": {"exhibit": "PC", "image": "pc.E01"}}]}]}
        payload = json.loads(self.request("/api/run?name=saved")[2])
        self.assertEqual(payload["run"], self.manager.run)   # the run itself is untouched
        self.assertEqual(payload["brief"]["counts"]["findings"], 1)
        self.assertEqual([(item["label"], item["images"], item["records"]) for item in payload["brief"]["exhibits"]],
                         [("PC", ["pc.E01"], 1)])

    def test_examiner_report_options_are_validated_and_passed_to_the_manager(self):
        (self.root / "runs" / "saved").mkdir(parents=True, exist_ok=True)
        status, headers, _ = self.request("/api/report?name=saved&format=html&download=1&ids=F1,F2"
                                          "&sections=needs,proofs&reference=R-1&examiner=A%20B&organisation=Lab")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="saved.html"')
        options = self.manager.calls[-1][3]
        self.assertEqual(self.manager.calls[-1][:3], ("report", "saved", "html"))
        self.assertEqual(options, {"ids": ["F1", "F2"], "sections": frozenset(("needs", "proofs")),
                                   "reference": "R-1", "examiner": "A B", "organisation": "Lab", "requested_by": "",
                                   "authority": "", "purpose": "", "received": "", "report_date": ""})
        self.request("/api/report?name=saved&requested_by=Det.%20X&authority=Warrant%207&purpose=" + "p" * 600
                     + "&received=2026-11-01&report_date=2026-11-14")
        self.assertEqual({key: self.manager.calls[-1][3][key] for key in ("requested_by", "authority", "received", "report_date")},
                         {"requested_by": "Det. X", "authority": "Warrant 7", "received": "2026-11-01", "report_date": "2026-11-14"})
        self.assertEqual(len(self.manager.calls[-1][3]["purpose"]), 600)
        self.request("/api/report?name=saved&sections=")      # findings alone
        self.assertEqual(self.manager.calls[-1][3]["sections"], frozenset())
        self.assertIsNone(self.manager.calls[-1][3]["ids"])
        self.request("/api/report?name=saved")                # no options: the complete report, as before
        self.assertEqual(self.manager.calls[-1], ("report", "saved", "html"))
        before = len(self.manager.calls)
        for bad in ("ids=", "ids=F1,F1", "ids=a%20b", "sections=findings", "sections=needs,needs",
                    "examiner=" + "x" * 201, "purpose=" + "x" * 601, "reference=a%0Ab", "format=md&ids=F1", "format=json&sections=needs",
                    "ids=F1&unknown=1"):
            with self.subTest(bad=bad):
                self.assert_error(400, self.request("/api/report?name=saved&" + bad))
        self.assertEqual(len(self.manager.calls), before)
        self.manager.failure = ValueError("The selection names a finding that is not recorded exactly once as verified.")
        status, _, body = self.request("/api/report?name=saved&ids=F9")
        self.assertEqual(status, 400)
        self.assertIn("selection names a finding", json.loads(body)["error"])

    def test_manager_failures_are_safe_json_and_preserve_status(self):
        for error, status in ((FileNotFoundError("provider-secret"), 404),
                              (FileExistsError("provider-secret"), 409),
                              (ValueError("provider-secret"), 400),
                              (RuntimeError("provider-secret"), 409),
                              (Exception("provider-secret"), 500)):
            with self.subTest(error=type(error).__name__):
                self.manager.failure = error
                self.assert_error(status, self.request("/api/run?name=a"))
        self.assert_error(501, self.request("/api/config", method="DELETE"))

    def test_close_calls_manager_once(self):
        manager = FakeManager()
        other = create_server(self.root, 0, manager=manager)
        other.server_close()
        other.server_close()
        self.assertEqual(manager.closed, 1)


if __name__ == "__main__":
    unittest.main()
