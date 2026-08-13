"""Data model for the SHP workflow, stored on the scene and window manager."""

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from . import utils

__all__ = ("register", "unregister")


def _update_use_alpha(self, context) -> None:
    """Sync the compositor's Alpha switch with the checkbox."""
    scene = context.scene
    if scene is None:
        return
    node_tree = scene.node_tree
    if node_tree is None:
        return
    alpha = node_tree.nodes.get("Alpha")
    if alpha is not None:
        alpha.check = self.use_alpha


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

    target: PointerProperty(
        name="目标",
        description="本场景的目标空对象名称",
        type=bpy.types.Object,
    )

    is_imported: BoolProperty(
        name="模板导入",
        description="是否从 CnC 模板导入的场景（显示渲染通道）",
        default=False,
    )

    active_pass: StringProperty(
        name="当前通道",
        description="最近应用的渲染通道（批量渲染使用）",
        default="object",
        maxlen=32,
    )

    use_alpha: BoolProperty(
        name="Alpha",
        description="勾选后启用合成器中的 Alpha 开关",
        default=False,
        update=_update_use_alpha,
    )

    output_template: StringProperty(
        name="输出模板",
        description="批量渲染输出路径模板，支持 <template>/<face>，帧号由 Blender 追加",
        default="//<template>/<face>/",
        maxlen=512,
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
