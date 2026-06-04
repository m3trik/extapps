"""Texture export operations — drive ``substance_painter.export``."""

from typing import List, Optional

from .registry import register


@register("export.list_presets")
def list_presets() -> List[str]:
    """Return user + built-in export preset names."""
    raise NotImplementedError


@register("export.textures")
def textures(
    output_path: str,
    preset: str,
    texture_sets: Optional[List[str]] = None,
    file_format: str = "png",
    bit_depth: int = 8,
) -> dict:
    """Export textures using ``preset``. ``texture_sets=None`` exports all.

    Returns ``{written: [...], errors: [...]}``.
    """
    raise NotImplementedError


@register("export.preset_to_dict")
def preset_to_dict(preset: str) -> dict:
    """Return the export-preset definition as a dict for inspection."""
    raise NotImplementedError
