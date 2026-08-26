# gamehub-tuner — Requirements

> Factory-artefact (PM + Architect). Versie 1.0 — 2026-08-26.

## 1. Probleem / context

GameHub (GameSir "盖世游戏", `com.gamemac.www`, macOS-bèta) draait Windows-games
op Apple Silicon via een eigen Wine-Proton-engine + GPTK 3.0 / DXMT / MoltenVK.
Per game slaat de app een JSON-config op in
`~/Library/Application Support/com.gamemac.www/gamehub/game-settings/<hash>.json`.

De community (Discord + GitHub-issue-tracker) deelt tips en compatibiliteit,
maar er is **geen gestandaardiseerde manier** om:
- per game een "60 fps-profiel" vast te leggen (hoogste instellingen bij 60 fps);
- presets te delen/toe te passen;
- compatibiliteitsrapporten te genereren.

## 2. Doel

Een open-source CLI (`gamehub-tuner`, MIT) die:

1. De huidige GameHub-config per game inzichtelijk maakt (`list`);
2. Per game een config **suggereert** op basis van een community
   compatibiliteitsdatabase + Steam-metadata (`suggest`);
3. Bewezen **presets toepast** (in-place JSON-patch, met backup) (`apply-preset`);
4. De **60 fps-ladder** begeleidt en metingen vastlegt (`benchmark`);
5. Een **compatibiliteitsrapport** genereert klaar voor Discord/GitHub (`report`);
6. Sanity-checks doet op de installatie (`doctor`).

## 3. Scope

**In scope (v1.0)**
- Lezen/schrijven van GameHub `game-settings` JSON (in-place, filename behouden).
- Preset-bibliotheek (TOML, community-editable) + compat-database (TOML).
- Steam Store API lookup met lokale cache (voor gamenaam + DX-versie).
- Benchmark-journal (JSON) + Markdown-rapport.
- Zero-runtime-dependencies (Python 3.11+ stdlib).
- Tests (pytest) + GitHub Action CI.

**Buiten scope**
- Reverse-engineering van de `stable_game_key_hash` (werken we omzeilt door
  in-place edits; zie ADR-1).
- GUI; het blijft een CLI.
- Automatisch games installeren/starten binnen GameHub.
- Wijzigen van de Wine-engine-binary's zelf.

## 4. Acceptatiecriteria

| # | Criterium |
|---|---|
| AC-1 | `gamehub-tuner list` toont alle games met huidige engine, graphics stack en API. |
| AC-2 | `gamehub-tuner apply-preset 517630 dx11-dxmt` past de config in-place aan, maakt backup en toont diff; filename blijft gelijk. |
| AC-3 | Preset-toepassing beschadigt geen JSON: na toepassing is het bestand valide en bevat alle oorspronkelijke velden (behalve de gepatchte). |
| AC-4 | `benchmark` schrijft een journal-entry met de ladder-parameters (render_res, upscale, quality, avg_fps, low_1pct). |
| AC-5 | `report` genereert Markdown met per game: status, rating, hardware, config, fps-metingen. |
| AC-6 | Tool draait op macOS met Python 3.11+ zonder pip-installatie van dependencies (alleen stdlib). |
| AC-7 | `doctor` detecteert: GameHub draait niet, config-map ontbreekt, geen engine geïnstalleerd. |
| AC-8 | CI draait tests + valideert alle TOML-data. |

## 5. Risico's

| Risico | Impact | Mitigatie |
|---|---|---|
| GameHub overschrijft config bij draaien | Middel | `apply-preset` waarschuwt als GameHub-process actief is; `doctor` checkt. |
| Hash van settings-file niet gekraakt | Hoog | ADR-1: in-place edit, filename behouden. |
| App wijzigt JSON-schema | Middel | Tool valideert schema; bij onbekend schema: weigeren met duidelijke melding. |
| Steam API rate-limit | Laag | Lokale cache + offline fallback. |
| 16 GB RAM bottleneck DX12-titels | n.v.t. (hardware) | TUNING.md geeft systeemtips. |

## 6. Planning (sprint-indicatie)

- Sprint 1 (deze run): CLI v0.1 + presets + compat-DB seed + tests + CI + docs.
- Sprint 2 (handmatig, door gebruiker): 60 fps-ladder uitvoeren op 6 games,
  resultaten terugvoeren in `database/compatibility.toml` + benchmarks/.
- Sprint 3: community-teruggave (GitHub issues, Discord-post) + tool delen.

## 7. ADR-1 — Settings-hash niet schrijven

De filename van settings-files is een hash (sha256-achtig) van de `key`; de
exacte canonicalisatie is niet gekraakt (getest 2026-08-26). Omdat de `key`
niet verandert wanneer alleen `settings` wijzigen, **patchen we in-place** en
behouden we de filename. Dit omzeilt hash-writing volledig en is veiliger dan
nieuwe bestanden genereren.

**Besluit:** in-place patch met backup. Heropen alleen als de app in-place
edits blijkt te negeren.