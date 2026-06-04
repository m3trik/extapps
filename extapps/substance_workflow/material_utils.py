"""Smart-material / preset operations — apply shelf materials onto layers."""

from typing import List, Optional

from .registry import register


@register("material.list_shelf")
def list_shelf() -> List[dict]:
    """Return shelf-bound smart materials as ``[{name, url, tags}, ...]``."""
    raise NotImplementedError


@register("material.apply_smart")
def apply_smart(
    texture_set: str,
    material_url: str,
    target_layer_uid: Optional[str] = None,
) -> str:
    """Apply a smart material. If ``target_layer_uid`` is None, add at top of stack.

    Returns the uid of the resulting layer/group.
    """
    raise NotImplementedError


@register("material.import_to_shelf")
def import_to_shelf(path: str, shelf_name: str = "your_assets") -> str:
    """Import an ``.spsm`` smart material into the named shelf."""
    raise NotImplementedError
