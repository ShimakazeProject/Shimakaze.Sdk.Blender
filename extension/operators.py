"""Operators for importing CnC template scenes and applying render passes."""

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
    bl_label = "Import Scene"
    bl_description = "Append the selected game + variant scene from the CnC template"

    def execute(self, context) -> set[OperatorReturnItems]:
        settings = context.window_manager.shimakaze_cnc
        game = settings.cnc_game
        variant = settings.cnc_variant
        if game not in utils.CNC_GAME_OPTIONS or variant not in utils.CNC_VARIANT_OPTIONS:
            self.report({"ERROR"}, "Unknown CnC game or variant selected")
            return {"CANCELLED"}

        template_scene, final_scene = utils.resolve_cnc_scene(game, variant)

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
        new_scene.shimakaze_sdk.is_imported = True
        context.window.scene = new_scene

        if new_scene.node_tree is not None:
            utils.repair_alpha_over(new_scene.node_tree)

        container = utils.get_scene_container_collection(new_scene)
        objects_to_link = utils.collect_objects_to_link(selected_objects)
        for obj in objects_to_link:
            if obj.name not in container.objects:
                container.objects.link(obj)

        target = self._ensure_target(new_scene, container)
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
    def _ensure_target(new_scene, container) -> bpy.types.Object:
        """Return this scene's target, reusing the one stored on the scene.

        Creates a uniquely named empty when none is recorded yet, keeps its
        Euler rotation at Z=225 degrees, and links it into the scene's
        container collection.
        """
        scene_settings = new_scene.shimakaze_sdk
        target = scene_settings.target
        if target is None or target.type != "EMPTY":
            target = bpy.data.objects.new(f"{new_scene.name} Target", None)
            scene_settings.target = target

        target.rotation_euler = (0.0, 0.0, radians(225))
        if target.name not in container.objects:
            container.objects.link(target)
        return target


class Shimakaze_OT_shp_pass(ShimakazeSDKBaseOperator):
    """Apply one SHP render pass to every CnC scene in the current file."""

    pass_name: str = ""

    def execute(self, context) -> set[OperatorReturnItems]:
        touched = utils.apply_shp_pass(self.pass_name)
        if not touched:
            self.report(
                {"ERROR"},
                "当前文件未找到 CnC 模板场景（如 Red Alert 2 / Tiberian Sun），"
                "请先打开包含这些场景的 blend 文件",
            )
            return {"CANCELLED"}
        self.report(
            {"INFO"},
            f"已应用 {self.bl_label} 到 {len(touched)} 个模板场景",
        )
        return {"FINISHED"}


class Shimakaze_OT_shp_object(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_object"
    bl_label = "Object"
    bl_description = "物体通道：渲染物体本体，隐藏全部平面"
    pass_name = "object"


class Shimakaze_OT_shp_buildup(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_buildup"
    bl_label = "Buildup"
    bl_description = "建造动画通道：蓝面可见，用于渲染建造动画"
    pass_name = "buildup"


class Shimakaze_OT_shp_shadow(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_shadow"
    bl_label = "Shadow"
    bl_description = "阴影通道：阴影面可见，用于渲染阴影"
    pass_name = "shadow"


class Shimakaze_OT_shp_preview(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_preview"
    bl_label = "Preview"
    bl_description = "预览通道：灰面可见"
    pass_name = "preview"


class Shimakaze_OT_shp_reset(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_reset"
    bl_label = "Reset"
    bl_description = "重置为默认状态：灰面可见，所有通道开关关闭"
    pass_name = "reset"


_CLASSES = (
    Shimakaze_OT_import_cnc_scene,
    Shimakaze_OT_shp_object,
    Shimakaze_OT_shp_buildup,
    Shimakaze_OT_shp_shadow,
    Shimakaze_OT_shp_preview,
    Shimakaze_OT_shp_reset,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
