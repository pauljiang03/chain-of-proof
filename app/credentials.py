"""The Anthropic API key for the API investigator: where it comes from and where it is kept.

The key is taken from the ANTHROPIC_API_KEY environment variable when that is set. Otherwise it
is read from one file in the user's own settings folder. That folder is outside every project
folder, so the key cannot be committed with a case, and the file is readable by that user only.
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
    """The key without surrounding space. Raises ValueError, with no part of the value, if it cannot be one."""
    key = value.strip() if isinstance(value, str) else ""
    if not 20 <= len(key) <= 512 or any(not 33 <= ord(c) <= 126 for c in key):
        raise ValueError("That does not look like an API key.")
    return key


def saved(directory) -> str | None:
    """The key in the settings folder, or None when there is none that can be used."""
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
    """Write the key so that only this user can read it. The old file is replaced in one step."""
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
    """Ask Anthropic whether this key can use this model. One small request; it starts no model run.

    Returns "ok", "rejected" (the key is wrong), "no_model" (the key cannot use this model),
    "offline" (Anthropic could not be reached) or "unknown".
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
