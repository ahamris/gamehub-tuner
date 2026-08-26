"""Command-line interface voor gamehub-tuner."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import benchmark, compat, config, presets, settings, steam

APP = "gamehub-tuner"


def _print_table(rows: list[list[str]]) -> None:
    widths = [max(len(str(c)) for c in col) for col in zip(*rows)]
    for row in rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))


def cmd_list(_args: argparse.Namespace) -> int:
    files = settings.settings_files()
    bindings = settings.bindings_map()
    installed = settings.installed_engine_ids()
    if not files:
        print("Geen game-settings gevonden in", config.settings_dir())
        return 1
    rows = [["APP_ID", "GAME", "ENGINE", "STACK", "API", "SYNC"]]
    for f in files:
        prof = f.current_profile()
        engine = prof["engine"] or "-"
        eid = str(f.settings.get("compatibility_layer", ""))
        if installed and eid and eid not in installed:
            engine += " (NIET GEINSTALLEERD)"
        rows.append(
            [
                f.app_id,
                bindings.get(f.app_id, f.game_id),
                engine,
                prof["graphics_stack"] or "-",
                prof["graphic_api"] or "-",
                prof["sync_mode"] or "-",
            ]
        )
    _print_table(rows)
    return 0


def cmd_presets(_args: argparse.Namespace) -> int:
    items = presets.list_presets()
    if not items:
        print("Geen presets gevonden in", config.presets_dir())
        return 1
    rows = [["PRESET", "ENGINE", "STACK", "BESCHRIJVING"]]
    for p in items:
        rows.append([p.name, p.engine or "-", p.graphics_stack or "-", p.description])
    _print_table(rows)
    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    app_id = str(args.app_id)
    try:
        entry = compat.get(app_id)
    except compat.DatabaseError as exc:
        print(f"Fout in compat-database: {exc}")
        entry = None

    # Game-naam: compat-DB, bindings, of Steam.
    name = entry.name if entry and entry.name else settings.bindings_map().get(app_id, "")
    dx = entry.dx if entry and entry.dx else ""
    details: dict[str, Any] = {}
    try:
        details = steam.fetch_app_details(app_id)
        if not name:
            name = details.get("name", app_id)
        if not dx:
            dx = steam.detect_dx_version(details)
    except steam.SteamError as exc:
        print(f"! {exc}")

    print(f"Game: {name} (Steam {app_id}, DX {dx or '?'})")
    if entry:
        print()
        print(f"  Status:     {entry.status} ({compat.STATUS_EMOJI.get(entry.status, '')})")
        print(f"  Rating:     {entry.rating or '-'}")
        print(f"  Engine:     {entry.engine or '-'}")
        print(f"  Stack:      {entry.graphics_stack or '-'}")
        print(f"  Res:        {entry.render_res or '-'} @ {entry.quality or '-'} ({entry.upscale or '-'})")
        print(f"  FPS:        {entry.avg_fps or '-'}/{entry.low_1pct or '-'} (target {entry.fps_target})")
        print(f"  Datum:      {entry.date or '-'} op {entry.hardware or '-'}")
        if entry.launch_args:
            print(f"  LaunchArgs: {entry.launch_args}")
        if entry.notes:
            print(f"  Notities:   {entry.notes}")
        return 0

    # Generiek advies obv DX-versie + hardware.
    print()
    if dx.startswith("12"):
        print("  Advies (DX12):")
        print("    - Preset:   dx12-gptk  (GPTK 3.0, proton 11)")
        print("    - Start op  720p + FSR Quality, ladder omhoog naar 60 fps.")
        print("    - Let op:   16 GB RAM is krap; sluit browsers. RT uit.")
        print("    - Zet nadien de meting vast met: gamehub-tuner benchmark", app_id)
    elif dx.startswith("11"):
        print("  Advies (DX11):")
        print("    - Preset:   dx11-dxmt  (DXMT is doorgaans sneller dan GPTK voor DX11)")
        print("    - Start op  720p + FSR Quality, ladder omhoog naar 60 fps.")
        print("    - Mocht het crashen: probeer proton 10 (engine wine-proton_10.0).")
    else:
        print("  Advies:")
        print("    - Probeer eerst dx11-dxmt; als de game DX12 is, dx12-gptk.")
        print("    - Bepaal de DX-versie op de Steam store-pagina van de game.")
    return 0


def cmd_apply_preset(args: argparse.Namespace) -> int:
    app_id = str(args.app_id)
    try:
        preset = presets.load_preset(args.preset)
    except settings.SettingsError as exc:
        print(f"Fout: {exc}")
        return 1

    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, app_id)
    if sf is None:
        print(
            f"Geen settings-bestand voor app_id {app_id} gevonden.\n"
            f"Importeer de game eerst in GameHub (Library -> game -> config), daarna opnieuw."
        )
        return 1

    if config.is_gamehub_running() and not args.yes:
        print(
            "GameHub draait. Sluit GameHub eerst (anders kan het de patch overschrijven),\n"
            "of forceer met: --yes"
        )
        return 1

    refs = settings.find_references(files)
    print(f"Preset '{preset.name}' op app {app_id} ({sf.path.name})")
    print(f"  beschrijving: {preset.description}")
    if args.dry_run:
        print("  (dry-run: er wordt NIETS geschreven)")

    try:
        changes = settings.patch_settings(
            sf,
            scalar_overrides=preset.scalar_overrides(),
            engine=preset.engine,
            graphics_stack=preset.graphics_stack,
            refs=refs,
            dry_run=args.dry_run,
        )
    except settings.SettingsError as exc:
        print(f"Fout: {exc}")
        return 1
    except OSError as exc:
        print(f"Fout bij schrijven: {exc}")
        return 1

    if not changes:
        print("  Geen wijzigingen nodig (config is al gelijk aan preset).")
        return 0
    if not args.dry_run:
        print("  Backup gemaakt (zelfde map, .bak-<timestamp>).")
    print("  Wijzigingen:")
    for c in changes:
        print(f"    - {c}")
    if args.dry_run:
        print("  Voer opnieuw uit zonder --dry-run om toe te passen.")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    app_id = str(args.app_id)
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, app_id)
    prof = sf.current_profile() if sf else {}
    name = settings.bindings_map().get(app_id, sf.game_id if sf else app_id)

    entry = benchmark.BenchmarkEntry(
        app_id=app_id,
        name=name,
        date=benchmark.now(),
        render_res=args.res or "",
        upscale=args.upscale or "",
        quality=args.quality or "",
        avg_fps=args.avg,
        low_1pct=args.low,
        notes=args.notes or "",
        config_snapshot=prof,
    )

    print(f"Benchmark {name} (Steam {app_id})")
    print("Huidige config:", json.dumps(prof, ensure_ascii=False) if prof else "niet gevonden")
    print()
    print("60 fps-ladder:")
    print(benchmark.render_ladder())
    print()

    if entry.avg_fps is not None:
        p = benchmark.save_entry(entry)
        ok = benchmark.stable(entry.avg_fps, entry.low_1pct, entry.fps_target)
        print(f"Meting vastgelegd: {entry.avg_fps} avg / {entry.low_1pct or '-'} 1% lows "
              f"(target {entry.fps_target}) -> {'STABIEL ✅' if ok else 'NIET STABIEL ❌'}")
        if ok:
            print(f"Volgende rung: quality omhoog naar '{benchmark.next_quality(entry.quality)}' "
                  f"of resolutie naar '{benchmark.next_resolution(entry.render_res)}'.")
        else:
            print("Volgende rung: upscaler naar Performance / render naar 540p / RT+HDR uit.")
        print("Journal:", p)
        print("Tip: leg het profiel vast in database/compatibility.toml als het stabiel is.")
    else:
        print("Geen meting gegeven. Draai bv.:")
        print(f"  {APP} benchmark {app_id} --res 720p --upscale fsr-quality --quality low --avg 63 --low 48")
    return 0


def _hardware_label() -> str:
    import platform
    import subprocess

    try:
        mem = int(
            subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
        ) // (1024**3)
    except Exception:
        mem = 0
    chip = platform.machine()
    return f"{chip}, {mem} GB, macOS" if mem else f"{chip}, macOS"


def cmd_report(_args: argparse.Namespace) -> int:
    try:
        entries = compat.load_database()
    except compat.DatabaseError as exc:
        print(f"Fout in compat-database: {exc}")
        return 1
    print("# GameHub compatibility-report")
    print()
    print(f"Generatie: {benchmark.now()}  |  hardware: {_hardware_label()}")
    print()
    print("## Compatibiliteitsdatabase")
    print(compat.render_markdown(entries))
    print()
    print("## Benchmark-journals")
    bench_files = sorted(config.benchmarks_dir().glob("*.json")) if config.benchmarks_dir().exists() else []
    if not bench_files:
        print("*(geen metingen)*")
    else:
        for p in bench_files:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            last = data[-1] if isinstance(data, list) and data else {}
            if not last:
                continue
            print(f"- {last.get('name', p.stem)}: {last.get('render_res','?')} @ {last.get('quality','?')} "
                  f"-> {last.get('avg_fps','?')} fps avg / {last.get('low_1pct','?')} 1% lows ({last.get('date','')})")
    print()
    print("## Methodiek")
    print("Doel: hoogste instellingen bij stabiele 60 fps (avg >= 60, 1% lows >= 45).")
    print("Ladder: 720p low + upscaler -> meten -> quality omhoog -> resolutie omhoog.")
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    issues = 0
    print("gamehub-tuner doctor")
    print("--------------------")

    if config.is_gamehub_running():
        print("⚠  GameHub draait — sluit het voor apply-preset.")
    else:
        print("✅ GameHub draait niet (goed voor presets).")

    sd = config.settings_dir()
    if sd.exists():
        n = len(settings.settings_files())
        print(f"✅ Settings-map gevonden ({n} games): {sd}")
    else:
        print(f"❌ Settings-map niet gevonden: {sd}")
        issues += 1

    engines = settings.list_installed_engines()
    if engines:
        print("✅ Wine-engines:")
        for e in engines:
            default = " (default)" if e["is_default"] else ""
            print(f"   - {e['name']} [{e['id']}]{default}")
    else:
        print("❌ Geen Wine-engines gevonden.")
        issues += 1

    files = settings.settings_files()
    referenced = settings.referenced_engine_ids(files)
    installed = settings.installed_engine_ids()
    missing = {eid: n for eid, n in referenced.items() if eid not in installed}
    if missing:
        print("⚠  Games verwijzen naar NIET-geïnstalleerde engines:")
        for eid, n in sorted(missing.items()):
            print(f"   - engine {eid} (gebruikt door {n} game(s)) — engine eerst installeren!")
        issues += 1
    else:
        print("✅ Alle gerefereerde engines zijn geïnstalleerd.")

    comps = settings.list_installed_components()
    if comps:
        print("✅ Graphics-componenten:")
        for c in comps:
            print(f"   - {c['display_name']} [{c['id']}] ({c['status']})")
    else:
        print("ℹ  Geen losse graphics-componenten (DXMT is builtin).")

    if config.database_path().exists():
        try:
            n = len(compat.load_database())
            print(f"✅ Compat-database: {n} entries")
        except compat.DatabaseError as exc:
            print(f"⚠  Compat-database: {exc}")
            issues += 1
    else:
        print("ℹ  Compat-database nog niet aangemaakt.")

    return 0 if issues == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    from . import __version__

    parser = argparse.ArgumentParser(
        prog=APP,
        description="Tune GameHub-for-Mac per-game settings + 60 fps-ladder + community-reports.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Toon alle games + huidige config")
    sub.add_parser("presets", help="Toon beschikbare presets")
    sub.add_parser("report", help="Genereer Markdown community-rapport")
    sub.add_parser("doctor", help="Check de GameHub-installatie")

    p = sub.add_parser("suggest", help="Suggestie voor een game")
    p.add_argument("app_id")

    p = sub.add_parser("apply-preset", help="Pas een preset toe (in-place, backup)")
    p.add_argument("app_id")
    p.add_argument("preset")
    p.add_argument("--yes", action="store_true", help="Forceer ondanks draaiend GameHub")
    p.add_argument("--dry-run", action="store_true", help="Toon wijzigingen zonder te schrijven")

    p = sub.add_parser("benchmark", help="60 fps-ladder: meet en leg vast")
    p.add_argument("app_id")
    p.add_argument("--res", help="render-resolutie (540p/720p/900p/1080p)")
    p.add_argument("--upscale", help="upscale-modus (bv. fsr-quality, fsr-performance)")
    p.add_argument("--quality", help="quality-preset (low/medium/high/ultra)")
    p.add_argument("--avg", type=int, help="gemiddelde fps (Metal HUD)")
    p.add_argument("--low", type=int, help="1%% lows (Metal HUD)")
    p.add_argument("--notes", help="notities")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dispatch = {
        "list": cmd_list,
        "presets": cmd_presets,
        "suggest": cmd_suggest,
        "apply-preset": cmd_apply_preset,
        "benchmark": cmd_benchmark,
        "report": cmd_report,
        "doctor": cmd_doctor,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())