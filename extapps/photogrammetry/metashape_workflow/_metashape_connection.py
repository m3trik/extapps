# !/usr/bin/python
# coding=utf-8
"""Headless launch connection for Agisoft Metashape.

:class:`~extapps.photogrammetry.metashape_workflow._metashape_workflow.MetashapeWorkflow` is the
*in-process* SDK wrapper — it runs INSIDE Metashape's embedded Python (started by
``metashape.exe -r <script>``). ``MetashapeConnection`` is the complement: the
*outside* driver that discovers ``metashape.exe`` and launches such a script
headless from any host — including a **non-interactive session** (SSH / Windows
service session 0).

Hard-won detail (Windows): launch with a plain ``metashape.exe -r <script>``.
Do **not** pass ``-platform offscreen`` there — the Windows bundle does not ship
the Qt *offscreen* plugin, so that path crashes; the default ``windows`` Qt
platform initializes fine for a headless script even with no interactive
desktop, and the license activates normally in that context. Linux is the
opposite case: ``metashape.sh`` on a host with no display (SSH, a render node)
needs ``-platform offscreen`` -- Agisoft's documented headless form -- or its
xcb platform aborts (unverified here: no Linux Metashape at hand).

Process spawn routes through :class:`pythontk.AppLauncher` (no raw subprocess).
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional, Sequence

from pythontk import AppLauncher, AppSpec

from ..profile import Profile

#: Metashape's standard locations, as data: the launcher names (PATH / the
#: Windows App Paths registry), then the Agisoft install dirs -- Windows under
#: either Program Files root, Linux's tarball unpacked under home or /opt.
APP = AppSpec(
    name="Agisoft Metashape",
    app_names=("metashape", "metashape.sh"),
    scan_globs=(
        r"{program_files}\Agisoft\Metashape Pro\metashape.exe",
        r"{program_files}\Agisoft\Metashape\metashape.exe",
        "~/metashape-pro/metashape.sh",
        "/opt/metashape-pro/metashape.sh",
        "~/metashape/metashape.sh",
        "/opt/metashape/metashape.sh",
    ),
    not_found_msg="Metashape not found (set $METASHAPE_EXE).",
)


class MetashapeConnection:
    """Discover + headlessly drive ``metashape.exe -r <script>`` from any host."""

    def __init__(self, exe: Optional[str] = None):
        self.exe = exe or self.find_exe()

    @staticmethod
    def find_exe() -> Optional[str]:
        """Locate ``metashape.exe`` via the shared :func:`resolve_app` chain:
        ``$METASHAPE_EXE`` (terminal — set-but-invalid returns ``None`` so the
        caller enters mock mode) → the profile's ``apps.metashape_exe``
        (network / non-standard install) → :data:`APP` (the launcher names, then
        the Agisoft install dirs). Returns the path or ``None``."""
        return Profile.resolve_app("METASHAPE_EXE", "metashape_exe", spec=APP)

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
            raise FileNotFoundError(APP.not_found_message)
        argv: List[str] = ["-r", script_path]
        if (
            sys.platform.startswith("linux")
            and not os.environ.get("DISPLAY")
            and not os.environ.get("WAYLAND_DISPLAY")
        ):
            argv = ["-platform", "offscreen"] + argv  # see the module docstring
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
