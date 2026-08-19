"""Regression suite: refactored implementation must reproduce legacy
behavior for identical inputs (skills.md sections 30, 31).

Legacy behavior was characterized BEFORE refactoring (Fase 1); every
expectation here matches the captured legacy output.
"""

from analyzers.extractor import (
    extract_account_names,
    extract_profile_image,
)
from correlation.username_matcher import contains_keyword, similarity
from scoring.risk_engine import RiskEngine
from storage.json_storage import save_results
from utils.normalization import normalize_text

import json
import os

from bs4 import BeautifulSoup


# --- normalization -------------------------------------------------------

def test_regression_normalization():
    assert normalize_text("M@l4k4j!___") == "malakaji"
    assert normalize_text("m4laj!__") == "malaji"
    assert normalize_text("m4l4k4j1") == "malakaji"
    assert normalize_text("MaLakaji") == "malakaji"
    assert normalize_text("") == ""
    assert normalize_text("malakaji_123!@#") == "malakajii2eia"


# --- matching ------------------------------------------------------------

def test_regression_matching():
    assert contains_keyword("M@l4k4j!___", "malakaji") is True
    assert contains_keyword("m4laj!__", "malakaji") is True
    assert contains_keyword(
        "Followers of m4laj!__ on Instagram", "malakaji"
    ) is False
    assert round(similarity("malaji", "malakaji"), 3) == 0.857
    assert similarity("malakaji", "malakaji") == 1.0


# --- extraction ----------------------------------------------------------

LEGACY_HTML = """
<html>
<head>
    <title>Jane Doe (@jane) | Instagram</title>
    <meta property="og:title" content="Jane Doe Profile"/>
    <meta name="twitter:title" content="Jane Doe Twitter"/>
    <meta property="og:image" content="https://cdn.example.com/avatar.jpg"/>
</head>
<body>
    <h1>Jane Doe</h1><h2>About</h2><h3>Contact</h3>
</body>
</html>
"""


def test_regression_extraction():
    soup = BeautifulSoup(LEGACY_HTML, "html.parser")
    assert set(extract_account_names(soup)) == {
        "Jane Doe (@jane) | Instagram",
        "Jane Doe Profile",
        "Jane Doe Twitter",
        "Jane Doe",
        "About",
        "Contact",
    }
    assert (
        extract_profile_image(soup)
        == "https://cdn.example.com/avatar.jpg"
    )


# --- risk scoring --------------------------------------------------------

def test_regression_risk_weights():
    engine = RiskEngine()
    assert engine.evaluate(keyword_detected=True).score == 4
    assert engine.evaluate(
        keyword_detected=True, ocr_detected=True
    ).score == 9
    assert engine.evaluate(
        keyword_detected=True,
        ocr_detected=True,
        reverse_image_match=True,
    ).score == 15


# --- storage -------------------------------------------------------------

def test_regression_atomic_save(tmp_path):
    target = str(tmp_path / "report.json")
    save_results([{"url": "https://a.example"}], target)
    assert os.path.exists(target)
    assert not os.path.exists(target + ".tmp")
    with open(target, encoding="utf-8") as f:
        assert json.load(f) == [{"url": "https://a.example"}]


# --- legacy output schema ------------------------------------------------

def test_regression_legacy_fields_remain():
    from core.models import LEGACY_FIELDS

    assert LEGACY_FIELDS == [
        "url",
        "account_names",
        "keyword_detected",
        "profile_image",
        "image_hash",
        "ocr_text",
        "reverse_image_match",
        "risk_score",
    ]
