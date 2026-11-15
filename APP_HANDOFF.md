# Local investigation app

The user requested a front end and CLI with a report as output, described as an AI investigator for digital forensics. This supersedes the earlier finish-pass restriction on new UI. Build locally in this repository; do not deploy forensic data or start a live model/benchmark.

Base: main `9f67dfd`. Root integrates and pushes. Use the existing investigator, restricted tools, audit, certificates, and report. No new agent framework or proof rules.

## Ownership

| Lane | Owner | Files |
| --- | --- | --- |
| U1 | Other terminal coordinator and workers | `app/server.py`, `app/jobs.py`, `app/cli.py`, `pyproject.toml`, `tests/test_app_server.py`, `tests/test_app_cli.py`, optional job tests |
| U2 | Root UI worker | `app/static/index.html`, `app/static/app.js`, `app/static/style.css` |
| U3 | Root report worker | `app/report.py`, `tests/test_app_report.py` |
| U0 | Root | `app/__init__.py`, integration, browser QA, docs and handoff |

## User workflow

Run `cop serve` (also `python -m app.cli serve`) to open a loopback browser app. List existing reports, start an investigation with an extracted facts file and public questions, inspect actual activity and progress, stop a run, and download HTML/Markdown/JSON. Raw disk extraction remains the existing separate CLI; label the facts input clearly. Never imply that arbitrary raw images are accepted by the investigator.

`cop investigate` wraps the existing `agent.run` with a new name, explicit facts/backend/model/minutes, optional public profile, and optional repeated free-text `--question` plus `--title`/`--brief`. Keep `--no-score` for the product path. Generate a temporary public profile when free-text questions are supplied. Preserve existing output directories. Print the output report path. The CLI also exposes `report`, `verify`, and `package` by delegating to existing components where possible. `report` uses U3 HTML or existing Markdown; never invent proof results. Core package includes app/static assets and a `cop` console entry point.

## HTTP contract

JSON responses use UTF-8 and `{error: "safe explanation"}` on failure. Same-origin only. Server listens on `127.0.0.1`, validates Host/Origin, and requires `X-COP-Token` for writes. The browser gets the per-server token from config. Never return credentials or raw provider exceptions. Use a fixed static-file/artifact allowlist; validate run names and reject symlink/path traversal. One active investigation is sufficient.

* `GET /api/config` -> `{token, defaults:{facts,backend,model,minutes}, backends:[{id,label,available}], active_run:null|string}`. Availability describes local executable/dependency/key presence, not successful authentication.
* `GET /api/runs` -> `{runs:[{name,title,status,generated_at,verified,rejected,sample?}]}`. Status is `running`, `completed`, `partial`, `failed`, `cancelled`, or `saved` (unknown legacy execution). The fixed sample may use name `sample`; clearly label it synthetic. Exclude internal probe directories and never scan arbitrary JSON siblings.
* `GET /api/run?name=...` -> `{name,status,run:null|<existing run bundle>,events:[...],error:null|string}`. Events are recent completed audit entries with `sequence`, `tool`, `outcome`, `completed_at`, `finding_id`, `arguments`; keep private references/provider transcripts out. During a run, `run` may be null; show observed activity rather than invented progress percentages.
* `POST /api/investigations` body `{name,facts,title,brief,questions:[string],backend,model,minutes}` -> `{name,status}`. Validate before spawn. Start only from this explicit action. Subprocess argv, no shell. Use the same CLI/runner pipeline; the public prompt contains no scorer/reference.
* `POST /api/stop` body `{name}` -> `{name,status}`. Stop only the app-owned active job, terminate its actual investigator child as well, retain logs and partial certificates, and export a partial report when possible. Mark cancellation honestly.
* `GET /api/report?name=...&format=html|md|json&download=1` -> fixed report artifact. HTML comes from `app.report.render_html(run)`. Markdown uses the existing renderer. JSON is the run bundle. Download filenames are sanitized. Unfinished runs with no report return a clear error.

No private-reference/scoring/upload/API-key routes. Package export and independent verification are CLI operations in v1. Poll active runs every 2 seconds; no WebSocket dependency. Clearly show failed and cancelled outcomes. Never display process exit alone as proof verification.

## U3 HTML report

Public API `render_html(run: dict) -> str`. Produce standalone HTML with embedded CSS, print styles, no remote assets/scripts, escaped untrusted text, and evidence/proof anchors. Include certified sentences exactly, strength labels, all cited records and available provenance, embedded Lean, diagnostic needs, separate judgments, audit/coverage/history when supplied. Preserve missing measurements as unknown. A report is a rendering, not an independent verification result. Printable HTML supports browser Save as PDF; do not pretend a native PDF export exists.

## Validation

Use synthetic jobs and temporary run roots; no provider calls. Test public-input validation, no overwrites, failed/cancelled jobs, path/Origin protection, truthful run state, literal evidence rendering, and downloadable outputs. Root tests the UI in a browser using saved/synthetic reports. Existing benchmark outputs remain unchanged. Root runs combined regression and pushes after integration.
