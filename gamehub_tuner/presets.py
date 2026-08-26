"""Preset-bibliotheek (TOML, community-editable).

Preset-schema:
    name = "dx11-dxmt"
    description = "..."

    # Optioneel: engine-id of -naam (bv. "wine-proton_11.0" of "10000073")
    engine = "wine-proton_11.0"

    # Optioneel: graphics stack kind ("gptk" | "dxmt" | "opengl")
    graphics_stack = "dxmt"

    # Directe settings-overrides
    [settings]
    sync_mode = "msync"
    avx_enabled = false
    ...
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config
from .settings import SettingsError


@dataclass
class Preset:
    name: str
    description: str
    engine: str | None
    graphics_stack: str | None
    settings: dict[str, Any]

    def scalar_overrides(self) -> dict[str, Any]:
        return dict(self.settings)


def load_preset(name: str) -> Preset:
    path = config.presets_dir() / f"{name}.toml"
    if not path.exists():
        raise SettingsError(f"preset '{name}' niet gevonden (zoekt: {path})")
    return _parse_preset(name, path)


def list_presets() -> list[Preset]:
    d = config.presets_dir()
    if not d.exists():
        return []
    out: list[Preset] = []
    for p in sorted(d.glob("*.toml")):
        try:
            out.append(_parse_preset(p.stem, p))
        except SettingsError:
            continue
    return out


def _parse_preset(name: str, path: Path) -> Preset:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise SettingsError(f"ongeldige TOML in {path}: {exc}") from exc
    return Preset(
        name=raw.get("name", name),
        description=raw.get("description", ""),
        engine=raw.get("engine"),
        graphics_stack=raw.get("graphics_stack"),
        settings=dict(raw.get("settings", {})),
    )