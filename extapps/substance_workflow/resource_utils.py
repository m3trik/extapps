"""Shelf / resource operations — query and import shelf assets."""

from typing import List

from .registry import register


@register("resource.list_shelves")
def list_shelves() -> List[str]:
    """Return the names of all configured shelves."""
    raise NotImplementedError


@register("resource.list_assets")
def list_assets(shelf: str, kind: str = "smartmaterial") -> List[dict]:
    """List assets of ``kind`` on ``shelf``. ``kind`` ∈ {smartmaterial, smartmask, brush, ...}."""
    raise NotImplementedError


@register("resource.import")
def import_(path: str, shelf: str = "your_assets", kind: str = "smartmaterial") -> str:
    """Import an asset file into the named shelf. Returns the resource url."""
    raise NotImplementedError
