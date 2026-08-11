"""Keymap registration for the Shimakaze SDK.

Keymap items are registered without a default key binding
(``type="NONE"``) so the add-on never steals a hotkey. Users can assign
one in Preferences > Keymap.
"""

import bpy
from bpy.types import KeyMap, KeyMapItem

__all__ = ("register", "unregister")

_ADDON_KEYMAPS: list[tuple[KeyMap, KeyMapItem]] = []


def register() -> None:
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig is None:
        return

    keymap = keyconfig.keymaps.new(name="3D View", space_type="VIEW_3D")
    item = keymap.keymap_items.new(
        "shimakaze.hello",
        type="NONE",
        value="PRESS",
    )
    _ADDON_KEYMAPS.append((keymap, item))


def unregister() -> None:
    for keymap, item in _ADDON_KEYMAPS:
        keymap.keymap_items.remove(item)
    _ADDON_KEYMAPS.clear()
