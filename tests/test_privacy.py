"""Unit tests: PII redaction wired into ProfileAnalyzer output
(skills.md section 36). Redaction must never affect keyword/OCR
detection - only what gets persisted."""

from analyzers.extractor import ExtractionResult
from analyzers.profile_analyzer import ProfileAnalyzer
from core.models import ImageAnalysis, OCRResult


class _FakeCollector:
    def fetch(self, url):
        return "<html>x</html>", url


class _FakeExtractor:
    def extract(self, html, final_url=""):
        return ExtractionResult(
            account_names=["Jane Doe (jane.doe@example.com)"],
            profile_image="https://cdn.example.com/a.jpg",
            page_text="malakaji profile",
            final_url=final_url,
        )


class _FakeImageDownloader:
    def download(self, url, image_dir):
        return "/tmp/fake.jpg"


class _FakeImageAnalyzer:
    def analyze(self, path):
        return ImageAnalysis(average_hash="abcd1234")


class _FakeOCREngine:
    def extract_text(self, path):
        return OCRResult(text="call 081234567890 now", engine="tesseract")


def _build_analyzer(privacy_config):
    return ProfileAnalyzer(
        collector=_FakeCollector(),
        extractor=_FakeExtractor(),
        image_analyzer=_FakeImageAnalyzer(),
        ocr_engine=_FakeOCREngine(),
        image_downloader=_FakeImageDownloader(),
        privacy_config=privacy_config,
    )


def _analyze(privacy_config):
    analyzer = _build_analyzer(privacy_config)
    return analyzer.analyze(
        {"url": "https://instagram.com/malakaji"}, "malakaji", {}, "/tmp"
    )


def test_redaction_applied_to_stored_fields():
    result = _analyze(
        {
            "redact_sensitive_data": True,
            "redact_email": True,
            "redact_phone": True,
        }
    )
    assert "[REDACTED_EMAIL]" in result.account_names[0]
    assert result.ocr_text == "call [REDACTED_PHONE] now"
    assert result.ocr_analysis["text"] == "call [REDACTED_PHONE] now"


def test_redaction_does_not_affect_keyword_detection():
    result = _analyze(
        {
            "redact_sensitive_data": True,
            "redact_email": True,
            "redact_phone": True,
        }
    )
    assert result.keyword_detected is True


def test_redaction_disabled_by_default():
    result = _analyze({})
    assert "jane.doe@example.com" in result.account_names[0]
    assert result.ocr_text == "call 081234567890 now"
