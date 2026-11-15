"""Conan, the CONAN-F desktop application: the local workbench in a native window.

    conan                                         # or: cop desktop, python -m app.desktop
    python -m app.desktop --make-app ~/Applications   # macOS: a double-clickable Conan.app

The window is the operating system's own web view (WebKit on macOS, WebView2 on
Windows, WebKitGTK on Linux) through pywebview, so no browser engine is bundled. It
shows the same loopback server as `cop serve` and stops it when the window closes. The
server keeps to one port when it can, so that the window remembers per-case conveniences
(findings marked for a report, cover details) from one start to the next.

Install the one extra dependency with:  pip install -e '.[desktop]'
"""
from __future__ import annotations

import argparse
import os
import plistlib
import shlex
import shutil
import sys
import threading
from collections.abc import MutableMapping
from pathlib import Path

from app.server import ROOT, create_server

TITLE = "Conan"   # the application's name: window, menu bar and launcher; the workbench inside is CONAN-F
ICON = Path(__file__).resolve().parent / "assets" / "Conan.icns"   # built by scripts/make_icon.py
PORT = 8766   # next to `cop serve` on 8765; any free port is used when this one is taken
BUNDLE_ID = "dev.conan-f.workbench"
WINDOW = {"width": 1600, "height": 1000, "min_size": (900, 600)}


class DesktopUnavailable(RuntimeError):
    """The native window library is not installed."""


class Bridge:
    """The one thing the page may ask the native window for: a file chooser.

    A page cannot learn a file's path from a browser file input, so the window's own open
    panel supplies it. Nothing is opened or read here; the path goes into a text box and
    the server checks it like a typed one. The page asks through the local server
    (POST /api/choose): the app's script policy forbids eval, which pywebview's own page
    bridge needs, so that bridge never reaches the page.
    """

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


def _webview():
    try:
        import webview
    except ImportError:
        raise DesktopUnavailable("the desktop window needs pywebview. Install it with: "
                                 "pip install -e '.[desktop]'  (or use `cop serve` in a browser)") from None
    return webview


def _name_the_application():
    """On macOS the menu bar would otherwise read "Python", under Python's own Dock icon."""
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
    except OSError:   # in use, for instance by a second window
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
        webview.create_window(TITLE, url, text_select=True, **WINDOW)
        webview.start(private_mode=False)   # keep the window's own storage between starts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


def make_app(directory, root=ROOT, executable=None) -> Path:
    """Write a small macOS application bundle that starts the workbench from this checkout.

    The bundle holds no code of its own: it runs this Python environment, so it works on
    the machine it was made on. The search path is copied in because applications started
    from the Finder do not inherit the shell's, and Lean has to be found.
    """
    if sys.platform != "darwin":
        raise ValueError("--make-app writes a macOS application bundle; on this system use `cop desktop`")
    bundle = Path(directory).expanduser() / f"{TITLE}.app"
    if bundle.exists() or bundle.is_symlink():
        raise ValueError(f"refusing to overwrite existing application: {bundle}")
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
    launcher.write_text("\n".join([
        "#!/bin/sh",
        "# Written by `python -m app.desktop --make-app`. Starts Conan (CONAN-F) from its checkout.",
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
    args = parser.parse_args(argv)
    try:
        if args.make_app:
            print(make_app(args.make_app))
            return 0
        return run(port=args.port)
    except (DesktopUnavailable, ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
