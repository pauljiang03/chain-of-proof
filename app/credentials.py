"""The Anthropic API key: from ANTHROPIC_API_KEY, or a user-only file in the per-user settings folder.

The settings folder is outside every project, so the key cannot be committed with a case.
The key is never written to a run folder or a log, and no reply to the page contains it.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

ENV = "ANTHROPIC_API_KEY"
FILE = "anthropic-api-key"


def folder() -> Path:
    """The per-user settings folder for this tool."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "conan-f"


def clean(value) -> str:
    """The trimmed key; the ValueError for a bad value contains no part of it."""
    key = value.strip() if isinstance(value, str) else ""
    if not 20 <= len(key) <= 512 or any(not 33 <= ord(c) <= 126 for c in key):
        raise ValueError("That does not look like an API key.")
    return key


def saved(directory) -> str | None:
    """The usable key in the settings folder, or None."""
    if directory is None:
        return None
    try:
        return clean((Path(directory) / FILE).read_text(encoding="ascii"))
    except (OSError, ValueError):
        return None


def source(directory=None, environ=None) -> str | None:
    """Where the key would come from: "environment", "saved", or None when there is no key."""
    environ = os.environ if environ is None else environ
    if (environ.get(ENV) or "").strip():
        return "environment"
    return "saved" if saved(directory) else None


def key(directory=None, environ=None) -> str | None:
    environ = os.environ if environ is None else environ
    return (environ.get(ENV) or "").strip() or saved(directory)


def save(value, directory) -> None:
    """Atomically write the key to a file only this user can read."""
    text, directory = clean(value), Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle, temporary = tempfile.mkstemp(dir=directory, prefix=".key-")   # created with mode 0600
    try:
        with os.fdopen(handle, "w", encoding="ascii") as stream:
            stream.write(text + "\n")
        os.replace(temporary, directory / FILE)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def clear(directory) -> None:
    try:
        (Path(directory) / FILE).unlink()
    except FileNotFoundError:
        pass


def check(value, model) -> str:
    """Ask Anthropic whether the key can use the model, without a model run.

    Returns "ok", "rejected", "no_model", "offline" or "unknown".
    """
    import anthropic

    client = anthropic.Anthropic(api_key=value, max_retries=1, timeout=15.0)
    try:
        client.models.retrieve(model)
    except anthropic.AuthenticationError:
        return "rejected"
    except (anthropic.NotFoundError, anthropic.PermissionDeniedError):
        return "no_model"
    except anthropic.APIConnectionError:
        return "offline"
    except anthropic.APIError:
        return "unknown"
    return "ok"
