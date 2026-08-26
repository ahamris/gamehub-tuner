# gamehub-tuner

Tune **GameHub for Mac** (GameSir "盖世游戏") per game naar een stabiele
**60 fps**, deel bewezen presets en draag bij aan de community
compatibiliteitsdatabase.

GameHub draait Windows-games op Apple Silicon via een eigen Wine-Proton-engine
+ GPTK 3.0 / DXMT / MoltenVK. Elke game heeft een JSON-config in
`~/Library/Application Support/com.gamemac.www/gamehub/game-settings/` —
precies daar werkt deze tool op.

> ⚠️ Dit is een **community-tool**, niet gemaakt door GameSir. Gebruik op
> eigen risico; de tool maakt altijd een backup vóór wijzigen.

## Installatie

```bash
git clone git@github.com:ahamris/gamehub-tuner.git
cd gamehub-tuner
python3 --version          # vereist Python 3.11+ (macOS-systeem-python kan 3.9 zijn)
                           # -> brew install python@3.12 als het ouder is
python3 -m gamehub_tuner doctor
```

Geen pip-installatie nodig (alleen stdlib ≥3.11). Wil je het `gamehub-tuner`
commando op je PATH (zonder `python3 -m`), gebruik dan een **editable** install:
`python3 -m pip install -e .` — de presets/database blijven dan in de repo
staan. Voor tests: `python3 -m venv .venv && .venv/bin/pip install pytest &&
.venv/bin/python -m pytest`.

## Gebruik

```bash
# Overzicht van alle games + huidige config
gamehub-tuner list

# Installatie-check (GameHub draait? engines? referenties?)
gamehub-tuner doctor

# Suggestie voor een game (uit compat-DB of generiek DX-advies)
gamehub-tuner suggest 517630

# Presets bekijken
gamehub-tuner presets

# Preset toepassen (in-place, backup + diff; sluit eerst GameHub)
gamehub-tuner apply-preset 517630 dx11-dxmt
gamehub-tuner apply-preset 1846380 dx12-gptk

# 60 fps-ladder meting vastleggen
gamehub-tuner benchmark 517630 --res 1080p --quality medium --avg 62 --low 47

# Community-rapport genereren (Markdown, klaar voor Discord/GitHub)
gamehub-tuner report
```

Zonder `gamehub-tuner` op je PATH: `python3 -m gamehub_tuner ...`.

## Hoe het werkt

- **Lezen** — parse de game-settings JSON (schema v2) per app_id.
- **Presets** (`presets/*.toml`) — community-editable TOML met de bewezen
  combinaties (`dx11-dxmt`, `dx12-gptk`, `proton10-legacy`, `benchmark-mode`, ...).
- **Toepassen** — patcht de settings **in-place** (filename/hash blijft gelijk,
  zie ADR-1 in `docs/Requirements.md`), maakt een backup en toont de diff.
  Engine- en graphics-stack-configs worden gekopieerd van een referentie die al
  in je installatie bestaat — we schrijven nooit data die we niet gezien hebben.
- **60 fps-ladder** — `docs/TUNING.md` beschrijft de methodiek: render 720p +
  upscaler → meten (Metal HUD) → quality omhoog → resolutie omhoog.

## Repository-structuur

```
gamehub_tuner/          # CLI (zero-dependency, Python 3.11+)
presets/*.toml          # bewezen per-game/algemene presets
database/compatibility.toml  # community compatibiliteitsdatabase
database/steam-cache.json    # Steam API cache (automatisch)
benchmarks/<app_id>.json     # benchmark-journals (automatisch)
docs/TUNING.md          # de 60 fps-ladder + per-game kennis
docs/Requirements.md    # requirements + ADR-1
docs/sprint_backlog.md  # backlog
tests/                  # pytest
```

## Community-database bijdragen

Open `database/compatibility.toml`, kopieer een `[[games]]`-entry, vul
status/hardware/config/fps in en open een PR. Zie `docs/TUNING.md`.

Status-waarden: `native` · `perfect` · `playable` · `unstable` · `broken` ·
`untested`. FPS-doel: avg ≥60 en 1% lows ≥45 = stabiel.

## License

MIT — zie [LICENSE](LICENSE). Vrij te gebruiken, delen en verbeteren.