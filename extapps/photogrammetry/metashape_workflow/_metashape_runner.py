# !/usr/bin/python
# coding=utf-8
"""Local, async runner the Metashape panel dispatches to.

A thin :class:`extapps.photogrammetry._process_runner.ProcessRunner` subclass:
the base owns the :class:`~qtpy.QtCore.QProcess` machinery (async launch, live
stdout streaming into the panel log, completion/error callbacks); this class
supplies only the Metashape specifics — exe discovery via
:class:`MetashapeConnection` and the ``metashape.exe -r run_combined.py`` launch
(the driver runs *inside* Metashape's bundled Python, which is why it doesn't use
the :class:`~extapps.photogrammetry._process_runner.PyModuleRunner` variant the
RealityScan / Brush panels do).
"""
from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

from .._process_runner import ProcessRunner
from ._metashape_connection import MetashapeConnection

# Path to the headless pipeline driver run inside metashape.exe.
_RUNNER = os.path.join(os.path.dirname(__file__), "run_combined.py")


class MetashapeRunner(ProcessRunner):
    """Discover + asynchronously drive ``run_combined`` in the local Metashape."""

    def __init__(self, exe: Optional[str] = None):
        super().__init__()
        self._conn = MetashapeConnection(exe=exe)

    @property
    def exe(self) -> Optional[str]:
        return self._conn.exe

    def is_available(self) -> bool:
        """True when a local ``metashape.exe`` was found (a real run is possible)."""
        return self._conn.is_available()

    def _command(self, argv: Sequence[str]) -> Tuple[str, List[str]]:
        return self._conn.exe, ["-r", _RUNNER, *list(argv)]

    def _unavailable_message(self) -> str:
        return (
            "metashape.exe not found. Install Agisoft Metashape, or set "
            "$METASHAPE_EXE to its path."
        )
