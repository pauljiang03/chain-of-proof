"""Same-origin, loopback-only HTTP interface to the local investigation jobs."""
from __future__ import annotations

import json
import re
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = Path(__file__).resolve().parent / "static"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/static/style.css": ("style.css", "text/css; charset=utf-8")}
REPORT_TYPES = {"html": "text/html; charset=utf-8", "md": "text/markdown; charset=utf-8",
                "json": "application/json; charset=utf-8"}
START_FIELDS = frozenset(("name", "facts", "title", "brief", "questions", "backend", "model", "minutes"))
MAX_BODY = 64 * 1024


class RequestError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def _reject_constant(value):
    raise ValueError("non-finite JSON number")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _name(value, root):
    if (not isinstance(value, str) or len(value) > 128 or not value
            or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", part)
                   for part in value.split("/"))):
        raise RequestError(400, "Invalid run name.")
    path = root / "runs"
    for part in [None] + value.split("/"):
        if part is not None:
            path /= part
        if path.is_symlink():
            raise RequestError(400, "Run paths cannot contain symlinks.")
    return value


def _start_payload(payload, root):
    if not isinstance(payload, dict) or set(payload) - START_FIELDS:
        raise RequestError(400, "Investigation fields do not match the public request contract.")
    name = _name(payload.get("name"), root)
    if name == "sample":
        raise RequestError(400, "The sample run name is reserved.")
    facts = payload.get("facts")
    if not isinstance(facts, str) or not facts.strip() or len(facts) > 4096 or "\x00" in facts:
        raise RequestError(400, "Provide the path to an extracted facts file.")
    for field, limit in (("title", 2000), ("brief", 32768), ("model", 256)):
        if field in payload and (not isinstance(payload[field], str)
                                 or len(payload[field]) > limit or "\x00" in payload[field]):
            raise RequestError(400, "Title, brief, or model is invalid or too long.")
    if "backend" in payload and payload["backend"] not in ("claude-code", "deepagents"):
        raise RequestError(400, "Select a supported investigator backend.")
    if "minutes" in payload and (type(payload["minutes"]) is not int or payload["minutes"] <= 0):
        raise RequestError(400, "Minutes must be a positive integer.")
    questions = payload.get("questions", [])
    if (not isinstance(questions, list) or len(questions) > 1000
            or any(not isinstance(q, str) or not q.strip() or len(q) > 8192 or "\x00" in q for q in questions)):
        raise RequestError(400, "Questions must be a list of nonempty text questions, each at most 8192 characters.")
    return payload


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, root, port, manager):
        self.root, self.manager = Path(root).resolve(), manager
        self.token = secrets.token_urlsafe(32)
        self._manager_closed = False
        super().__init__(("127.0.0.1", port), Handler)

    def server_close(self):
        try:
            super().server_close()
        finally:
            if not self._manager_closed:
                self._manager_closed = True
                self.manager.close()


