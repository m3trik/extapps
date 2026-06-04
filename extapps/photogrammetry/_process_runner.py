# !/usr/bin/python
# coding=utf-8
"""Async, log-streaming process runner shared by the photogrammetry panels.

The DCC bridges fire a quick RPC into a live host; a photogrammetry bake is
minutes-to-hours, so a panel must not block the Qt thread. ``ProcessRunner``
wraps a :class:`~qtpy.QtCore.QProcess`: it launches a command, streams merged
stdout into an *on_line* callback on the event loop, and reports completion via
*on_done* — no worker thread, no log-file polling. It exposes a
:class:`pythontk.LoggingMixin` ``.logger`` so :class:`uitk.bridge.BridgeSlotsBase`
redirects it into the panel's log pane exactly as it does for the DCC engines.

Subclasses supply only *what to launch* and *whether it can run*:

* :meth:`_command` — ``(program, args)`` for an *argv* tail.
* :meth:`is_available` / :attr:`exe` — engine discovery, so a panel reports a
  missing install instead of silently mocking.

:class:`PyModuleRunner` is the variant for engines whose headless driver is a
normal-Python ``run_combined`` module (RealityScan, Brush): it launches
``sys.executable -m <module>`` with the parent process's ``sys.path`` propagated
so the child resolves ``extapps`` regardless of install mode. Metashape differs
(its driver runs *inside* ``metashape.exe -r``) and supplies its own
:meth:`_command`.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from qtpy import QtCore

import pythontk as ptk


class ProcessRunner(ptk.LoggingMixin):
    """Launch + asynchronously stream a child process into Qt callbacks.

    Lifecycle: :meth:`start` launches and returns immediately; stdout lines
    arrive via *on_line*; *on_done* fires with the exit code (``-1`` if the
    process failed to launch). :meth:`cancel` kills a running job.
    """

    def __init__(self):
        super().__init__()
        self._proc: Optional[QtCore.QProcess] = None
        self._on_line: Optional[Callable[[str], None]] = None
        self._on_done: Optional[Callable[[int], None]] = None

    # ------------------------------------------------------------ subclass contract
    @property
    def exe(self) -> Optional[str]:
        """Path of the engine executable used (display / diagnostics)."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """True when a real run is possible (the engine was discovered)."""
        raise NotImplementedError

    def _command(self, argv: Sequence[str]) -> Tuple[str, List[str]]:
        """``(program, args)`` to launch for the given *argv* tail."""
        raise NotImplementedError

    def _env(self) -> Dict[str, str]:
        """Extra environment overrides for the child (merged over the system
        env). Default unbuffers stdout so pipeline status streams live rather
        than arriving in one burst at exit."""
        return {"PYTHONUNBUFFERED": "1"}

    def _unavailable_message(self) -> str:
        return "Engine executable not found."

    # ------------------------------------------------------------ state
    def is_running(self) -> bool:
        return (
            self._proc is not None
            and self._proc.state() != QtCore.QProcess.NotRunning
        )

    # ------------------------------------------------------------ run
    def start(
        self,
        argv: Sequence[str],
        on_line: Optional[Callable[[str], None]] = None,
        on_done: Optional[Callable[[int], None]] = None,
        cwd: Optional[str] = None,
    ) -> None:
        """Launch the engine command asynchronously.

        Raises ``FileNotFoundError`` when the engine is unavailable (the panel
        checks :meth:`is_available` first and reports it) and ``RuntimeError``
        if a run is already in flight.
        """
        if not self.is_available():
            raise FileNotFoundError(self._unavailable_message())
        if self.is_running():
            raise RuntimeError("A run is already in progress.")

        self._on_line = on_line
        self._on_done = on_done
        program, args = self._command(argv)

        proc = QtCore.QProcess()
        proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        if cwd:
            proc.setWorkingDirectory(cwd)
        env = QtCore.QProcessEnvironment.systemEnvironment()
        for k, v in self._env().items():
            env.insert(k, v)
        proc.setProcessEnvironment(env)

        proc.readyReadStandardOutput.connect(self._drain)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_error)

        self._proc = proc
        proc.start(program, list(args))

    def cancel(self) -> None:
        """Kill an in-flight run (no-op when idle)."""
        if self.is_running():
            self._proc.kill()

    # ------------------------------------------------------------ internals
    def _drain(self) -> None:
        if self._proc is None or self._on_line is None:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        if data:
            self._on_line(data)

    def _on_finished(self, code, _status=None) -> None:
        # Don't drop self._proc here — that would release the last Python ref to
        # the QProcess from inside its own signal handler. ``is_running()``
        # already reports idle via state() == NotRunning; the next ``start``
        # reassigns self._proc (dropping the old one safely, off-handler).
        self._drain()  # flush any trailing buffered output
        cb, self._on_done = self._on_done, None
        if cb is not None:
            cb(int(code))

    def _on_error(self, _error) -> None:
        # FailedToStart etc. — surface a launch failure as a -1 completion so the
        # panel re-enables and reports rather than hanging "busy". A following
        # ``finished`` (if any) is a no-op since on_done is cleared.
        if self._proc is None:
            return
        msg = self._proc.errorString()
        if self._on_line is not None:
            self._on_line(f"[runner] process error: {msg}\n")
        cb, self._on_done = self._on_done, None
        if cb is not None:
            cb(-1)


class PyModuleRunner(ProcessRunner):
    """``ProcessRunner`` for engines whose headless driver is a normal-Python
    ``run_combined`` module launched as ``sys.executable -m MODULE``.

    Subclasses set :attr:`MODULE` and wrap an engine connection for
    :meth:`is_available` / :attr:`exe`. (Metashape's driver runs *inside*
    ``metashape.exe -r`` instead, so it subclasses :class:`ProcessRunner`
    directly.)
    """

    MODULE = ""  # e.g. "extapps.photogrammetry.realityscan_workflow.run_combined"

    def _command(self, argv: Sequence[str]) -> Tuple[str, List[str]]:
        return sys.executable, ["-m", self.MODULE, *list(argv)]

    def _env(self) -> Dict[str, str]:
        env = dict(super()._env())
        # Propagate the panel process's import path so the child resolves
        # extapps / pythontk regardless of install mode (editable vs wheel).
        env["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)
        return env
