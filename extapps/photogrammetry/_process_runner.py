# !/usr/bin/python
# coding=utf-8
"""Async, log-streaming process runner shared by the photogrammetry panels.

The DCC bridges fire a quick RPC into a live host; a photogrammetry bake is
minutes-to-hours, so a panel must not block the Qt thread. ``ProcessRunner``
launches a command through :meth:`pythontk.AppLauncher.spawn` (the ecosystem's
one process boundary: no console window under a GUI host, and the child is
bound to this process's lifetime, so a crashed host does not orphan an
hours-long bake), reads its merged output on a :class:`pythontk.ProcessReader`
thread, and hands it to *on_line* on the Qt event loop from a timer -- the
callbacks only ever run on the thread that owns the panel. Completion arrives
via *on_done*. It exposes a
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
import queue
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

    #: Milliseconds between the event-loop ticks that forward the child's
    #: output and notice its exit.
    POLL_MS = 50

    def __init__(self):
        super().__init__()
        self._proc = None  # the spawned subprocess.Popen
        self._lines: "Optional[queue.Queue[str]]" = None
        self._reader = None
        self._unsubscribe: Optional[Callable[[], None]] = None
        self._timer: Optional[QtCore.QTimer] = None
        self._on_line: Optional[Callable[[str], None]] = None
        self._on_done: Optional[Callable[[int], None]] = None
        # True from cancel() until the next start() — lets a multi-stage
        # subclass (MetashapeRunner's prep chain) distinguish "stage killed by
        # the user" from "stage failed" and not launch the next stage.
        self._cancelled: bool = False

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
        """True from launch until *on_done* has been delivered (the output tail
        is still being forwarded after the child itself exits)."""
        return self._timer is not None and self._timer.isActive()

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

        self._cancelled = False
        self._on_line = on_line
        self._on_done = on_done
        program, args = self._command(argv)
        self._launch(program, args, cwd)

    def _launch(self, program, args, cwd=None, extra_env=None) -> None:
        """Launch one process, streaming into the already-set callbacks.

        Split out of :meth:`start` so a multi-stage subclass can run another
        command (with per-stage *extra_env*) before/after the engine stage
        while reusing the same plumbing. Callers must set ``self._on_line`` /
        ``self._on_done`` (``start`` does).

        The child's environment is this process's LIVE one
        (:meth:`pythontk.AppLauncher.process_environ` -- what a host that sets
        variables at the C level really hands its children) with
        :meth:`_env` and *extra_env* merged over it."""
        env = ptk.AppLauncher.process_environ()
        env.update(self._env())
        env.update(extra_env or {})
        try:
            proc = ptk.AppLauncher.spawn(program, args=list(args), cwd=cwd, env=env)
        except Exception as e:  # noqa: BLE001 - not found / failed to start
            # Reported from the event loop, as a start failure always was: the
            # caller finishes its own bookkeeping (a "busy" state) before the
            # -1 completion that undoes it arrives.
            message = str(e)
            QtCore.QTimer.singleShot(0, lambda: self._on_error(message))
            return

        lines: "queue.Queue[str]" = queue.Queue()
        stream = ptk.OutputStream()
        self._unsubscribe = stream.subscribe(lambda _source, line: lines.put(line))
        self._reader = ptk.ProcessReader(proc.stdout, stream, "stdout")
        self._reader.start()
        self._proc, self._lines = proc, lines

        timer = QtCore.QTimer()
        timer.setInterval(self.POLL_MS)
        timer.timeout.connect(self._tick)
        self._timer = timer
        timer.start()

    def cancel(self) -> None:
        """Kill an in-flight run (no-op when idle)."""
        if self.is_running() and self._proc is not None:
            self._cancelled = True
            ptk.AppLauncher.close_process(self._proc.pid, force=True)

    # ------------------------------------------------------------ internals
    def _drain(self) -> None:
        """Forward every line read so far to *on_line*, as one chunk."""
        if self._lines is None:
            return
        chunk = []
        while True:
            try:
                chunk.append(self._lines.get_nowait() + "\n")
            except queue.Empty:
                break
        if chunk and self._on_line is not None:
            self._on_line("".join(chunk))

    def _tick(self) -> None:
        """One event-loop tick: forward output; finish once the child has
        exited and its pipe is drained."""
        self._drain()
        proc = self._proc
        if proc is None or proc.poll() is None:
            return
        if self._reader is not None:
            # The child is gone; its pipe closes with it (or with the last
            # grandchild holding it -- ProcessReader ends either way).
            self._reader.join(timeout=2.0)
        self._drain()
        self._on_finished(proc.returncode)

    def _stop_streaming(self) -> None:
        """Stop the tick timer and release the output subscription."""
        if self._timer is not None:
            self._timer.stop()
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _on_finished(self, code) -> None:
        """Deliver the exit code once (a second finish is a no-op)."""
        self._stop_streaming()
        cb, self._on_done = self._on_done, None
        if cb is not None:
            cb(int(code))

    def _on_error(self, message: str) -> None:
        """Surface a launch failure as a -1 completion, so the panel re-enables
        and reports rather than hanging "busy". Single-fire with
        :meth:`_on_finished`: whichever comes first clears *on_done*."""
        self._stop_streaming()
        if self._on_line is not None:
            self._on_line(f"[runner] process error: {message}\n")
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
        return self._python(), ["-m", self.MODULE, *list(argv)]

    @staticmethod
    def _python() -> str:
        """A real interpreter for the child: this one when it is a python, else
        the host's own (``maya.exe`` / Linux ``maya.bin`` -> ``mayapy``, Blender's
        bundled python). Inside a DCC ``sys.executable`` is the host binary, and
        ``-m`` through it started another copy of the host instead of the run."""
        try:
            from uitk.managers.optional_package_manager import OptionalPackageManager

            return OptionalPackageManager.pip_python() or sys.executable
        except Exception:  # uitk / a Qt binding unavailable: a plain python host
            return sys.executable

    def _env(self) -> Dict[str, str]:
        env = dict(super()._env())
        # Propagate the panel process's import path so the child resolves
        # extapps / pythontk regardless of install mode (editable vs wheel).
        env["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)
        return env
