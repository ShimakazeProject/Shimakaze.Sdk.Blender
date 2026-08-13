"""Hi Five (Blender 5.x) template adaptation."""

from .._common import clear_input, first_output, set_input

CNC_TEMPLATE_FILE = "CnC_HiFive_1.1.0_build91_20260811.blend"

#: Order of the pass switch chain in the template compositor.
_PASS_CHAIN = (
    "Object",
    "Buildup.Cycles",
    "Buildup.Eevee",
    "Shadow.Cycles",
    "Shadow.Eevee",
    "Preview.Cycles",
    "Preview.Eevee",
)


def get_template_file_name() -> str:
    """Template .blend file name for this renderer."""
    return CNC_TEMPLATE_FILE


def repair_compositor(node_tree) -> bool:
    """Fix the Hi Five template's scrambled compositor wiring.

    The 5.x conversion of the Eevee Next template left the compositor
    mis-wired: the pass switch chain is fed through the control input, and the
    Alpha Over sockets landed in the wrong places. This rewires everything to
    match the patched Eevee Next layout. Returns True if anything was changed.
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

    alpha_output = first_output(alpha_switch, "Image", "Output")

    # Alpha switch: control unlinked, False <- BackgroundRGB, True <- BackgroundAlpha.
    changed |= clear_input(node_tree, alpha_switch, "Switch", 0)
    if bg_rgb is not None:
        changed |= set_input(node_tree, alpha_switch, "False", first_output(bg_rgb, "Color"), 1)
    if bg_alpha is not None:
        changed |= set_input(node_tree, alpha_switch, "True", first_output(bg_alpha, "Color"), 2)

    # Alpha Over: Background <- Alpha, Foreground <- content, Factor left clear.
    changed |= set_input(node_tree, alpha_over, "Background", alpha_output, 0)
    changed |= clear_input(node_tree, alpha_over, "Factor", 2)
    if group is not None:
        changed |= set_input(node_tree, alpha_over, "Foreground", first_output(group, "Image"), 1)

    changed |= set_input(node_tree, alpha_over_1, "Background", alpha_output, 0)
    changed |= clear_input(node_tree, alpha_over_1, "Factor", 2)
    if color_ramp is not None:
        changed |= set_input(
            node_tree, alpha_over_1, "Foreground", first_output(color_ramp, "Color"), 1
        )

    # Pass switch chain: control unlinked, False <- passthrough, True <- composited.
    prev_output = first_output(render_layers, "Image") if render_layers is not None else None
    alpha_over_out = first_output(alpha_over, "Image")
    alpha_over_1_out = first_output(alpha_over_1, "Image")
    for name in _PASS_CHAIN:
        switch = node_tree.nodes.get(name)
        if switch is None:
            continue
        changed |= clear_input(node_tree, switch, "Switch", 0)
        if prev_output is not None:
            changed |= set_input(node_tree, switch, "False", prev_output, 1)
        on_source = alpha_over_1_out if name.startswith("Shadow") else alpha_over_out
        changed |= set_input(node_tree, switch, "True", on_source, 2)
        prev_output = first_output(switch, "Output", "Image")

    return changed
