"""Unit tests: image hash comparison (skills.md section 18)."""

from correlation.image_matcher import (
    HIGH_SIMILARITY,
    NO_MATCH,
    POSSIBLE_MATCH,
    PROBABLE_MATCH,
    ImageMatcher,
)


def test_compare_identical_hashes_is_high_similarity():
    matcher = ImageMatcher()
    result = matcher.compare("abcd1234abcd1234", "abcd1234abcd1234")
    assert result.matched is True
    assert result.distance == 0
    assert result.state == HIGH_SIMILARITY
    assert result.similarity == 1.0


def test_compare_close_hashes_is_probable_match():
    matcher = ImageMatcher()
    # differs by exactly one bit in the last nibble
    result = matcher.compare("0000000000000000", "0000000000000001")
    assert result.matched is True
    assert result.distance == 1
    assert result.state == PROBABLE_MATCH


def test_compare_far_hashes_is_no_match():
    matcher = ImageMatcher()
    result = matcher.compare("0000000000000000", "ffffffffffffffff")
    assert result.matched is False
    assert result.state == NO_MATCH


def test_compare_method_label_defaults_to_ahash():
    matcher = ImageMatcher()
    result = matcher.compare("abcd", "abcd")
    assert result.method == "ahash"


def test_compare_method_label_can_be_overridden():
    matcher = ImageMatcher()
    result = matcher.compare("abcd", "abcd", method="phash")
    assert result.method == "phash"


def test_compare_length_mismatch_is_no_match():
    matcher = ImageMatcher()
    result = matcher.compare("abcd", "abcdef")
    assert result.state == NO_MATCH


def test_reverse_match_exact_only():
    matcher = ImageMatcher()
    assert matcher.reverse_match("abcd1234", {"abcd1234": "url"}) is True
    assert matcher.reverse_match("zzzz9999", {"abcd1234": "url"}) is False
    assert matcher.reverse_match("", {"abcd1234": "url"}) is False


def test_possible_match_boundary():
    matcher = ImageMatcher()
    # exactly at the possible-match distance boundary (10 bits: f=4, f=4, 3=2)
    result = matcher.compare("0000000000000000", "0000000000000ff3")
    assert result.distance == 10
    assert result.state == POSSIBLE_MATCH
