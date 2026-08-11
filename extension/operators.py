"""Operators exposed by the Shimakaze SDK."""

import bpy
from bpy.types import Operator

from . import utils

__all__ = ("register", "unregister")


class ShimakazeSDKBaseOperator(Operator):
    """Common behavior for every Shimakaze SDK operator."""

    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None


class Shimakaze_OT_hello(ShimakazeSDKBaseOperator):
    bl_idname = "shimakaze.hello"
    bl_label = "Hello Shimakaze"
    bl_description = "Compose a greeting from the current SDK settings"

    def execute(self, context):
        settings = context.scene.shimakaze_sdk
        prefs = utils.get_preferences()

        utils.configure_logging(debug=prefs.debug_logging)
        asset_name = utils.normalize_identifier(settings.asset_name)
        message = utils.compose_greeting(asset_name, settings.asset_version)

        self.report({"INFO"}, message)
        utils.logger.info(message)
        return {"FINISHED"}


class Shimakaze_OT_bump_asset_version(ShimakazeSDKBaseOperator):
    bl_idname = "shimakaze.bump_asset_version"
    bl_label = "Bump Asset Version"
    bl_description = "Increment the patch version of the current asset"

    def execute(self, context):
        settings = context.scene.shimakaze_sdk
        settings.asset_version = utils.bump_version(settings.asset_version)

        self.report({"INFO"}, f"Asset version bumped to {settings.asset_version}")
        return {"FINISHED"}


_CLASSES = (
    Shimakaze_OT_hello,
    Shimakaze_OT_bump_asset_version,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