class Handler(BaseHTTPRequestHandler):
    # Close each connection: request bodies cannot become a subsequent request.
    protocol_version = "HTTP/1.0"
    server_version = "ChainOfProof"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, format, *args):
        # Paths and malformed requests may contain sensitive user input.
        pass

    def _send(self, status, body, content_type, filename=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.send_header("Connection", "close")
        if filename:
            self.send_header("Content-Disposition", 'attachment; filename="' + filename + '"')
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status, value):
        body = (json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def send_error(self, code, message=None, explain=None):
        # BaseHTTPRequestHandler's default errors echo request details in HTML.
        self._json(code, {"error": "Invalid HTTP request."})

    def _origin(self, write):
        hosts = self.headers.get_all("Host", [])
        port = self.server.server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if port == 80:
            allowed.update(("127.0.0.1", "localhost"))
        if len(hosts) != 1 or hosts[0] not in allowed:
            raise RequestError(403, "Only the local application host is allowed.")
        origins = self.headers.get_all("Origin", [])
        if origins and (len(origins) != 1 or origins[0] != "http://" + hosts[0]):
            raise RequestError(403, "Only same-origin requests are allowed.")
        if write:
            tokens = self.headers.get_all("X-COP-Token", [])
            if len(tokens) != 1 or not secrets.compare_digest(tokens[0].encode("utf-8"), self.server.token.encode("ascii")):
                raise RequestError(403, "A valid application write token is required.")

    def _route(self):
        try:
            parsed = urlsplit(self.path)
            if (len(self.path) > 8192 or parsed.scheme or parsed.netloc or parsed.fragment
                    or "%" in parsed.path or "\\" in parsed.path
                    or any(p in (".", "..") for p in parsed.path.split("/"))):
                raise ValueError("invalid path")
            query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True, max_num_fields=8)
        except ValueError:
            raise RequestError(400, "Invalid request path or query.") from None
        if any(len(values) != 1 for values in query.values()):
            raise RequestError(400, "Query fields must not be repeated.")
        return parsed.path, {key: values[0] for key, values in query.items()}

    def _query(self, query, allowed):
        if set(query) - set(allowed):
            raise RequestError(400, "Unsupported query field.")

    def _body(self):
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not re.fullmatch(r"[0-9]+", lengths[0]):
            raise RequestError(400, "A valid Content-Length is required.")
        length = int(lengths[0])
        if length > MAX_BODY:
            raise RequestError(413, "Request body is too large.")
        content_types = self.headers.get_all("Content-Type", [])
        if len(content_types) != 1 or content_types[0].split(";", 1)[0].strip().lower() != "application/json":
            raise RequestError(415, "Use application/json for request bodies.")
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("incomplete body")
            return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=_reject_constant)
        except (ValueError, UnicodeError, TimeoutError):
            raise RequestError(400, "Request body must be valid UTF-8 JSON.") from None

    def _get(self, path, query):
        manager = self.server.manager
        if path in ASSETS:
            self._query(query, ())
            filename, content_type = ASSETS[path]
            asset = STATIC_ROOT / filename
            if STATIC_ROOT.is_symlink() or asset.is_symlink():
                raise RequestError(404, "Application asset not found.")
            try:
                body = asset.read_bytes()
            except OSError:
                raise RequestError(404, "Application asset not found.") from None
            return self._send(200, body, content_type)
        if path == "/api/config":
            self._query(query, ())
            config = manager.config()
            return self._json(200, {"token": self.server.token, **{key: config[key] for key in (
                "defaults", "backends", "active_run")}})
        if path == "/api/runs":
            self._query(query, ())
            return self._json(200, {"runs": manager.list_runs()})
        if path == "/api/run":
            self._query(query, ("name",))
            return self._json(200, manager.get_run(_name(query.get("name"), self.server.root)))
        if path == "/api/report":
            self._query(query, ("name", "format", "download"))
            name = _name(query.get("name"), self.server.root)
            fmt = query.get("format", "html")
            if fmt not in REPORT_TYPES or query.get("download", "1") != "1":
                raise RequestError(400, "Choose an HTML, Markdown, or JSON report.")
            body, content_type, filename = manager.report(name, fmt)
            if not isinstance(body, bytes):
                raise RuntimeError("report body must be bytes")
            filename = name.replace("/", "-") + "." + fmt if "download" in query else None
            return self._send(200, body, REPORT_TYPES[fmt], filename)
        raise RequestError(404, "Route not found.")

    def _post(self, path, query):
        self._query(query, ())
        if path not in ("/api/investigations", "/api/stop"):
            raise RequestError(404, "Route not found.")
        payload = self._body()
        if path == "/api/investigations":
            result = self.server.manager.start(_start_payload(payload, self.server.root))
            return self._json(200, result)
        if not isinstance(payload, dict) or set(payload) != {"name"}:
            raise RequestError(400, "Stop requests require only a run name.")
        result = self.server.manager.stop(_name(payload["name"], self.server.root))
        return self._json(200, result)

    def _dispatch(self, write=False):
        try:
            self._origin(write)
            if self.headers.get_all("Transfer-Encoding"):
                raise RequestError(400, "Transfer-Encoding is not supported.")
            path, query = self._route()
            return self._post(path, query) if write else self._get(path, query)
        except RequestError as error:
            self._json(error.status, {"error": error.message})
        except FileNotFoundError:
            self._json(404, {"error": "Run or report not found."})
        except FileExistsError:
            self._json(409, {"error": "Run name already exists; choose a new name."})
        except ValueError:
            self._json(400, {"error": "Invalid investigation request or run data."})
        except RuntimeError:
            self._json(409, {"error": "The operation is unavailable for this run or local configuration."})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self._json(500, {"error": "The local application could not complete this request."})

    def do_GET(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch(write=True)


def create_server(root=ROOT, port=8765, *, manager=None):
    """Bind to IPv4 loopback; tests may inject a manager and request port zero."""
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 to 65535")
    if manager is None:
        from app.jobs import JobManager
        manager = JobManager(root=root)
    return LocalServer(root, port, manager)


def serve(root=ROOT, port=8765, open_browser=True):
    """Serve the local app until interrupted, closing its owned jobs on exit."""
    with create_server(root, port) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Chain of Proof: {url}", flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
