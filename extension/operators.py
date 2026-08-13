"""Operators for importing CnC template scenes and applying render passes."""

from __future__ import annotations

import threading
from math import radians
from typing import TYPE_CHECKING

import bpy
from bpy.types import Operator

from . import i18n, utils

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
        t = i18n.t
        settings = context.window_manager.shimakaze_cnc
        game = settings.cnc_game
        variant = settings.cnc_variant
        if game not in utils.CNC_GAME_OPTIONS or variant not in utils.CNC_VARIANT_OPTIONS:
            self.report({"ERROR"}, "Unknown CnC game or variant selected")
            return {"CANCELLED"}

        template_scene, final_scene = utils.resolve_cnc_scene(game, variant)

        try:
            template_path = utils.ensure_template()
        except Exception as exc:
            self.report({"ERROR"}, t("Could not get template file: {exc}").format(exc=exc))
            return {"CANCELLED"}
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

        compositor = utils.get_scene_compositor(new_scene)
        if compositor is not None:
            utils.repair_compositor(compositor)

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
            self.report({"ERROR"}, i18n.t("Current scene is not a valid template scene"))
            return {"CANCELLED"}
        context.scene.shimakaze_sdk.active_pass = self.pass_name
        self.report(
            {"INFO"},
            i18n.t("Applied {label} to the current scene").format(label=self.bl_label),
        )
        return {"FINISHED"}


