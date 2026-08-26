"""Tests voor presets, compat-database en benchmark-ladder."""

from __future__ import annotations

import pytest

from gamehub_tuner import benchmark, compat, presets
from gamehub_tuner.settings import SettingsError


def test_presets_laden_en_listen(fake_gamehub):
    items = presets.list_presets()
    names = {p.name for p in items}
    assert "dx11-dxmt" in names
    assert "dx12-gptk" in names
    assert "benchmark-mode" in names


def test_preset_dx12_gptk(fake_gamehub):
    p = presets.load_preset("dx12-gptk")
    assert p.engine == "wine-proton_11.0"
    assert p.graphics_stack == "gptk"
    assert p.settings["sync_mode"] == "msync"
    assert p.settings["ray_tracing_mode"] == "off"


def test_preset_onbekend_faalt(fake_gamehub):
    with pytest.raises(SettingsError):
        presets.load_preset("bestaat-niet")


def test_compat_db_geladen(fake_gamehub):
    entries = compat.load_database()
    assert len(entries) >= 6
    app_ids = {e.app_id for e in entries}
    assert {"517630", "502500", "1846380", "1517290", "2651280", "1551360"} <= app_ids
    jc4 = compat.get("517630")
    assert jc4 is not None
    assert jc4.name == "Just Cause 4"
    assert jc4.status == "playable"
    assert jc4.dx == "11"
    assert compat.get("999999") is None


def test_compat_render_markdown(fake_gamehub):
    md = compat.render_markdown()
    assert "| Game |" in md
    assert "Just Cause 4" in md
    assert "🟢" in md


def test_benchmark_stable():
    assert benchmark.stable(60, 45, 60) is True
    assert benchmark.stable(60, 30, 60) is False
    assert benchmark.stable(59, 50, 60) is False
    # Review 2.3: zonder 1% lows is een meting NIET stabiel te noemen.
    assert benchmark.stable(60, None, 60) is False
    assert benchmark.stable(None, None, 60) is False


def test_benchmark_ladder_ops():
    assert benchmark.next_quality("low") == "medium"
    assert benchmark.next_quality("ultra") == "ultra"
    assert benchmark.next_quality(None) == "low"
    assert benchmark.next_resolution("720p") == "900p"
    assert benchmark.next_resolution("1080p") == "1080p"


def test_benchmark_journal(fake_gamehub):
    e = benchmark.BenchmarkEntry(
        app_id="517630", name="Just Cause 4", date="2026-08-26",
        render_res="720p", upscale="fsr-quality", quality="low",
        avg_fps=63, low_1pct=48,
    )
    p = benchmark.save_entry(e)
    assert p.exists()
    entries = benchmark.load_entries("517630")
    assert len(entries) == 1
    assert entries[0]["avg_fps"] == 63


def test_render_ladder_heeft_6_stappen():
    lines = benchmark.render_ladder().strip().splitlines()
    assert len(lines) == 6
    assert "720p" in benchmark.render_ladder()