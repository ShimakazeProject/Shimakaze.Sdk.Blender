"""Helpers for the CnC (SHP) template import and render passes.

Everything in this module must be importable and testable without Blender,
so keep Blender imports inside the functions that need them.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from bpy.types import Collection, CompositorNodeTree, Object

#: CnC games selectable in the wizard, keyed by enum identifier.
CNC_GAME_OPTIONS: dict[str, str] = {
    "RM": "C&C Remastered",
    "D2K": "Dune 2000",
    "RA": "Red Alert",
    "TD": "Tiberian Dawn",
    "RA2": "Red Alert 2",
    "RW": "ReWire",
    "TS": "Tiberian Sun",
}

#: Template game (scene name + plane code) each dropdown entry resolves to.
#: RA and TD share the combined "Red Alert / Tiberian Dawn" template scenes.
CNC_TEMPLATE_GAME: dict[str, tuple[str, str]] = {
    "RM": ("C&C Remastered", "RM"),
    "D2K": ("Dune 2000", "D2K"),
    "RA": ("Red Alert / Tiberian Dawn", "RA1"),
    "TD": ("Red Alert / Tiberian Dawn", "RA1"),
    "RA2": ("Red Alert 2", "RA2"),
    "RW": ("ReWire", "RW"),
    "TS": ("Tiberian Sun", "TS"),
}

#: Scene variants, keyed by enum identifier -> (scene suffix, object suffix, label).
CNC_VARIANT_OPTIONS: dict[str, tuple[str, str, str]] = {
    "BASE": ("", "", "Default"),
    "FX": (" - Effects", ".FX", "Effects"),
    "INF": (" - Infantry", ".INF", "Infantry"),
}

#: Plane types present in every template scene.
CNC_PLANE_TYPES = ("ambient", "blue", "grey", "holdout2", "shadow2", "shadow", "holdout")

#: File name of the bundled template that stores the CnC scenes.
CNC_TEMPLATE_FILE = "CnC_EeveeNext_1.1.0_build91_20260811.blend"

#: All pass switch nodes in a template compositor (Cycles + Eevee variants).
_PASS_SWITCH_NAMES = (
    "Object",
    "Buildup.Cycles",
    "Buildup.Eevee",
    "Shadow.Cycles",
    "Shadow.Eevee",
    "Preview.Cycles",
    "Preview.Eevee",
)


def get_cnc_template_path() -> Path:
    """Return the absolute path of the bundled CnC template blend file."""
    return Path(__file__).resolve().parent / CNC_TEMPLATE_FILE


def game_enum_items(self=None, context=None) -> list[tuple[str, str, str]]:
    """Build the EnumProperty items for the game selector."""
    return [
        (identifier, label, f"Append the '{label}' template scene")
        for identifier, label in CNC_GAME_OPTIONS.items()
    ]


def variant_enum_items(self=None, context=None) -> list[tuple[str, str, str]]:
    """Build the EnumProperty items for the scene-variant selector."""
    return [
        (key, label, f"Append the '{label}' variant")
        for key, (_, _, label) in CNC_VARIANT_OPTIONS.items()
    ]


def resolve_cnc_scene(game: str, variant: str) -> tuple[str, str]:
    """Map a game + variant to the (template scene, final scene name).

    RA and TD share the combined ``Red Alert / Tiberian Dawn`` template
    scenes; the imported scene is renamed to the chosen game name.
    """
    template_name, _code = CNC_TEMPLATE_GAME[game]
    scene_suffix = CNC_VARIANT_OPTIONS[variant][0]
    return f"{template_name}{scene_suffix}", f"{CNC_GAME_OPTIONS[game]}{scene_suffix}"


def template_games() -> list[tuple[str, str]]:
    """Unique (template scene name, plane code) pairs, in dropdown order.

    RA and TD both resolve to the same template game, so it is only listed
    once here.
    """
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for template_name, code in CNC_TEMPLATE_GAME.values():
        pair = (template_name, code)
        if pair not in seen:
            seen.add(pair)
            result.append(pair)
    return result


def is_valid_direction_count(value: int) -> bool:
    """Return True if a direction count is 1 or a multiple of 8."""
    return value == 1 or value % 8 == 0


def get_scene_container_collection(scene) -> Collection:
    """Return the collection named after the scene.

    The template ships an empty collection per scene (e.g. ``Red Alert 2 -
    Infantry``) meant to hold the user's model and the target empty, separate
    from the ``* Template`` collection. When the scene was renamed (e.g. a
    combined template split into ``Red Alert`` / ``Tiberian Dawn``) and no
    matching collection exists yet, one is created under the scene's root
    collection.
    """
    import bpy

    collection = bpy.data.collections.get(scene.name)
    if collection is not None:
        return collection
    collection = bpy.data.collections.new(scene.name)
    scene.collection.children.link(collection)
    return collection


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


class ShpPassConfig(TypedDict):
    switches: tuple[str, ...]
    planes: dict[str, bool]


#: Render-pass setups matching the template's compositor switch chain.
SHP_PASSES: dict[str, ShpPassConfig] = {
    "object": {
        "switches": ("Object",),
        "planes": {
            "ambient": True,
            "blue": True,
            "grey": True,
            "holdout2": True,
            "shadow2": True,
            "shadow": True,
            "holdout": True,
        },
    },
    "buildup": {
        "switches": ("Buildup.Cycles", "Buildup.Eevee"),
        "planes": {
            "ambient": True,
            "blue": False,
            "grey": True,
            "holdout2": True,
            "shadow2": True,
            "shadow": True,
            "holdout": True,
        },
    },
    "shadow": {
        "switches": ("Shadow.Cycles", "Shadow.Eevee"),
        "planes": {
            "ambient": True,
            "blue": True,
            "grey": True,
            "holdout2": True,
            "shadow2": False,
            "shadow": False,
            "holdout": True,
        },
    },
    "preview": {
        "switches": ("Preview.Cycles", "Preview.Eevee"),
        "planes": {
            "ambient": True,
            "blue": True,
            "grey": False,
            "holdout2": True,
            "shadow2": True,
            "shadow": True,
            "holdout": True,
        },
    },
    "reset": {
        "switches": (),
        "planes": {
            "ambient": True,
            "blue": True,
            "grey": False,
            "holdout2": True,
            "shadow2": True,
            "shadow": True,
            "holdout": True,
        },
    },
}


def apply_shp_pass(pass_name: str) -> list[str]:
    """Apply a render-pass setup to every CnC scene in the open blend.

    Toggles the pass switch chain and the per-scene plane visibility for all
    template scenes that exist in the current file. Returns the scene names
    that were touched.
    """
    import bpy

    config = SHP_PASSES[pass_name]
    touched: list[str] = []

    for template_name, code in template_games():
        for _variant, (scene_suffix, object_suffix, _label) in CNC_VARIANT_OPTIONS.items():
            scene = bpy.data.scenes.get(f"{template_name}{scene_suffix}")
            if scene is None:
                continue

            node_tree: CompositorNodeTree | None = scene.node_tree
            if node_tree is not None:
                repair_alpha_over(node_tree)
                for node in node_tree.nodes.values():
                    if node is not None and node.name in _PASS_SWITCH_NAMES:
                        node.check = node.name in config["switches"]

            for plane_type, hide in config["planes"].items():
                plane = bpy.data.objects.get(f"Plane.{plane_type}.{code}{object_suffix}")
                if plane is not None:
                    plane.hide_render = hide

            touched.append(scene.name)

    return touched


def repair_alpha_over(node_tree) -> bool:
    """Fix the compositor's Alpha Over foreground/background wiring.

    The template ships with the Alpha Over sockets swapped: the left node has
    an empty Image 1, and the right node has Image 1/Image 2 reversed, so the
    sprite never composites over the correct background. This rewires them at
    runtime without modifying the template file. Returns True if anything was
    changed.
    """
    alpha_switch = node_tree.nodes.get("Alpha")
    alpha_over = node_tree.nodes.get("Alpha Over")
    alpha_over_1 = node_tree.nodes.get("Alpha Over.001")
    if alpha_switch is None or alpha_over is None or alpha_over_1 is None:
        return False

    group = node_tree.nodes.get("Group")
    color_ramp = node_tree.nodes.get("Color Ramp")
    changed = False

    def set_input(node, index: int, from_socket) -> None:
        nonlocal changed
        socket = node.inputs[index]
        current = next(iter(socket.links), None)
        if current is not None and current.from_socket is from_socket:
            return
        for link in list(socket.links):
            node_tree.links.remove(link)
        node_tree.links.new(from_socket, socket)
        changed = True

    # Left Alpha Over: Image 1 <- Alpha output, Image 2 <- Alpha Convert (Group).
    set_input(alpha_over, 1, alpha_switch.outputs["Image"])
    if group is not None:
        set_input(alpha_over, 2, group.outputs["Image"])
    else:
        for link in list(alpha_over.inputs[2].links):
            node_tree.links.remove(link)
        changed = True

    # Right Alpha Over.001: Image 1 <- Alpha output, Image 2 <- Color Ramp.
    set_input(alpha_over_1, 1, alpha_switch.outputs["Image"])
    if color_ramp is not None:
        set_input(alpha_over_1, 2, color_ramp.outputs["Color"])
    else:
        for link in list(alpha_over_1.inputs[2].links):
            node_tree.links.remove(link)
        changed = True

    return changed
