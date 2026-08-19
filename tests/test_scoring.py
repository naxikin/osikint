"""Characterization tests: risk scoring inside analyze_profile (legacy)."""

import pytest

PROFILE_HTML = """
<html>
<head>
    <title>Malakaji (@malakaji) | Instagram</title>
    <meta property="og:image" content="https://cdn.example.com/avatar.jpg"/>
</head>
<body>
    <h1>Malakaji</h1>
</body>
</html>
"""


def _run(legacy, monkeypatch, tmp_path, image_hash="abcd", ocr_text=""):
    monkeypatch.setattr(
        legacy, "fetch_dynamic_page", lambda url: (PROFILE_HTML, url + "/final")
    )
    monkeypatch.setattr(legacy, "download_image", lambda url, filename: True)
    monkeypatch.setattr(legacy, "calculate_image_hash", lambda path: image_hash)
    monkeypatch.setattr(
        legacy, "extract_text_from_image", lambda path: ocr_text
    )
    return legacy.analyze_profile(
        {"url": "https://instagram.com/malakaji"},
        "malakaji",
        {},
        str(tmp_path),
    )


def test_risk_keyword_only(legacy, monkeypatch, tmp_path):
    result = _run(legacy, monkeypatch, tmp_path)
    assert result["risk_score"] == 4
    assert result["keyword_detected"] is True
    assert result["reverse_image_match"] is False


def test_risk_keyword_plus_ocr(legacy, monkeypatch, tmp_path):
    result = _run(legacy, monkeypatch, tmp_path, ocr_text="hello malakaji")
    assert result["risk_score"] == 9
    assert "malakaji" in result["ocr_text"]


def test_risk_full_15(legacy, monkeypatch, tmp_path):
    known = {"abcd": "https://other.example/profile"}
    monkeypatch.setattr(
        legacy, "fetch_dynamic_page", lambda url: (PROFILE_HTML, url + "/final")
    )
    monkeypatch.setattr(legacy, "download_image", lambda url, filename: True)
    monkeypatch.setattr(legacy, "calculate_image_hash", lambda path: "abcd")
    monkeypatch.setattr(
        legacy, "extract_text_from_image", lambda path: "ocr malakaji"
    )
    result = legacy.analyze_profile(
        {"url": "https://instagram.com/malakaji"},
        "malakaji",
        known,
        str(tmp_path),
    )
    assert result["risk_score"] == 15
    assert result["reverse_image_match"] is True


def test_fetch_failure_returns_none(legacy, monkeypatch):
    monkeypatch.setattr(legacy, "fetch_dynamic_page", lambda url: (None, None))
    assert (
        legacy.analyze_profile({"url": "x"}, "kw", {}, "tmp") is None
    )


def test_result_schema_keys(legacy, monkeypatch, tmp_path):
    result = _run(legacy, monkeypatch, tmp_path)
    assert set(result.keys()) == {
        "url",
        "account_names",
        "keyword_detected",
        "profile_image",
        "image_hash",
        "ocr_text",
        "reverse_image_match",
        "risk_score",
    }
