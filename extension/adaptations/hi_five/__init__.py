"""Hi Five (Blender 5.x) template adaptation package."""

CNC_TEMPLATE_FILE = "CnC_HiFive_1.2.0_build100_20260813.blend"


def get_template_file_name() -> str:
    """Template .blend file name for this renderer."""
    return CNC_TEMPLATE_FILE


def eevee_engine_name() -> str:
    """Blender EEVEE engine identifier for Blender 5.x."""
    return "BLENDER_EEVEE"
