"""Benchmark-journal + 60 fps-ladder.

De ladder-methodiek (zie docs/TUNING.md):
  Rung 1: render 720p, laagste quality, upscaler AAN (fsr-quality), V-sync uit, HDR uit
  Rung 2: meet -> stabiel = avg >= 60 en 1% lows >= 45
  Rung 3: niet stabiel -> upscaler performance, render 540p, RT/HDR uit
  Rung 4: stabiel -> quality-preset een trede omhoog (low -> medium -> high), hermeet
  Rung 5: quality vast -> render omhoog (720p -> 900p -> 1080p), upscaler als tegenwicht
  Rung 6: lock config -> profiel vastleggen in compat-database
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config

LADDER_STEPS = [
    ("1. Basis", "Render op 720p, laagste quality-preset, upscaler AAN (FSR Quality), V-sync uit, HDR uit, Metal HUD aan."),
    ("2. Meet", "Speel ~5 min gameplay (niet menu). Doel: avg fps >= 60 EN 1% lows >= 45 = stabiel."),
    ("3. Verlaag", "Niet stabiel? Upscaler naar Performance, render naar 540p, ray tracing/HDR uit. Hermeet."),
    ("4. Verhoog quality", "Stabiel? Quality-preset een trede omhoog (low -> medium -> high). Hermeet."),
    ("5. Verhoog resolutie", "Quality vast op hoogst stabiele punt. Render omhoog: 720p -> 900p -> 1080p."),
    ("6. Lock", "Hoogste rung met stabiele 60 fps = profiel. Leg vast in database/compatibility.toml."),
]

QUALITY_LADDER = ["low", "medium", "high", "ultra"]
RES_LADDER = ["540p", "720p", "900p", "1080p"]


@dataclass
class BenchmarkEntry:
    app_id: str
    name: str = ""
    date: str = ""
    render_res: str = ""
    upscale: str = ""
    quality: str = ""
    avg_fps: int | None = None
    low_1pct: int | None = None
    fps_target: int = 60
    notes: str = ""
    config_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "name": self.name,
            "date": self.date,
            "render_res": self.render_res,
            "upscale": self.upscale,
            "quality": self.quality,
            "avg_fps": self.avg_fps,
            "low_1pct": self.low_1pct,
            "fps_target": self.fps_target,
            "notes": self.notes,
            "config_snapshot": self.config_snapshot,
        }


def journal_path(app_id: str) -> Path:
    return config.benchmarks_dir() / f"{app_id}.json"


def save_entry(entry: BenchmarkEntry) -> Path:
    config.benchmarks_dir().mkdir(parents=True, exist_ok=True)
    p = journal_path(entry.app_id)
    entries: list[dict[str, Any]] = []
    if p.exists():
        try:
            entries = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                entries = []
        except json.JSONDecodeError:
            entries = []
    entries.append(entry.to_dict())
    p.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def load_entries(app_id: str) -> list[dict[str, Any]]:
    p = journal_path(app_id)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def render_ladder() -> str:
    return "\n".join(f"  {num}. {title}: {txt}" for num, (title, txt) in enumerate(LADDER_STEPS, 1))


def next_quality(current: str | None) -> str:
    """Eén trede omhoog in de quality-ladder."""
    if not current:
        return QUALITY_LADDER[0]
    try:
        idx = QUALITY_LADDER.index(current.lower())
    except ValueError:
        return QUALITY_LADDER[0]
    return QUALITY_LADDER[min(idx + 1, len(QUALITY_LADDER) - 1)]


def next_resolution(current: str | None) -> str:
    """Eén trede omhoog in de resolutie-ladder."""
    if not current:
        return RES_LADDER[0]
    try:
        idx = RES_LADDER.index(current.lower())
    except ValueError:
        return RES_LADDER[0]
    return RES_LADDER[min(idx + 1, len(RES_LADDER) - 1)]


def stable(avg_fps: int | None, low_1pct: int | None, target: int = 60) -> bool:
    """Stabiel = avg >= target EN 1% lows >= 0.75 * target.

    Beide metingen zijn verplicht: zonder 1% lows is een meting niet
    "stabiel" te noemen (review-bevinding 2.3).
    """
    if avg_fps is None or low_1pct is None:
        return False
    return avg_fps >= target and low_1pct >= int(target * 0.75)


def now() -> str:
    return time.strftime("%Y-%m-%d")