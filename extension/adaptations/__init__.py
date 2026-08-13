"""Version-specific template adaptations, selected at runtime.

Each renderer (``eevee_next``, ``hi_five``) has its own sub-package exposing
``get_template_file_name`` and ``repair_compositor`` under one consistent API.
The dispatcher imports the matching sub-package for the running Blender.
"""

import importlib


def current_template_renderer() -> str:
    """Return the template renderer folder matching the running Blender.

    Blender 4.2+ uses Eevee Next; Blender 5.x uses the "Hi Five" template.
    """
    import bpy

    if bpy.app.version[0] >= 5:
        return "hi_five"
    return "eevee_next"


def _renderer_module():
    return importlib.import_module(f"{__name__}.{current_template_renderer()}")


def get_template_file_name() -> str:
    """Template .blend file name for the running Blender version."""
    return _renderer_module().get_template_file_name()


def repair_compositor(node_tree) -> bool:
    """Repair the template compositor for the running Blender's renderer."""
    try:
        return _renderer_module().repair_compositor(node_tree)
    except ImportError:
        return False
