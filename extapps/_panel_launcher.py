# !/usr/bin/python
# coding=utf-8
"""The one launcher every extapps panel is.

Each tool's ``launcher.py`` used to hand-write the same shell -- build a
Switchboard from ``<tool>.ui`` + the tool's Slots class, set the frameless
chrome, style it, configure the header, title it -- eleven copies of one
recipe. The frameless-window fix once landed in three of them and the other
eight kept the bug for a release (``CODE_STANDARD.md`` section 6). The recipe
lives here once; a ``<Tool>UI`` declares only what differs, as data::

    class MetashapeWorkflowUI(PanelLauncher):
        TITLE = "Metashape Workflow"

Everything else is derived from where the subclass lives, so there is nothing
to restate:

* the ``.ui`` is ``<tool dir>/<tool>.ui`` beside the launcher module, and the
  loaded window is ``sb.loaded_ui.<tool>``;
* the Slots class is the one the tool's bootstrap root already names --
  ``DEFAULT_INCLUDE["slots"]`` in ``extapps/<tool>/__init__.py``, resolved from
  the sibling ``slots`` module.

``<Tool>UI()`` returns the built window (``__new__`` returns it; no instance of
the launcher class is made), which is what the ``uitk.external_apps.in_process``
entry points and the tools' ``__main__`` blocks call.
"""

from __future__ import annotations

import importlib
import os
import sys
from typing import Optional, Tuple

from pythontk import FileUtils
from uitk import Bootstrap

# Must run before QApplication is constructed, so before any import that
# touches Switchboard: every launcher imports this module first. No-ops inside
# DCC hosts that already own the QApplication.
Bootstrap.configure_high_dpi()


class _PanelLauncherInternal:
    """Derivation helpers for :class:`PanelLauncher`."""

    @classmethod
    def _tool(cls) -> Tuple[str, str, str]:
        """``(package, tool name, tool dir)`` of the launcher subclass.

        The package is read from the defining module's spec, not from
        ``cls.__module__``: a ``launcher.py`` run as a program defines its class
        in ``"__main__"``. Under ``python -m`` the spec still carries the real
        dotted name; run as a script the module has no spec, and the package is
        the chain of ``__init__.py`` folders above the file.
        """
        module = sys.modules[cls.__module__]
        folder = os.path.dirname(os.path.abspath(module.__file__))
        spec = getattr(module, "__spec__", None)
        package = spec.name.rpartition(".")[0] if spec is not None else ""
        if not package:
            package = (
                FileUtils.canonical_module_path(os.path.join(folder, "__init__.py"))
                or ""
            )
        return package, package.rpartition(".")[2], folder

    @staticmethod
    def _slots_class(package: str) -> type:
        """The Slots class the tool's bootstrap root names in DEFAULT_INCLUDE."""
        (name,) = importlib.import_module(package).DEFAULT_INCLUDE["slots"]
        return getattr(importlib.import_module(f"{package}.slots"), name)


class PanelLauncher(_PanelLauncherInternal):
    """Base of every extapps ``<Tool>UI``: calling it returns the built panel.

    Class attributes (data, per tool):
        TITLE: Window-title stem. A titled panel also shows the release on its
            header, is titled ``"<TITLE> v<version>"`` and opens at its size
            hint; ``None`` (the compact tools) leaves the ``.ui``'s own title
            and size.
        STYLE_CLASS: The uitk style class of the window.
        HEADER_BUTTONS: The header's window controls, in order.
    """

    TITLE: Optional[str] = None
    STYLE_CLASS: str = "bgWithBorder"
    HEADER_BUTTONS: Tuple[str, ...] = ("menu", "minimize", "fullscreen", "hide")

    def __new__(cls, *args, **kwargs):
        from qtpy import QtCore
        from uitk import PresetEditor, Switchboard

        # uitk names no app: the Preset Editor learns this package's label here.
        PresetEditor.register_app_label("extapps", "Standalone")
        package, name, folder = cls._tool()
        sb = Switchboard(
            *args,
            ui_source=os.path.join(folder, f"{name}.ui"),
            slot_source=cls._slots_class(package),
            **kwargs,
        )
        ui = getattr(sb.loaded_ui, name)
        Bootstrap.set_translucent(ui)  # opaque where nothing composites (X11)
        # Frameless chromed window: the uitk Header supplies the window
        # controls in place of the native OS frame. Set the SAME clean flag set
        # as uitk's WindowPanel rather than OR-ing FramelessWindowHint onto a
        # QMainWindow's defaults -- those defaults carry native decoration hints
        # which, on a frameless host-owned window, make it float always-on-top
        # of its parent. With the clean set it behaves as a normal window that
        # parents to the host (e.g. Maya, via the external-app handler).
        ui.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        ui.style.set(theme="dark", style_class=cls.STYLE_CLASS)
        ui.header.config_buttons(*cls.HEADER_BUTTONS)
        if cls.TITLE:
            from extapps import __version__

            ui.header.setVersion(__version__)
            ui.setWindowTitle(f"{cls.TITLE} v{__version__}")
            ui.resize(ui.sizeHint())
        return ui
