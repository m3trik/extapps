# !/usr/bin/python
# coding=utf-8
"""Local, async runner the RealityScan panel dispatches to.

A thin :class:`extapps.photogrammetry._process_runner.PyModuleRunner` subclass:
the base owns the async launch machinery (``AppLauncher.spawn`` + an event-loop reader), and the
``PyModuleRunner`` variant launches the headless driver as
``sys.executable -m ...run_combined`` — unlike Metashape (whose driver runs
*inside* ``metashape.exe``), RealityScan's ``run_combined`` is a normal-Python
driver that spawns ``RealityScan.exe`` itself, so it runs in the panel's own
interpreter. This class only supplies exe discovery via
:class:`RealityScanConnection` so the panel reports a missing install instead of
silently mocking.
"""
from __future__ import annotations

import os

from typing import Optional

from .._process_runner import PyModuleRunner
from ._realityscan_connection import RealityScanConnection


class RealityScanRunner(PyModuleRunner):
    """Discover RealityScan + asynchronously drive its ``run_combined``."""

    MODULE = "extapps.photogrammetry.realityscan_workflow.run_combined"

    def __init__(self, exe: Optional[str] = None):
        super().__init__()
        self._conn = RealityScanConnection(exe=exe)

    @property
    def exe(self) -> Optional[str]:
        return self._conn.exe

    def is_available(self) -> bool:
        """True when a RealityScan exe was found, or a remote
        RSNode is configured (``REALITYSCAN_RSNODE`` on + ``REALITYSCAN_RSNODE_URL``) -- the way a
        host without RealityScan (Linux: it is Windows-only) drives one."""
        return self._conn.is_available() or self._remote_node_configured()

    @staticmethod
    def _remote_node_configured() -> bool:
        from ._realityscan_workflow import RealityScanWorkflow

        env = RealityScanWorkflow.env_name
        flag = os.environ.get(env("REALITYSCAN_RSNODE"), "").strip().lower()
        return flag not in ("", "0", "false", "no") and bool(
            os.environ.get(env("REALITYSCAN_RSNODE_URL"))
        )

    def _unavailable_message(self) -> str:
        return (
            "RealityScan not found. Install it, or set "
            "$REALITYSCAN_EXE to its path."
        )
