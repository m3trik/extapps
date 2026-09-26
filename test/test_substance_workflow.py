# !/usr/bin/python
# coding=utf-8
"""Regression tests for extapps.substance_workflow.slots.

Covers the panel's log pane: its startup docs anchor and the width its boxes
are sized to. The panel is a plain ``ptk.LoggingMixin`` slots class, NOT a
``BridgeSlotsBase`` subclass, so it does not inherit the bridge base's log
wiring and sets uitk's ``TextEditLogHandler`` itself.
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qtpy.QtWidgets import QApplication, QTextBrowser  # noqa: E402

from extapps.substance_workflow.slots import SubstanceWorkflowSlots  # noqa: E402


def _ensure_app():
    return QApplication.instance() or QApplication([])


class TestSubstanceDocsLink(unittest.TestCase):
    """The startup docs line must be a LIVE anchor, not just styled text.

    A bare ``setup_logging_redirect`` attaches pythontk's
    ``DefaultTextLogHandler``. pythontk is deliberately Qt-free, so that
    handler cannot wire Qt link handling (the pane is left with
    ``openExternalLinks`` False and clicking the anchor does nothing) nor
    measure the pane. ``BridgeSlotsBase`` sets ``TextEditLogHandler`` for its
    own panels; this panel is not one, so it sets it itself.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_app()

    def test_logging_redirect_alone_leaves_the_pane_unrouted(self):
        """Pins WHY the panel sets its handler itself.

        ``setup_logging_redirect`` builds the logger's own text handler, else
        the process default ``LoggerExt._text_handler``, else pythontk's
        Qt-free ``DefaultTextLogHandler`` -- the case on this panel's
        documented standalone launch (``SubstanceWorkflowUI().show(...)``),
        where nothing else has registered one, and the anchor is inert. This
        test forces that unregistered state so the dependency is pinned
        deterministically rather than by suite order.

        Unrouted is worse than inert: QTextBrowser.openLinks defaults True, so
        a click navigates the pane to the URL and REPLACES the log document.
        """
        import pythontk as ptk
        from uitk.widgets.textEditLogHandler import TextEditLogHandler

        class _Host(ptk.LoggingMixin):
            pass

        from pythontk.core_utils.logging_mixin import LoggerExt

        host = _Host()
        saved = LoggerExt._text_handler
        try:
            LoggerExt._text_handler = None  # the standalone-launch state
            pane = QTextBrowser()
            host.logger.setup_logging_redirect(pane)

            self.assertIsNone(pane.property(TextEditLogHandler._LINKS_ROUTED_PROP))
            self.assertTrue(
                pane.openLinks(), "unrouted pane would navigate away on click"
            )
        finally:
            LoggerExt._text_handler = saved

    def _open_panel(self, pane):
        """Run the panel's real ``__init__`` against *pane* (no Painter scan)."""
        from unittest.mock import patch

        sb = Mock()
        sb.loaded_ui.substance_workflow.txt003 = pane
        with patch(
            "extapps.substance_workflow.slots.PainterFinder.find_installs",
            return_value={},
        ):
            inst = SubstanceWorkflowSlots(sb)
        for handler in inst.logger.handlers:
            if getattr(handler, "widget", None) is pane:
                self.addCleanup(inst.logger.removeHandler, handler)
                return inst, handler
        self.fail("the panel never redirected its log into the pane")

    def test_panel_log_pane_reports_its_width(self):
        """The panel logs boxes (its run header, WORKFLOW COMPLETE), and a box
        is sized to the width its handler reports. pythontk's Qt-free
        ``DefaultTextLogHandler`` reports none, so every box came out
        ``DEFAULT_BOX_WIDTH`` (100) columns wide whatever the pane, and broke
        in any narrower one."""
        _inst, handler = self._open_panel(QTextBrowser())
        self.assertTrue(callable(getattr(handler, "available_columns", None)))

    def test_panel_startup_routes_the_log_pane(self):
        """After the panel wires its pane, a web anchor reaches the browser and
        the log document is never navigated away from."""
        from unittest.mock import patch
        from qtpy.QtCore import QUrl
        from uitk.widgets.textEditLogHandler import TextEditLogHandler

        pane = QTextBrowser()
        self._open_panel(pane)

        self.assertTrue(pane.property(TextEditLogHandler._LINKS_ROUTED_PROP))
        # setOpenLinks(False) is what stops a click wiping the log document.
        self.assertFalse(pane.openLinks())
        self.assertFalse(pane.openExternalLinks())

        # And the docs anchor actually reaches the browser.
        with patch(
            "uitk.widgets.textEditLogHandler.QtGui.QDesktopServices.openUrl"
        ) as opened:
            pane.anchorClicked.emit(QUrl(SubstanceWorkflowSlots.DOCS_URL))
        self.assertEqual(opened.call_count, 1)
        self.assertEqual(
            opened.call_args[0][0].toString(), SubstanceWorkflowSlots.DOCS_URL
        )


if __name__ == "__main__":
    sys.exit(unittest.main())
