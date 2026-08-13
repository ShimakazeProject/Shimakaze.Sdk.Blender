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
    """Apply one SHP render pass to the active scene."""

    pass_name: str = ""

    def execute(self, context) -> set[OperatorReturnItems]:
        if not utils.apply_shp_pass_to_scene(context.scene, self.pass_name):
            self.report({"ERROR"}, "当前场景不是有效的模板场景")
            return {"CANCELLED"}
        context.scene.shimakaze_sdk.active_pass = self.pass_name
        self.report({"INFO"}, f"已应用 {self.bl_label} 到当前场景")
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


class Shimakaze_OT_render_batch(ShimakazeSDKBaseOperator):
    bl_idname = "shimakaze.render_batch"
    bl_label = "批量渲染"
    bl_description = "按方向数批量渲染 SHP 动画帧：每方向渲染动画并旋转目标"
    bl_options = {"REGISTER"}

    _target = None
    _faces = 0
    _frame_start = 0
    _frame_end = 0
    _step = 0.0
    _pass_name = ""
    _template = ""
    _face = 0
    _frame = 0
    _timer = None
    _progress_started = False

    def execute(self, context) -> set[OperatorReturnItems]:
        scene = context.scene
        settings = scene.shimakaze_sdk
        if not settings.is_imported:
            self.report({"ERROR"}, "请先导入模板场景再批量渲染")
            return {"CANCELLED"}

        target = settings.target
        if target is None:
            self.report({"ERROR"}, "未找到目标空对象")
            return {"CANCELLED"}

        faces = settings.faces
        if not utils.is_valid_direction_count(faces):
            self.report({"ERROR"}, "方向数必须是 1 或 8 的倍数")
            return {"CANCELLED"}

        pass_name = settings.active_pass
        if pass_name not in utils.SHP_PASSES:
            self.report({"ERROR"}, f"无效的渲染通道：{pass_name}")
            return {"CANCELLED"}
        if not utils.apply_shp_pass_to_scene(scene, pass_name):
            self.report({"ERROR"}, "当前场景不是有效的模板场景")
            return {"CANCELLED"}

        step = radians(360 / faces)
        self._target = target
        self._faces = faces
        self._frame_start = scene.frame_start
        self._frame_end = scene.frame_end
        self._pass_name = pass_name
        self._template = settings.output_template or "//<template>/<face>/"
        self._step = -step if settings.reverse else step
        self._face = 0
        self._frame = scene.frame_start
        self._timer = None

        scene.render.use_file_extension = True

        window = context.window
        if window is None:
            self._finish(context)
            return {"FINISHED"}
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, window=window)
        wm.modal_handler_add(self)
        frames_per_face = max(1, self._frame_end - self._frame_start + 1)
        wm.progress_begin(0, self._faces * frames_per_face)
        self._progress_started = True
        return {"RUNNING_MODAL"}

    def modal(self, context, event) -> set[OperatorReturnItems]:
        if event.type == "ESC":
            self._finish(context, cancelled=True)
            return {"CANCELLED"}
        if event.type != "TIMER":
            return {"RUNNING_MODAL"}

        if self._frame > self._frame_end:
            self._target.rotation_euler[2] += self._step
            self._face += 1
            self._frame = self._frame_start
            if self._face >= self._faces:
                self._finish(context)
                return {"FINISHED"}

        scene = context.scene
        scene.frame_set(self._frame)
        scene.render.filepath = self._frame_path()
        bpy.ops.render.render(write_still=True)

        frames_per_face = max(1, self._frame_end - self._frame_start + 1)
        done = self._face * frames_per_face + (self._frame - self._frame_start) + 1
        context.window_manager.progress_update(min(done, self._faces * frames_per_face))
        self._frame += 1
        return {"RUNNING_MODAL"}

    def _frame_path(self) -> str:
        """Build the per-frame output path from the output template."""
        path = self._template.replace("<template>", self._pass_name)
        path = path.replace("<face>", str(self._face))
        if "<frame>" in path:
            path = path.replace("<frame>", f"{self._frame:04d}")
        else:
            path += f"{self._frame:04d}"
        return path

    def _finish(self, context, cancelled: bool = False) -> None:
        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
            self._timer = None
        if self._progress_started:
            wm.progress_end()
            self._progress_started = False
        if self._target is not None:
            self._target.rotation_euler[2] = radians(225)
        if cancelled:
            self.report({"WARNING"}, "批量渲染已取消")
        else:
            self.report({"INFO"}, f"批量渲染完成：{self._pass_name} × {self._faces} 方向")


_CLASSES = (
    Shimakaze_OT_import_cnc_scene,
    Shimakaze_OT_shp_object,
    Shimakaze_OT_shp_buildup,
    Shimakaze_OT_shp_shadow,
    Shimakaze_OT_shp_preview,
    Shimakaze_OT_shp_reset,
    Shimakaze_OT_render_batch,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
