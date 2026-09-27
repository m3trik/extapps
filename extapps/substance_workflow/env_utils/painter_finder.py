"""Locate installed Substance 3D Painter."""

import os
import platform
from typing import Dict, List, Optional

from pythontk import AppLauncher


class PainterFinder:
    """Helper to locate Substance 3D Painter installations."""

    EXE_NAME = {
        "windows": "Adobe Substance 3D Painter.exe",
        "darwin": "Adobe Substance 3D Painter",
        "linux": "Adobe Substance 3D Painter",
    }

    @staticmethod
    def default_install_roots() -> List[str]:
        system = platform.system().lower()
        if system == "windows":
            return [
                r"C:\Program Files\Adobe",
                r"C:\Program Files\Allegorithmic",
            ]
        if system == "darwin":
            return ["/Applications"]
        if system == "linux":
            # Adobe's Linux installer puts it under /opt/Adobe (system) or
            # ~/Adobe (user); /opt covers a hand-unpacked copy.
            return [os.path.expanduser("~/Adobe"), "/opt/Adobe", "/opt"]
        return []

    @staticmethod
    def find_installs() -> Dict[str, str]:
        """Return ``{label: exe_path}`` for every Painter install found, newest first.

        "Newest" is the natural sort :meth:`AppLauncher.scan_install_dirs` owns
        (``Painter 10.0`` outranks ``Painter 9.1``); roots keep their priority order.
        """
        system = platform.system().lower()
        exe_name = PainterFinder.EXE_NAME.get(system, PainterFinder.EXE_NAME["windows"])

        # ``?`` for each space: the Linux install spells folder and binary with
        # underscores (/opt/Adobe/Adobe_Substance_3D_Painter/...).
        patterns = [
            os.path.join(root, "*Substance?3D?Painter*", exe_name.replace(" ", "?"))
            for root in PainterFinder.default_install_roots()
        ]
        found: Dict[str, str] = {
            os.path.basename(os.path.dirname(exe)): exe
            for exe in AppLauncher.scan_install_dirs(patterns)
        }

        if not found:
            via_path = AppLauncher.find_app(exe_name)
            if via_path:
                found["default"] = via_path
        return found

    @staticmethod
    def resolve(version_or_path: Optional[str] = None) -> Optional[str]:
        """Resolve an executable path.

        Accepts an absolute path, a version-fragment label substring, or
        None (returns the newest install).
        """
        if version_or_path and os.path.isfile(version_or_path):
            return version_or_path

        installs = PainterFinder.find_installs()
        if not installs:
            return None
        if version_or_path:
            for label, exe in installs.items():
                if version_or_path in label:
                    return exe
        return next(iter(installs.values()))
