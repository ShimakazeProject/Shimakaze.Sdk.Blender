"""Operators for importing CnC template scenes."""

from __future__ import annotations

from math import radians
from typing import TYPE_CHECKING

import bpy
from bpy.types import Operator

from . import utils

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems

__all__ = ("register", "unregister")


class ShimakazeSDKBaseOperator(Operator):
    """Common behavior for every Shimakaze SDK operator."""

    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None


class Shimakaze_OT_import_cnc_scene(ShimakazeSDKBaseOperator):
    bl_idname = "shimakaze.import_cnc_scene"
    bl_label = "Import CnC Template Scene"
    bl_description = "Append the selected scene from the CnC template into the current workspace"

    def execute(self, context) -> set[OperatorReturnItems]:
        settings = context.window_manager.shimakaze_cnc
        game = settings.cnc_game
        if game not in utils.CNC_GAME_OPTIONS:
            self.report({"ERROR"}, "Unknown CnC game selected")
            return {"CANCELLED"}

        template_scene, final_scene = utils.resolve_cnc_scene(game, settings.infantry)

        template_path = utils.get_cnc_template_path()
        if not template_path.is_file():
            self.report({"ERROR"}, f"CnC template file not found: {template_path}")
            return {"CANCELLED"}

        selected_objects = list(context.selected_objects)
        existing_scenes = set(bpy.data.scenes.keys())

        bpy.ops.wm.append(
            directory=f"{template_path}/Scene/",
            filename=template_scene,
            link=False,
        )

        appended = next(
            (name for name in bpy.data.scenes.keys() if name not in existing_scenes),
            None,
        )
        if appended is None:
            self.report({"ERROR"}, f"Failed to append the CnC template scene '{template_scene}'")
            return {"CANCELLED"}

        new_scene = bpy.data.scenes[appended]
        new_scene.name = final_scene
        context.window.scene = new_scene

        objects_to_link = utils.collect_objects_to_link(selected_objects)
        for obj in objects_to_link:
            if obj.name not in new_scene.objects:
                new_scene.collection.objects.link(obj)

        target = self._ensure_target(new_scene)
        for obj in objects_to_link:
            if obj.parent not in objects_to_link:
                obj.parent = target

        self.report(
            {"INFO"},
            f"Appended CnC template scene '{final_scene}' with target '{target.name}'"
            + (f" and {len(objects_to_link)} linked object(s)" if objects_to_link else ""),
        )
        return {"FINISHED"}

    @staticmethod
    def _ensure_target(new_scene) -> bpy.types.Object:
        """Return this scene's target, reusing the one stored on the scene.

        Creates a uniquely named empty when none is recorded yet, keeps its
        Euler rotation at Z=225 degrees, and links it into the scene.
        """
        scene_settings = new_scene.shimakaze_sdk
        target = bpy.data.objects.get(scene_settings.target)
        if target is None or target.type != "EMPTY":
            target = bpy.data.objects.new(utils.make_unique_target_name(), None)
            scene_settings.target = target.name

        target.rotation_euler = (0.0, 0.0, radians(225))
        if target.name not in new_scene.objects:
            new_scene.collection.objects.link(target)
        return target


class Shimakaze_OT_shp_pass(ShimakazeSDKBaseOperator):
    """Apply one SHP render pass to CnC scenes in the current file.

    These passes mirror the bundled tmp scripts and operate on any scene in
    the open blend whose name matches a template scene name.
    """

    pass_name: str = ""

    def execute(self, context) -> set[OperatorReturnItems]:
        touched, object_count = utils.apply_shp_pass(self.pass_name)
        if not touched:
            self.report(
                {"ERROR"},
                "当前文件未找到 CnC 模板场景（如 Red Alert 2 / Tiberian Sun），"
                "请先打开包含这些场景的 blend 文件",
            )
            return {"CANCELLED"}
        self.report(
            {"INFO"},
            f"已应用 {self.bl_label} 到 {len(touched)} 个模板场景（{object_count} 个物体）",
        )
        return {"FINISHED"}


class Shimakaze_OT_shp_buildup(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_buildup"
    bl_label = "Buildup"
    bl_description = "建造动画通道：蓝面可见，透明材质，用于渲染建造动画"
    pass_name = "buildup"


class Shimakaze_OT_shp_object(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_object"
    bl_label = "Object"
    bl_description = "物体通道：隐藏全部平面（模板）"
    pass_name = "object"


class Shimakaze_OT_shp_reset(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_reset"
    bl_label = "Reset"
    bl_description = "重置通道：灰面可见（模板）"
    pass_name = "reset"


class Shimakaze_OT_shp_shadow(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_shadow"
    bl_label = "Shadow"
    bl_description = "阴影通道：pass_index=1，关闭 AO（模板）"
    pass_name = "shadow"


_CLASSES = (
    Shimakaze_OT_import_cnc_scene,
    Shimakaze_OT_shp_buildup,
    Shimakaze_OT_shp_object,
    Shimakaze_OT_shp_reset,
    Shimakaze_OT_shp_shadow,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
