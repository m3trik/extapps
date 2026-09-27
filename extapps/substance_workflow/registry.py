"""Op registry — the callable Painter surface, on the shared RPC core.

The ops live in ``*_utils.py`` modules and register by name; the in-Painter
bridge serves them and :class:`PainterConnection` / :class:`Job` call them::

    @register("project.info")
    def info() -> dict: ...

There is no private RPC stack here. :data:`PLUGIN` is a
:class:`pythontk.RpcPlugin` -- the op table (:class:`pythontk.OpRegistry`), the
main-thread marshaller and the HTTP server that joins them, speaking the one
wire contract :class:`pythontk.RpcClient` speaks -- and the names below are its
registry's own methods. What stays Painter-specific is data on the plugin:

* ``env_prefix="SUBSTANCE_WORKFLOW"`` -- ``SUBSTANCE_WORKFLOW_PORT`` (the port
  :class:`PainterConnection` pins at launch; unset = OS-assigned),
  ``..._AUTOSTART``, ``..._DISABLE_MAIN_THREAD``.
* ``main_thread_timeout`` of an HOUR, not the core's 60 s default. Every op
  goes through the marshaller, including ``bake.mesh_maps`` /
  ``bake.all_texture_sets``, and a multi-texture-set 4K bake legitimately runs
  for many minutes: a bound near the slowest real op would turn working bakes
  into ``TimeoutError``. An hour still catches a genuinely deadlocked loop.

The plugin lives in this module, not in the bridge package, so a Painter
*Reload Plugins Folder* (which re-runs the bridge package) keeps the one table
its cached op modules registered on.
"""

from pythontk import RpcPlugin

#: The bridge's one plugin instance: op table + marshaller + server.
PLUGIN = RpcPlugin(
    label="substance_workflow",
    host_module="substance_painter",
    env_prefix="SUBSTANCE_WORKFLOW",
    default_port=0,
    main_thread_timeout=3600.0,
)

#: ``@register("ns.op")`` -- a duplicate name raises (a typo must not shadow).
register = PLUGIN.registry.register
#: The op callable registered under a name, or ``None``.
get = PLUGIN.registry.get
#: Every registered op name, sorted.
all_ops = PLUGIN.registry.all_ops
#: ``{name, doc, params}`` for one op, or a list of them for ``None``.
describe = PLUGIN.registry.describe
