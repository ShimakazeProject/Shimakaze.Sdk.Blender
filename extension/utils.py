"""Helpers for the CnC (SHP) template import and render passes.

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
from typing import TYPE_CHECKING, TypedDict

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
CNC_TEMPLATE_VERSION = "v1.1.0"

#: File name of the bundled Eevee Next template (Blender 4.2+).
CNC_TEMPLATE_FILE = "CnC_EeveeNext_1.1.0_build91_20260811.blend"

#: Template file name for the Hi Five renderer (Blender 5.x).
CNC_TEMPLATE_FILE_HI5 = "CnC_HiFive_1.1.0_build91_20260811.blend"


def current_template_renderer() -> str:
    """Return the template renderer folder matching the running Blender.

    Blender 4.2+ uses Eevee Next; Blender 5.x uses the "Hi Five" template.
    """
    import bpy

    if bpy.app.version[0] >= 5:
        return "hi_five"
    return "eevee_next"


def _renderer_display(renderer: str) -> str:
    """Pretty asset keyword for a renderer folder (``eevee_next`` -> ``EeveeNext``)."""
    return {"eevee_next": "EeveeNext", "hi_five": "HiFive"}.get(renderer, renderer)


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
    renderer = current_template_renderer()
    if renderer == "eevee_next":
        name = CNC_TEMPLATE_FILE
    elif renderer == "hi_five":
        name = CNC_TEMPLATE_FILE_HI5
    else:
        name = f"CnC_{_renderer_display(renderer)}_{CNC_TEMPLATE_VERSION}.blend"
    return Path(__file__).resolve().parent / name


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
    phase("正在连接…")
    with urllib.request.urlopen(api, timeout=30) as response:
        release = json.load(response)

    keyword = current_template_renderer().lower().replace("_", "")
    assets = [a for a in release.get("assets", []) if a["name"].lower().endswith(".zip")]
    match = [a for a in assets if keyword in a["name"].lower()]
    asset = (match or assets or [None])[0]
    if asset is None:
        raise RuntimeError(f"release {CNC_TEMPLATE_VERSION} 中没有 .zip 资源")
    url = asset["browser_download_url"]

    phase("正在下载…")
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "template.zip"
        if report_hook is not None:
            urllib.request.urlretrieve(url, zip_path, reporthook=report_hook)
        else:
            urllib.request.urlretrieve(url, zip_path)
        phase("正在解压…")
        with zipfile.ZipFile(zip_path) as archive:
            blends = [n for n in archive.namelist() if n.lower().endswith(".blend")]
            if not blends:
                raise RuntimeError("模板压缩包中没有 .blend 文件")
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


class ShpPassConfig(TypedDict):
    switch_prefixes: tuple[str, ...]
    planes: dict[str, bool]


#: Render-pass setups matching the template compositor switch chain. Switches
#: are matched by name prefix so the same setup works across template
#: variants/renderers that keep the Object/Buildup/Shadow/Preview naming.
SHP_PASSES: dict[str, ShpPassConfig] = {
    "object": {
        "switch_prefixes": ("Object",),
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
        "switch_prefixes": ("Buildup",),
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
        "switch_prefixes": ("Shadow",),
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
        "switch_prefixes": ("Preview",),
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
        "switch_prefixes": (),
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

#: Per-renderer tweaks to the base pass config, keyed by renderer then pass.
#: Templates that rename their compositor switches or planes can override
#: ``switch_prefixes`` / ``planes`` here.
SHP_PASS_OVERRIDES: dict[str, dict[str, ShpPassConfig]] = {}


def _pass_config(pass_name: str) -> ShpPassConfig:
    """Resolve the pass config, applying the current renderer's overrides."""
    base = SHP_PASSES[pass_name]
    override = SHP_PASS_OVERRIDES.get(current_template_renderer(), {}).get(pass_name)
    if override is None:
        return base
    return {
        "switch_prefixes": override.get("switch_prefixes", base["switch_prefixes"]),
        "planes": {**base["planes"], **override.get("planes", {})},
    }


