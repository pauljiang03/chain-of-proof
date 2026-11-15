#!/bin/sh
# Set up Conan (CONAN-F) in this folder and open it.
#
#   git clone https://github.com/pauljiang03/conan && cd conan && ./install.sh
#
# macOS: adds Conan.app, with its icon, to ~/Applications and opens it. Run this script
# again after `git pull`; it replaces only a Conan.app that it wrote.
# Other systems: opens the same window with .venv/bin/conan.
set -eu
cd "$(dirname "$0")"

# Python 3.9 or newer. 3.11 or newer also installs the Anthropic API investigator.
PY=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
    PY=$candidate; break
  fi
done
if [ -z "$PY" ]; then
  echo "Conan needs Python 3.9 or newer. Install it from https://www.python.org/downloads/ and run ./install.sh again." >&2
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "Creating .venv with $("$PY" --version 2>&1)..."
  "$PY" -m venv .venv
fi
extras=desktop
if .venv/bin/python -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then extras=desktop,agent; fi
echo "Installing Conan and its window ($extras)..."
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -e ".[$extras]"
[ "$extras" = desktop ] && echo "Note: the Anthropic API investigator needs Python 3.11 or newer; this setup uses $(.venv/bin/python --version 2>&1)."

if [ "$(uname -s)" = Darwin ]; then
  mkdir -p "$HOME/Applications"
  app=$(.venv/bin/python -m app.desktop --make-app "$HOME/Applications" --replace)
  echo "Installed $app"
  open "$app"
else
  echo "Opening Conan. Next time, run: $(pwd)/.venv/bin/conan"
  exec .venv/bin/conan
fi
