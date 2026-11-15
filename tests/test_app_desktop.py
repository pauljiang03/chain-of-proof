"""The desktop window wraps the same loopback server and stops it on close."""
import json
from collections import UserDict
import plistlib
import socket
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from app import desktop


class FakeManager:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True

    def config(self):
        return {"defaults": {}, "backends": [], "active_run": None}


class FakeWebview:
    """Stands in for pywebview: `start` blocks while the window is open."""

    def __init__(self):
        # the real library keeps its settings in a UserDict, which is not a dict
        self.settings, self.windows, self.seen, self.started = UserDict(), [], None, None

    def create_window(self, title, url, **options):
        self.windows.append((title, url, options))

    def start(self, **options):
        self.started = options
        _, url, _ = self.windows[0]
        with urllib.request.urlopen(url, timeout=5) as response:
            self.seen = (response.status, response.read())
        with urllib.request.urlopen(url + "api/config", timeout=5) as response:
            self.config = json.loads(response.read())


class FakeWindow:
    def create_file_dialog(self, kind, **options):
        self.asked = (kind, options)
        return self.answer


class Desktop(unittest.TestCase):
    def test_the_page_can_ask_the_window_only_for_a_file_chooser(self):
        fake, window = FakeWebview(), FakeWindow()
        fake.FileDialog = type("FileDialog", (), {"OPEN": 10})
        bridge = desktop.Bridge(fake)
        self.assertEqual(bridge.choose_evidence(), "")              # no window yet
        fake.windows.append(window)
        window.answer = ("/cases/one/facts.json",)
        self.assertEqual(bridge.choose_evidence(), "/cases/one/facts.json")
        self.assertEqual(window.asked[0], 10)
        self.assertFalse(window.asked[1]["allow_multiple"])
        window.answer = None                                        # cancelled
        self.assertEqual(bridge.choose_evidence(), "")
        window.answer = ("/a", "/b")                                # only ever one path
        self.assertEqual(bridge.choose_evidence(), "/a")

    def test_window_gives_the_location_of_a_dropped_file_by_name_once(self):
        self.assertIsNone(desktop._drops(FakeWebview()))            # a library that keeps no record of drops
        fake = FakeWebview()
        fake.dom = type("Dom", (), {"_dnd_state": {"num_listeners": 0, "paths": []}})
        drops = desktop._drops(fake)
        state = fake.dom._dnd_state
        self.assertEqual(state["num_listeners"], 1)                 # the window records drops only when asked to
        here = self.root / "case facts.json"
        here.write_text("{}")
        self.assertEqual(drops.path("case facts.json"), "")         # nothing was dropped
        state["paths"] += [("other.json", str(self.root / "other.json")), ("case facts.json", str(here))]
        self.assertEqual(drops.path("other.json"), "")              # recorded, but there is no such file
        self.assertEqual(state["paths"], [])                        # every drop is read once
        state["paths"] += [("case facts.json", str(here))]
        self.assertEqual(drops.path("case facts.json"), str(here))
        self.assertEqual(drops.path("case facts.json"), "")
        state["paths"] += [("cafe\u0301.json", str(here))]           # the same name, written with a combining accent
        self.assertEqual(drops.path("caf\u00e9.json"), str(here))
        manager = FakeManager()
        self.assertEqual(desktop.run(self.root, 0, webview=fake, manager=manager), 0)
        self.assertIs(fake.config["drop"], True)

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def test_window_shows_the_loopback_server_and_closing_it_stops_the_server(self):
        fake, manager = FakeWebview(), FakeManager()
        self.assertEqual(desktop.run(self.root, 0, webview=fake, manager=manager), 0)
        title, url, options = fake.windows[0]
        self.assertEqual(title, "Conan")
        self.assertTrue(url.startswith("http://127.0.0.1:"))
        self.assertEqual(options["min_size"], (900, 600))
        self.assertNotIn("js_api", options)                # the page asks through the server instead
        self.assertIs(fake.config["chooser"], True)
        self.assertIs(fake.config["drop"], False)           # this stand-in keeps no record of dropped files
        self.assertEqual(fake.seen[0], 200)
        self.assertIn(b"CONAN-F", fake.seen[1])
        self.assertTrue(fake.settings["ALLOW_DOWNLOADS"])
        self.assertEqual(fake.started, {"private_mode": False})
        self.assertTrue(manager.closed)
        port = int(url.rsplit(":", 1)[1].strip("/"))
        with socket.socket() as probe:
            self.assertNotEqual(probe.connect_ex(("127.0.0.1", port)), 0)

    def test_server_stops_when_the_window_fails(self):
        class Broken(FakeWebview):
            def start(self, **options):
                raise RuntimeError("no display")
        manager = FakeManager()
        with self.assertRaises(RuntimeError):
            desktop.run(self.root, 0, webview=Broken(), manager=manager)
        self.assertTrue(manager.closed)

    def test_keeps_to_one_port_and_falls_back_when_it_is_taken(self):
        with socket.socket() as holder:             # something else has the usual port
            holder.bind(("127.0.0.1", 0))
            holder.listen(1)
            taken = holder.getsockname()[1]
            with patch.object(desktop, "PORT", taken):
                fallback = FakeWebview()
                desktop.run(self.root, webview=fallback, manager=FakeManager())
                self.assertNotEqual(fallback.windows[0][1], f"http://127.0.0.1:{taken}/")
                self.assertEqual(fallback.seen[0], 200)
        with patch.object(desktop, "PORT", taken):   # free again: the window returns to it
            usual = FakeWebview()
            desktop.run(self.root, webview=usual, manager=FakeManager())
            self.assertEqual(usual.windows[0][1], f"http://127.0.0.1:{taken}/")

    def test_missing_window_library_is_explained(self):
        with patch.dict(sys.modules, {"webview": None}):
            with self.assertRaises(desktop.DesktopUnavailable) as raised:
                desktop.run(self.root, 0, manager=FakeManager())
        self.assertIn(".[desktop]", str(raised.exception))

    @unittest.skipUnless(sys.platform == "darwin", "application bundles are a macOS format")
    def test_make_app_writes_a_launcher_and_never_overwrites(self):
        bundle = desktop.make_app(self.root / "Applications", root=self.root, executable="/opt/py thon/bin/python")
        self.assertEqual(bundle.name, "Conan.app")
        with (bundle / "Contents" / "Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
        self.assertEqual(info["CFBundleExecutable"], "Conan")
        self.assertEqual(info["CFBundleName"], "Conan")
        self.assertEqual(info["CFBundleIconFile"], "Conan")
        icon = bundle / "Contents" / "Resources" / "Conan.icns"
        self.assertEqual(icon.read_bytes(), desktop.ICON.read_bytes())
        self.assertEqual(icon.read_bytes()[:4], b"icns")
        launcher = bundle / "Contents" / "MacOS" / "Conan"
        self.assertTrue(launcher.stat().st_mode & 0o111)
        script = launcher.read_text()
        self.assertIn("exec '/opt/py thon/bin/python' -m app.desktop", script)
        self.assertIn(f"cd {self.root.resolve()}", script)
        self.assertIn("export PATH=", script)
        with self.assertRaises(ValueError):
            desktop.make_app(self.root / "Applications", root=self.root)

    def test_conan_command_opens_the_window_and_keeps_every_cop_subcommand(self):
        from app import cli
        with patch("app.desktop.run", return_value=0) as window:
            self.assertEqual(cli.conan([], root=self.root), 0)
            window.assert_called_once_with(root=self.root, port=None)
            self.assertEqual(cli.conan(["desktop", "--port", "9123"], root=self.root), 0)
            window.assert_called_with(root=self.root, port=9123)
        with patch("app.server.serve") as serve:
            self.assertEqual(cli.conan(["serve", "--no-open"], root=self.root), 0)
            serve.assert_called_once()
        with patch("sys.stdout"), self.assertRaises(SystemExit) as stopped:
            cli.conan(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        self.assertEqual(cli._parser("conan").prog, "conan")

    @unittest.skipUnless(sys.platform == "darwin", "macOS application bundles")
    def test_make_app_replaces_only_a_bundle_it_wrote(self):
        bundle = desktop.make_app(self.root / "Applications", root=self.root, executable="/py")
        again = desktop.make_app(self.root / "Applications", root=self.root, executable="/py2", replace=True)
        self.assertIn("/py2", (again / "Contents" / "MacOS" / desktop.TITLE).read_text())
        (bundle / "Contents" / "MacOS" / desktop.TITLE).write_text("#!/bin/sh\necho someone else's app\n")
        with self.assertRaises(ValueError):
            desktop.make_app(self.root / "Applications", root=self.root, replace=True)
        self.assertIn("someone else", (bundle / "Contents" / "MacOS" / desktop.TITLE).read_text())

    @unittest.skipIf(sys.platform == "darwin", "only other systems refuse")
    def test_make_app_is_refused_off_macos(self):
        with self.assertRaises(ValueError):
            desktop.make_app(self.root)


if __name__ == "__main__":
    unittest.main()
