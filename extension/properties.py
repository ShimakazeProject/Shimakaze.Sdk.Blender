"""Data model for the SHP workflow, stored on the scene and window manager."""

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from . import utils

__all__ = ("register", "unregister")


class ShimakazeSceneSettings(PropertyGroup):
    """Per-scene SHP settings, including the scene's own target."""

    faces: IntProperty(
        name="面数（方向数）",
        description="SHP 方向数，必须是 1 或 8 的倍数",
        default=8,
        min=1,
        step=8,
    )

    reverse: BoolProperty(
        name="反向",
        description="反向，用于制作 SHP 载具",
        default=False,
    )

    target: StringProperty(
        name="目标",
        description="本场景的目标空对象名称",
        default="",
    )


class ShimakazeWindowSettings(PropertyGroup):
    """Global (window-level) settings that must survive scene switches."""

    cnc_game: EnumProperty(
        name="游戏",
        description="选择要导入的 CnC 游戏模板",
        items=utils.game_enum_items,
    )

    cnc_variant: EnumProperty(
        name="变体",
        description="选择模板场景变体（标准 / Effects / 步兵）",
        items=utils.variant_enum_items,
    )


def register() -> None:
    bpy.utils.register_class(ShimakazeSceneSettings)
    bpy.utils.register_class(ShimakazeWindowSettings)
    bpy.types.Scene.shimakaze_sdk = PointerProperty(type=ShimakazeSceneSettings)
    bpy.types.WindowManager.shimakaze_cnc = PointerProperty(type=ShimakazeWindowSettings)


def unregister() -> None:
    del bpy.types.Scene.shimakaze_sdk
    del bpy.types.WindowManager.shimakaze_cnc
    bpy.utils.unregister_class(ShimakazeSceneSettings)
    bpy.utils.unregister_class(ShimakazeWindowSettings)
