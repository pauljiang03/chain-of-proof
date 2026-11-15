"""Local investigation commands. Run ``cop --help`` or ``python -m app.cli --help``."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
POLL_SECONDS = 2


def _job_manager(root):
    from app.jobs import JobManager
    return JobManager(root=root)


def _positive(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _port(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("port must be an integer from 0 to 65535") from error
    if not 0 <= number <= 65535:
        raise argparse.ArgumentTypeError("port must be an integer from 0 to 65535")
    return number


def _print_report(manager, name, root, snapshot):
    if snapshot.get("run") is None:
        print("No report is available for this run.", file=sys.stderr)
        return False
    directory = Path(root).resolve() / "runs" / name
    html = directory / "report.html"
    if html.is_symlink() or (html.exists() and not html.is_file()):
        raise ValueError("HTML report output is not a regular file")
    if html.is_file():
        print(f"Report: {html}")
        return True
    try:
        content, content_type, _ = manager.report(name, "html")
    except ImportError:
        # The Markdown path remains usable while the optional app renderer is
        # unavailable in a checkout. No provider or investigation is retried.
        pass
    else:
        if not isinstance(content, bytes) or content_type.split(";", 1)[0] != "text/html":
            raise ValueError("HTML report renderer returned an invalid artifact")
        directory.mkdir(parents=True, exist_ok=True)
        with html.open("xb") as stream:
            stream.write(content)
        print(f"Report: {html}")
        return True
    # The manager may finalize a missing Markdown artifact for this owned job.
    manager.report(name, "md")
    path = directory / "report.md"
    if not path.is_file() or path.is_symlink():
        print("The run has a report, but no report file was saved.", file=sys.stderr)
        return False
    print(f"Report: {path}")
    return True


def _investigate(args, root):
    payload = {"name": args.name, "facts": args.facts, "questions": args.question or []}
    # The same manager supplies backend-aware defaults to the UI and CLI.
    for field in ("title", "brief", "backend", "model", "minutes"):
        value = getattr(args, field)
        if value is not None:
            payload[field] = value
    manager = _job_manager(root)
    try:
        started = manager.start(payload, case_profile=args.case_profile, question_profile=args.questions)
        name = started["name"]
        print(f"Investigation: {name}", flush=True)
        interrupted = False
        try:
            while True:
                snapshot = manager.get_run(name)
                if snapshot.get("status") != "running":
                    break
                time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            interrupted = True
            manager.stop(name)
            snapshot = manager.get_run(name)
        status = snapshot.get("status", "unknown")
        print(f"Status: {status}")
        if snapshot.get("error"):
            print(snapshot["error"], file=sys.stderr)
        has_report = _print_report(manager, name, root, snapshot)
        if interrupted:
            return 130
        return 0 if status == "completed" and has_report else 1
    finally:
        manager.close()


def _report(args):
    output = Path(args.out) if args.out else None
    if output is not None and (output.exists() or output.is_symlink()):
        raise ValueError(f"refusing to overwrite existing report output: {output}")
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("run JSON contains a duplicate key")
            value[key] = item
        return value

    def finite(_value):
        raise ValueError("run JSON contains a non-finite number")

    data = json.loads(Path(args.run).read_text(encoding="utf-8"),
                      object_pairs_hook=unique, parse_constant=finite)
    if not isinstance(data, dict) or not isinstance(data.get("findings"), list):
        raise ValueError("run must be a JSON object with a findings list")
    if args.format == "html":
        from app.report import render_html
        rendered = render_html(data)
    elif args.format == "md":
        from checker.report import render
        rendered = render(data)
    else:
        rendered = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if output is None:
        sys.stdout.write(rendered)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
        print(f"Report: {output.resolve()}")
    return 0


def _parser():
    parser = argparse.ArgumentParser(prog="cop", description="Local AI investigation of extracted forensic records.")
    commands = parser.add_subparsers(dest="command", required=True)
    investigate = commands.add_parser("investigate", help="investigate extracted facts and save a report")
    investigate.add_argument("--name", required=True, help="new run name; existing runs are preserved")
    investigate.add_argument("--facts", required=True, help="extracted fact store; not a raw disk image")
    investigate.add_argument("--backend", choices=("claude-code", "deepagents"), help="default: claude-code")
    investigate.add_argument("--model", help="model name; default depends on the selected backend")
    investigate.add_argument("--minutes", type=_positive, help="positive time budget in minutes; default: 45")
    investigate.add_argument("--title", help="public case title")
    investigate.add_argument("--brief", help="public case brief")
    investigate.add_argument("--question", action="append", help="public question; repeat for multiple questions")
    investigate.add_argument("--case-profile", help="public case-profile JSON path")
    investigate.add_argument("--questions", help="public schema-v2 question-profile JSON path")
    serve = commands.add_parser("serve", help="open the local browser app on 127.0.0.1")
    serve.add_argument("--port", type=_port, default=8765)
    serve.add_argument("--no-open", "--no-browser", dest="no_open", action="store_true",
                       help="start the server without opening a browser")
    report = commands.add_parser("report", help="render an existing run; does not independently verify its claims")
    report.add_argument("--run", required=True, help="saved run JSON")
    report.add_argument("--format", choices=("html", "md", "json"), default="html")
    report.add_argument("--out", help="new output file; omit to write to stdout")
    commands.add_parser("verify", add_help=False, help="delegate to the independent certificate verifier")
    commands.add_parser("package", add_help=False, help="build or verify a portable verification package")
    return parser


def main(argv=None, *, root=ROOT):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Keep the existing verifier/package argument contracts and exit statuses.
    if argv and argv[0] == "verify":
        from verifier.verify import main as verify_main
        return verify_main(argv[1:])
    if argv and argv[0] == "package":
        from verifier.package import main as package_main
        return package_main(argv[1:])
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "investigate":
            return _investigate(args, root)
        if args.command == "serve":
            from app.server import serve
            serve(root=root, port=args.port, open_browser=not args.no_open)
            return 0
        return _report(args)
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
