# Sprint Backlog — gamehub-tuner

> Factory-artefact. Sprint 1 = code; Sprint 2 = handmatige tuning (gebruiker);
> Sprint 3 = community. Prioriteit: Hoog/Middel/Laag.

## Sprint 1 — Tool bouwen (deze run)

| # | User story | Acceptatiecriteria | Prio |
|---|---|---|---|
| S1.1 | Als gebruiker wil ik alle games + huidige config zien | `list` toont gamenaam, app_id, engine, graphics stack, API | Hoog |
| S1.2 | Als gebruiker wil ik een suggestie per game | `suggest <app_id>` toont compat-DB entry of generieke DX-advies + Steam-metadata | Hoog |
| S1.3 | Als gebruiker wil ik een bewezen preset toepassen | `apply-preset <app_id> <preset>` patch in-place, backup, diff; filename gelijk; valid JSON | Hoog |
| S1.4 | Als gebruiker wil ik de 60fps-ladder doorlopen | `benchmark <app_id>` print ladder-stappen + schrijft journal | Hoog |
| S1.5 | Als gebruiker wil ik een community-rapport | `report` genereert Markdown (status, rating, config, fps) | Middel |
| S1.6 | Als gebruiker wil ik een installatie-check | `doctor` detecteert draaiend GameHub, config-map, engine | Middel |
| S1.7 | Als community wil ik data bijdragen | Presets + compat-DB in TOML met comments, gevalideerd in CI | Hoog |
| S1.8 | Als ontwikkelaar wil ik tests | pytest dekt settings in-place edit, preset-merge, compat load | Middel |
| S1.9 | Als ontwikkelaar wil ik CI | GitHub Action draait tests + TOML-validatie | Middel |

## Sprint 2 — 60 fps-ladder op de 6 games (handmatig, door Said)

Doel: per game het hoogste profiel dat **stabiel 60 fps** haalt (avg ≥60, 1% lows ≥45).

Volgorde (Said's keuze): **1)** Just Cause 4 → **2)** ACE COMBAT 7 → **3)** NFS
Unbound → **4)** Battlefield 2042 (verwacht broken) → **5)** Marvel's Spider-Man 2
→ **6)** Forza Horizon 5.

| # | Game | app_id | DX | Actie | Doel-resultaat |
|---|---|---|---|---|---|
| S2.1 | Just Cause 4 | 517630 | 11 | DXMT vs GPTK, proton 11 | 60fps-profiel + DB-entry |
| S2.2 | ACE COMBAT 7 | 502500 | 11 | proton 10 (huidig) vs 11+DXMT | 60fps-profiel + DB-entry |
| S2.3 | NFS Unbound | 1846380 | 12 | GPTK, Metal4 aan/uit, RT uit | 60fps-profiel + DB-entry |
| S2.4 | Battlefield 2042 | 1517290 | 12 | Testen (Denuvo+EAC) | "broken" + DB-entry |
| S2.5 | Spider-Man 2 | 2651280 | 12 | GPTK, 16GB managen | profiel of "unstable" + DB-entry |
| S2.6 | Forza Horizon 5 | 1551360 | 12 | GPTK | 60fps-profiel + DB-entry |

Elke game: benchmark-journal invullen via `benchmark`, resultaat terug in
`database/compatibility.toml`, en waar relevant preset toevoegen.

## Sprint 3 — Community-teruggave

| # | User story | Acceptatiecriteria | Prio |
|---|---|---|---|
| S3.1 | Resultaten delen op officiële GitHub-tracker | Issues met macOS-versie, gamenaam, repro-stappen, logs | Middel |
| S3.2 | Tool + database delen in GameHub Discord | Post met README-link + eerste rapporten | Laag |
| S3.3 | Repo publiceren | Public GitHub, MIT, README compleet | Hoog |

## Niet af / openstaand
- Exacte hash-algoritme van settings-files (omzeild via ADR-1).
- Automatisch "apply preset → start game → meet fps" (vereist app-automatisering;
  out of scope v1).