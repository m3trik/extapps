"""Project-level operations — open, save, close, info, mesh swap.

SPIKE: ``project.info`` is the canary used to verify the launcher +
main-thread RPC end-to-end. Other ops in this module follow the same
shape but need verification against the live Painter API.
"""

from typing import Optional

from .registry import register


@register("project.info")
def info() -> dict:
    """Return basic info about the current project, or ``{'open': False}``."""
    import substance_painter.project as project

    if not project.is_open():
        return {"open": False}
    return {
        "open": True,
        "name": project.name(),
        "file_path": project.file_path() if project.file_path() else None,
    }


@register("project.open")
def open_(path: str) -> dict:
    """Open an existing ``.spp`` project. Returns the project info dict."""
    import substance_painter.project as project

    project.open(path)
    return info()


@register("project.save")
def save() -> dict:
    """Save the current project to its existing path."""
    import substance_painter.project as project

    project.save()
    return info()


@register("project.save_as")
def save_as(path: str) -> dict:
    """Save the current project to ``path``."""
    import substance_painter.project as project

    project.save_as(path)
    return info()


@register("project.close")
def close() -> dict:
    """Close the current project without saving."""
    import substance_painter.project as project

    project.close()
    return {"open": False}


@register("project.create")
def create(mesh_path: str, template_path: Optional[str] = None) -> dict:
    """Create a new project from a mesh. ``template_path`` is optional."""
    import substance_painter.project as project

    settings = project.Settings()
    if template_path:
        project.create(mesh_file_path=mesh_path, template_file_path=template_path, settings=settings)
    else:
        project.create(mesh_file_path=mesh_path, settings=settings)
    return info()


@register("project.reload_mesh")
def reload_mesh(mesh_path: str) -> dict:
    """Reimport the project's mesh from ``mesh_path``."""
    import substance_painter.project as project

    project.reload_mesh(mesh_path)
    return info()
