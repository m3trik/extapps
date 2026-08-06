"""substance_workflow_bridge — Painter-side Python plugin.

Painter loads this whenever its containing directory appears in
``SUBSTANCE_PAINTER_PLUGINS_PATH``. The plugin always starts a JSON-RPC
HTTP server on ``SUBSTANCE_WORKFLOW_PORT`` (or an OS-assigned port if
unset). ``run_batch`` from the client side drives this same server —
there is no separate batch mode.
"""

import importlib
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Bootstrap: make ``extapps.substance_workflow`` and its ``pythontk`` dependency
# importable inside Painter's bundled Python, where neither is installed.
# Painter loads this plugin in place from the repo (``plugins_dir()`` goes on
# ``SUBSTANCE_PAINTER_PLUGINS_PATH``; it is never copied), so the walk-up below
# is a reliable way back to the checkout.
#
# Layout: _scripts/extapps/extapps/substance_workflow/plugins/substance_workflow_bridge/
#   parent[1] = plugins
#   parent[2] = substance_workflow
#   parent[3] = extapps      (the package)
#   parent[4] = extapps      (the repo)   <- holds the `extapps` PACKAGE
#   parent[5] = _scripts     (monorepo root)
#
# Add each package's PARENT — never the monorepo root. Two reasons, both proven
# by probe rather than assumed:
#
# 1. The root does not work. It holds only the bare repo dirs, and
#    ``_scripts/extapps`` has no ``__init__.py``, so ``import extapps`` binds an
#    empty **namespace** package and ``extapps.substance_workflow`` — one level
#    deeper — is never found. ``pythontk`` was equally unreachable, and was only
#    ever importable here because the dev environment already had these dirs on
#    PYTHONPATH.
# 2. The root is actively harmful. Every *sibling* repo dir (``unitytk/``,
#    ``mayatk/``, …) becomes such a namespace too, outranking the real installed
#    package — even an editable one, whose finder is appended to
#    ``sys.meta_path`` AFTER the path finder that returns the namespace. That is
#    what made the Unity Workflow panel read ``unitytk`` as not installed
#    (``optional_package_available`` documents the trap it triggers).
#
# Guarded per package, and skipped entirely when the import already works: this
# module is not reached only from Painter — ``bootstrap_package`` resolves the
# package surface with ``pkgutil.walk_packages``, which *imports* every
# subpackage it walks, so a plain ``import extapps`` lands here too and must not
# mutate ``sys.path`` (the repo rule: imports have no side effects).
def _ensure_importable(module_name: str, package_parent: str) -> None:
    """Put *package_parent* on ``sys.path`` only if *module_name* won't import.

    A module that imports but has no ``__file__`` is the namespace-shadow case
    above — present in name only, every attribute access ahead of it doomed — so
    it counts as *not* importable and the real parent still goes on the path,
    where a regular package outranks the namespace portion. Same rule uitk's
    ``optional_package_available`` applies on the probe side.
    """
    try:
        if getattr(importlib.import_module(module_name), "__file__", None):
            return
    except ImportError:
        pass
    if os.path.isdir(package_parent) and package_parent not in sys.path:
        sys.path.insert(0, package_parent)


_extapps_repo = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_scripts_root = os.path.dirname(_extapps_repo)

_ensure_importable("extapps", _extapps_repo)
_ensure_importable("pythontk", os.path.join(_scripts_root, "pythontk"))


# Every top-level ``*_utils.py`` op module in ``extapps.substance_workflow``.
# An op module missing here registers nothing inside Painter;
# ``test_ops_registration.py`` guards this list against the files on disk.
OP_MODULES = (
    "extapps.substance_workflow.project_utils",
    "extapps.substance_workflow.texture_set_utils",
    "extapps.substance_workflow.layer_utils",
    "extapps.substance_workflow.channel_utils",
    "extapps.substance_workflow.material_utils",
    "extapps.substance_workflow.bake_utils",
    "extapps.substance_workflow.export_utils",
    "extapps.substance_workflow.resource_utils",
)


def _load_ops() -> None:
    """Import op modules so their ``@register`` decorators run."""
    for mod in OP_MODULES:
        try:
            __import__(mod)
        except Exception as e:
            logger.error(f"[substance_workflow] Failed to load op module {mod}: {e}")


_load_ops()

_server = None


def start_plugin() -> None:
    """Painter plugin entry point — start the JSON-RPC bridge server."""
    global _server
    try:
        from .server import BridgeServer

        port = int(os.environ.get("SUBSTANCE_WORKFLOW_PORT", "0"))
        _server = BridgeServer(port=port)
        _server.start()
    except Exception as e:
        logger.exception(f"[substance_workflow] Bridge failed to start: {e}")
        _server = None


def close_plugin() -> None:
    """Painter plugin teardown."""
    global _server
    if _server is not None:
        try:
            _server.stop()
        except Exception as e:
            logger.exception(f"[substance_workflow] Bridge failed to stop cleanly: {e}")
        _server = None
