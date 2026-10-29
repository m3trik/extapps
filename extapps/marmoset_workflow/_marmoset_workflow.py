# !/usr/bin/python
# coding=utf-8
"""The Toolbag engine as the standalone Marmoset Workflow panel drives it.

:class:`MarmosetWorkflow` is the vendored :class:`MarmosetEngine` (kept
byte-identical with mayatk's, so never edited here) with the class-level door a
panel reads, as mayatk's ``MarmosetBridge`` carries it: the app it launches
(:attr:`APP`) and its template folder (:attr:`TEMPLATE_DIR`). The panel is
tentacle's (``slots/tools/marmoset_workflow.py``).
"""

from ._marmoset_engine import _TEMPLATE_DIR, APP, MarmosetEngine


class MarmosetWorkflow(MarmosetEngine):
    """The Toolbag engine with its app and template folder on the class."""

    #: The Toolbag install a send launches (``APP.not_found_msg`` when absent).
    APP = APP
    #: The bundled ``templates/*.py`` a send renders.
    TEMPLATE_DIR = _TEMPLATE_DIR