class Shimakaze_OT_shp_object(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_object"
    bl_label = "Object"
    bl_description = "Object pass: render the model, hide all planes"
    pass_name = "object"


class Shimakaze_OT_shp_buildup(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_buildup"
    bl_label = "Buildup"
    bl_description = "Buildup pass: blue plane visible for the construction animation"
    pass_name = "buildup"


class Shimakaze_OT_shp_shadow(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_shadow"
    bl_label = "Shadow"
    bl_description = "Shadow pass: shadow planes visible"
    pass_name = "shadow"


class Shimakaze_OT_shp_preview(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_preview"
    bl_label = "Preview"
    bl_description = "Preview pass: grey plane visible"
    pass_name = "preview"


class Shimakaze_OT_shp_reset(Shimakaze_OT_shp_pass):
    bl_idname = "shimakaze.shp_reset"
    bl_label = "Reset"
    bl_description = "Reset to default: grey plane visible, all pass switches off"
    pass_name = "reset"


class Shimakaze_OT_render_batch(ShimakazeSDKBaseOperator):
    bl_idname = "shimakaze.render_batch"
    bl_label = "Batch Render"
    bl_description = "Render SHP animation frames per direction, rotating the target after each"
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
        t = i18n.t
        scene = context.scene
        settings = scene.shimakaze_sdk
        if not settings.is_imported:
            self.report({"ERROR"}, t("Import a template scene before batch rendering"))
            return {"CANCELLED"}

        target = settings.target
        if target is None:
            self.report({"ERROR"}, t("Target empty not found"))
            return {"CANCELLED"}

        faces = settings.faces
        if not utils.is_valid_direction_count(faces):
            self.report({"ERROR"}, t("Direction count must be 1 or a multiple of 8"))
            return {"CANCELLED"}

        pass_name = settings.active_pass
        if pass_name not in utils.SHP_PASSES:
            self.report({"ERROR"}, t("Invalid render pass: {name}").format(name=pass_name))
            return {"CANCELLED"}
        if not utils.apply_shp_pass_to_scene(scene, pass_name):
            self.report({"ERROR"}, t("Current scene is not a valid template scene"))
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
        total = self._faces * frames_per_face
        context.window_manager.progress_update(min(done, total))
        self._set_status_text(context, done, total)
        self._frame += 1
        return {"RUNNING_MODAL"}

    def _set_status_text(self, context, done: int, total: int) -> None:
        """Show the batch progress in the status bar."""
        workspace = context.workspace
        if workspace is None:
            return
        pct = round(done / total * 100) if total else 100
        workspace.status_text_set(
            i18n.t("Batch render {name}: face {face}/{faces}, frame {frame}/{end} ({pct}%)").format(
                name=self._pass_name,
                face=self._face + 1,
                faces=self._faces,
                frame=self._frame,
                end=self._frame_end,
                pct=pct,
            )
        )

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
        workspace = context.workspace
        if workspace is not None:
            workspace.status_text_set(None)
        if self._target is not None:
            self._target.rotation_euler[2] = radians(225)
        if cancelled:
            self.report({"WARNING"}, i18n.t("Batch render cancelled"))
        else:
            self.report(
                {"INFO"},
                i18n.t("Batch render done: {name} × {faces} directions").format(
                    name=self._pass_name, faces=self._faces
                ),
            )


class Shimakaze_OT_download_template(ShimakazeSDKBaseOperator):
    bl_idname = "shimakaze.download_template"
    bl_label = "Download Template"
    bl_description = "Download the missing CnC template file asynchronously (pinned version)"
    bl_options = {"REGISTER"}

    _state = None
    _timer = None

    def execute(self, context) -> set[OperatorReturnItems]:
        t = i18n.t
        path = utils.get_cnc_template_path()
        if path.is_file():
            self.report({"INFO"}, t("Template ready: {name}").format(name=path.name))
            return {"FINISHED"}
        if self._state is not None:
            self.report({"INFO"}, t("Template is already downloading"))
            return {"CANCELLED"}

        window = context.window
        if window is None:
            try:
                utils.ensure_template()
            except Exception as exc:
                self.report({"ERROR"}, t("Template download failed: {exc}").format(exc=exc))
                return {"CANCELLED"}
            self.report({"INFO"}, t("Template ready"))
            return {"FINISHED"}

        self._state = {
            "ok": None,
            "message": "",
            "current": 0,
            "total": 0,
            "phase": i18n.t("Connecting…"),
        }
        self._timer = None
        thread = threading.Thread(target=self._worker, args=(self._state,), daemon=True)
        thread.start()

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=window)
        wm.modal_handler_add(self)
        wm.progress_begin(0, 100)
        return {"RUNNING_MODAL"}

    @staticmethod
    def _worker(state) -> None:
        """Run the blocking download on a worker thread (no bpy access)."""

        def report_hook(blocks: int, block_size: int, total_size: int) -> None:
            state["current"] = blocks * block_size
            state["total"] = total_size or state["total"]

        try:
            utils._download_template(
                utils.get_cnc_template_path(),
                report_hook=report_hook,
                set_phase=lambda text: state.update(phase=text),
            )
            state["ok"] = True
            state["message"] = i18n.t("Download complete")
        except Exception as exc:
            state["ok"] = False
            state["message"] = str(exc)

    def modal(self, context, event) -> set[OperatorReturnItems]:
        t = i18n.t
        if event.type != "TIMER":
            return {"RUNNING_MODAL"}
        state = self._state
        if state is None:
            return {"CANCELLED"}

        if state["ok"] is None:
            total = state["total"]
            if total:
                pct = min(int(state["current"] * 100 / total), 100)
                context.window_manager.progress_update(pct)
            workspace = context.workspace
            if workspace is not None:
                pct = f" {min(int(state['current'] * 100 / total), 100)}%" if total else ""
                workspace.status_text_set(
                    t("Download template {phase}{pct}").format(phase=state["phase"], pct=pct)
                )
            return {"RUNNING_MODAL"}

        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
            self._timer = None
        wm.progress_end()
        workspace = context.workspace
        if workspace is not None:
            workspace.status_text_set(None)
        ok = state["ok"]
        self._state = None
        if ok:
            path = utils.get_cnc_template_path()
            self.report({"INFO"}, t("Template ready: {name}").format(name=path.name))
        else:
            message = state["message"]
            self.report({"ERROR"}, t("Template download failed: {exc}").format(exc=message))
        return {"FINISHED"}


class Shimakaze_OT_add_excluded_material(ShimakazeSDKBaseOperator):
    bl_idname = "shimakaze.add_excluded_material"
    bl_label = "Add Excluded Material"
    bl_description = "Add the active object's active material to the exclusion list"

    def execute(self, context) -> set[OperatorReturnItems]:
        material = getattr(context.object, "active_material", None)
        if material is None:
            self.report({"ERROR"}, i18n.t("No active material to add"))
            return {"CANCELLED"}
        settings = context.scene.shimakaze_sdk
        if any(item.name == material.name for item in settings.excluded_materials.values()):
            self.report({"INFO"}, i18n.t("Material already in the list"))
            return {"CANCELLED"}
        item = settings.excluded_materials.add()
        item.name = material.name
        settings.active_excluded_index = len(settings.excluded_materials) - 1
        self.report({"INFO"}, i18n.t("Added material: {name}").format(name=material.name))
        return {"FINISHED"}


class Shimakaze_OT_remove_excluded_material(ShimakazeSDKBaseOperator):
    bl_idname = "shimakaze.remove_excluded_material"
    bl_label = "Remove Excluded Material"
    bl_description = "Remove the selected material from the exclusion list"

    def execute(self, context) -> set[OperatorReturnItems]:
        settings = context.scene.shimakaze_sdk
        index = settings.active_excluded_index
        if index < 0 or index >= len(settings.excluded_materials):
            self.report({"ERROR"}, i18n.t("No material selected to remove"))
            return {"CANCELLED"}
        settings.excluded_materials.remove(index)
        settings.active_excluded_index = min(index, len(settings.excluded_materials) - 1)
        return {"FINISHED"}


class Shimakaze_OT_apply_holdout(ShimakazeSDKBaseOperator):
    bl_idname = "shimakaze.apply_holdout"
    bl_label = "Apply Holdout"
    bl_description = "Set a Holdout shader on every material not in the exclusion list"

    def execute(self, context) -> set[OperatorReturnItems]:
        settings = context.scene.shimakaze_sdk
        excluded = {item.name for item in settings.excluded_materials.values()}
        count = 0
        for material in bpy.data.materials.values():
            if material is None or material.name in excluded:
                continue
            utils.apply_holdout_shader(material)
            count += 1
        self.report(
            {"INFO"},
            i18n.t("Applied holdout to {count} materials").format(count=count),
        )
        return {"FINISHED"}


_CLASSES = (
    Shimakaze_OT_import_cnc_scene,
    Shimakaze_OT_download_template,
    Shimakaze_OT_shp_object,
    Shimakaze_OT_shp_buildup,
    Shimakaze_OT_shp_shadow,
    Shimakaze_OT_shp_preview,
    Shimakaze_OT_shp_reset,
    Shimakaze_OT_render_batch,
    Shimakaze_OT_add_excluded_material,
    Shimakaze_OT_remove_excluded_material,
    Shimakaze_OT_apply_holdout,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
