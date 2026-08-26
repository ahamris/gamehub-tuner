"""Paden en defaults voor de GameHub-installatie.

Alles is overridable via env-vars (handig voor tests en andere gebruikers):
- GAMEHUB_DIR       -> gamehub-map (default: ~/Library/Application Support/com.gamemac.www/gamehub)
- GAMEHUB_WINE_DIR  -> wine-engine-map (default: .../com.gamemac.www/wine-engine)
- GAMEHUB_REPO_DIR  -> deze repo (default: naast het package)
"""

from __future__ import annotations

import os
from pathlib import Path

APP_SUPPORT = Path.home() / "Library" / "Application Support" / "com.gamemac.www"


def gamehub_dir() -> Path:
    return Path(os.environ.get("GAMEHUB_DIR", APP_SUPPORT / "gamehub"))


def wine_dir() -> Path:
    return Path(os.environ.get("GAMEHUB_WINE_DIR", APP_SUPPORT / "wine-engine"))


def settings_dir() -> Path:
    return gamehub_dir() / "game-settings"


def container_store_path() -> Path:
    return gamehub_dir() / "game_container_store.json"


def installations_path() -> Path:
    return wine_dir() / "container" / "wine_installations.json"


def components_path() -> Path:
    return wine_dir() / "component" / "components.json"


def repo_dir() -> Path:
    """Repo-map (met presets/database). Werkt vanuit een checkout of via env.

    Bij `pip install -e .` wijst __file__ naar de checkout; bij een platte
    checkout ook. Als die geen presets bevat, vallen we terug op GAMEHUB_REPO_DIR
    of de huidige werkmap.
    """
    env = os.environ.get("GAMEHUB_REPO_DIR")
    if env:
        return Path(env)
    here = Path(__file__).resolve().parent.parent
    if (here / "presets").exists():
        return here
    return Path.cwd()


def presets_dir() -> Path:
    return repo_dir() / "presets"


def database_path() -> Path:
    return repo_dir() / "database" / "compatibility.toml"


def steam_cache_path() -> Path:
    return repo_dir() / "database" / "steam-cache.json"


def benchmarks_dir() -> Path:
    return repo_dir() / "benchmarks"


def is_gamehub_running() -> bool:
    """Check of het GameHub.app-process draait (waarschuwing bij apply-preset)."""
    try:
        import subprocess

        out = subprocess.run(
            ["pgrep", "-x", "GameHub"], capture_output=True, text=True, timeout=5
        )
        return out.returncode == 0
    except Exception:
        return False