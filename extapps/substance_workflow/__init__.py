# !/usr/bin/python
# coding=utf-8
"""Substance Workflow — Adobe Substance 3D Painter integration.

A Switchboard panel (``SubstanceWorkflowUI``) drives the Painter engine that
lives in this package: an op **registry**, a client **``PainterConnection``**
(launches a fresh Painter and talks JSON-RPC), the **``run_batch``** wrapper,
and the in-Painter **bridge plugin** (``plugins/substance_workflow_bridge``).

Two execution modes share one op registry:

* :class:`PainterConnection` — live JSON-RPC against a Painter session.
* :func:`run_batch` — one-shot batch invocation that exits when done.

Op modules (``project_utils``, ``bake_utils``, …) register callables via
:func:`register`; the bridge plugin loads them inside Painter and dispatches
by name. They lazy-import ``substance_painter`` so the modules stay
import-safe outside Painter (tests, registry inspection).
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.substance_workflow"


DEFAULT_INCLUDE = {
    "launcher": ["SubstanceWorkflowUI"],
    "slots": ["SubstanceWorkflowSlots"],
    "env_utils.painter_connection": ["PainterConnection"],
    "env_utils.painter_finder": ["PainterFinder"],
    "job": ["Call", "Job", "Result", "run_batch"],
    "registry": ["register", "get", "all_ops", "describe"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "SubstanceWorkflowUI",
    "SubstanceWorkflowSlots",
    "PainterConnection",
    "PainterFinder",
    "Call",
    "Job",
    "Result",
    "run_batch",
    "register",
    "get",
    "all_ops",
    "describe",
]
