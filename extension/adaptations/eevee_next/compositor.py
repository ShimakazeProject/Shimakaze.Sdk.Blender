"""Eevee Next (Blender 4.x) template adaptation."""

from .._common import clear_input, first_output, set_input

CNC_TEMPLATE_FILE = "CnC_EeveeNext_1.1.0_build91_20260811.blend"


def get_template_file_name() -> str:
    """Template .blend file name for this renderer."""
    return CNC_TEMPLATE_FILE


def repair_compositor(node_tree) -> bool:
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

    alpha_output = first_output(alpha_switch, "Image", "Output")

    # Left Alpha Over: foreground <- Alpha, background <- Alpha Convert (Group).
    changed |= set_input(node_tree, alpha_over, "Foreground", alpha_output, 1)
    if group is not None:
        changed |= set_input(node_tree, alpha_over, "Background", first_output(group, "Image"), 2)
    else:
        changed |= clear_input(node_tree, alpha_over, "Background", 2)

    # Right Alpha Over.001: foreground <- Alpha, background <- Color Ramp.
    changed |= set_input(node_tree, alpha_over_1, "Foreground", alpha_output, 1)
    if color_ramp is not None:
        changed |= set_input(
            node_tree, alpha_over_1, "Background", first_output(color_ramp, "Color"), 2
        )
    else:
        changed |= clear_input(node_tree, alpha_over_1, "Background", 2)

    return changed
