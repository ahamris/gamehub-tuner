# Build Manifest — gamehub-tuner v0.1.0

> Factory-artefact (BUILD-agent). Sprint 1 opgeleverd: CLI + presets +
> compat-DB + tests + CI. Review doorlopen (Code Reviewer) en alle
> blokkerende/belangrijke bevindingen opgelost.

## Overzicht gewijzigde/nieuwe bestanden

| Laag | Bestand | Toelichting |
|---|---|---|
| CLI | `gamehub_tuner/__init__.py` | Versie 0.1.0 |
| CLI | `gamehub_tuner/__main__.py` | `python3 -m` entry met correcte exit-code |
| CLI | `gamehub_tuner/cli.py` | Commando's: `list`, `presets`, `suggest`, `apply-preset` (incl. `--dry-run`/`--yes`), `benchmark`, `report`, `doctor`, `--version` |
| CLI | `gamehub_tuner/settings.py` | Lezen/patchen van game-settings JSON; in-place met backup; engine-guard fail-closed; settings-whitelist; schema-guard; fsync |
| CLI | `gamehub_tuner/presets.py` | TOML-preset loader (stdlib `tomllib`) |
| CLI | `gamehub_tuner/compat.py` | Compat-DB loader + Markdown-render |
| CLI | `gamehub_tuner/steam.py` | Steam API lookup met cache; HTML-tolerante DX/opslag-detectie |
| CLI | `gamehub_tuner/benchmark.py` | 60 fps-ladder, journal, stable()-berekening |
| CLI | `gamehub_tuner/config.py` | Paden, env-overrides, GameHub-procesdetectie, robuuste repo-dir |
| Data | `presets/*.toml` (8) | `dx11-dxmt`, `dx12-gptk`, `proton10-legacy`, `max-fps-720p`, `stability-avx`, `skip-avdecode`, `benchmark-mode`, `gptk-metal4` |
| Data | `database/compatibility.toml` | 6 games geseed (JC4 playable, BF2042 broken, 4 untested) |
| Tests | `tests/test_settings.py` | 13 tests: in-place patch, backup, engine-guard (fail-closed), whitelist, dry-run, schema |
| Tests | `tests/test_core.py` | presets, compat-DB, ladder, journal |
| Tests | `tests/test_cli.py` | exit-codes, nette fouten, dry-run, doctor |
| Tests | `tests/test_steam.py` | HTML-tolerant DX/Storage-detectie |
| CI | `.github/workflows/ci.yml` | pytest op 3.11–3.13 + data-validatie |
| CI | `scripts/validate_data.py` | TOML + status/duplicate-app_id validatie |
| Docs | `docs/Requirements.md` | Requirements + ADR-1 |
| Docs | `docs/sprint_backlog.md` | Backlog S1/S2/S3 |
| Docs | `docs/TUNING.md` | De 60 fps-ladder + per-game kennis |
| Docs | `README.md`, `LICENSE` | MIT, installatie, gebruik |

## Review-afhandeling (Code Reviewer)

| Bevinding | Categorie | Oplossing |
|---|---|---|
| Engine-guard fail-open bij ontbrekend installaties-bestand | BLOKKEREND | `_ensure_engine_installed` nu fail-closed; `install_status != completed` telt niet |
| Scalar-overrides schreven ongevalideerde keys | BLOKKEREND | `KNOWN_SETTINGS_KEYS`-whitelist; onbekende key → `SettingsError` zonder write |
| `python3 -m` gaf altijd exit 0 | BELANGRIJK | `sys.exit(main())` in `__main__.py` |
| DX-detectie-regex matchte nooit op Steam-HTML | BELANGRIJK | HTML-tolerante regex (`DirectX.*?Version`), tests erbij |
| `stable(60, None)` = True (valse stabiliteit) | BELANGRIJK | 1% lows nu verplicht |
| Onbekende preset gaf traceback | BELANGRIJK | Nette `Fout:` + exit 1 |
| Schema-validatie beloofd maar afwezig | BELANGRIJK | `SCHEMA_VERSION`-guard op read + patch |
| `.gitignore` dekte steam-cache niet (persoonlijke data) | BELANGRIJK | `database/steam-cache.json` + `benchmarks/*.json` genegeerd |
| pip install claim / data niet in wheel | BELANGRIJK | README: `pip install -e .` of `python3 -m`; `repo_dir()` robuust |
| Backups: timestamp-collisie, geen fsync, vaste tmp | NITPICK | ms-timestamp, `os.fsync`, unieke tmp (`pid`) |
| Geen CLI/Steam/edge-tests + brittle counts | BELANGRIJK | +16 tests; counts → subset/minimum |

## Nieuwe "entiteiten" (data-schema's)

- **Preset-schema** (TOML): `name`, `description`, optioneel `engine` /
  `graphics_stack`, en `[settings]` (alleen keys in de whitelist).
- **Compat-DB-entry** (TOML `[[games]]`): `app_id`, `platform`, `name`, `dx`,
  `status`, `rating`, `date`, `hardware`, `engine`, `graphics_stack`,
  `render_res`, `upscale`, `quality`, `avg_fps`, `low_1pct`, `fps_target`,
  `launch_args`, `notes`.
- **Benchmark-journal** (JSON): per game een lijst van metingen met
  `render_res`, `upscale`, `quality`, `avg_fps`, `low_1pct`, `config_snapshot`.

## Configuratiewijzigingen

Geen — de tool is zero-dependency (Python 3.11+ stdlib). Dev-deps alleen in
`.venv` (pytest). Geen `.env`, geen secrets in de repo.

## Niet af / openstaande punten (Sprint 2+3)

1. **Handmatige tuning** (Sprint 2, door gebruiker): de 60 fps-ladder op
   JC4/AC7/NFS Unbound eerst, daarna BF2042 (verwacht broken), Spider-Man 2,
   Forza Horizon 5. Resultaten terug in `database/compatibility.toml` +
   `benchmarks/`.
2. **AC7/NFS Heat blokkade**: beide configs verwijzen naar wine-proton_10.0
   die niet geïnstalleerd is. Engine installeren in GameHub of preset naar 11.0.
3. **Hash-algoritme settings-files** nog niet gekraakt (omzeild via ADR-1,
   in-place edits). Heropenen als de app in-place edits negeert.
4. **Community-teruggave** (Sprint 3): Discord joinen, issues/PR's op
   `gamesir-labs/gamehub-for-mac`, tool delen.