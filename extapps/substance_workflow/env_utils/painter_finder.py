"""Locate installed Substance 3D Painter."""

import logging
import os
import platform
from typing import Dict, List, Optional

try:
    from pythontk import AppLauncher
except ImportError:
    from pythontk.core_utils.app_launcher import AppLauncher

logger = logging.getLogger(__name__)


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
            return [os.path.expanduser("~/Adobe"), "/opt"]
        return []

    @staticmethod
    def find_installs() -> Dict[str, str]:
        """Return ``{label: exe_path}`` for every Painter install found."""
        system = platform.system().lower()
        exe_name = PainterFinder.EXE_NAME.get(system, PainterFinder.EXE_NAME["windows"])

        found: Dict[str, str] = {}
        for root in PainterFinder.default_install_roots():
            if not os.path.isdir(root):
                continue
            try:
                for child in sorted(os.listdir(root), reverse=True):
                    if "Substance 3D Painter" not in child:
                        continue
                    install_dir = os.path.join(root, child)
                    exe_path = os.path.join(install_dir, exe_name)
                    if os.path.isfile(exe_path):
                        found[child] = exe_path
            except OSError as e:
                logger.debug(f"Skipping {root}: {e}")

        if not found:
            via_path = AppLauncher.find_app(exe_name)
            if via_path:
                found["default"] = via_path
        return found

    @staticmethod
    def resolve(version_or_path: Optional[str] = None) -> Optional[str]:
        """Resolve an executable path.

        Accepts an absolute path, a version-fragment label substring, or
        None (returns the first install found — typically the newest).
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
