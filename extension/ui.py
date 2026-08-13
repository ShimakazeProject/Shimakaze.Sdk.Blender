"""User interface panel for the CnC template scene import (SHP group)."""

import bpy
from bpy.types import Panel

from . import i18n, utils

__all__ = ("register", "unregister")


class Shimakaze_PT_scene(Panel):
    bl_idname = "SHIMAKAZE_PT_scene"
    bl_label = "SHP"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "SHP"

    def draw(self, context):
        cnc_settings = context.window_manager.shimakaze_cnc
        scene_settings = context.scene.shimakaze_sdk
        i18n.set_language(cnc_settings.language)
        t = i18n.t
        layout = self.layout

        template_path = utils.get_cnc_template_path()
        if template_path.is_file():
            layout.label(text=t("Template: {name}").format(name=template_path.name))
        else:
            box = layout.box()
            box.alert = True
            box.label(text=t("Template file not found"), icon="ERROR")
            box.operator("shimakaze.download_template", text=t("Download Template"))

        layout.prop(cnc_settings, "language", text=t("Language"))

        if not scene_settings.is_imported:
            layout.label(text=t("CnC Template Import"))
            layout.prop(cnc_settings, "cnc_game", text=t("Game"))
            layout.prop(cnc_settings, "cnc_variant", text=t("Variant"))
            if not bpy.context.active_object:
                layout.label(text=t("Select an object first"))
                return

            layout.operator("shimakaze.import_cnc_scene", text=t("Import Scene"))
            return

        layout.prop(scene_settings, "target", text=t("Target"))

        layout.label(text=t("Render Passes"))
        column = layout.column(align=True)
        row = column.row(align=True)
        row.operator("shimakaze.shp_object", text="Object")
        row.operator("shimakaze.shp_buildup", text="Buildup")
        row.operator("shimakaze.shp_shadow", text="Shadow")
        row = column.row(align=True)
        row.operator("shimakaze.shp_preview", text="Preview")
        row.operator("shimakaze.shp_reset", text="Reset")

        layout.prop(scene_settings, "use_alpha", text=t("Alpha"))
        pass_label = t("Active pass: {name}").format(name=scene_settings.active_pass.capitalize())
        layout.label(text=pass_label)
        layout.prop(scene_settings, "output_template", text=t("Output Template"))
        layout.operator("shimakaze.render_batch", text=t("Batch Render"))

        layout.separator()

        layout.label(text=t("SHP Settings"))
        layout.prop(scene_settings, "faces", text=t("Faces (directions)"))
        if not utils.is_valid_direction_count(scene_settings.faces):
            box = layout.box()
            box.alert = True
            box.label(text=t("Direction count must be 1 or a multiple of 8"), icon="ERROR")

        layout.prop(scene_settings, "reverse", text=t("Reverse"))


def register() -> None:
    bpy.utils.register_class(Shimakaze_PT_scene)


def unregister() -> None:
    bpy.utils.unregister_class(Shimakaze_PT_scene)
