"""Data model for the SHP workflow, stored on the scene and window manager."""

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from . import utils

__all__ = ("register", "unregister")


def _update_use_alpha(self, context) -> None:
    """Sync the compositor's Alpha switch and output color mode."""
    scene = context.scene
    if scene is None:
        return
    node_tree = utils.get_scene_compositor(scene)
    if node_tree is not None:
        alpha = node_tree.nodes.get("Alpha")
        if alpha is not None:
            utils.set_switch(alpha, self.use_alpha)
    scene.render.image_settings.color_mode = "RGBA" if self.use_alpha else "RGB"


class MaterialExclusion(PropertyGroup):
    """A material name kept out of the holdout batch."""

    name: StringProperty(name="Material", description="Material name to exclude")


class ShimakazeSceneSettings(PropertyGroup):
    """Per-scene SHP settings, including the scene's own target."""

    faces: IntProperty(
        name="Faces (directions)",
        description="SHP direction count; must be 1 or a multiple of 8",
        default=8,
        min=1,
        step=8,
    )

    reverse: BoolProperty(
        name="Reverse",
        description="Render in reverse direction (for SHP vehicles)",
        default=False,
    )

    target: PointerProperty(
        name="Target",
        description="Target empty object of this scene",
        type=bpy.types.Object,
    )

    is_imported: BoolProperty(
        name="Imported from template",
        description="Whether the scene was imported from a CnC template (shows render passes)",
        default=False,
    )

    active_pass: StringProperty(
        name="Active Pass",
        description="Last applied render pass (used by batch render)",
        default="object",
        maxlen=32,
    )

    use_alpha: BoolProperty(
        name="Alpha",
        description="Enable the compositor's Alpha switch",
        default=False,
        update=_update_use_alpha,
    )

    output_template: StringProperty(
        name="Output Template",
        description=(
            "Batch render output path template; supports <template>/<face>, frame added by Blender"
        ),
        default="//<template>/<face>/",
        maxlen=512,
    )

    excluded_materials: CollectionProperty(type=MaterialExclusion)

    active_excluded_index: IntProperty(
        name="Active Excluded Material",
        description="Index of the selected material in the exclusion list",
        default=0,
        min=0,
    )


class ShimakazeWindowSettings(PropertyGroup):
    """Global (window-level) settings that must survive scene switches."""

    cnc_game: EnumProperty(
        name="Game",
        description="CnC game template to import",
        items=utils.game_enum_items,
    )

    cnc_variant: EnumProperty(
        name="Variant",
        description="Template scene variant (Standard / Effects / Infantry)",
        items=utils.variant_enum_items,
    )


def register() -> None:
    bpy.utils.register_class(MaterialExclusion)
    bpy.utils.register_class(ShimakazeSceneSettings)
    bpy.utils.register_class(ShimakazeWindowSettings)
    bpy.types.Scene.shimakaze_sdk = PointerProperty(type=ShimakazeSceneSettings)
    bpy.types.WindowManager.shimakaze_cnc = PointerProperty(type=ShimakazeWindowSettings)


def unregister() -> None:
    del bpy.types.Scene.shimakaze_sdk
    del bpy.types.WindowManager.shimakaze_cnc
    bpy.utils.unregister_class(ShimakazeSceneSettings)
    bpy.utils.unregister_class(ShimakazeWindowSettings)
    bpy.utils.unregister_class(MaterialExclusion)
