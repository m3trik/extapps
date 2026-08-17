# !/usr/bin/python
# coding=utf-8
"""Regression tests for extapps.substance_workflow.slots.

Covers the panel's startup docs anchor. The panel is a plain
``ptk.LoggingMixin`` slots class, NOT a ``BridgeSlotsBase`` subclass, so it
does not inherit the bridge base's link wiring and has to do it itself.
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

    ``setup_logging_redirect`` attaches pythontk's ``DefaultTextLogHandler``.
    pythontk is deliberately Qt-free, so that handler cannot wire Qt link
    handling: the pane is left with ``openExternalLinks`` False and clicking
    the anchor does nothing. ``BridgeSlotsBase`` calls
    ``TextEditLogHandler.route_links`` for its own panels; this panel is not
    one, so it must call it itself.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_app()

    def test_logging_redirect_alone_leaves_the_pane_unrouted(self):
        """Pins WHY the explicit call is required.

        ``setup_logging_redirect`` builds whatever class is registered in
        ``LoggerExt._text_handler`` -- a PROCESS-GLOBAL. uitk's
        ``BridgeSlotsBase._redirect_log_to_panel`` sets it to
        ``TextEditLogHandler`` (whose constructor routes links), so once any
        bridge panel has opened, every later redirect gets routing for free.
        Nothing sets it on this panel's documented standalone launch
        (``SubstanceWorkflowUI().show(...)``), where the default is pythontk's
        Qt-free ``DefaultTextLogHandler`` and the anchor is inert.

        That process-global is exactly why the panel must not rely on it: the
        same code path is live or dead depending on which unrelated panel
        opened first. This test forces the unregistered state so the
        dependency is pinned deterministically rather than by suite order.

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

    def test_panel_startup_routes_the_log_pane(self):
        """After the panel wires its pane, a web anchor reaches the browser and
        the log document is never navigated away from."""
        from unittest.mock import patch
        from qtpy.QtCore import QUrl
        from uitk.widgets.textEditLogHandler import TextEditLogHandler

        pane = QTextBrowser()
        sb = Mock()
        sb.loaded_ui.substance_workflow.txt003 = pane

        inst = SubstanceWorkflowSlots.__new__(SubstanceWorkflowSlots)
        inst.sb = sb
        inst.ui = sb.loaded_ui.substance_workflow
        inst.logger.setLevel(20)
        inst.logger.hide_logger_name(True)
        inst.logger.setup_logging_redirect(pane)

        # The line under test, exactly as __init__ runs it.
        TextEditLogHandler.route_links(inst.ui.txt003)

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
