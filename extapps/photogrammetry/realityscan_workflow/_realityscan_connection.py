# !/usr/bin/python
# coding=utf-8
"""Launch connection for RealityScan / RealityCapture.

RealityScan 2.0 (Epic's rebrand) is **window-station bound and Epic-sign-in
gated**: its CLI commands only execute inside an interactive desktop session
where the user is signed into Epic. In a non-interactive context (SSH / Windows
service *session 0*) RC starts but sits idle at the Epic sign-in with no window
station — it never processes. This connection encapsulates that reality so the
engine and any remote driver don't each re-learn it the hard way:

* **Interactive session** -> run the CLI directly (blocking, output captured).
* **Non-interactive session** -> launch RC into the **active console session**
  via :meth:`pythontk.AppLauncher.launch_in_session` (PsExec), recovering the
  exit code through a done-marker + poll (PsExec detaches).
* **No logged-in console session** to borrow -> raise
  :class:`RealityScanInteractiveError` instead of hanging.

Process spawn routes through :class:`pythontk.AppLauncher` (no raw ``subprocess``
for the cross-session launch).
"""
from __future__ import annotations

import os
import time
import subprocess
from typing import List, Optional, Sequence

from pythontk import AppLauncher


class RealityScanInteractiveError(RuntimeError):
    """An RC run needs an interactive, Epic-signed-in desktop session that is not
    available (e.g. driving from SSH with no user logged in)."""


class RealityScanConnection:
    """Discover + drive the RealityScan/RealityCapture CLI, interactive-aware."""

    def __init__(self, exe: Optional[str] = None):
        if exe is None:
            # Deferred import avoids a module-load cycle with the engine.
            from ._realityscan_workflow import RealityCaptureWorkflow

            exe = RealityCaptureWorkflow.find_realitycapture_exe()
        self.exe = exe

    def is_available(self) -> bool:
        return bool(self.exe)

    @staticmethod
    def is_interactive() -> bool:
        """True if the current process can host RC's window (session != 0)."""
        return AppLauncher.is_interactive_session()

    @staticmethod
    def epic_signin_active() -> bool:
        """Heuristic: True if Epic sign-in helpers are running (RC is waiting on
        authentication). Diagnostic only — not a hard gate."""
        for name in ("EpicWebHelper.exe", "EpicGamesLauncher.exe"):
            if AppLauncher.get_running_processes(name):
                return True
        return False

    def run(
        self,
        commands: Sequence[str],
        log_path: str,
        timeout: Optional[float] = None,
        session: Optional[int] = None,
        poll_interval: float = 5.0,
    ) -> subprocess.CompletedProcess:
        """Run RC as ``[exe] + commands`` (the caller supplies the full CLI tail,
        e.g. ``-load .. -align .. -save .. -quit``).

        Interactive session: blocking ``subprocess`` with stdout+stderr -> *log_path*.
        Non-interactive: launch into the active console session (PsExec) and poll
        a done-marker beside *log_path* for the exit code.

        :return: ``subprocess.CompletedProcess`` (returncode is meaningful).
        :raises FileNotFoundError: RC exe not found.
        :raises RealityScanInteractiveError: non-interactive with no console session.
        :raises subprocess.TimeoutExpired | TimeoutError: on timeout.
        """
        if not self.exe:
            raise FileNotFoundError("RealityScan/RealityCapture exe not found.")
        argv: List[str] = [self.exe] + list(commands)

        if self.is_interactive():
            # Route through AppLauncher (the ecosystem's subprocess boundary —
            # never raw subprocess) and let it stream stdout+stderr to the log.
            return AppLauncher.run(
                self.exe,
                args=list(commands),
                output_file=log_path,
                timeout=timeout,
            )

        # Non-interactive: borrow the logged-in console session.
        target = (
            session if session is not None else AppLauncher.active_console_session_id()
        )
        if target is None:
            raise RealityScanInteractiveError(
                "RealityScan needs an interactive, Epic-signed-in desktop session; "
                "none is logged in to launch into. Sign in on the console (or over "
                "RDP) and retry."
            )
        marker = log_path + ".done"
        bat = log_path + ".run.bat"
        try:
            if os.path.exists(marker):
                os.remove(marker)
        except OSError:
            pass
        quoted = " ".join(
            f'"{a}"' if (" " in a or "\\" in a) else a for a in argv
        )
        # cmd reads .bat text in the console OEM codepage; write it that way so
        # non-ASCII paths survive verbatim. No errors="replace" — a path cmd
        # cannot represent must fail loudly (UnicodeEncodeError) rather than be
        # silently mangled to '?', which would redirect RC output / the .done
        # marker to a wrong file and hang the poll loop to its deadline.
        with open(bat, "w", encoding="oem") as fh:
            fh.write("@echo off\r\n")
            fh.write(f'{quoted} > "{log_path}" 2>&1\r\n')
            # Leading-redirect form is deliberate: ``echo %errorlevel%>file``
            # would expand to ``echo 0>file`` and cmd treats the bare digit as a
            # file-handle redirect (``0>`` = stdin), writing an EMPTY marker — so
            # a successful run (exit 0-9) would be misread as failure. Putting the
            # redirect first avoids the digit-binding entirely.
            fh.write(f'>"{marker}" echo %errorlevel%\r\n')
        launched = AppLauncher.launch_in_session(
            "cmd", args=["/c", bat], session=target
        )
        if launched.returncode != 0:
            raise RealityScanInteractiveError(
                f"Failed to launch RealityScan into session {target}: "
                f"{getattr(launched, 'stderr', '')}"
            )
        wait_secs = timeout if timeout else 7200
        deadline = time.time() + wait_secs
        while time.time() < deadline:
            if os.path.exists(marker):
                break
            time.sleep(poll_interval)
        else:
            raise TimeoutError(
                f"RealityScan did not finish within {wait_secs:g}s (session "
                f"{target}). It may be waiting on an interactive Epic sign-in "
                "on the desktop."
            )
        try:
            with open(marker, "r", encoding="utf-8", errors="replace") as fh:
                rc = int((fh.read().strip() or "1"))
        except Exception:
            rc = 1
        return subprocess.CompletedProcess(argv, rc)
