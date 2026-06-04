"""Texture set operations — list, resolution, channel inventory."""

from typing import List

from .registry import register


@register("texture_set.list")
def list_() -> List[str]:
    """Return the names of all texture sets in the current project."""
    raise NotImplementedError


@register("texture_set.resolution")
def resolution(name: str) -> List[int]:
    """Return ``[width, height]`` of the named texture set."""
    raise NotImplementedError


@register("texture_set.set_resolution")
def set_resolution(name: str, width: int, height: int) -> None:
    """Set the texture set resolution. Must be power-of-two."""
    raise NotImplementedError


@register("texture_set.channels")
def channels(name: str) -> List[str]:
    """Return the channel identifiers active on the named texture set."""
    raise NotImplementedError


@register("texture_set.add_channel")
def add_channel(name: str, channel: str, fmt: str = "sRGB8") -> None:
    """Add a channel to the texture set (``BaseColor``, ``Roughness``, ...)."""
    raise NotImplementedError
