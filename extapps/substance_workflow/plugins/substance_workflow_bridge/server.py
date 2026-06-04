"""Live-mode HTTP bridge — runs inside Painter, dispatches ops on the main thread."""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from extapps.substance_workflow import registry

logger = logging.getLogger(__name__)


def _qtimer():
    """Resolve QTimer from Painter's bundled Qt binding (PySide6 newer, PySide2 older)."""
    try:
        from PySide6.QtCore import QTimer

        return QTimer
    except ImportError:
        from PySide2.QtCore import QTimer

        return QTimer


def call_on_main_thread(func, *args, **kwargs):
    """Marshal ``func`` onto Painter's main Qt event loop and block until done.

    Painter's API is main-thread-only; the HTTP server runs on a worker
    thread, so every dispatched op has to hop back here.
    """
    QTimer = _qtimer()
    done = threading.Event()
    container: dict = {}

    def runner() -> None:
        try:
            container["value"] = func(*args, **kwargs)
        except Exception as e:
            container["error"] = e
        finally:
            done.set()

    QTimer.singleShot(0, runner)
    done.wait()
    if "error" in container:
        raise container["error"]
    return container.get("value")


def dispatch_request(path: str, payload: dict, executor=None) -> tuple:
    """Pure dispatch: route ``(path, payload)`` and return ``(status, body)``.

    Decoupled from the HTTP layer so the routing logic is testable without
    Qt or a real socket. ``executor`` is the function that runs an op —
    defaults to :func:`call_on_main_thread` (Qt-dependent); tests pass a
    synchronous direct-call.
    """
    if executor is None:
        executor = call_on_main_thread

    if path == "/describe":
        op = payload.get("op", "")
        return 200, {"ok": True, "value": registry.describe(op)}

    if path == "/health":
        return 200, {"ok": True}

    op = payload.get("op", "")
    kwargs = payload.get("kwargs", {}) or {}

    fn = registry.get(op)
    if fn is None:
        return 404, {"ok": False, "error": f"Unknown op: {op!r}"}

    try:
        result = executor(fn, **kwargs)
        return 200, {"ok": True, "value": result}
    except Exception as e:
        return 500, {"ok": False, "error": f"{type(e).__name__}: {e}"}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        status, body = dispatch_request(self.path, payload)
        self._send_json(status, body)

    def do_GET(self) -> None:  # noqa: N802
        status, body = dispatch_request(self.path, {})
        self._send_json(status, body)

    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args) -> None:  # noqa: A002
        logger.debug("[bridge] " + format, *args)


class BridgeServer:
    def __init__(self, port: int = 0, host: str = "localhost") -> None:
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> int:
        self._server = HTTPServer((self.host, self.port), _Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="substance_workflow_bridge",
        )
        self._thread.start()
        print(f"[substance_workflow] Bridge listening on {self.host}:{self.port}")
        return self.port

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
