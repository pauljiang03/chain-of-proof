"""The user's Anthropic API key: kept in their settings folder, passed to the worker, never sent back."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from app import credentials, jobs
from app.server import create_server

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "fixtures/sample_facts.json"
KEY = "sk-ant-test-0123456789abcdefghijklmnopqrstuvwxyz"   # made up; opens nothing


class Scratch(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name) / "project"
        self.root.mkdir()
        self.secrets = Path(scratch.name) / "settings" / "conan-f"
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(credentials.ENV, None)


class Store(Scratch):
    def test_key_is_saved_for_this_user_only_and_can_be_removed(self):
        self.assertIsNone(credentials.source(self.secrets))
        credentials.save("  " + KEY + "\n", self.secrets)
        self.assertEqual(credentials.key(self.secrets), KEY)
        self.assertEqual(credentials.source(self.secrets), "saved")
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE((self.secrets / credentials.FILE).stat().st_mode), 0o600)
        self.assertEqual([path.name for path in self.secrets.iterdir()], [credentials.FILE])   # no stray temporary file
        credentials.save(KEY + "-second", self.secrets)
        self.assertEqual(credentials.key(self.secrets), KEY + "-second")
        credentials.clear(self.secrets)
        credentials.clear(self.secrets)                         # removing twice is not an error
        self.assertIsNone(credentials.key(self.secrets))

    def test_environment_comes_first_and_no_folder_means_environment_only(self):
        credentials.save(KEY, self.secrets)
        self.assertIsNone(credentials.key(None))
        os.environ[credentials.ENV] = " from-the-environment-0123456789 "
        self.assertEqual(credentials.source(self.secrets), "environment")
        self.assertEqual(credentials.key(self.secrets), "from-the-environment-0123456789")
        self.assertEqual(credentials.key(None), "from-the-environment-0123456789")

    def test_values_that_cannot_be_keys_are_refused_without_repeating_them(self):
        for value in ("", "short", "has a space in the middle of it all", "x" * 513, "line\nbreak-0123456789abcdef", None, 7,
                      "café-0123456789abcdefghij"):
            with self.subTest(value=value), self.assertRaises(ValueError) as raised:
                credentials.save(value, self.secrets)
            self.assertEqual(str(raised.exception), "That does not look like an API key.")
        self.assertFalse(self.secrets.exists())
        self.secrets.mkdir(parents=True)
        (self.secrets / credentials.FILE).write_text("not a key")
        self.assertIsNone(credentials.key(self.secrets))        # a damaged file is no key

    def test_settings_folder_is_outside_the_project(self):
        folder = credentials.folder()
        self.assertEqual(folder.name, "conan-f")
        self.assertNotIn(ROOT, [folder, *folder.parents])


class Manager(Scratch):
    def manager(self, verdict="ok", installed=True):
        self.checked = []
        manager = jobs.JobManager(self.root, secrets=self.secrets,
                                  check=lambda key, model: self.checked.append((key, model)) or verdict)
        self.addCleanup(manager.close)
        installed_patch = patch.object(jobs.JobManager, "_api_installed", staticmethod(lambda: installed))
        installed_patch.start()
        self.addCleanup(installed_patch.stop)
        return manager

    def api(self, manager):
        return next(item for item in manager.config()["backends"] if item["id"] == "deepagents")

    def test_api_is_the_default_once_it_has_a_key(self):
        manager = self.manager()
        with patch("shutil.which", return_value="/usr/bin/claude"):
            before = manager.config()
            self.assertEqual((before["defaults"]["backend"], before["defaults"]["model"]), ("claude-code", "opus"))
            self.assertEqual((self.api(manager)["available"], self.api(manager)["needs"], self.api(manager)["key"]), (False, "key", None))
            self.assertEqual(manager.set_api_key(KEY), {"key": "saved", "check": "ok"})
            after = manager.config()
        self.assertEqual((after["defaults"]["backend"], after["defaults"]["model"]), ("deepagents", "claude-opus-5-5"))
        self.assertEqual((self.api(manager)["available"], self.api(manager)["needs"], self.api(manager)["key"]), (True, None, "saved"))
        self.assertEqual(self.checked, [(KEY, "claude-opus-5-5")])
        self.assertNotIn(KEY, json.dumps(after))                # the page learns where the key is from, not the key
        with patch("shutil.which", return_value=None):          # nothing else installed: the API is what to set up
            manager.set_api_key("")
            self.assertEqual(manager.config()["defaults"]["backend"], "deepagents")
            self.assertEqual(manager.config()["backends"][0]["needs"], "program")

    def test_refused_key_is_not_saved_and_an_unchecked_key_is(self):
        manager = self.manager(verdict="rejected")
        with self.assertRaises(ValueError) as raised:
            manager.set_api_key(KEY)
        self.assertNotIn(KEY, str(raised.exception))
        self.assertIsNone(credentials.key(self.secrets))
        for verdict in ("offline", "no_model", "unknown"):
            with self.subTest(verdict=verdict):
                manager = self.manager(verdict=verdict)
                self.assertEqual(manager.set_api_key(KEY), {"key": "saved", "check": verdict})
                self.assertEqual(manager.set_api_key(""), {"key": None, "check": None})
        manager = self.manager(installed=False)                 # nothing to check the key with
        self.assertEqual(manager.set_api_key(KEY), {"key": "saved", "check": None})
        self.assertEqual(self.checked, [])
        self.assertEqual(self.api(manager)["needs"], "packages")
        with self.assertRaises(RuntimeError):                   # a manager without a settings folder saves nothing
            jobs.JobManager(self.root).set_api_key(KEY)

    def test_worker_gets_the_key_in_its_environment_only(self):
        seen = []

        class Recording(jobs.JobManager):
            def _spawn(self, command, env):
                seen.append((command, env, json.loads(Path(command[command.index("--spec") + 1]).read_text())))
                return jobs.subprocess.Popen([sys.executable, "-c", "pass"])

        manager = Recording(self.root, secrets=self.secrets, check=lambda key, model: "ok")
        self.addCleanup(manager.close)
        with patch.object(jobs.JobManager, "_api_installed", staticmethod(lambda: True)), \
             patch("shutil.which", return_value="/usr/bin/claude"), \
             patch.dict(os.environ, {"LANGSMITH_TRACING": "true"}):
            manager.set_api_key(KEY)
            manager.start({"name": "with-api", "facts": str(FACTS), "backend": "deepagents"})
            manager._jobs["with-api"]["done"].wait(10)
            manager.start({"name": "with-code", "facts": str(FACTS), "backend": "claude-code"})
            manager._jobs["with-code"]["done"].wait(10)
        (command, env, spec), (_, other, _) = seen
        self.assertEqual(env[credentials.ENV], KEY)
        self.assertEqual((env["LANGSMITH_TRACING"], env["LANGCHAIN_TRACING_V2"]), ("false", "false"))
        self.assertNotIn(KEY, " ".join(command))
        self.assertNotIn(KEY, json.dumps(spec))
        self.assertNotIn(credentials.ENV, other)                # the saved key is for the API service only
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(KEY.encode(), path.read_bytes(), path)


class Route(Scratch):
    def setUp(self):
        super().setUp()
        self.manager = jobs.JobManager(self.root, secrets=self.secrets, check=lambda key, model: self.verdict)
        self.verdict = "ok"
        self.server = create_server(self.root, 0, manager=self.manager)
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), thread.join(timeout=2), self.server.server_close()))
        installed = patch.object(jobs.JobManager, "_api_installed", staticmethod(lambda: True))
        installed.start()
        self.addCleanup(installed.stop)

    def post(self, payload, token=True):
        host = "127.0.0.1:%d" % self.server.server_port
        headers = {"Content-Type": "application/json", "Host": host, "Origin": "http://" + host}
        if token:
            headers["X-COP-Token"] = self.server.token
        request = urllib.request.Request("http://" + host + "/api/credentials", data=json.dumps(payload).encode(),
                                         headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.read().decode()
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode()

    def test_page_can_save_and_remove_the_key_but_never_reads_it_back(self):
        status, body = self.post({"anthropic_api_key": KEY})
        self.assertEqual((status, json.loads(body)), (200, {"key": "saved", "check": "ok"}))
        self.assertEqual(credentials.key(self.secrets), KEY)
        with urllib.request.urlopen("http://127.0.0.1:%d/api/config" % self.server.server_port, timeout=5) as response:
            config = response.read().decode()
        self.assertNotIn(KEY, config)
        self.assertIn('"key": "saved"', config)
        self.assertEqual(json.loads(self.post({"anthropic_api_key": ""})[1]), {"key": None, "check": None})
        self.assertIsNone(credentials.key(self.secrets))

    def test_bad_requests_change_nothing_and_do_not_repeat_the_key(self):
        self.verdict = "rejected"
        for payload, status in (({"anthropic_api_key": KEY}, 400), ({"anthropic_api_key": "short"}, 400),
                                ({"anthropic_api_key": KEY, "path": "/tmp/x"}, 400), ({"anthropic_api_key": 5}, 400), ({}, 400)):
            with self.subTest(payload=payload):
                code, body = self.post(payload)
                self.assertEqual(code, status)
                self.assertNotIn(KEY, body)
        self.verdict = "ok"
        self.assertEqual(self.post({"anthropic_api_key": KEY}, token=False)[0], 403)
        self.assertIsNone(credentials.key(self.secrets))


if __name__ == "__main__":
    unittest.main()
