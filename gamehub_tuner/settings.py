"""Lezen en in-place patchen van GameHub game-settings JSON.

De filename is een hash van de `key` (platform + app_id + game_id). Omdat de
`key` niet verandert wanneer alleen `settings` wijzigen, patchen we IN-PLACE en
behouden we de filename (zie docs/Requirements.md -> ADR-1).

We schrijven nooit velden die we niet in het echte bestand hebben gezien.
Nieuwe componentconfigs (engine / graphics stack) kopiëren we van een
"referentie" uit een ander settings-bestand dat die config al gebruikt.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config

SCHEMA_VERSION = 2
SETTINGS_GLOB = "*.json"

# Graphics stack "kinds" die we kennen (zoals geobserveerd in echte files).
KNOWN_GRAPHICS_KINDS = {"gptk", "dxmt", "opengl"}

# Whitelist van settings-keys die presets mogen wijzigen (geobserveerd schema v2).
# We schrijven NOOIT velden buiten deze lijst (ADR-1 + code-review bevinding 1.2).
KNOWN_SETTINGS_KEYS = {
    "language",
    "start_parameters",
    "sync_mode",
    "bypass_av_decode",
    "avx_enabled",
    "gamepad_compat_mode",
    "retina_mode",
    "metal_hud_enabled",
    "metal4_enabled",
    "dlss_mode",
    "ray_tracing_mode",
    "dxmt_experimental_dx12_support",
    "molten_vk",
    "open_gl",
    "graphic_api",
}


class SettingsError(Exception):
    """Fout bij lezen/schrijven van settings."""


@dataclass
class SettingsFile:
    path: Path
    data: dict[str, Any]
    app_id: str
    platform: str
    game_id: str

    @property
    def settings(self) -> dict[str, Any]:
        return self.data.get("settings", {})

    def current_profile(self) -> dict[str, Any]:
        s = self.settings
        stack = s.get("graphics_stack", {})
        layer = s.get("compatibility_layer_config", {})
        return {
            "engine": layer.get("display_name", s.get("compatibility_layer")),
            "engine_id": s.get("compatibility_layer"),
            "graphics_stack": stack.get("kind"),
            "graphic_api": s.get("graphic_api"),
            "sync_mode": s.get("sync_mode"),
            "avx_enabled": s.get("avx_enabled", False),
            "bypass_av_decode": s.get("bypass_av_decode", False),
            "retina_mode": s.get("retina_mode", False),
            "metal_hud_enabled": s.get("metal_hud_enabled", False),
            "metal4_enabled": s.get("metal4_enabled", False),
            "dlss_mode": s.get("dlss_mode"),
            "ray_tracing_mode": s.get("ray_tracing_mode"),
            "start_parameters": s.get("start_parameters", ""),
        }


def _load_json(path: Path, required: bool = True) -> Any:
    if not path.exists():
        if required:
            raise SettingsError(f"bestand niet gevonden: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SettingsError(f"ongeldige JSON in {path}: {exc}") from exc


def settings_files() -> list[SettingsFile]:
    """Alle game-settings bestanden, gesorteerd op app_id."""
    d = config.settings_dir()
    if not d.exists():
        return []
    result: list[SettingsFile] = []
    for p in sorted(d.glob(SETTINGS_GLOB)):
        if ".bak" in p.name:
            continue
        try:
            data = _load_json(p)
        except SettingsError:
            continue
        key = data.get("key", {})
        if not isinstance(data, dict) or key.get("kind") != "platform":
            continue
        if "schema_version" in data and data["schema_version"] != SCHEMA_VERSION:
            # Onbekend schema: niet aanraken (veiligheid, zie Requirements risico-tabel).
            continue
        result.append(
            SettingsFile(
                path=p,
                data=data,
                app_id=str(key.get("platform_app_id", "")),
                platform=str(key.get("platform", "")),
                game_id=str(key.get("game_id", "")),
            )
        )
    return result


def bindings_map() -> dict[str, str]:
    """app_id -> game_name uit game_container_store.json."""
    store = _load_json(config.container_store_path(), required=False)
    out: dict[str, str] = {}
    if not store:
        return out
    for b in store.get("bindings", []):
        if b.get("platform_app_id") and b.get("game_name"):
            out[str(b["platform_app_id"])] = str(b["game_name"])
    return out


def find_references(files: list[SettingsFile]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(engine_refs, graphics_refs) uit alle bestaande configs.

    engine_refs:  {engine_id: compatibility_layer_config}
    graphics_refs: {kind: graphics_stack_block}
    """
    engine_refs: dict[str, Any] = {}
    graphics_refs: dict[str, Any] = {}
    for f in files:
        s = f.settings
        layer_id = s.get("compatibility_layer")
        cfg = s.get("compatibility_layer_config")
        if layer_id and cfg and layer_id not in engine_refs:
            engine_refs[str(layer_id)] = cfg
        stack = s.get("graphics_stack", {})
        kind = stack.get("kind")
        if kind and stack and kind not in graphics_refs:
            graphics_refs[str(kind)] = stack
    return engine_refs, graphics_refs


