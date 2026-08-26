"""Steam-detectie tests (review-bevinding 2.2: HTML-tolerant regex)."""

from __future__ import annotations

from gamehub_tuner import steam


def test_detect_dx_version_met_html():
    """Echte Steam-tekst bevat <strong>-tags tussen 'DirectX' en 'Version'."""
    details = {
        "pc_requirements": {
            "minimum": "<ul><li><strong>DirectX:</strong> Version 11</li></ul>",
            "recommended": "<strong>DirectX:</strong> Version 12",
        }
    }
    assert steam.detect_dx_version(details) == "11"  # minimum wint (eerst in tekst)


def test_detect_dx_version_geen_match():
    assert steam.detect_dx_version({"pc_requirements": {"minimum": ""}}) == ""


def test_detect_size_hint_met_html():
    details = {
        "pc_requirements": {
            "minimum": "<strong>Storage:</strong> 110 GB available space",
            "recommended": "",
        }
    }
    assert steam.detect_size_hint(details) == "110 GB"


def test_detect_size_hint_geen_match():
    assert steam.detect_size_hint({"pc_requirements": {"minimum": "onbekend"}}) == ""