def apply_shp_pass_to_scene(scene, pass_name: str) -> bool:
    """Apply a render-pass setup to a single scene.

    Toggles the pass switch chain and the visibility of every ``Plane.*``
    object in the scene (detected by name, so imported/renamed scenes work
    too). Also repairs the Alpha Over wiring. Returns True when the scene has
    a compositor to drive.
    """
    import bpy

    config = _pass_config(pass_name)
    node_tree = get_scene_compositor(scene)
    if node_tree is None:
        return False

    if current_template_renderer() in ("eevee_next", "hi_five"):
        repair_compositor(node_tree)
    for node in node_tree.nodes.values():
        if node is not None and node.type == "SWITCH":
            on = any(node.name.startswith(prefix) for prefix in config["switch_prefixes"])
            set_switch(node, on)

    alpha = node_tree.nodes.get("Alpha")
    if alpha is not None:
        set_switch(alpha, scene.shimakaze_sdk.use_alpha)

    scene.render.image_settings.color_mode = "RGBA" if scene.shimakaze_sdk.use_alpha else "RGB"

    for obj in bpy.data.objects:
        if obj.name not in scene.objects or not obj.name.startswith("Plane."):
            continue
        parts = obj.name.split(".")
        if len(parts) >= 2 and parts[1] in config["planes"]:
            obj.hide_render = config["planes"][parts[1]]

    return True


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

    def first_output(node, *names):
        """Return the first output socket matching a name, else the first one."""
        for name in names:
            socket = node.outputs.get(name)
            if socket is not None:
                return socket
        return node.outputs[0]

    def find_input(node, name: str, fallback_index: int | None = None):
        """Return an input socket by name, falling back to an index."""
        socket = node.inputs.get(name)
        if socket is not None:
            return socket
        if fallback_index is not None:
            return node.inputs[fallback_index]
        return node.inputs[0]

    def set_input(node, target: str, from_socket, fallback_index: int | None) -> None:
        nonlocal changed
        socket = find_input(node, target, fallback_index)
        current = next(iter(socket.links), None)
        if current is not None and current.from_socket is from_socket:
            return
        for link in list(socket.links):
            node_tree.links.remove(link)
        node_tree.links.new(from_socket, socket)
        changed = True

    def clear_input(node, target: str, fallback_index: int | None) -> None:
        nonlocal changed
        socket = find_input(node, target, fallback_index)
        if socket.links:
            for link in list(socket.links):
                node_tree.links.remove(link)
            changed = True

    alpha_output = first_output(alpha_switch, "Image", "Output")

    # Left Alpha Over: foreground <- Alpha, background <- Alpha Convert (Group).
    # Blender 4.x inputs are (Fac, Image, Image); 5.x reordered them to
    # (Background, Foreground, Factor, Type, Straight Alpha).
    set_input(alpha_over, "Foreground", alpha_output, 1)
    if group is not None:
        set_input(alpha_over, "Background", first_output(group, "Image"), 2)
    else:
        clear_input(alpha_over, "Background", 2)

    # Right Alpha Over.001: foreground <- Alpha, background <- Color Ramp.
    set_input(alpha_over_1, "Foreground", alpha_output, 1)
    if color_ramp is not None:
        set_input(alpha_over_1, "Background", first_output(color_ramp, "Color"), 2)
    else:
        clear_input(alpha_over_1, "Background", 2)

    return changed


