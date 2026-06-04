# !/usr/bin/python
# coding=utf-8
"""Headless launch connection for Agisoft Metashape.

:class:`~extapps.photogrammetry.metashape_workflow._metashape_workflow.MetashapeWorkflow` is the
*in-process* SDK wrapper — it runs INSIDE Metashape's embedded Python (started by
``metashape.exe -r <script>``). ``MetashapeConnection`` is the complement: the
*outside* driver that discovers ``metashape.exe`` and launches such a script
headless from any host — including a **non-interactive session** (SSH / Windows
service session 0).

Hard-won detail: launch with a plain ``metashape.exe -r <script>``. Do **not**
pass ``-platform offscreen`` — Metashape does not bundle the Qt *offscreen*
plugin, so that path crashes; the default ``windows`` Qt platform initializes
fine for a headless script even with no interactive desktop, and the license
activates normally in that context.

Process spawn routes through :class:`pythontk.AppLauncher` (no raw subprocess).
"""
from __future__ import annotations

import os
from typing import List, Optional, Sequence

from pythontk import AppLauncher

from ..profile import configured_app_path

# Fallbacks if neither $METASHAPE_EXE nor AppLauncher discovery resolves it.
_KNOWN_PATHS = [
    r"C:\Program Files\Agisoft\Metashape Pro\metashape.exe",
    r"C:\Program Files\Agisoft\Metashape\metashape.exe",
]


class MetashapeConnection:
    """Discover + headlessly drive ``metashape.exe -r <script>`` from any host."""

    def __init__(self, exe: Optional[str] = None):
        self.exe = exe or self.find_exe()

    @staticmethod
    def find_exe() -> Optional[str]:
        """Locate ``metashape.exe``: ``$METASHAPE_EXE`` → the profile's
        ``apps.metashape_exe`` (network / non-standard install) →
        :meth:`AppLauncher.find_app` → known Agisoft install paths. Returns the
        path or ``None``."""
        env = os.environ.get("METASHAPE_EXE")
        if env and os.path.isfile(env):
            return env
        configured = configured_app_path("metashape_exe")
        if configured and os.path.isfile(configured):
            return configured
        found = AppLauncher.find_app("metashape")
        if found:
            return found
        for p in _KNOWN_PATHS:
            if os.path.isfile(p):
                return p
        return None

    def is_available(self) -> bool:
        """True if a metashape.exe was found (i.e. a headless run is possible)."""
        return bool(self.exe)

    def run_script(
        self,
        script_path: str,
        args: Optional[Sequence[str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
        log_file: Optional[str] = None,
        env: Optional[dict] = None,
    ):
        """Run a Python *script* inside Metashape headless via ``-r``.

        No ``-platform offscreen`` (see module docstring). With *log_file*,
        stdout+stderr stream to that file instead of buffering in memory — use it
        for long bakes.

        :return: ``subprocess.CompletedProcess``.
        :raises FileNotFoundError: if ``metashape.exe`` was not found.
        """
        if not self.exe:
            raise FileNotFoundError("metashape.exe not found (set $METASHAPE_EXE).")
        argv: List[str] = ["-r", script_path]
        if args:
            argv += list(args)
        return AppLauncher.run(
            self.exe, args=argv, cwd=cwd, timeout=timeout, output_file=log_file, env=env
        )

    def run_combined(self, args: Optional[Sequence[str]] = None, **kwargs):
        """Convenience: drive this package's ``run_combined`` workflow headless.

        Equivalent to ``run_script(<run_combined.py>, args, ...)`` — the full
        align → depth → model → UV → texture → export pipeline runs on the
        Metashape host, driven from a remote / headless caller.
        """
        runner = os.path.join(os.path.dirname(__file__), "run_combined.py")
        return self.run_script(runner, args=args, **kwargs)
