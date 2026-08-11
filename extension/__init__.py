"""Shimakaze SDK - a Blender 4.5 add-on extension.

This module is the add-on entry point. It only handles registration and
keeps the single source of truth for the version number in
``blender_manifest.toml``.
"""

import importlib
import tomllib
from pathlib import Path

__all__ = (
    "__version__",
    "__version_info__",
    "register",
    "unregister",
)

_MANIFEST_PATH = Path(__file__).resolve().parent / "blender_manifest.toml"


def _read_version() -> str:
    try:
        with _MANIFEST_PATH.open("rb") as stream:
            manifest = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError, KeyError):
        return "0.0.0"
    return str(manifest["version"])


__version__ = _read_version()
__version_info__ = tuple(int(part) for part in __version__.split("."))

# Registration order matters: properties first, then the operators and UI
# that reference them.
_ADDON_MODULES = ("properties", "operators", "ui")


def register() -> None:
    """Register every sub-module of the add-on."""
    for module_name in _ADDON_MODULES:
        module = importlib.import_module(f"{__name__}.{module_name}")
        module.register()


def unregister() -> None:
    """Unregister every sub-module, in reverse registration order."""
    for module_name in reversed(_ADDON_MODULES):
        module = importlib.import_module(f"{__name__}.{module_name}")
        module.unregister()
