"""Pure, testable helpers for the CnC template scene import.

Everything in this module must be importable and testable without Blender,
so keep Blender imports inside the functions that need them.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

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


#: Template scenes and the data-block names they use, keyed by original
#: template scene name (as stored in CnC_template2_11.blend).
CNC_SCENES: dict[str, dict[str, str]] = {
    "Tiberian Sun": {
        "material": "Plane.blue.material.TS",
        "blue": "Plane.blue.TS",
        "grey": "Plane.grey.TS",
    },
    "Tiberian Sun - Infantry": {
        "material": "Plane.blue.material.TS.INF",
        "blue": "Plane.blue.TS.INF",
        "grey": "Plane.grey.TS.INF",
    },
    "Red Alert 2": {
        "material": "Plane.blue.material.RA2",
        "blue": "Plane.blue.RA2",
        "grey": "Plane.grey.RA2",
    },
    "Red Alert 2 - Infantry": {
        "material": "Plane.blue.material.RA2.INF",
        "blue": "Plane.blue.RA2.INF",
        "grey": "Plane.grey.RA2.INF",
    },
    "Red Alert / Tiberian Dawn": {
        "material": "Plane.blue.material.RA1",
        "blue": "Plane.blue.RA1",
        "grey": "Plane.grey.RA1",
        "grass": "Plane.grass.RA1",
    },
}


class ShpPassConfig(TypedDict):
    switch: bool
    pass_index: int
    transparent: bool
    gtao: bool
    plane_hide: dict[str, bool]


#: Render-pass setups matching the bundled tmp scripts. These only ever apply
#: to the *template* scenes (original names), never to imported scenes.
SHP_PASSES: dict[str, ShpPassConfig] = {
    "buildup": {
        "switch": True,
        "pass_index": 0,
        "transparent": True,
        "gtao": True,
        "plane_hide": {"blue": False, "grey": True, "grass": True},
    },
    "object": {
        "switch": True,
        "pass_index": 0,
        "transparent": False,
        "gtao": True,
        "plane_hide": {"blue": True, "grey": True, "grass": True},
    },
    "reset": {
        "switch": True,
        "pass_index": 0,
        "transparent": False,
        "gtao": True,
        "plane_hide": {"blue": True, "grey": False, "grass": True},
    },
    "shadow": {
        "switch": False,
        "pass_index": 1,
        "transparent": False,
        "gtao": False,
        "plane_hide": {"blue": False, "grey": True, "grass": True},
    },
}


def apply_shp_pass(pass_name: str) -> tuple[list[str], int]:
    """Apply a render-pass setup to scenes named as in the CnC template.

    Works on any open blend: every scene that matches a template scene name
    (e.g. ``Red Alert 2``, ``Tiberian Sun``) gets the pass settings applied.
    Returns the scenes that matched and how many objects were tagged.
    """
    import bpy

    config = SHP_PASSES[pass_name]
    touched: list[str] = []
    object_count = 0

    for scene_name, names in CNC_SCENES.items():
        scene = bpy.data.scenes.get(scene_name)
        if scene is None:
            continue

        node_tree = scene.node_tree
        switch = node_tree.nodes.get("Switch") if node_tree is not None else None
        if switch is not None:
            switch.check = config["switch"]

        for plane_key, hide in config["plane_hide"].items():
            plane_name = names.get(plane_key)
            if plane_name is None:
                continue
            plane = bpy.data.objects.get(plane_name)
            if plane is not None:
                plane.hide_render = hide

        material = bpy.data.materials.get(names["material"])
        if material is not None:
            material.blend_method = "BLEND" if config["transparent"] else "OPAQUE"

        scene.eevee.use_gtao = config["gtao"]

        for obj in bpy.data.objects:
            if obj.name not in scene.objects:
                continue
            obj.pass_index = config["pass_index"]
            object_count += 1

        if pass_name == "shadow":
            _repair_shadow_compositor(scene)

        touched.append(scene_name)

    return touched, object_count


def _repair_shadow_compositor(scene) -> None:
    """Make the compositor's shadow branch actually detect the shadow.

    The template's original extraction (Normal node + ID Mask + ColorRamp)
    no longer works in Blender 4.5: the Normal node normalizes the render,
    compressing the shadow signal so the ColorRamp threshold never triggers
    and the frame renders as a flat blue. This rewires the Switch's Off
    (shadow) input to a blue-channel threshold of the render image, so the
    shadow (dark blue) maps to black and the plane (bright blue) to blue.
    """
    node_tree = scene.node_tree
    if node_tree is None:
        return
    switch = next((n for n in node_tree.nodes if n.type == "SWITCH"), None)
    render_layer = next((n for n in node_tree.nodes if n.type == "R_LAYERS"), None)
    if switch is None or render_layer is None:
        return

    mask = node_tree.nodes.get("SHP.ShadowMask")
    ramp = node_tree.nodes.get("SHP.ShadowCR")
    if mask is None or ramp is None:
        mask = node_tree.nodes.new("CompositorNodeSeparateColor")
        mask.name = "SHP.ShadowMask"
        mask.mode = "RGB"
        ramp = node_tree.nodes.new("CompositorNodeValToRGB")
        ramp.name = "SHP.ShadowCR"
        ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        ramp.color_ramp.elements[0].position = 0.15
        ramp.color_ramp.elements[1].color = (0.0, 0.0, 1.0, 1.0)
        ramp.color_ramp.elements[1].position = 0.25
        node_tree.links.new(render_layer.outputs["Image"], mask.inputs["Image"])
        node_tree.links.new(mask.outputs["Blue"], ramp.inputs["Fac"])

    for link in list(switch.inputs["Off"].links):
        node_tree.links.remove(link)
    node_tree.links.new(ramp.outputs[0], switch.inputs["Off"])
