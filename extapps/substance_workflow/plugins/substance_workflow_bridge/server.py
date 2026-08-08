"""Live-mode HTTP bridge — runs inside Painter, dispatches ops on the main thread.

The *routing* here is deliberately this app's own: :class:`PainterConnection` and
this server are a matched pair with a richer ``describe`` shape (parameter
annotations and return types) than the generic ``pythontk.RpcClient`` contract,
which the panel's op browser relies on.

The *marshalling* is not app-specific, and is shared —
:class:`pythontk.MainThreadMarshaller`. This plugin loads in place from the
checkout and bootstraps ``sys.path`` (see the package ``__init__``), so it can
import pythontk directly rather than carrying a staged copy like the installed
mayatk/blendertk plugins do.
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from pythontk.net_utils.rpc.plugin_core import MainThreadMarshaller

from extapps.substance_workflow import registry

logger = logging.getLogger(__name__)

#: Painter's API is main-thread-only, but the HTTP server answers on a worker
#: thread, so every dispatched op has to hop back. The shared marshaller adds two
#: things a bare ``QTimer.singleShot`` + ``Event.wait()`` cannot do: a bound on a
#: wedged event loop, and a direct-call fallback when there is no Qt / no
#: QApplication / we are already on the main thread — which is what lets tests
#: exercise the real dispatch path.
#:
#: The bound is deliberately an HOUR, not the marshaller's 60 s default. Every op
#: goes through here, including ``bake.mesh_maps`` / ``bake.all_texture_sets``,
#: and a multi-texture-set 4K bake legitimately runs for many minutes. The
#: predecessor here waited forever, so any bound at all is new: it must sit far
#: above the slowest real op or it converts working bakes into TimeoutErrors,
#: which is a worse failure than the hang it replaces. An hour still catches a
#: genuinely deadlocked event loop, which never returns at any bound.
MARSHALLER = MainThreadMarshaller(
    "SUBSTANCE_WORKFLOW_DISABLE_MAIN_THREAD", timeout=3600.0
)


def call_on_main_thread(func, *args, **kwargs):
    """Marshal ``func`` onto Painter's main Qt event loop and block until done."""
    return MARSHALLER.run(func, *args, **kwargs)


def dispatch_request(path: str, payload: dict, executor=None) -> tuple:
    """Pure dispatch: route ``(path, payload)`` and return ``(status, body)``.

    Decoupled from the HTTP layer so the routing logic is testable without a
    real socket. ``executor`` is the function that runs an op, defaulting to
    :func:`call_on_main_thread`; the shared marshaller behind it already
    degrades to a direct call with no Qt / no QApplication / on the main
    thread, so the override is a seam for asserting *how* an op was run rather
    than a requirement for running one at all.
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
