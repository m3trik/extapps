# !/usr/bin/python
# coding=utf-8
"""RSNode-backed connection — drive a running RealityScan 2.1 over REST.

Drop-in alternative to :class:`RealityScanConnection`: same duck-typed surface
(:meth:`is_available` + :meth:`run` returning a ``subprocess.CompletedProcess``)
so :class:`RealityCaptureWorkflow` can use either transport without branching.

Why this exists: RealityScan's CLI (``RealityScan.exe -<cmd> ...``) is window-
station + Epic-sign-in gated and will not process in *session 0* (SSH / service).
RSNode exposes the same CLI commands over HTTP against a **persistent, signed-in**
RealityScan, so commands run from any session — that is the headless win.

Transport mapping (the workflow's :meth:`RealityCaptureWorkflow._run_rc` builds a
CLI tail ``[-load <proj>] <stage cmds> -save <proj> -quit``):

* ``-load`` / ``-quit``  -> **dropped** — the REST *session* keeps the project
  loaded across command groups (verified live), and we must never ``-quit`` the
  user's running RealityScan.
* ``-save <proj>``       -> ``GET /project/save?name=<proj>`` (after the group).
* ``-addFolder`` / ``-add`` with a local path -> the image(s) are **uploaded**
  (``POST /project/upload``) into the session ``data`` folder and the parameter
  is rewritten to the relative name RSNode resolves (it sandboxes inputs to the
  session's private ``_data`` folder, so an absolute disk path never resolves).
* model/report export (``-exportSelectedModel`` / ``-exportModel`` /
  ``-exportReport``) -> the absolute output path is rewritten to a basename
  (RSNode writes exports into the session ``output`` folder) and the files
  produced by the run are **downloaded** back to the caller's dir.
  ``-exportReport``'s 2nd param (the report *template*) is additionally
  **uploaded** to the ``output`` folder + relativized — RSNode resolves command
  auxiliary files there, and the template is excluded from the download.
* everything else        -> one ``POST /project/commandgroup`` (async 202
  ``{taskID}``), then poll ``GET /project/tasks`` until the task is
  ``finished`` / ``failed``.

Session safety: like ``PainterConnection``'s ``force_new_instance``, this creates
its **own** RSNode session via ``/project/create`` — it never attaches to the
project the user has open in the GUI.

Host independence: the *deliverables* move over REST — inputs are uploaded and
the exported model/report are downloaded — so the workflow needn't share a
filesystem with the RSNode/RealityScan and can drive a remote node (the common
case is still the local GPU host, a same-machine copy). The one exception is
``-save``: its path is resolved on the node's filesystem, since the ``.rsproj``
is node-side working state, not a downloaded deliverable.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional, Sequence

from ..profile import IMAGE_EXTS
from ._rsnode_client import RsNodeClient, RsNodeError

DEFAULT_RSNODE_URL = "http://127.0.0.1:8000"

# CLI tokens that describe the per-invocation project lifecycle, not a stage of
# work. Over REST the session is persistent, so these are handled out-of-band
# (or dropped) rather than sent in the command group.
_LIFECYCLE = frozenset({"load", "save", "quit", "open", "close"})

# Commands whose first parameter is a local image path/dir that RSNode cannot
# read directly (it resolves inputs relative to the session's private _data
# folder). Such paths are uploaded, then the parameter is rewritten to the
# relative name RSNode expects.
_INPUT_CMDS = frozenset({"addFolder", "add"})

# Commands whose first parameter is an output file path. RSNode writes exports
# into the session ``output`` folder (not the absolute path the caller passed),
# so the path is rewritten to a basename and the produced files are downloaded
# back to the caller's directory after a successful run.
_EXPORT_CMDS = frozenset({"exportSelectedModel", "exportModel", "exportReport"})


class RsNodeConnection:
    """Run RealityScan CLI command tails over the RSNode REST API."""

    @staticmethod
    def _list_images(directory: str) -> List[str]:
        """Image files directly under *directory* (non-recursive), sorted.

        Extensions come from the photogrammetry SSoT (``profile.IMAGE_EXTS``) so the
        set uploaded matches what the workflow's ``add_image_dirs`` counts.
        """
        return [
            os.path.join(directory, f)
            for f in sorted(os.listdir(directory))
            if f.lower().endswith(IMAGE_EXTS)
        ]

    def __init__(
        self,
        client: Optional[RsNodeClient] = None,
        base_url: Optional[str] = None,
        app_token: str = "extapps.photogrammetry",
        connect_timeout: float = 8.0,
        exe: Optional[str] = None,
    ):
        """
        Parameters:
            client: Inject a pre-built :class:`RsNodeClient` (tests / reuse). When
                None, one is constructed against *base_url*.
            base_url: RSNode base URL. Defaults to ``RC_RSNODE_URL`` env or
                ``http://127.0.0.1:8000``.
            app_token: Caller-app identifier sent on every request.
            connect_timeout: Timeout for the availability probe + token handshake.
            exe: Informational only (recorded in the returned CompletedProcess.args).
        """
        self.base_url = base_url or os.environ.get("RC_RSNODE_URL") or DEFAULT_RSNODE_URL
        self.client = client or RsNodeClient(
            base_url=self.base_url, app_token=app_token, timeout=connect_timeout
        )
        # Keep base_url in sync with an injected client.
        self.base_url = self.client.base_url
        self.exe = exe

    # -- availability ------------------------------------------------------
    def is_available(self) -> bool:
        """True if a RealityScan RSNode answers the token handshake at *base_url*.

        Cheap on localhost: a refused connection returns immediately. Stores the
        auth token on success so the first :meth:`run` reuses it.
        """
        try:
            self.client.connect()
            return bool(self.client.auth_token)
        except RsNodeError:
            return False

    # -- session lifecycle -------------------------------------------------
    def _ensure_session(self) -> None:
        if not self.client.auth_token:
            self.client.connect()
        if not self.client.session:
            self.client.create_session()

    def close(self) -> None:
        """Best-effort teardown of this connection's own RSNode session.

        ``GET /project/close`` frees the session slot immediately (verified:
        ``activeSessions`` drops, the id leaves ``sessionIds``); RSNode also
        auto-reaps idle sessions as a safety net. Close can itself fail in some
        project states, so this is best-effort. The session is cleared either
        way so a subsequent :meth:`run` starts a fresh one.
        """
        try:
            if self.client.session:
                self.client.close_project()
        except RsNodeError:
            pass
        finally:
            self.client.session = None

    # -- run ---------------------------------------------------------------
    def run(
        self,
        commands: Sequence[str],
        log_path: str,
        timeout: Optional[float] = None,
        **_ignored: Any,
    ) -> subprocess.CompletedProcess:
        """Execute a CLI command tail over REST; return a ``CompletedProcess``.

        ``-load`` / ``-quit`` are dropped, ``-save`` becomes a ``/project/save``,
        and the remaining stage commands run as one command group whose task is
        awaited. ``returncode`` is 0 on a ``finished`` task, non-zero on a
        ``failed`` task or transport error — matching how the CLI connection
        signals failure so :meth:`RealityCaptureWorkflow._run_rc` can read the log
        tail and raise. Extra kwargs (``session`` / ``poll_interval``) accepted
        for signature parity with :class:`RealityScanConnection`.
        """
        argv = [self.exe or "RSNode"] + list(commands)
        self._ensure_session()

        stage: List[Dict[str, Any]] = []
        save_path: Optional[str] = None
        had_save = False
        for cmd in RsNodeClient.normalize_commands([list(commands)]):
            name = cmd["commandName"]
            if name == "save":
                had_save = True
                if cmd["parameters"]:
                    save_path = cmd["parameters"][0]
                continue
            if name in _LIFECYCLE:  # load / quit / open / close
                continue
            stage.append(cmd)

        rc = 0
        detail = ""
        try:
            self._upload_inputs(stage)
            export_info = self._rewrite_exports(stage)
            if stage:
                task_id = self.client.run_commands(
                    [(c["commandName"], c["parameters"]) for c in stage]
                )
                if not task_id:
                    # 202 must carry a taskID; without one we can't confirm
                    # completion. Fail fast rather than poll for the full timeout.
                    rc = 1
                    detail = "commandgroup accepted but returned no taskID"
                else:
                    status = self.client.wait_for_task(task_id, timeout=timeout or 7200.0)
                    state = status.get("state")
                    ec = status.get("errorCode")
                    # A genuine failure is state=="failed" with a negative HRESULT.
                    # A *finished* task may carry a small positive errorCode (e.g.
                    # the count of items a successful add touched) which is NOT an
                    # error -- so key off state, not errorCode truthiness.
                    if state == "failed" or (isinstance(ec, int) and ec < 0):
                        rc = int(ec) if (isinstance(ec, int) and ec) else 1
                        detail = (
                            status.get("errorMessage")
                            or f"task {task_id} failed (state={state}, errorCode={ec})"
                        )
            if had_save and rc == 0:
                try:
                    self.client.save_project(save_path)
                except RsNodeError as e:
                    detail += f"\n[save warning] {e}"
            if rc == 0:
                self._download_outputs(export_info)
        except RsNodeError as e:
            rc = e.code or 1
            detail = str(e)

        self._write_log(log_path, stage, rc, detail)
        return subprocess.CompletedProcess(argv, rc)

    def _upload_inputs(self, stage: List[Dict[str, Any]]) -> None:
        """Upload local image inputs to the session, rewriting paths to relative.

        For each ``addFolder``/``add`` whose first parameter is a local dir/file,
        upload the image(s) into the session ``data`` folder and replace the
        parameter with the relative name RSNode resolves against ``_data``. A
        parameter that is not a local path (already a relative name) is left
        untouched, so this is idempotent and safe for re-issued commands.
        """
        for cmd in stage:
            if cmd["commandName"] not in _INPUT_CMDS or not cmd["parameters"]:
                continue
            p = cmd["parameters"][0]
            if os.path.isdir(p):
                rel = os.path.basename(os.path.normpath(p))
                for img in self._list_images(p):
                    with open(img, "rb") as fh:
                        self.client.upload_file(f"{rel}/{os.path.basename(img)}", fh.read())
                cmd["parameters"] = [rel]
            elif os.path.isfile(p):
                rel = os.path.basename(p)
                with open(p, "rb") as fh:
                    self.client.upload_file(rel, fh.read())
                cmd["parameters"] = [rel]
            # else: not a local path -> already a relative/uploaded name; leave as-is.

    def _rewrite_exports(self, stage: List[Dict[str, Any]]):
        """Rewrite absolute export paths to basenames; snapshot the output folder.

        Returns ``(target_dir, pre_existing_names)`` so :meth:`_download_outputs`
        can pull the files produced by this run back to the caller's directory,
        or ``None`` when the stage has no export command.
        """
        target_dir = None
        for cmd in stage:
            if cmd["commandName"] in _EXPORT_CMDS and cmd["parameters"]:
                p = cmd["parameters"][0]
                if os.path.isabs(p):
                    target_dir = target_dir or os.path.dirname(p)
                    cmd["parameters"][0] = os.path.basename(p)
                # exportReport's 2nd param is a template file RealityScan reads
                # to render the report. RSNode resolves command auxiliary files
                # (templates, export configs) relative to the session ``output``
                # folder (API docs: "for multiple inputs ... upload with
                # folder=output"), so a local template is uploaded there and the
                # param rewritten to its basename. Done before the pre-run
                # snapshot below so the template lands in ``pre`` and is not
                # pulled back as a produced output.
                if cmd["commandName"] == "exportReport" and len(cmd["parameters"]) > 1:
                    tpl = cmd["parameters"][1]
                    if os.path.isfile(tpl):
                        with open(tpl, "rb") as fh:
                            self.client.upload_file(
                                os.path.basename(tpl), fh.read(), folder="output"
                            )
                        cmd["parameters"][1] = os.path.basename(tpl)
        if target_dir is None:
            return None
        try:
            pre = set(self.client.list_files("output"))
        except RsNodeError:
            pre = set()
        return (target_dir, pre)

    def _download_outputs(self, export_info) -> None:
        """Download files newly produced in the session output folder to *target_dir*.

        An export (``exportSelectedModel``) emits several files (``.obj`` + ``.mtl``
        + texture pages); downloading everything new since the pre-run snapshot
        retrieves the full set regardless of the engine's texture-page naming.
        """
        if not export_info:
            return
        target_dir, pre = export_info
        try:
            produced = [n for n in self.client.list_files("output") if n not in pre]
        except RsNodeError:
            return
        if not produced:
            return
        os.makedirs(target_dir, exist_ok=True)
        for name in produced:
            try:
                data = self.client.download_file(name, "output")
            except RsNodeError:
                continue
            with open(os.path.join(target_dir, os.path.basename(name)), "wb") as fh:
                fh.write(data)

    @staticmethod
    def _write_log(log_path: str, stage: Sequence[Dict[str, Any]], rc: int, detail: str) -> None:
        """Mirror RC's per-stage log so ``_run_rc``'s failure-tail read is useful."""
        try:
            os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
            with open(log_path, "w", encoding="utf-8", errors="replace") as fh:
                fh.write("[RSNode REST transport]\n")
                for c in stage:
                    fh.write(f"  -{c['commandName']} {' '.join(c['parameters'])}\n")
                fh.write(f"exit={rc}\n")
                if detail:
                    fh.write(detail + "\n")
        except OSError:
            pass