def repair_hi_five_compositor(node_tree) -> bool:
    """Fix the Hi Five template's scrambled compositor wiring.

    The 5.x conversion of the Eevee Next template left the compositor
    mis-wired: the pass switch chain is fed through the control input, and the
    Alpha Over sockets landed in the wrong places. This rewires everything to
    match the patched Eevee Next layout.
    """
    changed = False

    render_layers = next((n for n in node_tree.nodes.values() if n.type == "R_LAYERS"), None)
    alpha_over = node_tree.nodes.get("Alpha Over")
    alpha_over_1 = node_tree.nodes.get("Alpha Over.001")
    alpha_switch = node_tree.nodes.get("Alpha")
    group = node_tree.nodes.get("Group")
    color_ramp = node_tree.nodes.get("Color Ramp")
    bg_rgb = node_tree.nodes.get("BackgroundRGB")
    bg_alpha = node_tree.nodes.get("BackgroundAlpha")
    if alpha_over is None or alpha_over_1 is None or alpha_switch is None:
        return False

    def first_output(node, *names):
        for name in names:
            socket = node.outputs.get(name)
            if socket is not None:
                return socket
        return node.outputs[0]

    def find_input(node, name: str, fallback_index: int | None = None):
        socket = node.inputs.get(name)
        if socket is not None:
            return socket
        if fallback_index is not None:
            return node.inputs[fallback_index]
        return node.inputs[0]

    def set_input(node, target: str, from_socket, fallback_index: int | None) -> None:
        nonlocal changed
        socket = find_input(node, target, fallback_index)
        current = next(iter(socket.links), None)
        if current is not None and current.from_socket is from_socket:
            return
        for link in list(socket.links):
            node_tree.links.remove(link)
        node_tree.links.new(from_socket, socket)
        changed = True

    def clear_input(node, target: str, fallback_index: int | None) -> None:
        nonlocal changed
        socket = find_input(node, target, fallback_index)
        if socket.links:
            for link in list(socket.links):
                node_tree.links.remove(link)
            changed = True

    alpha_output = first_output(alpha_switch, "Image", "Output")

    # Alpha switch: control unlinked, False <- BackgroundRGB, True <- BackgroundAlpha.
    clear_input(alpha_switch, "Switch", 0)
    if bg_rgb is not None:
        set_input(alpha_switch, "False", first_output(bg_rgb, "Color"), 1)
    if bg_alpha is not None:
        set_input(alpha_switch, "True", first_output(bg_alpha, "Color"), 2)

    # Alpha Over: Background <- Alpha, Foreground <- content, Factor left clear.
    set_input(alpha_over, "Background", alpha_output, 0)
    clear_input(alpha_over, "Factor", 2)
    if group is not None:
        set_input(alpha_over, "Foreground", first_output(group, "Image"), 1)

    set_input(alpha_over_1, "Background", alpha_output, 0)
    clear_input(alpha_over_1, "Factor", 2)
    if color_ramp is not None:
        set_input(alpha_over_1, "Foreground", first_output(color_ramp, "Color"), 1)

    # Pass switch chain: control unlinked, False <- passthrough, True <- composited.
    chain = (
        "Object",
        "Buildup.Cycles",
        "Buildup.Eevee",
        "Shadow.Cycles",
        "Shadow.Eevee",
        "Preview.Cycles",
        "Preview.Eevee",
    )
    prev_output = first_output(render_layers, "Image") if render_layers is not None else None
    alpha_over_out = first_output(alpha_over, "Image")
    alpha_over_1_out = first_output(alpha_over_1, "Image")
    for name in chain:
        switch = node_tree.nodes.get(name)
        if switch is None:
            continue
        clear_input(switch, "Switch", 0)
        if prev_output is not None:
            set_input(switch, "False", prev_output, 1)
        on_source = alpha_over_1_out if name.startswith("Shadow") else alpha_over_out
        set_input(switch, "True", on_source, 2)
        prev_output = first_output(switch, "Output", "Image")

    return changed


def repair_compositor(node_tree) -> bool:
    """Repair the template compositor for the running Blender's renderer."""
    renderer = current_template_renderer()
    if renderer == "eevee_next":
        return repair_alpha_over(node_tree)
    if renderer == "hi_five":
        return repair_hi_five_compositor(node_tree)
    return False
