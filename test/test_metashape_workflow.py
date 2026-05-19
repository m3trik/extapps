#!/usr/bin/env python
# coding=utf-8
"""Smoke tests — the UI builds and Run Workflow doesn't crash on empty input.

Scope is deliberately narrow: regression net for "did we break the UI build
again?" (the AttributeError / import-order class of bugs that bit us
earlier in development). Behavioral coverage of the photogrammetry pipeline
is out of scope — that needs Metashape installed and real input data.

Three assertions:

* :meth:`test_ui_builds` — :class:`MetashapeWorkflowUI` constructs, the
  expected ``Header`` / ``Footer`` are in place, and the frameless window
  flag is set.
* :meth:`test_named_widgets_resolve` — every objectName declared in
  :data:`PIPELINE_STAGES` and :data:`ADVANCED_PARAMS` resolves via
  ``getattr(ui, key)``. Catches dynamic-widget plumbing breakage where the
  popup tree disconnects from ``findChild``.
* :meth:`test_run_workflow_empty_inputs_bails_gracefully` — clicking Run
  Workflow with no project directory set: ``_validate`` rejects, no
  exception escapes, ``_busy`` is not stuck, button stays enabled.

Run::

    pytest extapps/test/test_metashape_workflow.py

Any Python with ``qtpy`` and the monorepo on PYTHONPATH works.
"""
from __future__ import annotations

import sys
import unittest

from qtpy import QtCore
from qtpy.QtWidgets import QApplication


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestMetashapeWorkflowLoads(unittest.TestCase):
    """Smoke checks against a freshly-built MetashapeWorkflow UI."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from extapps import metashape_workflow as m
        self.ui = m.MetashapeWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        # Drop the window; QApplication persists for the next test.
        self.ui.deleteLater()
        self.app.processEvents()

    # ------------------------------------------------------------------

    def test_ui_builds(self) -> None:
        self.assertEqual(self.ui.objectName(), "metashape_workflow")

        from uitk.widgets.header import Header
        from uitk.widgets.footer import Footer
        self.assertIsInstance(self.ui.header, Header)
        self.assertIsInstance(self.ui.footer, Footer)

        self.assertTrue(
            bool(self.ui.windowFlags() & QtCore.Qt.FramelessWindowHint),
            "FramelessWindowHint is not set — OS frame would be visible",
        )

    def test_named_widgets_resolve(self) -> None:
        """Every declared widget objectName is reachable via getattr(ui, key).

        This is the canary for the popup-tree / findChild integration:
        widgets created inside QMenu via QWidgetAction must still be
        findable from the top-level UI for ``_collect_*`` to work.
        """
        from extapps.metashape_workflow.slots import (
            ADVANCED_PARAMS,
            PIPELINE_STAGES,
        )
        for stage_name, *_ in PIPELINE_STAGES:
            self.assertIsNotNone(
                getattr(self.ui, stage_name, None),
                f"Pipeline stage widget {stage_name!r} not reachable on ui",
            )
        for spec in ADVANCED_PARAMS:
            self.assertIsNotNone(
                getattr(self.ui, spec.key, None),
                f"Advanced param widget {spec.key!r} not reachable on ui",
            )

    def test_run_workflow_empty_inputs_bails_gracefully(self) -> None:
        """Run Workflow with no project dir: validate rejects, no exception."""
        self.ui.txt000.clear()
        self.ui.txt002.clear()

        # _validate is the gate inside _run_workflow; call it directly so
        # any exception surfaces as a test failure rather than being
        # swallowed by the switchboard's execution monitor.
        self.assertFalse(
            self.slots._validate(),
            "_validate should reject an empty project directory",
        )

        # Now exercise the full b000 callback path (button click -> slot
        # framework -> _run_workflow). Any uncaught exception inside
        # _run_workflow would still propagate via .click() under qtpy.
        try:
            self.ui.b000.click()
        except Exception as exc:  # noqa: BLE001 — we want any failure to fail the test
            self.fail(f"b000 click raised: {type(exc).__name__}: {exc}")

        self.assertFalse(
            getattr(self.slots, "_busy", False),
            "_busy stuck True after validate failure — UI would be locked",
        )
        self.assertTrue(
            self.ui.b000.isEnabled(),
            "Run Workflow button left disabled after validate failure",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
