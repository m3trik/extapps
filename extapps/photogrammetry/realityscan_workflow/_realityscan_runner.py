# !/usr/bin/python
# coding=utf-8
"""Local, async runner the RealityCapture panel dispatches to.

A thin :class:`extapps.photogrammetry._process_runner.PyModuleRunner` subclass:
the base owns the :class:`~qtpy.QtCore.QProcess` machinery, and the
``PyModuleRunner`` variant launches the headless driver as
``sys.executable -m ...run_combined`` — unlike Metashape (whose driver runs
*inside* ``metashape.exe``), RealityScan's ``run_combined`` is a normal-Python
driver that spawns ``RealityCapture.exe`` itself, so it runs in the panel's own
interpreter. This class only supplies exe discovery via
:class:`RealityScanConnection` so the panel reports a missing install instead of
silently mocking.
"""
from __future__ import annotations

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
        """True when a RealityScan / RealityCapture exe was found."""
        return self._conn.is_available()

    def _unavailable_message(self) -> str:
        return (
            "RealityScan / RealityCapture not found. Install it, or set "
            "$RC_EXE to its path."
        )
