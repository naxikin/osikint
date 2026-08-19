"""Characterization tests: normalization engine (legacy behavior)."""


def test_legacy_normalization_exact(legacy):
    assert legacy.normalize_text("M@l4k4j!___") == "malakaji"


def test_legacy_normalization_borderline(legacy):
    assert legacy.normalize_text("m4laj!__") == "malaji"


def test_legacy_normalization_full_leet(legacy):
    assert legacy.normalize_text("m4l4k4j1") == "malakaji"


def test_legacy_normalization_case(legacy):
    assert legacy.normalize_text("MaLakaji") == "malakaji"


def test_legacy_normalization_empty(legacy):
    assert legacy.normalize_text("") == ""
    assert legacy.normalize_text(None) == ""


def test_legacy_normalization_special_chars(legacy):
    assert legacy.normalize_text("malakaji_123!@#") == "malakajii2eia"


def test_legacy_normalization_strips_punctuation(legacy):
    assert legacy.normalize_text("___malakaji___") == "malakaji"


def test_legacy_leet_map_values(legacy):
    assert legacy.LEET_MAP == {
        "4": "a",
        "@": "a",
        "3": "e",
        "1": "i",
        "!": "i",
        "0": "o",
        "$": "s",
        "5": "s",
        "7": "t",
    }
