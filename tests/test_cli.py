"""CLI-tests: exit codes + nette foutafhandeling (review-bevindingen 2.1/2.4)."""

from __future__ import annotations

import json
from pathlib import Path

from gamehub_tuner import config, settings
from gamehub_tuner.cli import main


def test_main_list_exit_0(fake_gamehub):
    assert main(["list"]) == 0


def test_main_list_zonder_config_exit_1(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMEHUB_DIR", str(tmp_path / "nope"))
    monkeypatch.setenv("GAMEHUB_WINE_DIR", str(tmp_path / "nope"))
    assert main(["list"]) == 1


def test_main_onbekende_preset_nette_fout(fake_gamehub, capsys):
    rc = main(["apply-preset", "517630", "bestaat-niet"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "Fout:" in out
    assert "Traceback" not in out


def test_main_apply_preset_dry_run_schrijft_niet(fake_gamehub):
    # --yes om deterministisch te zijn (op deze Mac draait GameHub écht; CI niet).
    files = settings.settings_files()
    sf = settings.find_file_by_app_id(files, "517630")
    assert sf is not None
    before = sf.path.read_text(encoding="utf-8")
    rc = main(["apply-preset", "517630", "dx11-dxmt", "--yes", "--dry-run"])
    assert rc == 0
    assert sf.path.read_text(encoding="utf-8") == before
    assert not list(sf.path.parent.glob(f"{sf.path.name}.bak-*"))


def test_main_apply_preset_engine_niet_geinstalleerd(fake_gamehub, capsys):
    """proton10 preset moet weigeren: engine niet geïnstalleerd."""
    rc = main(["apply-preset", "517630", "proton10-legacy", "--yes"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "Fout:" in out


def test_main_apply_dx11_dxmt_zonder_dxmt_component(fake_gamehub, capsys):
    """Real-world bug: dx11-dxmt preset moet netjes weigeren als dxmt ontbreekt."""
    import json

    comp_path = fake_gamehub["wine_dir"] / "component" / "components.json"
    data = json.loads(comp_path.read_text())
    data["components"] = [c for c in data["components"] if c["manifest"]["id"] != "10000163"]
    comp_path.write_text(json.dumps(data))

    rc = main(["apply-preset", "517630", "dx11-dxmt", "--yes"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "Fout:" in out
    assert "dxmt" in out
    assert "Traceback" not in out


def test_main_version(fake_gamehub, capsys):
    with pytest_raises_systemexit(capsys):
        main(["--version"])


class pytest_raises_systemexit:
    def __init__(self, capsys):
        self.capsys = capsys

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        assert exc_type is SystemExit
        out = self.capsys.readouterr().out
        assert "gamehub-tuner" in out
        return True


def test_main_doctor(fake_gamehub, capsys):
    # In de fake-omgeving mist proton10 (gerefereerd door AC7) -> doctor moet
    # dat terecht signaleren en exit 1 geven.
    rc = main(["doctor"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "Wine-engines" in out
    assert "wine-proton_11.0" in out
    assert "NIET-geïnstalleerde engines" in out