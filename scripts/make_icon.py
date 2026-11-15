"""Build app/assets/Conan.icns from app/static/icon.svg.

    python scripts/make_icon.py

macOS only: it uses the system's `sips` and `iconutil`. The drawing lives in the SVG;
the .icns file is a build product kept in the repository so the app needs no build step.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "app" / "static" / "icon.svg"
TARGET = ROOT / "app" / "assets" / "Conan.icns"
SIZES = (16, 32, 128, 256, 512)   # each also at twice the size


def mac_svg(source: str) -> str:
    """The tile at the size macOS expects inside its canvas, over a soft shadow."""
    inner = source[source.index("<defs>"):source.rindex("</svg>")]
    shadow = "".join(
        f'<rect x="{100 - i * 3}" y="{114 - i * 3}" width="{824 + i * 6}" height="{824 + i * 6}" '
        f'rx="{184 + i * 3}" fill="#000" opacity="0.028"/>' for i in range(1, 9))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">'
            + shadow + '<g transform="translate(100 100) scale(0.8046875)">' + inner + "</g></svg>\n")


def run(*command) -> None:
    subprocess.run([str(part) for part in command], check=True, stdout=subprocess.DEVNULL)


def main() -> int:
    if sys.platform != "darwin":
        print("make_icon needs macOS (sips, iconutil)", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        drawing, base, iconset = scratch / "mac.svg", scratch / "base.png", scratch / "Conan.iconset"
        drawing.write_text(mac_svg(SOURCE.read_text()))
        iconset.mkdir()
        run("sips", "-s", "format", "png", "--resampleWidth", 1024, drawing, "--out", base)
        for size in SIZES:
            run("sips", "-z", size, size, base, "--out", iconset / f"icon_{size}x{size}.png")
            run("sips", "-z", size * 2, size * 2, base, "--out", iconset / f"icon_{size}x{size}@2x.png")
        TARGET.parent.mkdir(exist_ok=True)
        run("iconutil", "-c", "icns", iconset, "-o", TARGET)
    print(TARGET.relative_to(ROOT), TARGET.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
