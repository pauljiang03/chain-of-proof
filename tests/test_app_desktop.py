"""The desktop window wraps the same loopback server and stops it on close."""
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


class FakeWebview:
    """Stands in for pywebview: `start` blocks while the window is open."""

    def __init__(self):
        self.settings, self.windows, self.seen, self.started = {}, [], None, None

    def create_window(self, title, url, **options):
        self.windows.append((title, url, options))

    def start(self, **options):
        self.started = options
        _, url, _ = self.windows[0]
        with urllib.request.urlopen(url, timeout=5) as response:
            self.seen = (response.status, response.read())


class Desktop(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def test_window_shows_the_loopback_server_and_closing_it_stops_the_server(self):
        fake, manager = FakeWebview(), FakeManager()
        self.assertEqual(desktop.run(self.root, 0, webview=fake, manager=manager), 0)
        title, url, options = fake.windows[0]
        self.assertEqual(title, "CONAN-F")
        self.assertTrue(url.startswith("http://127.0.0.1:"))
        self.assertEqual(options["min_size"], (1120, 700))
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
        self.assertEqual(bundle.name, "CONAN-F.app")
        with (bundle / "Contents" / "Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
        self.assertEqual(info["CFBundleExecutable"], "CONAN-F")
        launcher = bundle / "Contents" / "MacOS" / "CONAN-F"
        self.assertTrue(launcher.stat().st_mode & 0o111)
        script = launcher.read_text()
        self.assertIn("exec '/opt/py thon/bin/python' -m app.desktop", script)
        self.assertIn(f"cd {self.root.resolve()}", script)
        self.assertIn("export PATH=", script)
        with self.assertRaises(ValueError):
            desktop.make_app(self.root / "Applications", root=self.root)

    @unittest.skipIf(sys.platform == "darwin", "only other systems refuse")
    def test_make_app_is_refused_off_macos(self):
        with self.assertRaises(ValueError):
            desktop.make_app(self.root)


if __name__ == "__main__":
    unittest.main()
