"""Unit tests: pHash/dHash image hashing (skills.md section 15)."""

from analyzers.image_analyzer import (
    ImageAnalyzer,
    calculate_dhash,
    calculate_phash,
)


def test_calculate_phash_deterministic(sample_image):
    assert calculate_phash(sample_image) == calculate_phash(sample_image)


def test_calculate_dhash_deterministic(sample_image):
    assert calculate_dhash(sample_image) == calculate_dhash(sample_image)


def test_calculate_phash_is_hex_string(sample_image):
    result = calculate_phash(sample_image)
    assert isinstance(result, str)
    int(result, 16)  # raises ValueError if not hex


def test_image_analyzer_computes_all_configured_algorithms(sample_image):
    analyzer = ImageAnalyzer(algorithms=["average", "sha256", "phash", "dhash"])
    result = analyzer.analyze(sample_image)

    assert result.average_hash is not None
    assert result.sha256 is not None
    assert result.phash is not None
    assert result.dhash is not None


def test_image_analyzer_skips_disabled_algorithms(sample_image):
    analyzer = ImageAnalyzer(algorithms=["average"])
    result = analyzer.analyze(sample_image)

    assert result.average_hash is not None
    assert result.phash is None
    assert result.dhash is None
    assert result.sha256 is None


def test_image_analyzer_handles_missing_file(tmp_path):
    analyzer = ImageAnalyzer(algorithms=["average", "phash", "dhash", "sha256"])
    result = analyzer.analyze(str(tmp_path / "missing.jpg"))

    assert result.average_hash is None
    assert result.phash is None
    assert result.dhash is None
    assert result.sha256 is None
