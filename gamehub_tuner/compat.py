"""Community compatibiliteitsdatabase (TOML).

Schema per game:
    [[games]]
    app_id = 517630
    platform = "steam"
    name = "Just Cause 4"
    dx = "11"                       # DirectX-versie die de game gebruikt
    status = "playable"             # native | perfect | playable | unstable | broken | untested
    rating = "B+"                   # community-rating (optioneel)
    date = "2026-08-26"
    hardware = "M2 Pro, 16 GB, macOS 26.5.1"
    engine = "wine-proton_11.0"
    graphics_stack = "gptk"         # gptk | dxmt | opengl
    render_res = "1080p"
    upscale = "fsr-quality"
    quality = "medium"
    avg_fps = 60
    low_1pct = 45
    fps_target = 60
    launch_args = ""
    notes = "..."
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from typing import Any

from . import config


@dataclass
class GameEntry:
    app_id: str
    platform: str = "steam"
    name: str = ""
    dx: str = ""
    status: str = "untested"
    rating: str = ""
    date: str = ""
    hardware: str = ""
    engine: str = ""
    graphics_stack: str = ""
    render_res: str = ""
    upscale: str = ""
    quality: str = ""
    avg_fps: int | None = None
    low_1pct: int | None = None
    fps_target: int = 60
    launch_args: str = ""
    notes: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class DatabaseError(Exception):
    pass


def load_database() -> list[GameEntry]:
    path = config.database_path()
    if not path.exists():
        return []
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise DatabaseError(f"ongeldige TOML in {path}: {exc}") from exc
    out: list[GameEntry] = []
    for g in raw.get("games", []):
        out.append(
            GameEntry(
                app_id=str(g.get("app_id", "")),
                platform=str(g.get("platform", "steam")),
                name=str(g.get("name", "")),
                dx=str(g.get("dx", "")),
                status=str(g.get("status", "untested")),
                rating=str(g.get("rating", "")),
                date=str(g.get("date", "")),
                hardware=str(g.get("hardware", "")),
                engine=str(g.get("engine", "")),
                graphics_stack=str(g.get("graphics_stack", "")),
                render_res=str(g.get("render_res", "")),
                upscale=str(g.get("upscale", "")),
                quality=str(g.get("quality", "")),
                avg_fps=g.get("avg_fps"),
                low_1pct=g.get("low_1pct"),
                fps_target=int(g.get("fps_target", 60)),
                launch_args=str(g.get("launch_args", "")),
                notes=str(g.get("notes", "")),
                raw=dict(g),
            )
        )
    return out


def get(app_id: str) -> GameEntry | None:
    for g in load_database():
        if g.app_id == str(app_id):
            return g
    return None


STATUS_EMOJI = {
    "native": "✅",
    "perfect": "🏆",
    "playable": "🟢",
    "unstable": "🟡",
    "broken": "🔴",
    "untested": "⚪",
}


def render_markdown(entries: list[GameEntry] | None = None) -> str:
    entries = entries if entries is not None else load_database()
    if not entries:
        return "*(nog geen entries in de compatibiliteitsdatabase)*"
    lines = [
        "| Game | DX | Status | Stack | Engine | Res | Upscale | Quality | FPS (avg/1%) | Datum |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for g in sorted(entries, key=lambda e: e.name.lower()):
        emoji = STATUS_EMOJI.get(g.status, "⚪")
        fps = f"{g.avg_fps}/{g.low_1pct}" if g.avg_fps is not None else "–"
        lines.append(
            f"| {g.name} | {g.dx} | {emoji} {g.status} | {g.graphics_stack or '–'} | "
            f"{g.engine or '–'} | {g.render_res or '–'} | {g.upscale or '–'} | "
            f"{g.quality or '–'} | {fps} | {g.date or '–'} |"
        )
    return "\n".join(lines)