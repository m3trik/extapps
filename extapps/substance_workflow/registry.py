"""Op registry — single source of truth for callable Painter operations.

Both the live HTTP server and the batch runner look up ops here by name.
Decorate functions in ``*_utils.py`` modules to register them::

    @register("project.info")
    def info() -> dict: ...
"""

import inspect
import logging
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, Callable] = {}


def register(name: Optional[str] = None) -> Callable:
    """Decorator: register a function as an op.

    Parameters:
        name: Dotted op name (e.g. ``"project.info"``). If None, derived
              from the function's module + name (``project_utils.info``
              becomes ``project.info``).
    """

    def wrap(fn: Callable) -> Callable:
        op_name = name or _derive_name(fn)
        if op_name in _REGISTRY:
            logger.warning(f"[registry] Op {op_name!r} re-registered (overriding).")
        fn._op_name = op_name
        _REGISTRY[op_name] = fn
        return fn

    return wrap


def get(name: str) -> Optional[Callable]:
    return _REGISTRY.get(name)


def all_ops() -> Dict[str, Callable]:
    return dict(_REGISTRY)


def describe(name: str = "") -> dict:
    """Return op signature + docstring for agent self-discovery.

    If ``name`` is empty, returns a dict of ``{name: description}`` for all ops.
    """
    if not name:
        return {n: describe(n) for n in _REGISTRY}

    fn = _REGISTRY.get(name)
    if fn is None:
        return {}
    sig = inspect.signature(fn)
    return {
        "name": name,
        "doc": inspect.getdoc(fn) or "",
        "parameters": {
            p.name: {
                "annotation": _ann(p.annotation),
                "default": None if p.default is p.empty else repr(p.default),
                "kind": p.kind.name,
            }
            for p in sig.parameters.values()
        },
        "return": _ann(sig.return_annotation),
    }


def _ann(a) -> str:
    if a is inspect.Signature.empty or a is inspect.Parameter.empty:
        return "Any"
    return getattr(a, "__name__", None) or str(a)


def _derive_name(fn: Callable) -> str:
    module = fn.__module__.rsplit(".", 1)[-1]
    if module.endswith("_utils"):
        module = module[:-6]
    return f"{module}.{fn.__name__}"
