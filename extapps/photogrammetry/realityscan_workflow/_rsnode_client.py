# !/usr/bin/python
# coding=utf-8
"""RSNode REST client — drive a running RealityScan 2.1 over its REST API (headless).

RealityScan 2.1 ships **RSNode** (`<install>\\RSNode.exe`, started from the GUI's
*WORKFLOW > Assistants > Real-time Assistance* tool, or bridged via `-rsApp`). It
exposes a REST API — documented in `<install>\\RSNode\\Static\\docu\\API.v1.json` —
that is the proper headless control surface: instead of launching `RealityScan.exe`
per CLI command (which is window-station / Epic-sign-in gated and hangs in session 0),
a persistent signed-in RealityScan is driven over HTTP.

Flow (all calls carry ``clientId`` + ``appToken`` headers; the agent runs on the
desktop, i.e. localhost, so the token handshake is non-interactive):

1. ``GET /node/connection`` (localhost-only, no bearer) -> ``authToken``.
2. ``GET /project/create`` (bearer) -> **201**, ``Session`` id returned in a header.
3. ``POST /project/commandgroup`` (bearer + Session) -> array of
   ``{commandName, parameters[]}`` -> **202** ``{taskID}``.
4. ``GET /project/status`` (bearer + Session) -> ``{progress, errorCode, ...}``;
   ``GET /project/tags`` -> fired ``-tag`` markers, for completion detection.

Zero-dependency: stdlib ``urllib`` only (no ``requests``), so it stays import-safe
everywhere the package loads.
"""
from __future__ import annotations

import json
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# A command is either a raw CLI token list (["-addFolder", dir]) or a
# (name, params) pair. Both normalize to {commandName, parameters}.
CommandLike = Union[str, Sequence[str], Tuple[str, Sequence[str]]]


class RsNodeError(RuntimeError):
    """An RSNode REST call failed (transport error or non-2xx apiError)."""

    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(message)
        self.code = code


def normalize_commands(commands: Sequence[CommandLike]) -> List[Dict[str, Any]]:
    """Translate CLI-style command specs into RSNode ``commandCall`` dicts.

    Accepts, per item:
      * ``"-align"`` or ``"align"``                  -> {commandName: "align", parameters: []}
      * ``("addFolder", ["C:/imgs"])``               -> {commandName: "addFolder", parameters: ["C:/imgs"]}
      * a flat token list spanning multiple commands (``["-addFolder", "C:/imgs",
        "-align"]``) is split on tokens beginning with ``-``.
    """
    out: List[Dict[str, Any]] = []

    def _emit(name: str, params: Sequence[str]) -> None:
        out.append({"commandName": name.lstrip("-"), "parameters": [str(p) for p in params]})

    for item in commands:
        if isinstance(item, tuple) and len(item) == 2 and not isinstance(item[1], str):
            _emit(str(item[0]), item[1])
        elif isinstance(item, str):
            _emit(item, [])
        else:  # a token sequence, possibly several "-cmd arg arg" runs
            name: Optional[str] = None
            params: List[str] = []
            for tok in item:
                if isinstance(tok, str) and tok.startswith("-"):
                    if name is not None:
                        _emit(name, params)
                    name, params = tok, []
                else:
                    if name is None:
                        raise ValueError(f"command token list must start with a -flag: {item!r}")
                    params.append(tok)
            if name is not None:
                _emit(name, params)
    return out


