"""Pytest-fixtures: sandbox GameHub-map + repo-data via env-vars."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import gamehub_tuner.config as config
import gamehub_tuner.presets as presets
import gamehub_tuner.compat as compat


@pytest.fixture()
def fake_gamehub(tmp_path: Path, monkeypatch):
    """Zet een nep GameHub-map + nep-repo-data op en wijst env-vars erop.

    - gamehub/game-settings: 3 settings-files (JC4-op-gptk, AC7-op-dxmt/proton10,
      NFS-op-gptk) + game_container_store.json.
    - wine-engine/container/wine_installations.json: alleen proton 11.
    - repo: presets/ en database/compatibility.toml gekopieerd van de echte repo.
    """
    root = tmp_path
    gh_dir = root / "com.gamemac.www" / "gamehub"
    wine_dir = root / "com.gamemac.www" / "wine-engine"
    (gh_dir / "game-settings").mkdir(parents=True)
    (wine_dir / "container").mkdir(parents=True)

    def make_settings(fname: str, app_id: str, game_id: str, engine_id: str, engine_name: str, stack_kind: str, stack_block: dict, api: str) -> Path:
        data = {
            "schema_version": 2,
            "key": {"kind": "platform", "platform": "steam", "platform_app_id": app_id, "game_id": game_id},
            "settings": {
                "language": "system",
                "start_parameters": "",
                "compatibility_layer": engine_id,
                "compatibility_layer_config": {
                    "display_name": engine_name,
                    "framework": "X64",
                    "framework_type": "proton",
                    "id": int(engine_id),
                    "is_steam": 1,
                    "name": engine_name,
                    "version": "1.0.0",
                    "version_code": 1,
                },
                "sync_mode": "msync",
                "bypass_av_decode": False,
                "avx_enabled": False,
                "graphics_stack": stack_block,
                "dlss_mode": "disabled",
                "ray_tracing_mode": "auto",
                "metal_hud_enabled": False,
                "graphic_api": api,
            },
        }
        p = gh_dir / "game-settings" / fname
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    gptk_block = {"kind": "gptk", "component_id": "10000085"}
    dxmt_block = {"kind": "dxmt", "component_id": "10000163"}
    make_settings("aa11.json", "517630", "112146", "10000073", "wine-proton_11.0", "gptk", gptk_block, "DirectX 11.0")
    make_settings("bb22.json", "502500", "10523", "10000033", "wine-proton_10.0", "dxmt", dxmt_block, "DirectX 11.0")
    make_settings("cc33.json", "1846380", "96668", "10000073", "wine-proton_11.0", "gptk", gptk_block, "DirectX 12.0")

    (gh_dir / "game_container_store.json").write_text(
        json.dumps({"schema_version": 3, "bindings": [
            {"platform_app_id": "517630", "game_name": "Just Cause 4 Reloaded"},
            {"platform_app_id": "1846380", "game_name": "Need for Speed Unbound"},
        ]}),
        encoding="utf-8",
    )
    (wine_dir / "container" / "wine_installations.json").write_text(
        json.dumps({"wine_installations": {
            "10000073": {"id": "10000073", "name": "wine-proton_11.0", "version_code": 20, "is_default": True, "install_status": "completed"},
        }}),
        encoding="utf-8",
    )

    # repo-data (presets + compat-database) kopiëren
    repo_tmp = root / "repo"
    repo_tmp.mkdir()
    shutil.copytree(config.presets_dir(), repo_tmp / "presets")
    shutil.copytree(config.database_path().parent, repo_tmp / "database")

    monkeypatch.setenv("GAMEHUB_DIR", str(gh_dir))
    monkeypatch.setenv("GAMEHUB_WINE_DIR", str(wine_dir))
    monkeypatch.setenv("GAMEHUB_REPO_DIR", str(repo_tmp))

    # herlaad evt. gecachte modules state
    return {"root": root, "gh_dir": gh_dir, "wine_dir": wine_dir, "repo": repo_tmp}