def find_file_by_app_id(files: list[SettingsFile], app_id: str) -> SettingsFile | None:
    for f in files:
        if f.app_id == str(app_id):
            return f
    return None


def backup(path: Path) -> Path:
    bak = path.with_name(f"{path.name}.bak-{int(time.time() * 1000)}")
    shutil.copy2(path, bak)
    return bak


def patch_settings(
    sf: SettingsFile,
    scalar_overrides: dict[str, Any],
    engine: str | None = None,
    graphics_stack: str | None = None,
    refs: tuple[dict[str, Any], dict[str, Any]] | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Patch de settings in-place. Geeft lijst van toegepaste wijzigingen terug.

    - scalar_overrides: directe settings-keys (sync_mode, avx_enabled, ...).
      Alleen keys in KNOWN_SETTINGS_KEYS worden geaccepteerd.
    - engine: engine-id of -naam (bv. "10000073" of "wine-proton_11.0"); de
      compatibility_layer_config wordt gekopieerd van een referentie.
    - graphics_stack: kind ("gptk"|"dxmt"|"opengl"); block gekopieerd van
      referentie.
    - dry_run: bereken wijzigingen maar schrijf niets (geen backup, geen write).
    """
    if refs is None:
        refs = find_references(settings_files())
    engine_refs, graphics_refs = refs

    # Schema-guard: weigeren op onbekend schema.
    if sf.data.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise SettingsError(
            f"onbekend schema_version {sf.data.get('schema_version')} in {sf.path.name}; "
            "weigeren om de config te wijzigen."
        )

    changes: list[str] = []
    s = sf.settings

    unknown = set(scalar_overrides) - KNOWN_SETTINGS_KEYS
    if unknown:
        raise SettingsError(
            "onbekende settings-keys in preset: "
            + ", ".join(sorted(unknown))
            + " (whitelist: "
            + ", ".join(sorted(KNOWN_SETTINGS_KEYS))
            + ")"
        )
    for key, value in scalar_overrides.items():
        old = s.get(key)
        if old == value:
            continue
        s[key] = value
        changes.append(f"{key}: {old!r} -> {value!r}")

    if engine is not None:
        resolved = _resolve_engine(engine, engine_refs)
        if resolved is None:
            raise SettingsError(
                f"engine '{engine}' niet gevonden in referenties. "
                "Installeer de engine eerst in GameHub of kies uit: "
                + ", ".join(sorted(engine_refs.keys()) or ["<geen>"])
            )
        eid, cfg = resolved
        _ensure_engine_installed(eid)
        if s.get("compatibility_layer") != eid or s.get("compatibility_layer_config") != cfg:
            changes.append(f"engine: {s.get('compatibility_layer')} -> {eid}")
            s["compatibility_layer"] = eid
            s["compatibility_layer_config"] = cfg

    if graphics_stack is not None:
        if graphics_stack not in KNOWN_GRAPHICS_KINDS:
            raise SettingsError(
                f"onbekende graphics stack '{graphics_stack}'; kies uit {sorted(KNOWN_GRAPHICS_KINDS)}"
            )
        block = graphics_refs.get(graphics_stack)
        if block is None:
            raise SettingsError(
                f"geen referentie-config voor graphics stack '{graphics_stack}' gevonden "
                "(configureer de stack eerst ergens in GameHub)."
            )
        _ensure_component_installed(block, graphics_stack)
        current_kind = s.get("graphics_stack", {}).get("kind")
        if current_kind != graphics_stack:
            changes.append(f"graphics_stack: {current_kind!r} -> {graphics_stack!r}")
            s["graphics_stack"] = block

    if not changes:
        return changes

    if dry_run:
        return changes

    backup(sf.path)
    _write_json(sf.path, sf.data)
    return changes


def _resolve_engine(
    engine: str, engine_refs: dict[str, Any]
) -> tuple[str, dict[str, Any]] | None:
    """Zoek engine-id + config; accepteer id of display-naam."""
    if engine in engine_refs:
        return engine, engine_refs[engine]
    for eid, cfg in engine_refs.items():
        if cfg.get("display_name") == engine or cfg.get("name") == engine:
            return eid, cfg
    return None


def installed_engine_ids() -> set[str]:
    return {e["id"] for e in list_installed_engines()}


def _ensure_engine_installed(eid: str) -> None:
    """Weiger als de engine niet verifieerbaar geïnstalleerd is (fail-closed)."""
    installed = installed_engine_ids()
    if not installed:
        raise SettingsError(
            "kan de installatiestatus van engines niet verifiëren "
            "(wine_installations.json ontbreekt of bevat geen voltooide engines); "
            "weiger uit veiligheid een engine-wijziging door te voeren."
        )
    if eid not in installed:
        raise SettingsError(
            f"engine {eid} is NIET lokaal geïnstalleerd (wine_installations.json toont "
            f"alleen: {', '.join(sorted(installed))}). Installeer de engine eerst in GameHub."
        )


def _ensure_component_installed(block: dict[str, Any], stack: str) -> None:
    """Weiger als de graphics-stack-component niet geïnstalleerd is (fail-closed).

    Prevents "Failed to start game" in GameHub's preflight (bv. dxmt-v0.80
    gerefereerd maar nergens geïnstalleerd). Builtin-stacks zonder
    component_id (bv. opengl) kunnen niet geverifieerd worden en passeren.
    """
    cid = str(block.get("component_id", ""))
    if not cid:
        return  # builtin, geen component-afhankelijkheid
    installed = {c["id"] for c in list_installed_components()}
    if not installed:
        raise SettingsError(
            f"kan de installatiestatus van graphics stack '{stack}' niet verifiëren "
            "(components.json ontbreekt of bevat geen componenten); weiger uit veiligheid."
        )
    if cid not in installed:
        raise SettingsError(
            f"graphics stack '{stack}' (component {cid}) is NIET lokaal geïnstalleerd; "
            f"beschikbaar: {', '.join(sorted(installed))}. "
            "Installeer de stack eerst in GameHub, of gebruik een andere preset."
        )


def referenced_engine_ids(files: list[SettingsFile]) -> dict[str, int]:
    """engine-id -> aantal settings-files die er naar verwijzen."""
    counts: dict[str, int] = {}
    for f in files:
        eid = str(f.settings.get("compatibility_layer", ""))
        if eid:
            counts[eid] = counts.get(eid, 0) + 1
    return counts


def _write_json(path: Path, data: dict[str, Any]) -> None:
    import os

    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, indent=2, ensure_ascii=False))
        fh.flush()
        os.fsync(fh.fileno())
    tmp.replace(path)


def list_installed_engines() -> list[dict[str, Any]]:
    inst = _load_json(config.installations_path(), required=False) or {}
    raw = inst.get("wine_installations", {})
    engines = []
    for eid, meta in raw.items():
        # Alleen voltooide engines tellen (status "downloading" is niet speelbaar).
        if meta.get("install_status") and meta["install_status"] != "completed":
            continue
        engines.append(
            {
                "id": str(eid),
                "name": meta.get("name"),
                "version": meta.get("version"),
                "version_code": meta.get("version_code"),
                "is_default": meta.get("is_default", False),
                "install_status": meta.get("install_status"),
                "architecture": meta.get("architecture"),
            }
        )
    return sorted(engines, key=lambda e: e["name"] or "")


def list_installed_components() -> list[dict[str, Any]]:
    comp = _load_json(config.components_path(), required=False) or {}
    out = []
    for c in comp.get("components", []):
        m = c.get("manifest", {})
        out.append(
            {
                "id": str(m.get("id")),
                "name": m.get("name"),
                "display_name": m.get("metadata", {}).get("display_name", m.get("name")),
                "kind": m.get("metadata", {}).get("component_kind"),
                "status": c.get("status"),
            }
        )
    return out