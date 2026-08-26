"""Steam Store API lookup met lokale cache (geen rate-limit problemen)."""

from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

from . import config

STEAM_API = "https://store.steampowered.com/api/appdetails?appids={app_id}&l=en"
CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 dagen


class SteamError(Exception):
    pass


def _read_cache() -> dict[str, Any]:
    p = config.steam_cache_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    now = time.time()
    return {k: v for k, v in data.items() if now - v.get("fetched", 0) < CACHE_TTL_SECONDS}


def _write_cache(cache: dict[str, Any]) -> None:
    p = config.steam_cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_app_details(app_id: str, offline_ok: bool = True) -> dict[str, Any]:
    cache = _read_cache()
    if app_id in cache:
        return cache[app_id]["data"]

    if offline_ok and config.database_path().exists():
        # offline: probeer de compat-database naam als fallback (geen netwerk)
        from .compat import get

        entry = get(app_id)
        if entry and entry.name:
            return {"name": entry.name, "type": "game", "offline": True}

    url = STEAM_API.format(app_id=app_id)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise SteamError(f"Steam API niet bereikbaar voor {app_id}: {exc}") from exc

    info = payload.get(app_id, {})
    if not info.get("success") or not info.get("data"):
        return {}
    data = info["data"]
    result = {
        "name": data.get("name", ""),
        "type": data.get("type", "game"),
        "short_description": data.get("short_description", ""),
        "pc_requirements": data.get("pc_requirements", {}),
        "release_date": (data.get("release_date") or {}).get("date", ""),
        "price": (data.get("price_overview") or {}).get("final_formatted", ""),
        "url": f"https://store.steampowered.com/app/{app_id}",
    }
    cache[app_id] = {"fetched": time.time(), "data": result}
    _write_cache(cache)
    return result


def detect_dx_version(details: dict[str, Any]) -> str:
    """Detecteer DirectX-versie uit pc_requirements-tekst (HTML-tolerant).

    Echte Steam-tekst: '<strong>DirectX:</strong> Version 11' enz.
    """
    reqs = details.get("pc_requirements", {})
    text = " ".join(
        str(v) for v in (reqs.get("minimum", ""), reqs.get("recommended", ""))
    )
    m = re.search(r"DirectX.*?Version\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1)
    return ""


def detect_size_hint(details: dict[str, Any]) -> str:
    """Grofweg de opslagvereiste uit de requirements-tekst halen (HTML-tolerant)."""
    reqs = details.get("pc_requirements", {})
    text = " ".join(
        str(v) for v in (reqs.get("minimum", ""), reqs.get("recommended", ""))
    )
    m = re.search(r"Storage.*?([\d.]+)\s*GB", text, re.IGNORECASE | re.DOTALL)
    return f"{m.group(1)} GB" if m else ""