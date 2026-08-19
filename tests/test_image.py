"""Characterization tests: image pipeline (legacy)."""

from PIL import Image


def test_calculate_image_hash_legacy(legacy, sample_image):
    result = legacy.calculate_image_hash(sample_image)
    assert isinstance(result, str)
    assert len(result) == 16


def test_calculate_image_hash_same_image_same_hash(legacy, sample_image):
    assert legacy.calculate_image_hash(sample_image) == legacy.calculate_image_hash(
        sample_image
    )


def test_calculate_image_hash_invalid_path(legacy, tmp_path):
    assert legacy.calculate_image_hash(str(tmp_path / "missing.jpg")) is None


def test_extract_text_failure_returns_empty(legacy, tmp_path):
    result = legacy.extract_text_from_image(str(tmp_path / "missing.jpg"))
    assert result == ""


def test_download_image_mocked(legacy, tmp_path, monkeypatch):
    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "image/jpeg"}

        def iter_content(self, chunk_size):
            return [b"fakeimagebytes"]

    class FakeRequests:
        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(legacy.requests, "get", FakeRequests().get)

    target = str(tmp_path / "img.jpg")
    assert legacy.download_image("https://example.com/a.jpg", target) is True
    with open(target, "rb") as f:
        assert f.read() == b"fakeimagebytes"


def test_download_image_not_image(legacy, tmp_path, monkeypatch):
    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}

    class FakeRequests:
        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(legacy.requests, "get", FakeRequests().get)
    assert legacy.download_image("https://example.com/a", str(tmp_path / "x.jpg")) is False


def test_download_image_failure(legacy, tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise legacy.requests.RequestException("network down")

    monkeypatch.setattr(legacy.requests, "get", boom)
    assert legacy.download_image("https://example.com/a.jpg", str(tmp_path / "x.jpg")) is False
