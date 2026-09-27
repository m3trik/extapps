# !/usr/bin/python
# coding=utf-8
"""Substance Workflow — Adobe Substance 3D Painter integration.

A Switchboard panel (``SubstanceWorkflowUI``) drives the Painter engine that
lives in this package: an op **registry**, a client **``PainterConnection``**
(launches a fresh Painter and talks JSON-RPC), the **``Job.run_batch``** wrapper,
and the in-Painter **bridge plugin** (``plugins/substance_workflow_bridge``).
The RPC itself is pythontk's shared pair -- the registry is a
:class:`pythontk.RpcPlugin`, the client a :class:`pythontk.RpcClient`, the batch
loop :class:`pythontk.RpcJob` over :class:`pythontk.Call` / :class:`pythontk.Result`.

Two execution modes share one op registry:

* :class:`PainterConnection` — live JSON-RPC against a Painter session.
* :meth:`Job.run_batch` — one-shot batch invocation that exits when done.

Op modules (``project_utils``, ``bake_utils``, …) register callables via
:func:`register`; the bridge plugin loads them inside Painter and dispatches
by name. They lazy-import ``substance_painter`` so the modules stay
import-safe outside Painter (tests, registry inspection).
"""

import pythontk as ptk
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.substance_workflow"


DEFAULT_INCLUDE = {
    "launcher": ["SubstanceWorkflowUI"],
    "slots": ["SubstanceWorkflowSlots"],
    "env_utils.painter_connection": ["PainterConnection"],
    "env_utils.painter_finder": ["PainterFinder"],
    "job": ["Job"],
    "registry": ["register", "get", "all_ops", "describe"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)

# The batch types are pythontk's since the RPC stack collapsed onto the shared
# core; the names here only alias them for one release.
ptk.Deprecation.attributes(
    globals(),
    {
        "Call": "pythontk.Call",
        "Result": "pythontk.Result",
    },
    remove_in="0.4.0",
    since="2026-09-26",
)


__all__ = [
    "SubstanceWorkflowUI",
    "SubstanceWorkflowSlots",
    "PainterConnection",
    "PainterFinder",
    "Job",
    "register",
    "get",
    "all_ops",
    "describe",
]
