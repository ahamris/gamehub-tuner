"""Valideer alle data-bestanden (presets + compat-database) die CI draait."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors = 0
    files = sorted((ROOT / "presets").glob("*.toml")) + [
        ROOT / "database" / "compatibility.toml"
    ]
    for p in files:
        try:
            tomllib.loads(p.read_text(encoding="utf-8"))
            print(f"OK   {p.relative_to(ROOT)}")
        except tomllib.TOMLDecodeError as exc:
            print(f"FAIL {p.relative_to(ROOT)}: {exc}")
            errors += 1

    # sanity: compat-database velden + dubbele app_ids
    try:
        raw = tomllib.loads((ROOT / "database" / "compatibility.toml").read_text(encoding="utf-8"))
        valid_status = {"native", "perfect", "playable", "unstable", "broken", "untested"}
        seen: set[str] = set()
        for g in raw.get("games", []):
            app_id = str(g.get("app_id", ""))
            if not app_id:
                print("FAIL game zonder app_id")
                errors += 1
                continue
            if app_id in seen:
                print(f"FAIL game {app_id}: dubbele app_id")
                errors += 1
            seen.add(app_id)
            status = g.get("status", "untested")
            if status not in valid_status:
                print(f"FAIL game {app_id}: ongeldige status '{status}'")
                errors += 1
    except tomllib.TOMLDecodeError as exc:
        print(f"FAIL database parse: {exc}")
        errors += 1

    print(f"{'PASS' if errors == 0 else 'FAIL'} — {errors} fouten")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())