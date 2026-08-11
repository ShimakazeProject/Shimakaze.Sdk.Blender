"""User interface panels for the Shimakaze SDK."""

import bpy
from bpy.types import Panel

__all__ = ("register", "unregister")


class Shimakaze_PT_sidebar(Panel):
    bl_idname = "SHIMAKAZE_PT_sidebar"
    bl_label = "Shimakaze SDK"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "SDK"

    def draw(self, context):
        settings = context.scene.shimakaze_sdk
        layout = self.layout

        layout.label(text="Scene Settings")
        layout.prop(settings, "asset_name")
        layout.prop(settings, "asset_version")
        layout.prop(settings, "dry_run")

        layout.separator()

        layout.operator("shimakaze.hello")
        layout.operator("shimakaze.bump_asset_version")


def register() -> None:
    bpy.utils.register_class(Shimakaze_PT_sidebar)


def unregister() -> None:
    bpy.utils.unregister_class(Shimakaze_PT_sidebar)
