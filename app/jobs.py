"""Local, single-job access to the existing investigator and report pipeline.

The internal worker is a subprocess, never a new investigator implementation.
Only an explicit ``start`` launches it. Provider output is not exposed by this API.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timedelta
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid

from agent.case import read_question_profile, select_case, with_questions
from checker import export, report as markdown_report
from checker.facts import open_source


ROOT = Path(__file__).resolve().parent.parent
SAMPLE = Path(__file__).resolve().parent / "sample"
STATUSES = {"running", "completed", "partial", "failed", "cancelled", "saved"}
PAYLOAD_FIELDS = {"name", "facts", "title", "brief", "questions", "backend", "model", "minutes"}
EVENT_FIELDS = ("sequence", "tool", "outcome", "completed_at", "finding_id", "arguments")
ARGUMENT_FIELDS = {"forms": (), "sql": ("query",), "fact": ("id", "fact_id"),
                   "check": ("question", "claim", "revises"), "conclude": ("text", "finding_ids"),
                   "plan": (), "update_question": ("question_id", "finding_ids", "searched", "unresolved", "next_actions", "status"),
                   "review": (), "evidence_needs": ("proof_gap",), "collect": ("reader", "exhibit")}
GRACE_SECONDS = 2.0
KILL_SECONDS = 1.0


def _name(value):
    if (not isinstance(value, str) or not value or len(value) > 128
            or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", part) for part in value.split("/"))):
        raise ValueError("Use a relative run name containing letters, digits, dots, underscores, and hyphens.")
    if any(part.startswith(".") or part in ("gate-probes", "probes") for part in value.split("/")):
        raise ValueError("That run name is reserved for internal artifacts.")
    return value


def _directory(root, name):
    name = _name(name)
    path = Path(root) / "runs"
    for part in [None] + name.split("/"):
        if part is not None:
            path = path / part
        if path.is_symlink():
            raise ValueError("Run paths cannot contain symlinks.")
        if path.exists() and not path.is_dir():
            raise ValueError("Run paths must be directories.")
    return path


def _open(path):
    if Path(path).is_symlink():
        raise ValueError("Run artifacts cannot be symlinks.")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError("Run artifacts must be regular files.")
    return os.fdopen(fd, "rb")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate metadata key.")
        result[key] = value
    return result


def _invalid_json(_value):
    raise ValueError("Non-finite metadata value.")


def _read_json(path):
    with _open(path) as stream:
        value = json.load(stream, object_pairs_hook=_unique_pairs, parse_constant=_invalid_json)
    if not isinstance(value, dict):
        raise ValueError("Saved metadata must be an object.")
    return value


def _atomic(path, value):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Run artifacts cannot be symlinks.")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".cop-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(value.encode("utf-8"))
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json(path, value):
    _atomic(path, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def _status(run):
    case = run.get("case")
    audit = run.get("audit")
    case = case if isinstance(case, dict) else {}
    audit = audit if isinstance(audit, dict) else {}
    ended = case.get("ended")
    if ended == "cancelled":
        return "cancelled"
    if case.get("is_error") or case.get("gate_error_type") or audit.get("status") == "invalid":
        return "failed"
    if ended == "time_limit":
        return "partial"
    if case.get("exit_code") not in (None, 0):
        return "failed"
    if ended == "success" and case.get("exit_code") in (None, 0):
        return "completed"
    return "failed" if ended else "saved"


def _safe_error(status):
    return "Investigation failed. Saved artifacts remain available." if status == "failed" else None


def _owned(directory, job_id):
    try:
        return _read_json(directory / "app-job.json").get("job_id") == job_id
    except (OSError, ValueError):
        return False


def _finish_partial(directory, spec, status):
    """Preserve source artifacts and assemble a partial bundle when they are readable."""
    if not _owned(directory, spec["job_id"]):
        return False
    try:
        metadata = {}
        if (directory / "run.json").is_file():
            try:
                existing = _read_json(directory / "run.json")
                if isinstance(existing.get("case"), dict):
                    metadata.update(existing["case"])
            except (OSError, ValueError):
                # Preserve a truncated owned output before replacing it with a
                # bundle rebuilt from the intact fixed certificate/log artifacts.
                with _open(directory / "run.json") as incoming, (directory / "interrupted-run.json").open("xb") as saved:
                    shutil.copyfileobj(incoming, saved)
        metadata.update(backend=spec["backend"], model=spec["model"], ended=status,
                        scoring_requested=False, is_error=status == "failed")
        data = export.bundle(directory, spec["title"], case_metadata=metadata)
        _write_json(directory / "run.json", data)
        _atomic(directory / "report.md", markdown_report.render(data))
        if not (directory / "results.json").exists():
            _write_json(directory / "results.json", {"schema_version": 2,
                "evaluation": {"measured": False, "reason": "Product investigation; no scoring requested"}})
        return True
    except Exception:
        # A cancelled write may leave an incomplete proposal/certificate. Keep it
        # intact for review rather than pretending a complete report was made.
        return False


def _needs_report(directory):
    try:
        value = _read_json(directory / "run.json")
        return (not isinstance(value.get("case"), dict) or not isinstance(value.get("findings"), list)
                or not (directory / "report.md").is_file())
    except (OSError, ValueError):
        return True


def _processes(popen=None):
    """PID, parent, process group and creation time; never read command lines."""
    try:
        # Use the original factory in a worker whose runtime Popen is guarded.
        with (popen or subprocess.Popen)(["ps", "-axo", "pid=,ppid=,pgid=,lstart="],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True) as process:
            try:
                output, _ = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                return {}
        if process.returncode:
            return {}
        rows = {}
        for line in output.splitlines():
            fields = line.split(None, 3)
            if len(fields) == 4:
                try:
                    rows[int(fields[0])] = (int(fields[1]), int(fields[2]), fields[3])
                except ValueError:
                    continue
        return rows
    except (OSError, subprocess.SubprocessError):
        return {}


def _descendants(pid, rows):
    selected, parents = {}, {pid}
    while parents:
        children = {child for child, entry in rows.items() if entry[0] in parents and child not in selected}
        selected.update({child: rows[child] for child in children})
        parents = children
    return selected


def _signal_known(identities, sig, popen=None):
    current = _processes(popen)
    for pid, old in identities.items():
        now = current.get(pid)
        # Parent IDs can change after reparenting, but PID/group/creation time
        # must still match the app-owned process captured before cancellation.
        if now is not None and now[1:] == old[1:]:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass


def _registered(path, rows):
    """Include direct children recorded before the worker handles deferred termination."""
    known = {}
    if path is None:
        return known
    try:
        entries = _read_json(path).get("children", {})
        for key, identity in entries.items():
            pid = int(key)
            if isinstance(identity, list) and len(identity) == 3:
                current = rows.get(pid)
                if current is not None and list(current[1:]) == identity[1:]:
                    known[pid] = current
                    known.update(_descendants(pid, rows))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return known


def _terminate(process, registry=None):
    rows = _processes()
    known = _descendants(process.pid, rows)
    known.update(_registered(registry, rows))
    try:
        if process.poll() is None:
            try:
                process.terminate()  # The worker turns SIGTERM into KeyboardInterrupt.
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            known.update(_descendants(process.pid, _processes()))
            _signal_known(known, signal.SIGTERM)
            if process.poll() is None:
                try:
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                except ProcessLookupError:
                    pass
            process.wait(timeout=KILL_SECONDS)
    finally:
        # Claude creates another session, and nested helpers can do so too. A
        # worker process-group signal alone would not stop these descendants.
        rows = _processes()
        known.update(_descendants(process.pid, rows))
        known.update(_registered(registry, rows))
        _signal_known(known, signal.SIGKILL)


class JobManager:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self._lock = threading.RLock()
        self._jobs = {}
        self._active = None
        self._closed = False

    def config(self):
        with self._lock:
            return {"defaults": {"facts": str(self.root / "evidence/case_facts.json"),
                                 "backend": "claude-code", "model": "opus", "minutes": 45},
                    "backends": [{"id": "claude-code", "label": "Claude Code", "available": shutil.which("claude") is not None},
                        {"id": "deepagents", "label": "Anthropic API", "available": bool(
                            importlib.util.find_spec("deepagents") and importlib.util.find_spec("langchain_anthropic")
                            and os.environ.get("ANTHROPIC_API_KEY"))}], "active_run": self._active}

    def _input(self, value, label):
        if not isinstance(value, (str, Path)) or not str(value).strip():
            raise ValueError(label + " must name a local file.")
        path = self.root / value
        if path.is_symlink() or not path.is_file():
            raise ValueError(label + " must be an existing regular file.")
        return path.resolve()

    def _prepare(self, payload, case_profile, question_profile):
        if not isinstance(payload, dict) or set(payload) - PAYLOAD_FIELDS:
            raise ValueError("Investigation fields are invalid; private scoring inputs are not accepted.")
        name = _name(payload.get("name"))
        if name == "sample":
            raise ValueError("The synthetic sample name is reserved.")
        facts = self._input(payload.get("facts"), "Facts")
        if facts.suffix not in (".json", ".duckdb"):
            raise ValueError("Supply an extracted .json or .duckdb fact store, not a raw disk image.")
        try:
            source = open_source(facts)
            source.all()
            if hasattr(source, "_db"):
                source._db.close()
        except Exception:
            raise ValueError("Facts must contain a readable extracted fact store.") from None
        backend = payload.get("backend", "claude-code")
        if backend not in ("claude-code", "deepagents"):
            raise ValueError("Choose a supported investigation backend.")
        model = payload.get("model")
        if model is not None and not isinstance(model, str):
            raise ValueError("Model must be a nonempty model identifier.")
        model = model or ("opus" if backend == "claude-code" else "claude-opus-5-5")
        if not isinstance(model, str) or not model.strip() or len(model) > 200 or any(ord(c) < 32 for c in model):
            raise ValueError("Model must be a nonempty model identifier.")
        minutes = payload.get("minutes", 45)
        if type(minutes) is not int or minutes <= 0:
            raise ValueError("Minutes must be a positive integer.")
        questions = payload.get("questions", [])
        if not isinstance(questions, list) or any(not isinstance(q, str) or not q.strip() for q in questions):
            raise ValueError("Questions must be a list of nonempty public question strings.")
        if questions and question_profile is not None:
            raise ValueError("Choose free-text questions or a question profile, not both.")
        for field in ("title", "brief"):
            if field in payload and not isinstance(payload[field], str):
                raise ValueError("Title and brief must be text.")
        try:
            context = self._input(case_profile, "Public case profile") if case_profile is not None else None
            public = self._input(question_profile, "Public questions") if question_profile is not None else None
            profile, _ = select_case(facts, context, default_facts=self.root / "evidence/case_facts.json")
            profile = replace(profile, name=payload.get("title", "").strip() or profile.name,
                              brief=payload.get("brief", "").strip() or profile.brief,
                              questions=tuple(q.strip() for q in questions) if questions else profile.questions)
            if public is not None:
                with_questions(profile, read_question_profile(public))
        except (OSError, ValueError, KeyError, TypeError):
            raise ValueError("Public case or question profile is invalid or conflicts with the selected case.") from None
        return {"name": name, "facts": str(facts), "backend": backend, "model": model,
                "minutes": minutes, "title": profile.name, "profile": profile.public_dict(),
                "question_profile": str(public) if public is not None else None}

    def _spawn(self, command, env):
        return subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=(os.name == "posix"))

    def start(self, payload, *, case_profile=None, question_profile=None,
              resume_from=None, intake_config=None):
        spec = self._prepare(payload, case_profile, question_profile)
        if resume_from is not None:
            from agent.continuation import parent
            spec["resume_from"] = str(parent(resume_from)["directory"])
        if intake_config is not None:
            spec["intake_config"] = str(self._input(intake_config, "Intake configuration"))
        with self._lock:
            if self._closed:
                raise RuntimeError("The job manager is closed.")
            if self._active is not None:
                raise RuntimeError("An investigation is already active.")
            directory = _directory(self.root, spec["name"])
            if directory.exists():
                raise FileExistsError("Run already exists; choose a new name.")
            if not next(item["available"] for item in self.config()["backends"] if item["id"] == spec["backend"]):
                raise RuntimeError("Selected backend is unavailable; check its local installation and credentials.")
            temporary = tempfile.TemporaryDirectory(prefix="cop-job-")
            stage = Path(temporary.name)
            spec.update(job_id=uuid.uuid4().hex)
            _write_json(stage / "profile.json", spec.pop("profile"))
            spec["case_profile"] = str(stage / "profile.json")
            _write_json(stage / "spec.json", spec)
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            command = [sys.executable, "-m", "app.jobs", "_worker", "--root", str(self.root),
                       "--spec", str(stage / "spec.json")]
            try:
                process = self._spawn(command, env)
            except OSError:
                temporary.cleanup()
                raise RuntimeError("Investigation worker could not start.") from None
            job = {"spec": spec, "temporary": temporary, "stage": stage, "process": process,
                   "status": "running", "error": None, "cancel_requested": False,
                   "termination_done": threading.Event(), "done": threading.Event()}
            self._jobs[spec["name"]] = job
            self._active = spec["name"]
            threading.Thread(target=self._watch, args=(spec["name"], job), daemon=True).start()
            return {"name": spec["name"], "status": "running"}

    def _watch(self, name, job):
        code = job["process"].wait()
        if job["cancel_requested"]:
            job["termination_done"].wait()
        spec = job["spec"]
        try:
            directory = _directory(self.root, name)
            status = "cancelled" if job["cancel_requested"] else "failed"
            if not job["cancel_requested"]:
                try:
                    outcome = _read_json(job["stage"] / "outcome.json")
                    if outcome.get("status") in STATUSES - {"running", "saved"}:
                        status = outcome["status"]
                except (OSError, ValueError):
                    if code == 0:
                        try:
                            status = _status(_read_json(directory / "run.json"))
                        except (OSError, ValueError):
                            pass
            if _owned(directory, spec["job_id"]):
                if status == "cancelled" or _needs_report(directory):
                    _finish_partial(directory, spec, status)
                _write_json(directory / "app-job.json", {"schema_version": 1, "job_id": spec["job_id"],
                    "name": name, "status": status, "title": spec["title"], "error": _safe_error(status)})
            with self._lock:
                job["status"], job["error"] = status, _safe_error(status)
        except Exception:
            with self._lock:
                job["status"], job["error"] = "failed", "Saved job artifacts could not be finalized."
        finally:
            job["temporary"].cleanup()
            with self._lock:
                if self._active == name:
                    self._active = None
                job["done"].set()

    def stop(self, name):
        name = _name(name)
        with self._lock:
            job = self._jobs.get(name)
            if name != self._active or job is None or job["status"] != "running":
                raise RuntimeError("Only this server's active investigation can be stopped.")
            already = job["cancel_requested"]
            finished = job["process"].poll() is not None
            if not finished:
                job["cancel_requested"] = True
        if not already and not finished:
            try:
                _terminate(job["process"], job["stage"] / "children.json")
            finally:
                job["termination_done"].set()
        if not job["done"].wait(timeout=GRACE_SECONDS + KILL_SECONDS + 10):
            raise RuntimeError("Cancellation is still finalizing saved artifacts.")
        return {"name": name, "status": job["status"]}

    def _location(self, name):
        name = _name(name)
        if name == "sample":
            if SAMPLE.is_symlink():
                raise ValueError("Sample cannot be a symlink.")
            return SAMPLE
        return _directory(self.root, name)

    def get_run(self, name):
        directory = self._location(name)
        with self._lock:
            job = self._jobs.get(name)
            status = job["status"] if job else None
            error = job["error"] if job else None
        if job is None and not directory.is_dir():
            raise FileNotFoundError("Run does not exist.")
        if job is None and not any((directory / item).exists() or (directory / item).is_symlink()
                                   for item in ("run.json", "app-job.json")):
            raise FileNotFoundError("Run does not exist.")
        data = None
        unreadable = False
        try:
            data = _read_json(directory / "run.json")
            if not isinstance(data.get("case"), dict) or not isinstance(data.get("stats"), dict) or not isinstance(data.get("findings"), list):
                raise ValueError("Run bundle is invalid.")
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            data = None
            unreadable = True
            error = None if status == "running" else "Saved run could not be read."
        if status is None:
            status = "failed" if unreadable else _status(data) if data else "saved"
            try:
                recorded = _read_json(directory / "app-job.json")
                if not unreadable and recorded.get("name") == name and recorded.get("status") in STATUSES - {"running"}:
                    status = recorded["status"]
            except (OSError, ValueError):
                pass
            error = error or _safe_error(status)
        events = []
        try:
            with _open(directory / "audit.jsonl") as stream:
                stream.seek(0, os.SEEK_END)
                start = max(0, stream.tell() - 1024 * 1024)
                stream.seek(start)
                raw_tail = stream.read(1024 * 1024)
                lines = raw_tail.splitlines()
                if start:
                    lines = lines[1:]
                if raw_tail and not raw_tail.endswith(b"\n"):
                    lines = lines[:-1]
                for raw in lines[-100:]:
                    try:
                        entry = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_invalid_json)
                        if not isinstance(entry, dict) or entry.get("tool") not in ARGUMENT_FIELDS:
                            continue
                        if (type(entry.get("sequence")) is not int or entry["sequence"] < 1
                                or entry.get("outcome") not in ("success", "rejected", "error")
                                or not isinstance(entry.get("completed_at"), str)):
                            continue
                        completed = datetime.fromisoformat(entry["completed_at"].replace("Z", "+00:00"))
                        if completed.utcoffset() != timedelta(0):
                            continue
                        event = {key: entry.get(key) for key in EVENT_FIELDS}
                        arguments = entry.get("arguments")
                        event["arguments"] = {key: _bounded(arguments[key]) for key in ARGUMENT_FIELDS[entry["tool"]]
                                               if isinstance(arguments, dict) and key in arguments}
                        events.append(event)
                    except (ValueError, UnicodeError):
                        continue
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            error = error or "Recent audit activity could not be read."
        return {"name": name, "status": status, "run": data, "events": events, "error": error}

    def list_runs(self):
        with self._lock:
            names = set(self._jobs)
        base = self.root / "runs"
        if base.is_symlink():
            raise ValueError("Run paths cannot contain symlinks.")
        if base.is_dir():
            for directory, children, files in os.walk(base, followlinks=False):
                children[:] = [child for child in children if not child.startswith(".")
                               and child not in ("gate-probes", "probes")
                               and not (Path(directory) / child).is_symlink()]
                if "run.json" in files or "app-job.json" in files:
                    name = str(Path(directory).relative_to(base)).replace(os.sep, "/")
                    try:
                        _name(name)
                        names.add(name)
                    except ValueError:
                        pass
        result = []
        for name in sorted(names):
            try:
                value = self.get_run(name)
            except (OSError, ValueError):
                continue
            data = value["run"] or {}
            case, stats = data.get("case", {}), data.get("stats", {})
            job = self._jobs.get(name)
            result.append({"name": name, "title": case.get("name") or (job["spec"]["title"] if job else name),
                           "status": value["status"], "generated_at": case.get("generated_at"),
                           "verified": stats.get("verified"), "rejected": stats.get("rejected"),
                           "sample": name == "sample"})
        return result

    def report(self, name, fmt, options=None):
        """Render a saved run. `options` (app.report.report_options) shapes the HTML report only."""
        if fmt not in ("html", "md", "json"):
            raise ValueError("Choose HTML, Markdown, or JSON report output.")
        if options is not None and fmt != "html":
            raise ValueError("Selections and sections apply to the HTML report.")
        snapshot = self.get_run(name)
        data = snapshot["run"]
        if data is None:
            raise FileNotFoundError("This investigation has no saved report yet.")
        if fmt == "html":
            from app.report import render_html
            text = render_html(data) if options is None else render_html(data, options)
            content_type = "text/html; charset=utf-8"
        elif fmt == "md":
            text, content_type = markdown_report.render(data), "text/markdown; charset=utf-8"
        else:
            text = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
            content_type = "application/json; charset=utf-8"
        return text.encode("utf-8"), content_type, "cop-" + name.replace("/", "-") + "." + fmt

    def close(self):
        with self._lock:
            self._closed = True
            active = self._active
        if active is not None:
            try:
                self.stop(active)
            except RuntimeError:
                pass


def _bounded(value, depth=0):
    if depth >= 5:
        return "[truncated]"
    if isinstance(value, str):
        return value[:2000] + ("…" if len(value) > 2000 else "")
    if isinstance(value, list):
        return [_bounded(item, depth + 1) for item in value[:20]]
    if isinstance(value, dict):
        return {key: _bounded(item, depth + 1) for key, item in list(value.items())[:20]}
    return value


def _worker(root, spec_path):
    """Run the existing CLI entry in a child with a graceful termination hook."""
    from agent import run

    spec = _read_json(spec_path)
    directory = _directory(root, spec["name"])
    original_root, original_prepare = run.ROOT, run.prepare_run_dir
    previous_term = signal.getsignal(signal.SIGTERM)
    owned = False
    original_popen = subprocess.Popen
    cancelled = threading.Event()
    children_lock = threading.RLock()
    children, identities = [], {}
    spawning = 0

    def terminate(_signum, _frame):
        cancelled.set()
        if not spawning:
            raise KeyboardInterrupt()

    def guarded_popen(*args, **kwargs):
        # Claude's session is created before its runner try/finally. Defer the
        # Python interrupt across spawn/registration without changing the child's
        # signal mask. No new runtime work may start after cancellation. An active
        # synchronous proof still uses the manager's bounded process-tree fallback.
        nonlocal spawning
        main_thread = threading.current_thread() is threading.main_thread()
        if main_thread:
            spawning += 1
        try:
            with children_lock:
                if cancelled.is_set():
                    raise RuntimeError("Investigation is stopping.")
                child = original_popen(*args, **kwargs)
                children.append(child)
                identity = _processes(original_popen).get(child.pid)
                if identity is not None:
                    identities[str(child.pid)] = identity
                    _write_json(Path(spec_path).parent / "children.json", {"children": identities})
                if cancelled.is_set() and child.poll() is None:
                    child.kill()
                return child
        finally:
            if main_thread:
                spawning -= 1
                if cancelled.is_set():
                    raise KeyboardInterrupt()

    def cleanup_children():
        with children_lock:
            rows = _processes(original_popen)
            known = _registered(Path(spec_path).parent / "children.json", rows)
            known.update(_descendants(os.getpid(), rows))
            _signal_known(known, signal.SIGKILL, original_popen)
            for child in children:
                if child.poll() is None:
                    try:
                        child.kill()
                        child.wait(timeout=KILL_SECONDS)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        pass

    def prepare(name, selected_root):
        nonlocal owned
        path = original_prepare(name, selected_root)
        owned = True
        _write_json(path / "app-job.json", {"schema_version": 1, "job_id": spec["job_id"],
            "name": spec["name"], "status": "running", "title": spec["title"], "error": None})
        return path

    args = ["--name", spec["name"], "--facts", spec["facts"], "--backend", spec["backend"],
            "--model", spec["model"], "--minutes", str(spec["minutes"]),
            "--case-profile", spec["case_profile"], "--no-score"]
    if spec.get("question_profile"):
        args += ["--questions", spec["question_profile"]]
    for key in ("resume_from", "intake_config"):
        if spec.get(key):
            args += ["--" + key.replace("_", "-"), spec[key]]
    status = "failed"
    try:
        run.ROOT, run.prepare_run_dir = Path(root).resolve(), prepare
        signal.signal(signal.SIGTERM, terminate)
        subprocess.Popen = guarded_popen
        try:
            code = run.main(args)
            status = _status(_read_json(directory / "run.json")) if code == 0 else "failed"
        except KeyboardInterrupt:
            status = "cancelled"
        except (Exception, SystemExit):
            status = "failed"
        # Finish all child writes before rebuilding a cancelled bundle. Repeated
        # cancellation during finalization is handled by the manager fallback.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        cleanup_children()
        if owned:
            if status == "cancelled" or _needs_report(directory):
                _finish_partial(directory, spec, status)
            _write_json(directory / "app-job.json", {"schema_version": 1, "job_id": spec["job_id"],
                "name": spec["name"], "status": status, "title": spec["title"], "error": _safe_error(status)})
        _write_json(Path(spec_path).parent / "outcome.json", {"status": status})
    finally:
        subprocess.Popen = original_popen
        run.ROOT, run.prepare_run_dir = original_root, original_prepare
        signal.signal(signal.SIGTERM, previous_term)
    return 0 if status in ("completed", "partial") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Internal investigation worker")
    parser.add_argument("mode", choices=("_worker",))
    parser.add_argument("--root", required=True)
    parser.add_argument("--spec", required=True)
    arguments = parser.parse_args()
    raise SystemExit(_worker(arguments.root, arguments.spec))
