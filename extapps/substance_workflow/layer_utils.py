"""Layer stack operations — list, add, remove, reorder, set properties."""

from typing import List, Optional

from .registry import register


@register("layer.list")
def list_(texture_set: str) -> List[dict]:
    """Return the layer stack for ``texture_set`` as a list of ``{name, uid, kind}`` dicts."""
    raise NotImplementedError


@register("layer.add_fill")
def add_fill(texture_set: str, name: str, color: Optional[List[float]] = None) -> str:
    """Add a fill layer. Returns the layer uid."""
    raise NotImplementedError


@register("layer.add_paint")
def add_paint(texture_set: str, name: str) -> str:
    """Add a paint layer. Returns the layer uid."""
    raise NotImplementedError


@register("layer.add_group")
def add_group(texture_set: str, name: str) -> str:
    """Add a folder/group node. Returns the group uid."""
    raise NotImplementedError


@register("layer.delete")
def delete(texture_set: str, uid: str) -> None:
    """Delete the layer identified by ``uid``."""
    raise NotImplementedError


@register("layer.set_opacity")
def set_opacity(texture_set: str, uid: str, channel: str, opacity: float) -> None:
    """Set per-channel opacity (0.0 - 1.0)."""
    raise NotImplementedError


@register("layer.set_blend_mode")
def set_blend_mode(texture_set: str, uid: str, channel: str, mode: str) -> None:
    """Set per-channel blend mode (``Normal``, ``Multiply``, ``Screen``, ...)."""
    raise NotImplementedError
