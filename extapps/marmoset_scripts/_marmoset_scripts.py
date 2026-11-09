# !/usr/bin/python
# coding=utf-8
"""The Toolbag engine as the standalone Marmoset Scripts panel drives it.

:class:`MarmosetScripts` is the vendored :class:`MarmosetEngine` (kept
byte-identical with the host bridges' copy, so never edited here) with the
class-level door a panel reads, as a host bridge carries it: the app it
launches (:attr:`APP`) and its bundled template folder (:attr:`TEMPLATE_DIR`;
the folders a script name resolves in, the person's own first, are the
engine's :meth:`~MarmosetEngine.template_dirs`). The panel is this package's
(``slots.py``).
"""

from ._marmoset_engine import _TEMPLATE_DIR, APP, MarmosetEngine


class MarmosetScripts(MarmosetEngine):
    """The Toolbag engine with its app and template folder on the class."""

    #: The Toolbag install a send launches (``APP.not_found_msg`` when absent).
    APP = APP
    #: The bundled ``templates/*.py`` a send renders.
    TEMPLATE_DIR = _TEMPLATE_DIR
