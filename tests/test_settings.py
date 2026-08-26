"""Tests voor settings lezen/patchen (in-place)."""

from __future__ import annotations

import json

import pytest

from gamehub_tuner import config, settings


def test_settings_files_leest_3(fake_gamehub):
    files = settings.settings_files()
    assert len(files) >= 3
    app_ids = {f.app_id for f in files}
    # De 3 bekende apps moeten erin zitten; community kan er later meer aan toevoegen.
    assert {"517630", "502500", "1846380"} <= app_ids


def test_bindings_map(fake_gamehub):
    bindings = settings.bindings_map()
    assert bindings["517630"] == "Just Cause 4 Reloaded"
    assert bindings["1846380"] == "Need for Speed Unbound"


def test_find_references(fake_gamehub):
    files = settings.settings_files()
    engine_refs, graphics_refs = settings.find_references(files)
    assert "10000073" in engine_refs
    assert "10000033" in engine_refs
    assert engine_refs["10000073"]["display_name"] == "wine-proton_11.0"
    assert set(graphics_refs) == {"gptk", "dxmt"}


def test_patch_settings_in_place_backup_en_filename_behouden(fake_gamehub):
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "517630")
    assert sf is not None
    before_name = sf.path.name

    refs = settings.find_references(files)
    changes = settings.patch_settings(
        sf,
        scalar_overrides={"sync_mode": "esync", "metal_hud_enabled": True},
        graphics_stack="dxmt",
        refs=refs,
    )
    assert "sync_mode: 'msync' -> 'esync'" in changes
    assert "metal_hud_enabled: False -> True" in changes
    assert any("graphics_stack" in c for c in changes)

    # filename blijft gelijk
    assert sf.path.name == before_name
    # backup gemaakt
    backups = list(config.backups_dir().glob(f"{sf.path.stem}.bak-*"))
    assert len(backups) == 1
    # valid JSON + alle oorspronkelijke velden behouden
    data = json.loads(sf.path.read_text(encoding="utf-8"))
    assert data["key"]["platform_app_id"] == "517630"
    assert data["settings"]["graphics_stack"]["kind"] == "dxmt"
    assert data["settings"]["graphic_api"] == "DirectX 11.0"
    assert data["settings"]["language"] == "system"


def test_patch_engine_naar_proton11(fake_gamehub):
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "502500")
    refs = settings.find_references(files)
    changes = settings.patch_settings(sf, {}, engine="wine-proton_11.0", refs=refs)
    assert any("engine" in c for c in changes)
    data = json.loads(sf.path.read_text(encoding="utf-8"))
    assert data["settings"]["compatibility_layer"] == "10000073"


def test_patch_engine_niet_geinstalleerd_weigert(fake_gamehub):
    """proton10 is in referenties (AC7), maar NIET geïnstalleerd -> weigeren."""
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "517630")
    refs = settings.find_references(files)
    with pytest.raises(settings.SettingsError, match="NIET lokaal geïnstalleerd"):
        settings.patch_settings(sf, {}, engine="wine-proton_10.0", refs=refs)


def test_geen_wijzigingen_bij_identieke_config(fake_gamehub):
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "517630")
    refs = settings.find_references(files)
    changes = settings.patch_settings(
        sf, scalar_overrides={"sync_mode": "msync"}, refs=refs
    )
    assert changes == []


def test_onbekende_graphics_stack(fake_gamehub):
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "517630")
    refs = settings.find_references(files)
    with pytest.raises(settings.SettingsError):
        settings.patch_settings(sf, {}, graphics_stack="vulkan", refs=refs)


def test_graphics_stack_niet_geinstalleerd_wordt_geweigerd(fake_gamehub):
    """Real-world bug: dxmt gerefereerd maar component niet geïnstalleerd.

    Dit veroorzaakte "Failed to start game" in GameHub's preflight. Nu fail-closed.
    """
    import json

    comp_path = fake_gamehub["wine_dir"] / "component" / "components.json"
    data = json.loads(comp_path.read_text())
    data["components"] = [c for c in data["components"] if c["manifest"]["id"] != "10000163"]
    comp_path.write_text(json.dumps(data))

    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "517630")
    refs = settings.find_references(files)
    with pytest.raises(settings.SettingsError, match="NIET lokaal geïnstalleerd"):
        settings.patch_settings(sf, {}, graphics_stack="dxmt", refs=refs)
    # bestand onaangeroerd
    assert not list(config.backups_dir().glob(f"{sf.path.stem}.bak-*"))


def test_onbekende_settings_key_wordt_geweigerd(fake_gamehub):
    """Review 1.2: typo/onbekende scalar-key mag NIET in de config belanden."""
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "517630")
    refs = settings.find_references(files)
    with pytest.raises(settings.SettingsError, match="onbekende settings-keys"):
        settings.patch_settings(sf, scalar_overrides={"sync_mod": "esync"}, refs=refs)
    # bestand moet onaangeroerd zijn (geen backup, geen write)
    assert not list(config.backups_dir().glob(f"{sf.path.stem}.bak-*"))


def test_engine_guard_fail_closed_zonder_installaties_bestand(fake_gamehub, monkeypatch):
    """Review 1.1: als wine_installations.json ontbreekt -> weigeren i.p.v. stil doorlaten."""
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "502500")  # op proton10
    refs = settings.find_references(files)
    # installaties-bestand weghalen
    (fake_gamehub["wine_dir"] / "container" / "wine_installations.json").unlink()
    with pytest.raises(settings.SettingsError, match="niet verifiëren"):
        settings.patch_settings(sf, {}, engine="wine-proton_10.0", refs=refs)


def test_engine_downloading_telt_niet_als_geinstalleerd(fake_gamehub):
    """Review 2.7: engine met install_status 'downloading' is niet speelbaar."""
    import json

    p = fake_gamehub["wine_dir"] / "container" / "wine_installations.json"
    data = json.loads(p.read_text())
    data["wine_installations"]["99999999"] = {
        "id": "99999999", "name": "wine-proton_99.0", "install_status": "downloading",
    }
    p.write_text(json.dumps(data))
    ids = settings.installed_engine_ids()
    assert "99999999" not in ids
    assert "10000073" in ids


def test_patch_dry_run_schrijft_niet(fake_gamehub):
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "517630")
    refs = settings.find_references(files)
    before = sf.path.read_text(encoding="utf-8")
    changes = settings.patch_settings(
        sf, scalar_overrides={"sync_mode": "esync"}, refs=refs, dry_run=True
    )
    assert changes
    assert not list(config.backups_dir().glob(f"{sf.path.stem}.bak-*"))
    assert sf.path.read_text(encoding="utf-8") == before


def test_schema_version_onbekend_wordt_overgeslagen(fake_gamehub):
    """Review 2.5: bestand met vreemd schema mag niet geopend/gepatcht worden."""
    import json

    weird = fake_gamehub["gh_dir"] / "game-settings" / "zz99.json"
    data = {
        "schema_version": 99,
        "key": {"kind": "platform", "platform": "steam", "platform_app_id": "999999", "game_id": "x"},
        "settings": {"sync_mode": "msync"},
    }
    weird.write_text(json.dumps(data))
    files = settings.settings_files()
    assert all(f.app_id != "999999" for f in files)
    sf = settings.find_file_by_app_id(files, "999999")
    assert sf is None