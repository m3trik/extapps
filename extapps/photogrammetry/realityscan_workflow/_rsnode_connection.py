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
* ``-save <proj>``       -> ``GET /project/save?name=<scene>`` (after the group),
  where ``<scene>`` is the project's bare stem: the API names it a *scene name*,
  and the node keeps the project in its own store (``/node/projects``, reopened
  by guid), not at a path the caller chose.
* ``-addFolder`` / ``-add`` with a local path -> the image(s) are **uploaded**
  (``POST /project/upload``) into the session ``data`` folder and the parameter
  is rewritten to the relative name RSNode resolves (it sandboxes inputs to the
  session's private ``_data`` folder, so an absolute disk path never resolves).
  A name another client path already holds this session is uploaded as
  ``<stem>~N`` instead of overwriting it (:meth:`_claim`); image layers
  (``<image>.mask.png``) are renamed with their image. The sidecars RealityScan
  reads beside an image ride along: each image's ``<stem>.xmp`` (under the
  image's node stem) and, for a folder, its ``_common.xmp``.
* model/report export (``-exportSelectedModel`` / ``-exportModel`` /
  ``-exportReport``) -> the output path is rewritten to a bare name (RSNode
  writes exports into the session ``output`` folder) and the files produced by
  the run are **downloaded** back to the caller's dir.
* command-auxiliary files (``-exportReport``'s 2nd param, the report
  *template*; ``-importModel``'s mesh) -> **uploaded** to the ``output`` folder
  + referenced by name — RSNode resolves command auxiliary files there. An
  upload lands before the export snapshot, so it is never pulled back.
* everything else        -> one ``POST /project/commandgroup`` (async 202
  ``{taskID}``), then poll ``GET /project/tasks`` until the task is
  ``finished`` / ``failed``.

Session safety: like ``PainterConnection``'s ``force_new_instance``, this creates
its **own** RSNode session via ``/project/create`` — it never attaches to the
project the user has open in the GUI.

Host independence: no client path ever reaches the node. Inputs are uploaded,
exports are downloaded, and the saved project is named, so the workflow needn't
share a filesystem with the RSNode/RealityScan (a Linux client driving a
Windows node). Every client path becomes a bare name via :meth:`_node_name`.
The token handshake (``/node/connection``) answers only on the node's own
localhost, so a client on another host reaches the node through a tunnel
(``ssh -L 8000:127.0.0.1:8000 <node-host>``) with ``RC_RSNODE_URL`` at its
local end.
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Sequence, Tuple

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

# Command -> index of a parameter that names a local command-auxiliary file
# (report template, imported mesh). RSNode resolves these relative to the
# session ``output`` folder, so each is uploaded there and referenced by name.
_AUX_INPUT_PARAMS = {"exportReport": 1, "importModel": 0}

# Sidecars RealityScan reads beside an image by name (rshelp "XMP Metadata
# Files"): ``<stem>.xmp`` pairs with the image of that stem in the same folder,
# and ``_common.xmp`` applies to every image in its folder. Uploaded with the
# images so camera priors survive; kept apart from IMAGE_EXTS, which means
# images.
_STEM_SIDECAR_EXTS = (".xmp",)
_FOLDER_SIDECARS = ("_common.xmp",)


class RsNodeConnection:
    """Run RealityScan CLI command tails over the RSNode REST API."""

    @staticmethod
    def _node_name(path: str) -> str:
        """The bare name the node resolves for the client's *path*.

        Splits on both separators, not only this host's: a POSIX client's
        ``/home/...`` must arrive bare too, and on the Windows node either one
        would read as a directory. The node shares no filesystem with the
        client, so no client directory may reach it.
        """
        return re.split(r"[\\/]", path.rstrip("\\/"))[-1]

    @classmethod
    def _scene_name(cls, path: str) -> str:
        """``/project/save``'s scene name for the client's project *path*: its
        bare stem (``.../job.rsproj`` -> ``job``)."""
        return os.path.splitext(cls._node_name(path))[0]

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
        # (node folder, case-folded name) -> the client path uploaded under it
        # this session; see _claim.
        self._claims: Dict[Tuple[str, str], str] = {}

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
            # A new session has empty folders, so its node names start over.
            self._claims.clear()

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

        ``-load`` / ``-quit`` are dropped, ``-save`` becomes a ``/project/save``
        of the project's scene name, and the remaining stage commands run as one
        command group whose task is
        awaited. ``returncode`` is 0 on a ``finished`` task, non-zero on a
        ``failed`` task or transport error — matching how the CLI connection
        signals failure so :meth:`RealityCaptureWorkflow._run_rc` can read the log
        tail and raise. Extra kwargs (``session`` / ``poll_interval``) accepted
        for signature parity with :class:`RealityScanConnection`.
        """
        argv = [self.exe or "RSNode"] + list(commands)
        self._ensure_session()

        stage: List[Dict[str, Any]] = []
        save_name: Optional[str] = None
        had_save = False
        for cmd in RsNodeClient.normalize_commands([list(commands)]):
            name = cmd["commandName"]
            if name == "save":
                had_save = True
                if cmd["parameters"]:
                    save_name = self._scene_name(cmd["parameters"][0])
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
                    self.client.save_project(save_name)
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
        """Upload local inputs to the session, rewriting paths to node names.

        For each ``addFolder``/``add`` whose first parameter is a local dir/file,
        upload the image(s) into the session ``data`` folder and replace the
        parameter with the relative name RSNode resolves against ``_data``,
        with each image's XMP sidecars (:meth:`_upload_sidecars`). For
        each command-auxiliary file (:data:`_AUX_INPUT_PARAMS`: the report
        template, an imported mesh), upload it to the ``output`` folder, where
        RSNode resolves those (API docs: "for multiple inputs ... upload with
        folder=output"). A bare name (already uploaded) is left untouched, so
        this is idempotent and safe for re-issued commands; a path that is not
        on this client raises rather than reach the node. Runs before
        :meth:`_rewrite_exports` snapshots the output folder, so an uploaded
        file is never pulled back as an output.
        """
        for cmd in stage:
            name, params = cmd["commandName"], cmd["parameters"]
            aux = _AUX_INPUT_PARAMS.get(name)
            if aux is not None and len(params) > aux:
                p = params[aux]
                if os.path.isfile(p):
                    rel = self._upload_name("output", p)
                    with open(p, "rb") as fh:
                        self.client.upload_file(rel, fh.read(), folder="output")
                    params[aux] = rel
                else:
                    self._require_node_name(name, p)
            if name not in _INPUT_CMDS or not params:
                continue
            p = params[0]
            if os.path.isdir(p):
                rel = self._claim("data", self._node_name(p), p)
                folder = f"data/{rel}"
                for img in self._list_images(p):
                    node = self._upload_name(folder, img)
                    with open(img, "rb") as fh:
                        self.client.upload_file(f"{rel}/{node}", fh.read())
                    self._upload_sidecars(folder, f"{rel}/", img, node)
                for side in _FOLDER_SIDECARS:
                    side_path = os.path.join(p, side)
                    if os.path.isfile(side_path):
                        node = self._claim(folder, side, side_path)
                        with open(side_path, "rb") as fh:
                            self.client.upload_file(f"{rel}/{node}", fh.read())
                cmd["parameters"] = [rel]
            elif os.path.isfile(p):
                rel = self._upload_name("data", p)
                with open(p, "rb") as fh:
                    self.client.upload_file(rel, fh.read())
                # A single image's own <stem>.xmp only: _common.xmp speaks for
                # a whole client folder, and the data root mixes folders.
                self._upload_sidecars("data", "", p, rel)
                cmd["parameters"] = [rel]
            else:
                self._require_node_name(name, p)

    def _claim(self, folder: str, name: str, source: str) -> str:
        """Reserve a session-unique node name in *folder* for client path *source*.

        Uploads land in shared session folders under bare names, so two client
        files with one name (frames from two capture folders) would overwrite
        each other there and the run would silently lose images. Returns *name*
        while no other client path holds it this session -- so non-colliding
        names never change and a re-issued path gets back the name it had --
        else the first free ``<stem>~N<ext>`` (N from 2). Claims are keyed by
        *stem*, held by the client's ``<dir>/<stem>``: RealityScan pairs
        same-stem files (an image and its ``<stem>.xmp`` act as one), so
        ``a.jpg`` and ``a.png`` from two folders must not share a node stem, or
        one image would take the other's camera priors; same-stem files from
        one folder share it, as they do there. Stems compare case-folded: the
        node is Windows, where ``IMG.JPG`` and ``img.jpg`` are one file.

        Parameters:
            folder: The node folder the name lives in (``data``,
                ``data/<dir>``, ``output``).
            name: The bare name wanted.
            source: The client file or directory being uploaded.

        Returns:
            The node name *source* is uploaded under.
        """
        holder = os.path.normcase(os.path.abspath(os.path.splitext(source)[0]))
        stem, ext = os.path.splitext(name)
        candidate, n = stem, 1
        while True:
            key = (folder.casefold(), candidate.casefold())
            if self._claims.setdefault(key, holder) == holder:
                return candidate + ext
            n += 1
            candidate = f"{stem}~{n}"

    def _upload_sidecars(self, folder: str, prefix: str, image: str, node: str) -> None:
        """Upload the stem-paired sidecars beside client *image* (``<stem>.xmp``)
        under the image's node stem, so a renamed image keeps its priors
        (``a~2.jpg`` -> ``a~2.xmp``). *prefix* is the upload path of *folder*
        (``"<dir>/"``, or ``""`` for the data root). An image layer has no
        sidecar of its own: its image carries it.
        """
        if self._layer_owner(image):
            return
        base, node_stem = os.path.splitext(image)[0], os.path.splitext(node)[0]
        for ext in _STEM_SIDECAR_EXTS:
            # the node (Windows) pairs either case; a POSIX client must look
            side = next(
                (base + e for e in (ext, ext.upper()) if os.path.isfile(base + e)), None
            )
            if side:
                name = self._claim(folder, node_stem + ext, side)
                with open(side, "rb") as fh:
                    self.client.upload_file(prefix + name, fh.read())

    @staticmethod
    def _layer_owner(path: str) -> Optional[str]:
        """The image beside *path* that *path* is a layer of, or None.

        RealityScan pairs an image layer with its image by the image's full
        name (``DSC_0001.jpg.mask.png``, ``DSC_0001.jpg.texture.jpg``). The
        owner is the longest ``<prefix>.`` of the name that is an image file in
        the same directory.
        """
        directory, name = os.path.split(path)
        dot = len(name)
        while True:
            dot = name.rfind(".", 0, dot)
            if dot <= 0:
                return None
            owner = os.path.join(directory, name[:dot])
            if owner.lower().endswith(IMAGE_EXTS) and os.path.isfile(owner):
                return owner

    def _upload_name(self, folder: str, path: str) -> str:
        """The session-unique node name client file *path* uploads under.

        An image layer takes its image's node name plus its own suffix, so a
        renamed image keeps its mask/texture layers paired.
        """
        name = self._node_name(path)
        owner = self._layer_owner(path)
        if owner:
            name = (
                self._upload_name(folder, owner) + name[len(self._node_name(owner)) :]
            )
        return self._claim(folder, name, path)

    @classmethod
    def _require_node_name(cls, command: str, param: str) -> None:
        """Raise unless *param* is already a bare node name.

        A parameter that is neither a local file/dir nor a bare name is a client
        path this host doesn't have. Sent as-is, the node would resolve it inside
        its session sandbox and fail with an opaque "file not found"; failing
        here names the missing path instead.
        """
        if cls._node_name(param) != param:
            raise RsNodeError(
                f"-{command} {param!r}: not found on this client, and a client "
                "path cannot resolve on the RSNode host"
            )

    def _rewrite_exports(self, stage: List[Dict[str, Any]]):
        """Rewrite export paths to bare names; snapshot the output folder.

        Any spelling of the client's path -- absolute, relative, POSIX or
        Windows -- is a client path, so each becomes the bare name RSNode writes
        into the session ``output`` folder. Returns ``(target_dir,
        pre_existing_names)`` so :meth:`_download_outputs` can pull the files
        produced by this run back to the caller's directory, or ``None`` when
        the stage has no export command. The names the exports write are left
        out of the snapshot: a re-export under the same name (the workflow's
        per-stage ``model.xml`` report) overwrites the node's copy and must be
        pulled back again, not skipped as pre-existing.
        """
        target_dir = None
        named = set()
        for cmd in stage:
            if cmd["commandName"] in _EXPORT_CMDS and cmd["parameters"]:
                p = cmd["parameters"][0]
                target_dir = target_dir or os.path.dirname(p) or os.curdir
                cmd["parameters"][0] = self._node_name(p)
                named.add(cmd["parameters"][0])
        if target_dir is None:
            return None
        try:
            pre = set(self.client.list_files("output")) - named
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
