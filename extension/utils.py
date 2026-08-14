"""Helpers for the CnC (SHP) template import and render setup.

Everything in this module must be importable and testable without Blender,
so keep Blender imports inside the functions that need them.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from .adaptations import (
    current_template_renderer,
    eevee_engine_name,
    get_template_file_name,
)
from .i18n import t

if TYPE_CHECKING:
    from bpy.types import Collection, Object

# ---------------------------------------------------------------------------
# Template release metadata.
#
# When the template file for the running Blender version is missing, it is
# downloaded from the pinned release below. Bump CNC_TEMPLATE_VERSION when
# adapting to a newer template; different versions require different code, so
# never use "latest".
CNC_TEMPLATE_REPO = "Zawaro/blender-cnc-templates"
CNC_TEMPLATE_VERSION = "v1.2.0"


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


def get_scene_compositor(scene):
    """Return the scene's compositor node tree across Blender versions.

    Blender 4.x exposes it as ``scene.node_tree``; Blender 5.0 renamed it to
    ``scene.compositing_node_group``.
    """
    node_tree = getattr(scene, "node_tree", None)
    if node_tree is None:
        node_tree = getattr(scene, "compositing_node_group", None)
    return node_tree


def get_cnc_template_path() -> Path:
    """Return the path of the template for the running Blender version."""
    return Path(__file__).resolve().parent / get_template_file_name()


def ensure_template() -> Path:
    """Return the template .blend, downloading it from the release if missing."""
    path = get_cnc_template_path()
    if path.is_file():
        return path
    _download_template(path)
    return path


def _download_template(destination: Path, report_hook=None, set_phase=None) -> None:
    """Download the pinned release .zip and extract the .blend to destination.

    ``report_hook`` receives ``(count, block_size, total_size)`` download
    progress; ``set_phase`` receives a short status string. Both are optional
    and must not touch bpy (they run on a worker thread).
    """

    def phase(text: str) -> None:
        if set_phase is not None:
            set_phase(text)

    api = f"https://api.github.com/repos/{CNC_TEMPLATE_REPO}/releases/tags/{CNC_TEMPLATE_VERSION}"
    phase(t("Connecting…"))
    with urllib.request.urlopen(api, timeout=30) as response:
        release = json.load(response)

    keyword = current_template_renderer().lower().replace("_", "")
    assets = [a for a in release.get("assets", []) if a["name"].lower().endswith(".zip")]
    match = [a for a in assets if keyword in a["name"].lower()]
    asset = (match or assets or [None])[0]
    if asset is None:
        msg = t("No .zip asset in release {version}").format(version=CNC_TEMPLATE_VERSION)
        raise RuntimeError(msg)
    url = asset["browser_download_url"]

    phase(t("Downloading…"))
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "template.zip"
        if report_hook is not None:
            urllib.request.urlretrieve(url, zip_path, reporthook=report_hook)
        else:
            urllib.request.urlretrieve(url, zip_path)
        phase(t("Extracting…"))
        with zipfile.ZipFile(zip_path) as archive:
            blends = [n for n in archive.namelist() if n.lower().endswith(".blend")]
            if not blends:
                raise RuntimeError(t("No .blend file in the template archive"))
            name = blends[0]
            archive.extract(name, tmp)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(Path(tmp) / name, destination)


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


#: Render engines selectable in the panel: Cycles and EEVEE.
RENDER_ENGINES: tuple[str, str] = ("CYCLES", "EEVEE")

#: Render targets (passes) selectable in the panel, in template order.
RENDER_TARGETS: tuple[str, ...] = ("object", "shadow", "buildup", "preview", "reset")

#: Compositor switch chain the template wires the pass output through.
RENDER_SWITCH_CHAIN: tuple[str, ...] = (
    "Object",
    "Buildup.Cycles",
    "Buildup.Eevee",
    "Shadow.Cycles",
    "Shadow.Eevee",
    "Preview.Cycles",
    "Preview.Eevee",
)

#: Plane visibility per target, per engine. Keys are object name parts
#: (``holdout``, ``shadow``, ``grey``, ...) that appear right after the
#: ``Plane.`` prefix; the value is the ``hide_render`` flag. Mirrors the
#: template's own ``<Engine>.Render.<Target>`` scripts exactly (only the
#: Object pass shows ambient and the Shadow pass shows holdout in Cycles).
RENDER_PLANES: dict[str, dict[str, dict[str, bool]]] = {
    "object": {
        "CYCLES": {
            "holdout": True,
            "holdout2": True,
            "shadow": True,
            "shadow2": True,
            "blue": True,
            "grey": True,
            "ambient": False,
        },
        "EEVEE": {
            "holdout": True,
            "holdout2": True,
            "shadow": True,
            "shadow2": True,
            "blue": True,
            "grey": True,
            "ambient": True,
        },
    },
    "buildup": {
        "CYCLES": {
            "holdout": True,
            "holdout2": False,
            "shadow": True,
            "shadow2": True,
            "blue": True,
            "grey": True,
            "ambient": True,
        },
        "EEVEE": {
            "holdout": True,
            "holdout2": False,
            "shadow": True,
            "shadow2": True,
            "blue": True,
            "grey": True,
            "ambient": True,
        },
    },
    "shadow": {
        "CYCLES": {
            "holdout": False,
            "holdout2": True,
            "shadow": False,
            "shadow2": True,
            "blue": True,
            "grey": True,
            "ambient": True,
        },
        "EEVEE": {
            "holdout": True,
            "holdout2": True,
            "shadow": False,
            "shadow2": True,
            "blue": True,
            "grey": True,
            "ambient": True,
        },
    },
    "preview": {
        "CYCLES": {
            "holdout": False,
            "holdout2": False,
            "shadow": False,
            "shadow2": False,
            "blue": True,
            "grey": True,
            "ambient": True,
        },
        "EEVEE": {
            "holdout": False,
            "holdout2": False,
            "shadow": False,
            "shadow2": False,
            "blue": True,
            "grey": True,
            "ambient": True,
        },
    },
    "reset": {
        "CYCLES": {
            "holdout": True,
            "holdout2": True,
            "shadow": True,
            "shadow2": True,
            "blue": True,
            "grey": False,
            "ambient": True,
        },
        "EEVEE": {
            "holdout": True,
            "holdout2": True,
            "shadow": True,
            "shadow2": True,
            "blue": True,
            "grey": False,
            "ambient": True,
        },
    },
}

#: Render-quality settings per target: (filter_width, filter_size, single_layer).
RENDER_QUALITY: dict[str, tuple[float, float, bool]] = {
    "object": (0.9, 0.7, True),
    "shadow": (0.01, 0.01, False),
    "buildup": (0.9, 0.7, True),
    "preview": (0.9, 0.7, True),
    "reset": (0.9, 0.7, True),
}


def resolve_plane_suffix(game: str, variant: str) -> str:
    """Compute the plane object suffix for a game + variant (e.g. ``RA2.INF``)."""
    code = CNC_TEMPLATE_GAME[game][1]
    variant_suffix = CNC_VARIANT_OPTIONS[variant][1]
    return f"{code}{variant_suffix}"


def render_engine_enum_items(self=None, context=None) -> list[tuple[str, str, str]]:
    """Build the EnumProperty items for the render engine selector."""
    return [
        (engine, "Cycles" if engine == "CYCLES" else "EEVEE", f"Render with {engine}")
        for engine in RENDER_ENGINES
    ]


def render_target_enum_items(self=None, context=None) -> list[tuple[str, str, str]]:
    """Build the EnumProperty items for the render target selector."""
    labels = {
        "object": "Object",
        "shadow": "Shadow",
        "buildup": "Buildup",
        "preview": "Preview",
        "reset": "Reset",
    }
    return [
        (target, labels[target], f"Render the {labels[target]} pass") for target in RENDER_TARGETS
    ]


def set_switch(node, value: bool) -> None:
    """Toggle a compositor switch node across Blender versions.

    Blender 4.x exposes ``node.check``; Blender 5.x reuses ``GeometryNodeSwitch``
    which is toggled through its ``Switch`` boolean input.
    """
    if hasattr(node, "check"):
        node.check = value
    else:
        switch_input = node.inputs.get("Switch")
        if switch_input is not None:
            switch_input.default_value = value


def apply_render_setup(scene, engine: str, use_alpha: bool, target: str) -> bool:
    """Apply a render-engine + alpha + target setup to a single scene.

    This is the unified, generic replacement for the template's many
    ``<Engine>.Render.<Target>`` and ``Alpha.Enable/Disable`` scripts: it
    picks the engine, toggles the pass switch chain, flips the Alpha switch,
    sets the output color mode, and updates plane visibility. Returns True
    when the scene has a compositor to drive.
    """
    import bpy

    if engine not in RENDER_ENGINES or target not in RENDER_TARGETS:
        return False

    node_tree = get_scene_compositor(scene)
    if node_tree is None:
        return False

    scene.render.engine = "CYCLES" if engine == "CYCLES" else eevee_engine_name()

    filter_width, filter_size, single_layer = RENDER_QUALITY[target]
    scene.cycles.filter_width = filter_width
    scene.render.filter_size = filter_size
    scene.render.use_single_layer = single_layer

    # Toggle the pass switch chain: exactly one of the per-engine switches
    # (or "Object") is on, matching the template's render scripts.
    switch_on = None
    if target == "object":
        switch_on = "Object"
    elif target != "reset":
        engine_suffix = "Cycles" if engine == "CYCLES" else "Eevee"
        switch_on = f"{target.title()}.{engine_suffix}"
    for name in RENDER_SWITCH_CHAIN:
        node = node_tree.nodes.get(name)
        if node is not None:
            set_switch(node, name == switch_on)

    alpha = node_tree.nodes.get("Alpha")
    if alpha is not None:
        set_switch(alpha, use_alpha)
    if use_alpha:
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
    else:
        scene.render.image_settings.color_mode = "RGB"

    planes = RENDER_PLANES[target][engine]
    for obj in bpy.data.objects:
        if obj.name not in scene.objects:
            continue
        if obj.name.startswith("Sun."):
            obj.hide_render = False
            continue
        for kind, hidden in planes.items():
            if obj.name.startswith(f"Plane.{kind}."):
                obj.hide_render = hidden
                break

    return True


def apply_holdout_shader(material) -> None:
    """Set a material's surface to a Holdout shader (blocks the object)."""
    if not material.use_nodes:
        material.use_nodes = True
    node_tree = material.node_tree
    if node_tree is None:
        return
    output = next(
        (n for n in node_tree.nodes.values() if n is not None and n.type == "OUTPUT_MATERIAL"),
        None,
    )
    if output is None:
        output = node_tree.nodes.new("ShaderNodeOutputMaterial")
    holdout = next(
        (n for n in node_tree.nodes.values() if n is not None and n.type == "HOLDOUT"),
        None,
    )
    if holdout is None:
        holdout = node_tree.nodes.new("ShaderNodeHoldout")
    for link in list(output.inputs["Surface"].links):
        node_tree.links.remove(link)
    node_tree.links.new(holdout.outputs["Holdout"], output.inputs["Surface"])
