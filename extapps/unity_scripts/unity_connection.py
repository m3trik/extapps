# !/usr/bin/python
# coding=utf-8
"""One Unity project's connection: the editor package and its script queue.

Unity Scripts reaches an editor a person has open only through what they
installed into that project (CODE_STANDARD section 15): the editor package
bundled beside this module (``unity_package/``, ``com.m3trik.unity-scripts``),
copied into ``<project>/Packages/`` as an embedded package -- Unity's own way to
ship a package inside a project: it works offline, needs no git, and travels
with the project to the person's teammates. The package serves pythontk's
:class:`~pythontk.JobQueue` in ``<project>/Library/M3trikUnityScripts/queue``
(a folder of JSON jobs, no network port) while the project is open, visible in
the Console and paused from Unity's Tools menu.

Weighed: a Package Manager line (a git URL pinned to a release) needs git on
every machine and a tag extapps does not publish; a ``file:`` line names this
machine's install, so it breaks for a teammate. The copy carries neither cost.

Qt-free and host-free: the panel and its deliverer share it, and a test drives
it against a Python worker serving the same queue.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pythontk as ptk


class UnityConnection:
    """The connection to the Unity project at *project*.

    Parameters:
        project: The Unity project folder (the one holding ``Assets/``).
    """

    #: The editor package's name: its folder under the project's ``Packages/``.
    PACKAGE = "com.m3trik.unity-scripts"
    #: The package as this extapps ships it.
    BUNDLED = Path(__file__).resolve().parent / "unity_package"
    #: The queue's folder under the project.
    QUEUE = ("Library", "M3trikUnityScripts", "queue")
    #: Where the package writes a job's script, in the project (its own assembly).
    SCRIPTS_FOLDER = ("Assets", "M3trikScripts")
    #: A running job's cancel request, ``<id><CANCEL_SUFFIX>`` beside it; the
    #: package's ``ScriptWorker.CancelSuffix`` (held equal by a test).
    CANCEL_SUFFIX = ".cancel"
    #: Seconds a heartbeat may be old for the editor to count as serving: it
    #: beats every 2 s, and stops for the few seconds a domain reload takes.
    STALE = 60.0
    #: Seconds a heartbeat that names the job waited on still counts: Unity
    #: finishes a job it took through a long domain reload (no beat) and through
    #: a Pause asked mid-run (its beat says "stopped").
    BUSY_STALE = 600.0
    #: Seconds an editor must stay unheard before a wait gives up on it: its
    #: heartbeat file is missing for an instant each time it is replaced.
    GONE_GRACE = 3.0

    def __init__(self, project: str):
        self.project = str(project)

    # ------------------------------------------------------------------ the project
    @staticmethod
    def is_project(path: Optional[str]) -> bool:
        """Whether *path* is a Unity project folder (``Assets/`` and ``ProjectSettings/``)."""
        return bool(path) and all(
            os.path.isdir(os.path.join(str(path), sub)) for sub in ("Assets", "ProjectSettings")
        )

    @property
    def installed_dir(self) -> Path:
        """The package's folder in the project."""
        return Path(self.project) / "Packages" / self.PACKAGE

    @classmethod
    def bundled_version(cls) -> str:
        """The bundled package's version (its ``package.json``)."""
        return cls._version(cls.BUNDLED)

    def installed_version(self) -> Optional[str]:
        """The installed package's version, or ``None`` when it is not installed."""
        return self._version(self.installed_dir) if self.installed_dir.is_dir() else None

    @staticmethod
    def _version(folder: Path) -> str:
        try:
            return str(json.loads((folder / "package.json").read_text(encoding="utf-8")).get("version") or "")
        except (OSError, ValueError):
            return ""

    @classmethod
    def _bundled_files(cls) -> List[Path]:
        """The bundled package's files, relative to it (Python's own ignored)."""
        return sorted(
            p.relative_to(cls.BUNDLED)
            for p in cls.BUNDLED.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        )

    def state(self) -> str:
        """``"missing"``, ``"outdated"`` (a bundled file differs from, or is
        absent in, the installed copy) or ``"installed"``."""
        if not self.installed_dir.is_dir():
            return "missing"
        for rel in self._bundled_files():
            installed = self.installed_dir / rel
            if not installed.is_file() or installed.read_bytes() != (self.BUNDLED / rel).read_bytes():
                return "outdated"
        return "installed"

    def install(self, ctx: Optional[Any] = None) -> List[str]:
        """Copy the bundled package into the project, or bring an installed copy
        up to date: changed files are rewritten, files it no longer ships go,
        and the ``.meta`` Unity made for a file that stays is kept (so the
        project's history shows no new GUIDs). Unity loads it on its next focus.

        Parameters:
            ctx: An operation context, asked before the write (``should_write``).

        Returns:
            The files written (absolute paths).
        """
        target = self.installed_dir
        if ctx is not None and not ctx.should_write(str(target), "install the Unity Scripts editor package"):
            return []
        written = []
        shipped = set()
        for rel in self._bundled_files():
            shipped.add(rel.as_posix())
            source, dest = self.BUNDLED / rel, target / rel
            if dest.is_file() and dest.read_bytes() == source.read_bytes():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            written.append(str(dest))
        for path in sorted(target.rglob("*"), reverse=True):
            rel = path.relative_to(target).as_posix()
            if path.is_file():
                kept = rel[: -len(".meta")] if rel.endswith(".meta") else rel
                if kept not in shipped and not (target / kept).is_dir():
                    path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        return written

    def remove(self, ctx: Optional[Any] = None) -> bool:
        """Take the package out of the project, with the scripts it wrote into
        ``Assets/M3trikScripts`` (copies: your own scripts stay in your scripts
        folder), which would not compile without it.

        Returns:
            Whether anything was removed.
        """
        scripts = Path(self.project, *self.SCRIPTS_FOLDER)
        targets = [p for p in (self.installed_dir, scripts) if p.exists()]
        if not targets:
            return False
        if ctx is not None and not ctx.should_delete(
            str(self.installed_dir), "remove the Unity Scripts editor package and the scripts it wrote"
        ):
            return False
        for path in targets:
            shutil.rmtree(path, ignore_errors=True)
            meta = Path(str(path) + ".meta")
            if meta.is_file():
                meta.unlink()
        return True

    # ------------------------------------------------------------------ the queue
    @property
    def queue(self) -> "ptk.JobQueue":
        return ptk.JobQueue(os.path.join(self.project, *self.QUEUE))

    def worker(self) -> Optional[Dict[str, Any]]:
        """The editor's last heartbeat, or ``None`` when it never served."""
        return self.queue.worker()

    def serving(self, settle: float = 0.0) -> bool:
        """Whether an editor has the project open with the package, serving now.

        Parameters:
            settle: Seconds to look again over before answering no, for a
                decision made once (send a script or not): the editor's
                heartbeat is missing for an instant while it is replaced.
        """
        end = time.time() + settle
        while True:
            if self.queue.alive(self.STALE):
                return True
            if time.time() >= end:
                return False
            time.sleep(0.05)

    def paused(self) -> bool:
        """Whether the person paused the package in Unity (Tools > M3trik Scripts)."""
        worker = self.worker()
        return bool(worker and worker.get("paused")) and time.time() - float(worker.get("beat", 0)) < self.STALE

    def status(self) -> str:
        """One line for the panel: what the project's connection can do now."""
        if not self.is_project(self.project):
            return f"{self.project} is no Unity project (no Assets/ and ProjectSettings/)."
        state = self.state()
        if state == "missing":
            return "Connection not installed: Install Connection (the Unity Project field's menu) to run scripts here."
        version = self.installed_version() or "?"
        if state == "outdated":
            return f"Connection v{version} is older than this panel's v{self.bundled_version()}: Update Connection."
        if self.paused():
            return f"Connection v{version} is paused in Unity: Tools > M3trik Scripts > Pause resumes it."
        if self.serving():
            unity = (self.worker() or {}).get("unity")
            who = f"Unity {unity}" if unity else "Unity"
            return f"Connection v{version}: {who} is serving this project."
        return f"Connection v{version}: open the project in Unity to run scripts (delivered files import on its next open)."

    def run(self, script_path: str, args: Optional[Dict[str, Any]] = None, asset: Optional[str] = None) -> str:
        """Queue *script_path* (a ``.cs`` file whose class is named as it) to run
        with *args*, on the project path *asset* (``Assets/...``) when given.

        Returns:
            The job's id.
        """
        path = Path(script_path)
        return self.queue.submit(
            {
                "op": "script.run",
                "script": path.stem,
                "source": path.read_text(encoding="utf-8").replace("\r\n", "\n"),
                "args": dict(args or {}),
                "asset": asset,
            }
        )

    def outcome(self, job_id: str) -> Optional[Dict[str, Any]]:
        """A finished job's record, ``{"state": "done" | "failed", ...}`` with its
        ``result`` or ``error`` and what the Console said, else ``None``
        (``ptk.JobQueue.outcome``)."""
        return self.queue.outcome(job_id)

    def wait(
        self,
        job_id: str,
        timeout: Optional[float] = None,
        poll: float = 0.25,
        cancelled: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """The job's record once it finishes (:meth:`outcome`).

        Parameters:
            timeout: Seconds to wait at most (``None``: while the editor serves).
            poll: Seconds between looks.
            cancelled: Asked each look; true cancels the job (:meth:`cancel`) and
                keeps waiting for the editor to answer.

        Raises:
            TimeoutError: *timeout* passed.
            RuntimeError: the editor stopped serving with the job unfinished; a
                job it had not taken is withdrawn first, so none waits to run
                on the next open (against whatever scene Unity restored).
        """
        end = None if timeout is None else time.time() + timeout
        asked = False
        unheard_since = None
        while True:
            record = self.outcome(job_id)
            if record is not None:
                return record
            if cancelled is not None and not asked and cancelled():
                asked = True
                self.cancel(job_id)
            state = self.queue.status(job_id)
            if state is None:  # withdrawn before it ran, Unity serving or not
                return {"state": "failed", "error": "Cancelled before Unity ran it."}
            if self._there_for(job_id):
                unheard_since = None
            elif unheard_since is None:
                unheard_since = time.time()
            if unheard_since is not None and time.time() - unheard_since >= self.GONE_GRACE:
                if state == "queued":
                    self.queue.discard(job_id)
                    raise RuntimeError(
                        "Unity stopped serving this project before it ran the script "
                        "(closed or paused); the script was withdrawn, so nothing runs "
                        "when the project next opens."
                    )
                raise RuntimeError(
                    "Unity stopped serving this project before the script finished "
                    "(closed, or silent for over ten minutes)."
                )
            if end is not None and time.time() >= end:
                raise TimeoutError(f"The script is still {state} in Unity.")
            time.sleep(poll)

    def _there_for(self, job_id: str) -> bool:
        """Whether an editor is there for *job_id*: serving, or running this very
        job and heard from within :attr:`BUSY_STALE` (a domain reload, a Pause
        asked mid-run: Unity finishes it)."""
        if self.serving():
            return True
        worker = self.worker() or {}
        return worker.get("job") == job_id and time.time() - float(worker.get("beat") or 0) < self.BUSY_STALE

    def cancel(self, job_id: str) -> None:
        """Withdraw a queued job; ask a running one to stop (its script checks
        ``ScriptArgs.CancelRequested`` between steps)."""
        if self.queue.status(job_id) == "queued":
            self.queue.discard(job_id)
            return
        cancel_file = os.path.join(self.queue.root, job_id + self.CANCEL_SUFFIX)
        try:
            with open(cancel_file, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except OSError:
            pass
