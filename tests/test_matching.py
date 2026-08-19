"""Characterization tests: matching engine (legacy behavior)."""


def test_contains_keyword_leet_full(legacy):
    assert legacy.contains_keyword("M@l4k4j!___", "malakaji") is True


def test_contains_keyword_leet_borderline(legacy):
    assert legacy.contains_keyword("m4laj!__", "malakaji") is True


def test_contains_keyword_body_false(legacy):
    assert legacy.contains_keyword(
        "Followers of m4laj!__ on Instagram", "malakaji"
    ) is False


def test_contains_keyword_empty(legacy):
    assert legacy.contains_keyword("", "malakaji") is False
    assert legacy.contains_keyword(None, "malakaji") is False


def test_contains_keyword_plain(legacy):
    assert legacy.contains_keyword("hello malakaji world", "malakaji") is True


def test_similarity_short_variant(legacy):
    score = legacy.similarity("malaji", "malakaji")
    assert round(score, 3) == 0.857


def test_similarity_identical(legacy):
    assert legacy.similarity("malakaji", "malakaji") == 1.0


def test_similarity_different(legacy):
    assert legacy.similarity("abc", "xyz") == 0.0
