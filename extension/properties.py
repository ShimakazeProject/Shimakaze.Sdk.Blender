"""Data model for the Shimakaze SDK, stored on the current scene."""

import bpy
from bpy.props import BoolProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

__all__ = ("register", "unregister")


class ShimakazeSceneSettings(PropertyGroup):
    asset_name: StringProperty(
        name="Asset Name",
        description="Name of the asset this SDK export targets",
        maxlen=128,
        default="My Asset",
    )

    asset_version: StringProperty(
        name="Asset Version",
        description="Semantic version of the asset",
        maxlen=32,
        default="0.1.0",
    )

    dry_run: BoolProperty(
        name="Dry Run",
        description="Validate without applying changes",
        default=True,
    )


def register() -> None:
    bpy.utils.register_class(ShimakazeSceneSettings)
    bpy.types.Scene.shimakaze_sdk = PointerProperty(type=ShimakazeSceneSettings)


def unregister() -> None:
    del bpy.types.Scene.shimakaze_sdk
    bpy.utils.unregister_class(ShimakazeSceneSettings)
