"""Unit tests: matching engine (multi-method)."""

from correlation.username_matcher import (
    METHOD_SEQUENCE,
    UsernameMatcher,
    contains_keyword,
)


def test_match_leet_full():
    matcher = UsernameMatcher()
    result = matcher.match("malakaji", "M@l4k4j!___")
    assert result.matched is True
    assert result.score == 100.0


def test_match_borderline_variant():
    matcher = UsernameMatcher()
    result = matcher.match("malakaji", "m4laj!__")
    assert result.matched is True
    assert result.method == METHOD_SEQUENCE
    assert result.score == 85.71


def test_match_sequence_method():
    matcher = UsernameMatcher()
    result = matcher.match("malakaji", "malaji")
    assert result.matched is True
    assert result.score == 85.71


def test_sequence_similarity_value():
    from correlation.username_matcher import sequence_similarity

    assert round(
        sequence_similarity("malaji", "malakaji") * 100, 2
    ) == 85.71


def test_match_no_match():
    matcher = UsernameMatcher()
    result = matcher.match("malakaji", "xyzabc")
    assert result.matched is False


def test_match_returns_details():
    matcher = UsernameMatcher()
    details = matcher.match_details("malakaji", "m4laj!__")
    assert set(details.keys()) == {
        "matched", "method", "score", "target", "candidate",
    }
    assert details["target"] == "malakaji"
    assert details["candidate"] == "m4laj!__"


def test_contains_keyword_threshold_custom():
    assert contains_keyword("m4laj!__", "malakaji", threshold=80) is True
    assert contains_keyword("m4laj!__", "malakaji", threshold=81) is False
