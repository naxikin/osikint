"""Regression tests: known bugs (skills.md section 41)."""

import hashlib
import inspect
import os

EXPECTED_SITES = [
    "instagram.com",
    "facebook.com",
    "x.com",
    "tiktok.com",
    "github.com",
    "linkedin.com",
    "gitlab.com",
]


def test_platforms_are_separate(legacy):
    assert legacy.TARGET_SITES == EXPECTED_SITES
    assert "linkedin.comgitlab.com" not in legacy.TARGET_SITES


def test_no_bare_except_in_legacy(legacy):
    source = inspect.getsource(legacy)
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("except:"):
            raise AssertionError(f"bare except found: {stripped}")


def test_image_filename_deterministic(legacy, monkeypatch, tmp_path):
    profile_url = "https://cdn.example.com/avatar.jpg"
    html = (
        "<html><head><title>Malakaji</title>"
        f'<meta property="og:image" content="{profile_url}"/></head></html>'
    )
    monkeypatch.setattr(legacy, "fetch_dynamic_page", lambda url: (html, url))
    monkeypatch.setattr(legacy, "extract_text_from_image", lambda path: "")
    monkeypatch.setattr(legacy, "calculate_image_hash", lambda path: "h")

    def fake_download(url, filename):
        with open(filename, "wb") as f:
            f.write(b"x")
        return True

    monkeypatch.setattr(legacy, "download_image", fake_download)

    legacy.analyze_profile(
        {"url": "https://instagram.com/malakaji"},
        "malakaji",
        {},
        str(tmp_path),
    )

    expected_name = (
        hashlib.sha256(profile_url.encode("utf-8")).hexdigest() + ".jpg"
    )
    assert os.path.exists(os.path.join(str(tmp_path), expected_name))