class RsNodeClient:
    """Minimal stdlib REST client for the RSNode API of a running RealityScan."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        app_token: str = "extapps.photogrammetry",
        client_id: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.app_token = app_token
        self.client_id = client_id or str(uuid.uuid4())
        self.timeout = timeout
        self.auth_token: Optional[str] = None
        self.session: Optional[str] = None

    # -- low-level ---------------------------------------------------------
    @staticmethod
    def _header_value(headers: Dict[str, str], name: str) -> Optional[str]:
        """Case-insensitive response-header lookup (HTTP header names are
        case-insensitive; ``_request`` returns them with the server's casing)."""
        target = name.lower()
        for key, value in headers.items():
            if key.lower() == target:
                return value
        return None

    def _headers(self, *, auth: bool = True, session: bool = False) -> Dict[str, str]:
        h = {"clientId": self.client_id, "appToken": self.app_token}
        if auth and self.auth_token:
            h["Authorization"] = "Bearer " + self.auth_token
        if session:
            if not self.session:
                raise RsNodeError("no active session; call create_session() first")
            h["Session"] = self.session
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Dict[str, str], Any]:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                parsed = json.loads(raw) if raw else None
                return resp.status, {k: v for k, v in resp.headers.items()}, parsed
        except urllib.error.HTTPError as e:
            raw = b""
            try:
                raw = e.read()
            except Exception:
                pass
            msg = None
            if raw:
                try:
                    msg = json.loads(raw).get("message")
                except Exception:
                    msg = raw.decode("utf-8", "replace")
            raise RsNodeError(f"{method} {path} -> {e.code}: {msg or e.reason}", code=e.code)
        except urllib.error.URLError as e:
            raise RsNodeError(f"{method} {path} -> connection failed: {e.reason}")
        except OSError as e:
            # socket.timeout / TimeoutError are OSError but NOT URLError, so the
            # clause above misses them (urlopen's read/connect timeout is raised
            # raw). Wrap so callers — is_available(), wait_for_task() — only ever
            # see RsNodeError, never a stray socket error.
            raise RsNodeError(f"{method} {path} -> connection failed: {e}")

    # -- high-level flow ---------------------------------------------------
    def connect(self) -> Dict[str, Any]:
        """``GET /node/connection`` (localhost) — fetch + store the auth token."""
        _, _, body = self._request("GET", "/node/connection", headers=self._headers(auth=False))
        if not body or not body.get("authToken"):
            raise RsNodeError("/node/connection returned no authToken")
        self.auth_token = body["authToken"]
        return body

    def node_status(self) -> Dict[str, Any]:
        _, _, body = self._request("GET", "/node/status", headers=self._headers())
        return body or {}

    def create_session(self) -> str:
        """``GET /project/create`` — start a session; capture the ``Session`` header."""
        _, headers, _ = self._request("GET", "/project/create", headers=self._headers())
        sess = self._header_value(headers, "Session")
        if not sess:
            raise RsNodeError("/project/create did not return a Session header")
        self.session = sess
        return sess

    def run_commands(self, commands: Sequence[CommandLike]) -> str:
        """``POST /project/commandgroup`` — run a CLI command sequence; return taskID."""
        payload = normalize_commands(commands)
        _, _, body = self._request(
            "POST", "/project/commandgroup", body=payload, headers=self._headers(session=True)
        )
        return (body or {}).get("taskID", "")

    # -- file transfer -----------------------------------------------------
    def upload_file(
        self, name: str, data: bytes, folder: str = "data",
        timeout: Optional[float] = None,
    ) -> int:
        """``POST /project/upload`` — upload raw *data* into the session folder.

        RSNode sandboxes input paths to the session's private ``_data`` directory,
        so images on local disk must be uploaded before ``add`` / ``addFolder``
        can reference them by *name* (an absolute disk path is prefixed with the
        session dir -> "File not found"). Verified live: upload each image to
        ``data/<dir>/<file>`` then ``addFolder <dir>`` -> task state ``finished``.
        *folder* must be ``data`` for image inputs (``output`` rejects them).
        Returns the HTTP status (200 on success); raises :class:`RsNodeError`.
        """
        url = self.base_url + "/project/upload?" + urllib.parse.urlencode(
            {"name": name, "folder": folder}
        )
        headers = self._headers(session=True)
        headers["Content-Type"] = "application/octet-stream"
        req = urllib.request.Request(url, data=data, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout or max(self.timeout, 120.0)) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            raise RsNodeError(f"upload {name!r} -> {e.code}: {e.reason}", code=e.code)
        except (urllib.error.URLError, OSError) as e:
            raise RsNodeError(f"upload {name!r} -> connection failed: {e}")

    def list_files(self, folder: str = "output") -> List[str]:
        """``GET /project/list`` — names of files in the session ``output``/``data`` folder."""
        _, _, body = self._request(
            "GET", "/project/list", query={"folder": folder},
            headers=self._headers(session=True),
        )
        return list(body or [])

    def download_file(self, name: str, folder: str = "output",
                      timeout: Optional[float] = None) -> bytes:
        """``GET /project/download`` — fetch raw bytes of session file *name*.

        Symmetric to :meth:`upload_file`: RSNode writes export outputs
        (``exportSelectedModel`` / ``exportReport``) into the session ``output``
        folder, so the driving host retrieves them by name rather than reading an
        absolute path the sandbox never honored.
        """
        url = self.base_url + "/project/download?" + urllib.parse.urlencode(
            {"name": name, "folder": folder}
        )
        req = urllib.request.Request(url, method="GET", headers=self._headers(session=True))
        try:
            with urllib.request.urlopen(req, timeout=timeout or max(self.timeout, 120.0)) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise RsNodeError(f"download {name!r} -> {e.code}: {e.reason}", code=e.code)
        except (urllib.error.URLError, OSError) as e:
            raise RsNodeError(f"download {name!r} -> connection failed: {e}")

    def project_status(self) -> Dict[str, Any]:
        _, _, body = self._request("GET", "/project/status", headers=self._headers(session=True))
        return body or {}

    def tags(self) -> List[str]:
        _, _, body = self._request("GET", "/project/tags", headers=self._headers(session=True))
        return list(body or [])

    def has_tag(self, tag: str) -> bool:
        _, _, body = self._request(
            "GET", "/project/testtag", query={"tag": tag}, headers=self._headers(session=True)
        )
        return bool(body)

    def wait_for_tag(self, tag: str, *, poll: float = 2.0, timeout: float = 7200.0,
                     sleep=time.sleep, clock=time.monotonic) -> Dict[str, Any]:
        """Poll ``/project/status`` until *tag* fires; raise on errorCode/timeout."""
        deadline = clock() + timeout
        while True:
            st = self.project_status()
            err = st.get("errorCode")
            if err:
                raise RsNodeError(f"RealityScan reported errorCode={err}", code=err)
            if self.has_tag(tag):
                return st
            if clock() >= deadline:
                raise RsNodeError(f"timed out after {timeout}s waiting for tag {tag!r}")
            sleep(poll)

    # -- tasks (per-command completion) ------------------------------------
    def tasks(self, task_ids: Optional[Union[str, Sequence[str]]] = None) -> List[Dict[str, Any]]:
        """``GET /project/tasks`` — task records ``{taskID, state, errorCode, ...}``.

        *state* is one of ``scheduled`` / ``started`` / ``finished`` / ``failed``.
        """
        query = None
        if task_ids is not None:
            ids = task_ids if isinstance(task_ids, str) else ",".join(task_ids)
            query = {"taskIDs": ids}
        _, _, body = self._request(
            "GET", "/project/tasks", query=query, headers=self._headers(session=True)
        )
        return list(body or [])

    def wait_for_task(self, task_id: str, *, poll: float = 1.0, timeout: float = 7200.0,
                      sleep=time.sleep, clock=time.monotonic) -> Dict[str, Any]:
        """Poll ``/project/tasks`` until *task_id* reaches a terminal state.

        Returns the terminal ``taskStatus`` (``state`` is ``finished`` or
        ``failed``); the caller inspects ``errorCode`` / ``errorMessage``. The
        commandgroup is async (202 ``{taskID}``) so this is how a stage's
        completion is detected. GUIDs are compared case-insensitively.
        """
        target = (task_id or "").lower()
        deadline = clock() + timeout
        while True:
            for t in self.tasks(task_id):
                if str(t.get("taskID", "")).lower() == target:
                    if t.get("state") in ("finished", "failed"):
                        return t
                    break
            if clock() >= deadline:
                raise RsNodeError(
                    f"timed out after {timeout}s waiting for task {task_id}"
                )
            sleep(poll)

    # -- project lifecycle -------------------------------------------------
    def save_project(self, name: Optional[str] = None) -> None:
        """``GET /project/save`` — persist the session project to disk (async)."""
        query = {"name": name} if name else None
        self._request("GET", "/project/save", query=query, headers=self._headers(session=True))

    def open_project(self, guid: str, name: Optional[str] = None) -> str:
        """``GET /project/open`` — open an existing project by guid into a session.

        Returns the ``Session`` id (also stored on the client). Note RSNode opens
        by **guid** (from ``/node/projects``), not by file path.
        """
        query: Dict[str, str] = {"guid": guid}
        if name:
            query["name"] = name
        _, headers, _ = self._request(
            "GET", "/project/open", query=query, headers=self._headers()
        )
        sess = self._header_value(headers, "Session")
        if sess:
            self.session = sess
        return sess or (self.session or "")

    def close_project(self) -> None:
        """``GET /project/close`` — close the session's project (teardown)."""
        self._request("GET", "/project/close", headers=self._headers(session=True))
