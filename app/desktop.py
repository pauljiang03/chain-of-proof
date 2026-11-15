"""Conan, the CONAN-F desktop app: the local workbench in a native window.

    conan                                             # or: cop desktop, python -m app.desktop
    python -m app.desktop --make-app ~/Applications   # macOS: a double-clickable Conan.app

The window is the system web view, through pywebview, showing the same loopback server as
`cop serve`; closing it stops the server. Install with:  pip install -e '.[desktop]'
"""
from __future__ import annotations

import argparse
import os
import plistlib
import shlex
import shutil
import sys
import threading
import unicodedata
from collections.abc import MutableMapping
from pathlib import Path

from app.server import ROOT, create_server

TITLE = "Conan"   # window, menu bar and launcher name
ICON = Path(__file__).resolve().parent / "assets" / "Conan.icns"   # built by scripts/make_icon.py
PORT = 8766   # a fixed port keeps the window's local storage between starts; any free port if taken
BUNDLE_ID = "dev.conan-f.workbench"
WINDOW = {"width": 1600, "height": 1000, "min_size": (900, 600)}


class DesktopUnavailable(RuntimeError):
    """The native window library is not installed."""


class Bridge:
    """The native open panel, which gives the page a file path and reads nothing."""
    # Reached through POST /api/choose: pywebview's own page bridge needs eval, which the page's CSP forbids.

    def __init__(self, webview):
        self._webview = webview

    def choose_evidence(self):
        windows = getattr(self._webview, "windows", None) or []
        if not windows:
            return ""
        kind = getattr(getattr(self._webview, "FileDialog", None), "OPEN", None)
        if kind is None:
            kind = getattr(self._webview, "OPEN_DIALOG", 10)
        chosen = windows[0].create_file_dialog(
            kind, allow_multiple=False, file_types=("Evidence records (*.json;*.duckdb)", "All files (*.*)"))
        return str(chosen[0]) if chosen else ""


class Drops:
    """Paths of the files last dropped on the window, looked up by name; reads nothing."""

    def __init__(self, state):
        self._state = state
        state["num_listeners"] = state.get("num_listeners", 0) + 1   # pywebview records drops only with a listener

    def path(self, name):
        waiting, self._state["paths"] = list(self._state.get("paths") or ()), []   # each drop is read once
        same = lambda text: unicodedata.normalize("NFC", str(text))
        for base, full in reversed(waiting):
            if same(base) == same(name) and os.path.isfile(full):
                return str(full)
        return ""


def _drops(webview):
    """pywebview's record of dropped files, or None when this version keeps none."""
    state = getattr(getattr(webview, "dom", None), "_dnd_state", None)
    return Drops(state) if isinstance(state, dict) else None


def _webview():
    try:
        import webview
    except ImportError:
        raise DesktopUnavailable("the desktop window needs pywebview. Install it with: "
                                 "pip install -e '.[desktop]'  (or use `cop serve` in a browser)") from None
    return webview


def _name_the_application():
    """Name the macOS menu bar and Dock icon after the app instead of "Python"."""
    if sys.platform != "darwin":
        return
    try:
        from Foundation import NSBundle
        info = NSBundle.mainBundle().localizedInfoDictionary() or NSBundle.mainBundle().infoDictionary()
        if info is not None:
            info["CFBundleName"] = TITLE
        if ICON.is_file():
            import AppKit
            image = AppKit.NSImage.alloc().initWithContentsOfFile_(str(ICON))
            if image is not None:
                AppKit.NSApplication.sharedApplication().setApplicationIconImage_(image)
    except Exception:   # cosmetic only
        pass


def _server(root, port, manager):
    if port is not None:
        return create_server(root, port, manager=manager)
    try:
        return create_server(root, PORT, manager=manager)
    except OSError:   # port in use, for instance by a second window
        return create_server(root, 0, manager=manager)


def run(root=ROOT, port=None, *, webview=None, manager=None) -> int:
    """Serve the workbench on loopback and show it in a native window until it is closed."""
    webview = webview or _webview()
    server = _server(root, port, manager)
    url = f"http://127.0.0.1:{server.server_port}/"
    thread = threading.Thread(target=server.serve_forever, name="conan-f-server", daemon=True)
    thread.start()
    try:
        settings = getattr(webview, "settings", None)
        if isinstance(settings, MutableMapping):    # pywebview's settings are a UserDict, not a dict
            settings["ALLOW_DOWNLOADS"] = True          # report exports
            settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        _name_the_application()
        server.chooser = Bridge(webview).choose_evidence
        drops = _drops(webview)
        if drops is not None:
            server.dropped = drops.path
        webview.create_window(TITLE, url, text_select=True, **WINDOW)
        webview.start(private_mode=False)   # keep the window's own storage between starts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


MARK = "Written by `python -m app.desktop --make-app`"


def make_app(directory, root=ROOT, executable=None, replace=False) -> Path:
    """Write a macOS Conan.app that starts the workbench from this checkout and Python environment."""
    if sys.platform != "darwin":
        raise ValueError("--make-app writes a macOS application bundle; on this system use `cop desktop`")
    bundle = Path(directory).expanduser() / f"{TITLE}.app"
    if bundle.exists() or bundle.is_symlink():
        # With `replace`, only a bundle this function wrote is removed: its launcher carries MARK.
        launcher = bundle / "Contents" / "MacOS" / TITLE
        ours = not bundle.is_symlink() and launcher.is_file() and MARK in launcher.read_text(errors="replace")
        if not (replace and ours):
            raise ValueError(f"refusing to overwrite existing application: {bundle}")
        shutil.rmtree(bundle)
    launcher = bundle / "Contents" / "MacOS" / TITLE
    launcher.parent.mkdir(parents=True)
    info = {
        "CFBundleName": TITLE, "CFBundleDisplayName": TITLE, "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleExecutable": TITLE, "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "1", "LSMinimumSystemVersion": "11.0", "NSHighResolutionCapable": True,
    }
    if ICON.is_file():
        resources = bundle / "Contents" / "Resources"
        resources.mkdir()
        shutil.copyfile(ICON, resources / ICON.name)
        info["CFBundleIconFile"] = ICON.stem
    with (bundle / "Contents" / "Info.plist").open("wb") as stream:
        plistlib.dump(info, stream)
    # Finder-started apps do not inherit the shell's PATH, and Lean must be found.
    launcher.write_text("\n".join([
        "#!/bin/sh",
        f"# {MARK}. Starts Conan (CONAN-F) from its checkout.",
        f"export PATH={shlex.quote(os.environ.get('PATH', '/usr/bin:/bin'))}",
        f"cd {shlex.quote(str(Path(root).resolve()))} || exit 1",
        f"exec {shlex.quote(str(executable or sys.executable))} -m app.desktop",
        "",
    ]))
    launcher.chmod(0o755)
    return bundle


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cop desktop", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, help=f"loopback port; default: {PORT}, or any free port if it is taken")
    parser.add_argument("--make-app", metavar="DIR", help="macOS: write Conan.app into DIR and exit")
    parser.add_argument("--replace", action="store_true", help="with --make-app: replace a Conan.app this command wrote before")
    args = parser.parse_args(argv)
    try:
        if args.make_app:
            print(make_app(args.make_app, replace=args.replace))
            return 0
        return run(port=args.port)
    except (DesktopUnavailable, ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
