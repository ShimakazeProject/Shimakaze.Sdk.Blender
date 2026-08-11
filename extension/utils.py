"""Pure, testable helpers shared across the add-on.

Everything in this module must be importable and testable without Blender,
so keep Blender imports inside the functions that need them.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bpy.types import AddonPreferences

logger = logging.getLogger(__name__)


def configure_logging(*, debug: bool) -> None:
    """Configure the module logger based on the add-on preference."""
    logger.setLevel(logging.DEBUG if debug else logging.INFO)


def get_preferences() -> AddonPreferences:
    """Return the Shimakaze SDK add-on preferences."""
    import bpy

    return bpy.context.preferences.addons[__package__].preferences


def compose_greeting(asset_name: str, asset_version: str) -> str:
    """Compose the greeting shown by the ``shimakaze.hello`` operator."""
    return f"Hello from the Shimakaze SDK, {asset_name} v{asset_version}!"


def normalize_identifier(name: str) -> str:
    """Convert an arbitrary string into a snake_case identifier.

    >>> normalize_identifier("  My Cool-Asset!  ")
    'my_cool_asset'
    """
    words = re.findall(r"[A-Za-z0-9]+", name)
    return "_".join(word.lower() for word in words)


def bump_version(version: str) -> str:
    """Increment the last numeric component of a dotted version string.

    >>> bump_version("0.1.0")
    '0.1.1'
    """
    parts = version.split(".")
    if not parts or not parts[-1].isdigit():
        return version + ".1"
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)
