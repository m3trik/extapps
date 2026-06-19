# !/usr/bin/python
# coding=utf-8
"""Slots for the standalone Unity Studio launcher panel.

A DCC-agnostic Switchboard panel over :class:`unitytk.UnityLauncher` /
:class:`unitytk.UnityFinder`: list the installed Unity Editors, pick (or create) a
project, and launch the editor. Runs from any host that loads uitk (tentacle, a bare
``python -c`` launch, etc.). The engine half (discovery + launch + project creation)
lives in ``unitytk``; this file is UI wiring only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from qtpy import QtCore, QtWidgets


_MAX_RECENTS = 8


def _open_in_file_manager(path: str) -> None:
    """Best-effort reveal of *path* in the platform's file manager."""
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606 — Windows-only API
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class UnityStudioSlots:
    """Switchboard slots wired to ``unity_studio.ui``."""

    def __init__(self, switchboard, **kwargs):
        self.sb = switchboard
        self.ui = self.sb.loaded_ui.unity_studio
        self._recents: List[str] = self._load_recents()

        # Clickable action:// links in the log (reveal folders).
        try:
            self.ui.txt000.anchorClicked.connect(self._on_log_link)
        except Exception:  # noqa: BLE001
            pass

        # Restore the most recent project into the field on first open.
        if self._recents and not self.ui.project_field.text().strip():
            self.ui.project_field.setText(self._recents[0])

    # ------------------------------------------------------------------ widget init
    def cmb000_init(self, widget):
        """Populate the Unity version dropdown (newest first)."""
        from unitytk import UnityFinder

        widget.clear()
        editors = UnityFinder.find_editors()
        if not editors:
            widget.addItem("No Unity installs found", None)
            self._log(
                "No Unity Editors found under the Unity Hub path. Install one via "
                "Unity Hub, then reopen this panel.",
                "warning",
            )
            return
        for ver in sorted(editors, reverse=True):  # newest first
            widget.addItem(ver, editors[ver])
        self._log(f"Found {len(editors)} Unity Editor(s); newest selected.")

    def cmb001_init(self, widget):
        """Populate the recent-projects dropdown and wire selection."""
        self._populate_recents()
        widget.currentIndexChanged.connect(self._on_recent_changed)

    # ------------------------------------------------------------------ actions
    def b010(self):
        """Browse for an existing Unity project folder."""
        start = self.ui.project_field.text().strip() or os.path.expanduser("~")
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self.ui, "Select Unity project folder", start
        )
        if path:
            self.ui.project_field.setText(path)

    def b000(self):
        """Launch the selected Unity Editor on the project."""
        from unitytk import UnityLauncher

        project = self.ui.project_field.text().strip()
        if not self._require_project(project):
            return
        launcher = UnityLauncher(
            executable_path=self.ui.cmb000.currentData(), project_path=project
        )
        if not launcher.executable_path:
            self._log(
                "No Unity Editor available to launch (select a version above).", "error"
            )
            return
        proc = launcher.launch_editor(detached=True)
        if proc is None:
            self._log(f"Failed to launch the Unity Editor on {project}.", "error")
            return
        self._remember(project)
        self._log(
            f'Launched Unity on <a href="action://open?path={project}">{project}</a>.'
        )

    def b001(self):
        """Create a new Unity project, then load it into the field."""
        from unitytk import UnityLauncher

        launcher = UnityLauncher(executable_path=self.ui.cmb000.currentData())
        if not launcher.executable_path:
            self._log(
                "No Unity Editor available to create a project (select a version "
                "above).",
                "error",
            )
            return

        parent = QtWidgets.QFileDialog.getExistingDirectory(
            self.ui, "Choose where to create the new project", os.path.expanduser("~")
        )
        if not parent:
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self.ui, "New Unity Project", "Project name:"
        )
        name = (name or "").strip()
        if not ok or not name:
            return
        target = os.path.join(parent, name)
        if os.path.exists(target):
            self._log(f"Target already exists: {target}", "error")
            return

        self._log(
            f"Creating Unity project at {target} (batch mode; this can take a minute)…"
        )
        QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            created = launcher.create_project(target)
        except Exception as e:  # noqa: BLE001
            self._log(f"Project creation failed: {e}", "error")
            return
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        if created:
            self.ui.project_field.setText(target)
            self._remember(target)
            self._log(
                f'Created project at <a href="action://open?path={target}">{target}</a>.'
            )
        else:
            self._log(f"Project creation did not complete at {target}.", "error")

    # ------------------------------------------------------------------ helpers
    def _on_recent_changed(self, idx):
        data = self.ui.cmb001.itemData(idx)
        if data:
            self.ui.project_field.setText(data)

    def _require_project(self, project: str) -> bool:
        if not project:
            self._log("Set a Unity project folder (Browse…), or create one.", "error")
            return False
        if not os.path.isdir(os.path.join(project, "Assets")):
            self._log(f"Not a Unity project (no Assets/ folder): {project}", "error")
            return False
        return True

    def _log(self, msg: str, level: str = "info") -> None:
        color = {"info": "#FFFFFF", "warning": "#FFCC00", "error": "#FF5555"}.get(
            level, "#FFFFFF"
        )
        self.ui.txt000.append(f'<span style="color:{color}">{msg}</span>')

    def _on_log_link(self, url) -> None:
        try:
            if url.scheme() == "action" and url.host() == "open":
                from urllib.parse import parse_qs

                path = parse_qs(url.query()).get("path", [""])[0]
                if path:
                    _open_in_file_manager(path)
        except Exception as e:  # noqa: BLE001
            self._log(f"Could not open link: {e}", "error")

    @staticmethod
    def _shorten(path: str, n: int = 52) -> str:
        return path if len(path) <= n else "…" + path[-(n - 1):]

    # ------------------------------------------------------------------ recents
    def _populate_recents(self) -> None:
        widget = self.ui.cmb001
        widget.blockSignals(True)
        try:
            widget.clear()
            widget.addItem("Recent projects…", None)
            for path in self._recents:
                widget.addItem(self._shorten(path), path)
        finally:
            widget.blockSignals(False)

    def _recents_file(self) -> Path:
        from pythontk import user_config_root

        d = user_config_root() / "unity_studio"
        d.mkdir(parents=True, exist_ok=True)
        return d / "recents.json"

    def _load_recents(self) -> List[str]:
        try:
            data = json.loads(self._recents_file().read_text(encoding="utf-8"))
            return [p for p in data if isinstance(p, str)]
        except Exception:  # noqa: BLE001
            return []

    def _remember(self, project: str) -> None:
        project = os.path.normpath(project)
        ordered = [project] + [
            p for p in self._recents if os.path.normpath(p) != project
        ]
        self._recents = ordered[:_MAX_RECENTS]
        try:
            self._recents_file().write_text(
                json.dumps(self._recents, indent=2), encoding="utf-8"
            )
        except Exception:  # noqa: BLE001
            pass
        self._populate_recents()
