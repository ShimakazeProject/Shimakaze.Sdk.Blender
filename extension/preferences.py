"""Add-on preferences for the Shimakaze SDK."""

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import AddonPreferences

__all__ = ("register", "unregister")


class ShimakazePreferences(AddonPreferences):
    # For extensions the add-on module is imported under the ``bl_ext.<repo>.<pkg>``
    # namespace, so ``__package__`` is always the correct ``bl_idname``.
    bl_idname: str = __package__ or ""

    api_endpoint: StringProperty(
        name="API Endpoint",
        description="Base URL of the backend the SDK talks to",
        default="https://example.com/api",
    )

    debug_logging: BoolProperty(
        name="Debug Logging",
        description="Print debug messages to the system console",
        default=False,
    )

    def draw(self, _context):
        layout = self.layout
        layout.prop(self, "api_endpoint")
        layout.prop(self, "debug_logging")


def register() -> None:
    bpy.utils.register_class(ShimakazePreferences)


def unregister() -> None:
    bpy.utils.unregister_class(ShimakazePreferences)
