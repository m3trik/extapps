"""Channel operations — query and modify per-channel state on a texture set."""

from typing import List

from .registry import register


@register("channel.list_formats")
def list_formats() -> List[str]:
    """Return the channel format names supported by Painter (``sRGB8``, ``L16``, ...)."""
    raise NotImplementedError


@register("channel.format")
def format(texture_set: str, channel: str) -> str:  # noqa: A001
    """Return the storage format of the named channel."""
    raise NotImplementedError


@register("channel.set_format")
def set_format(texture_set: str, channel: str, fmt: str) -> None:
    """Set the storage format of the named channel."""
    raise NotImplementedError


@register("channel.export_path")
def export_path(texture_set: str, channel: str) -> str:
    """Return the channel's user-defined export path template, if any."""
    raise NotImplementedError
