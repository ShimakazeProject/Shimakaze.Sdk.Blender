"""Pure, testable helpers for the CnC template scene import.

Everything in this module must be importable and testable without Blender,
so keep Blender imports inside the functions that need them.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bpy.types import Object

#: CnC games selectable in the wizard, keyed by enum identifier.
CNC_GAME_OPTIONS: dict[str, str] = {
    "RA": "Red Alert",
    "TD": "Tiberian Dawn",
    "RA2": "Red Alert 2",
    "TS": "Tiberian Sun",
}

#: Games that have a dedicated infantry template scene.
_INFANTRY_GAMES = ("RA2", "TS")

#: Template scene shared by the RA and TD options (the combined scene).
_COMBINED_TEMPLATE_SCENE = "Red Alert / Tiberian Dawn"

#: File name of the bundled template that stores the CnC scenes.
CNC_TEMPLATE_FILE = "CnC_template2_11.blend"


def get_cnc_template_path() -> Path:
    """Return the absolute path of the bundled CnC template blend file."""
    return Path(__file__).resolve().parent / CNC_TEMPLATE_FILE


def cnc_game_enum_items(self=None, context=None) -> list[tuple[str, str, str]]:
    """Build the EnumProperty items for the game selector."""
    return [
        (identifier, label, f"Append the '{label}' template scene")
        for identifier, label in CNC_GAME_OPTIONS.items()
    ]


def is_infantry_game(game: str) -> bool:
    """Return True if the game has a dedicated infantry template scene."""
    return game in _INFANTRY_GAMES


def resolve_cnc_scene(game: str, infantry: bool) -> tuple[str, str]:
    """Map a game + infantry flag to the (template scene, final scene name).

    RA and TD share the combined 'Red Alert / Tiberian Dawn' template scene,
    so the imported scene is renamed to the chosen game. RA2/TS use their own
    scene, with an optional ' - Infantry' suffix.
    """
    game_name = CNC_GAME_OPTIONS[game]
    if is_infantry_game(game):
        scene_name = f"{game_name}{' - Infantry' if infantry else ''}"
        return scene_name, scene_name
    return _COMBINED_TEMPLATE_SCENE, game_name


def is_valid_direction_count(value: int) -> bool:
    """Return True if a direction count is 1 or a multiple of 8."""
    return value == 1 or value % 8 == 0


def make_unique_target_name() -> str:
    """Return a globally unique name for a fresh target empty."""
    from uuid import uuid4

    import bpy

    while True:
        candidate = f"target_{uuid4().hex[:8]}"
        if candidate not in bpy.data.objects:
            return candidate


def collect_objects_to_link(objects: Iterable[Object]) -> set[Object]:
    """Collect an object and everything it depends on for a scene link.

    Recursively includes the full child hierarchy, plus any objects referenced
    by constraints or animation drivers, so linked animation keeps working.
    """
    import bpy

    result: set[Object] = set()
    pending = list(objects)
    while pending:
        obj = pending.pop()
        if obj is None or obj in result:
            continue
        result.add(obj)
        pending.extend(obj.children)

        for constraint in obj.constraints:
            target = getattr(constraint, "target", None)
            if target is not None:
                pending.append(target)

        animation_data = obj.animation_data
        if animation_data is not None:
            for fcurve in animation_data.drivers:
                driver = fcurve.driver
                if driver is None:
                    continue
                for variable in driver.variables:
                    for target in variable.targets:
                        referenced = getattr(target, "id", None)
                        if isinstance(referenced, bpy.types.Object):
                            pending.append(referenced)
    return result
