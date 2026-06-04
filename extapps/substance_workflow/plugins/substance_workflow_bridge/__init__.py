"""substance_workflow_bridge — Painter-side Python plugin.

Painter loads this whenever its containing directory appears in
``SUBSTANCE_PAINTER_PLUGINS_PATH``. The plugin always starts a JSON-RPC
HTTP server on ``SUBSTANCE_WORKFLOW_PORT`` (or an OS-assigned port if
unset). ``run_batch`` from the client side drives this same server —
there is no separate batch mode.
"""

import logging
import os
import sys

logger = logging.getLogger(__name__)

# Bootstrap: make the ``extapps.substance_workflow`` package (and its
# ``pythontk`` dependency) importable inside Painter's bundled Python.
# Layout: _scripts/extapps/extapps/substance_workflow/plugins/substance_workflow_bridge/__init__.py
#   parent[1] = plugins
#   parent[2] = substance_workflow
#   parent[3] = extapps          (the package)
#   parent[4] = extapps          (the repo)
#   parent[5] = _scripts         (monorepo root — add to sys.path)
# Importing ``extapps`` only needs ``pythontk`` (zero-dep, lazy bootstrap);
# it does NOT pull in qtpy/uitk.
_here = os.path.abspath(os.path.dirname(__file__))
_scripts_root = os.path.abspath(os.path.join(_here, "..", "..", "..", "..", ".."))
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)


def _load_ops() -> None:
    """Import op modules so their ``@register`` decorators run."""
    op_modules = [
        "extapps.substance_workflow.project_utils",
        "extapps.substance_workflow.texture_set_utils",
        "extapps.substance_workflow.layer_utils",
        "extapps.substance_workflow.channel_utils",
        "extapps.substance_workflow.material_utils",
        "extapps.substance_workflow.bake_utils",
        "extapps.substance_workflow.export_utils",
        "extapps.substance_workflow.resource_utils",
    ]
    for mod in op_modules:
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
