# TUNING.md — GameHub 60 fps-ladder

De doelstelling van dit project: per game de **hoogste instellingen** vinden
die **stabiel 60 fps** halen (gemiddelde ≥60, 1% lows ≥45) op een M2 Pro
(16 GB, macOS 26.5.1). Eerst werkbaar, daarna pas omhoog.

## De knopjes die GameHub per game biedt

Deze zitten in de game-settings JSON
(`~/Library/Application Support/com.gamemac.www/gamehub/game-settings/`):

| Setting | Betekenis | Advies |
|---|---|---|
| `compatibility_layer` | Wine-engine (proton 11 / proton 10 / ...) | Start op 11.0; 10.0 bij regressies |
| `graphics_stack` | `gptk` (D3DMetal) / `dxmt` / `opengl` | **DX11 → DXMT**, **DX12 → GPTK** |
| `sync_mode` | `msync` / `esync` | Blijf op `msync` |
| `avx_enabled` | AVX-emulatie (rosetta_x87) | Aan als game crasht met "illegal instruction"; kost CPU |
| `bypass_av_decode` | Skip CGs (zwart beeld) | Aan bij hangende introvideo's |
| `metal_hud_enabled` | Metal HUD (FPS/GPU-overlay) | Aan tijdens benchmarken, uit daarna |
| `metal4_enabled` | Metal 4 | Experimenteel; test bij DX12 |
| `retina_mode` | HiDPI-scalen | Uit tijdens de ladder (perf) |
| `dlss_mode` | Upscaling-modus | `quality`/`performance` = FSR-achtig; gebruik als ladder-hefboom |
| `ray_tracing_mode` | RT | Altijd uit onder translatie (kost veel) |
| `dxmt_experimental_dx12_support` | DXMT DX12 | Alleen voor testen |
| `start_parameters` | Launch-args | Per game, zie database |

## De 60 fps-ladder (per game)

1. **Basis** — render op 720p, laagste quality-preset, upscaler AAN
   (FSR Quality), V-sync uit, HDR uit, Metal HUD aan.
2. **Meet** — ~5 min echte gameplay (niet het menu). Doel: avg ≥60 én
   1% lows ≥45 = stabiel.
3. **Niet stabiel?** — upscaler naar Performance, render naar 540p,
   ray tracing/HDR uit. Hermeet.
4. **Stabiel?** — quality-preset één trede omhoog
   (low → medium → high), hermeet.
5. **Quality vast** — render-resolutie omhoog (720p → 900p → 1080p),
   upscaler-kwaliteit als tegenwicht.
6. **Lock** — hoogste rung met stabiele 60 fps = profiel. Leg vast in
   `database/compatibility.toml` en in het benchmark-journal.

Op elk moment: `gamehub-tuner benchmark <app_id> --avg N --low N --res ... --quality ...`
om een meting vast te leggen.

## Systeem-tips (M2 Pro / 16 GB)

- **macOS Game Mode aan** (menu → opties, of automatisch bij fullscreen).
- **Sluit browsers/andere apps** — 16 GB is de grootste bottleneck bij DX12.
- **Thermals**: M2 Pro klokt af bij langdurige belasting; zorg voor goede airflow.
- **Metal HUD**: `gamehub-tuner apply-preset <app_id> benchmark-mode` voor de meting,
  daarna terug naar het profiel (HUD kost een paar fps).
- **Eerste launch** duurt lang (shader-compilatie). Meet pas ná de eerste minuut.

## Per-game kennis (stand 2026-08-26)

### Just Cause 4 (517630, DX11) — 🟢 playable
- Draait netjes (laatste log exit 0). Profiel: proton 11 + GPTK, 1080p medium.
- **Volgende test:** DXMT-variant (`dx11-dxmt`) — DX11 is vaak sneller op DXMT.

### ACE COMBAT 7 (502500, DX11) — ⚪ waarschuwing
- Geconfigureerd op **wine-proton_10.0**, maar die engine is **niet lokaal
  geïnstalleerd** (alleen 11.0). Vóór het testen: proton 10 installeren in
  GameHub, óf preset naar 11.0 toepassen.

### NFS Unbound (1846380, DX12) — ⚪ untested
- Frostbite. Ladder: 720p + FSR, RT uit. `gptk-metal4`-variant testen.

### Battlefield 2042 (1517290, DX12) — 🔴 verwacht broken
- Denuvo + Easy Anti-Cheat werken niet onder Wine/GPTK. Test ter bevestiging
  en documenteer. (Gratis community-waarde: bespaart anderen de download van ~100 GB.)

### Marvel's Spider-Man 2 (2651280, DX12) — ⚪ untested
- Zware Nixxes-port. 16 GB is krap. Verwacht: 720p/900p medium, 60 fps is
  ambitieus. Heeft ingebouwde FSR/DLSS.

### Forza Horizon 5 (1551360, DX12) — ⚪ untested
- Goed gedocumenteerd in de GPTK-community. Ladder: 720p + FSR, daarna omhoog.

## Bijdragen aan de database

1. Kopieer een bestaande `[[games]]`-entry in `database/compatibility.toml`.
2. Vul app_id, status, hardware, engine/stack, res/quality en fps in.
3. `gamehub-tuner doctor` + `gamehub-tuner report` om te controleren.
4. PR openen (of post de entry in de GameHub Discord).