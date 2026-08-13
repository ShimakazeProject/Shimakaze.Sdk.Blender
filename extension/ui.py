"""User interface panel for the CnC template scene import (SHP group)."""

import bpy
from bpy.types import Panel

from . import utils

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
        layout = self.layout

        template_path = utils.get_cnc_template_path()
        if template_path.is_file():
            layout.label(text=f"模板：{template_path.name}")
        else:
            box = layout.box()
            box.alert = True
            box.label(text="模板文件不存在", icon="ERROR")
            box.operator("shimakaze.download_template")

        if not scene_settings.is_imported:
            layout.label(text="CnC 模板导入")
            layout.prop(cnc_settings, "cnc_game")
            layout.prop(cnc_settings, "cnc_variant")
            if not bpy.context.active_object:
                layout.label(text="请先选择一个对象")
                return

            layout.operator("shimakaze.import_cnc_scene")
            return

        layout.prop(scene_settings, "target")

        layout.label(text="渲染通道")
        column = layout.column(align=True)
        row = column.row(align=True)
        row.operator("shimakaze.shp_object")
        row.operator("shimakaze.shp_buildup")
        row.operator("shimakaze.shp_shadow")
        row = column.row(align=True)
        row.operator("shimakaze.shp_preview")
        row.operator("shimakaze.shp_reset")

        layout.prop(scene_settings, "use_alpha")
        layout.label(text=f"当前通道：{scene_settings.active_pass.capitalize()}")
        layout.prop(scene_settings, "output_template")
        layout.operator("shimakaze.render_batch")

        layout.separator()

        layout.label(text="SHP Settings")
        layout.prop(scene_settings, "faces")
        if not utils.is_valid_direction_count(scene_settings.faces):
            box = layout.box()
            box.alert = True
            box.label(text="方向数必须是 1 或 8 的倍数", icon="ERROR")

        layout.prop(scene_settings, "reverse")


def register() -> None:
    bpy.utils.register_class(Shimakaze_PT_scene)


def unregister() -> None:
    bpy.utils.unregister_class(Shimakaze_PT_scene)
