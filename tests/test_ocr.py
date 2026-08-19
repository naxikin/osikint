"""OCR failure must not terminate the scan (legacy)."""

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


def test_ocr_internal_failure_returns_empty(legacy, sample_image):
    def boom(*args, **kwargs):
        raise legacy.pytesseract.TesseractError(1, "tesseract crash")

    original = legacy.pytesseract.image_to_string
    legacy.pytesseract.image_to_string = boom
    try:
        assert legacy.extract_text_from_image(sample_image) == ""
    finally:
        legacy.pytesseract.image_to_string = original


def test_ocr_failure_keeps_scan_alive(legacy, monkeypatch, tmp_path):
    monkeypatch.setattr(
        legacy, "fetch_dynamic_page", lambda url: (PROFILE_HTML, url)
    )
    monkeypatch.setattr(legacy, "download_image", lambda url, filename: True)
    monkeypatch.setattr(legacy, "calculate_image_hash", lambda path: "hash1")
    monkeypatch.setattr(legacy, "extract_text_from_image", lambda path: "")

    result = legacy.analyze_profile(
        {"url": "https://instagram.com/malakaji"},
        "malakaji",
        {},
        str(tmp_path),
    )

    assert result is not None
    assert result["risk_score"] == 4
    assert result["ocr_text"] == ""
