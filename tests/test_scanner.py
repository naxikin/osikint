"""Unit tests: scanner + report manager (mocked, no network)."""

import json
import os

from core.models import ProfileResult
from core.scanner import OSINTScanner
from core.config import load_config
from storage.report_manager import ReportManager


def _scanner(tmp_path, profiles, connections=None, config=None):
    config = config or load_config()
    config.output["directory"] = str(tmp_path / "output")

    class FakeAnalyzer:
        def __init__(self, items):
            self.items = list(items)
            self.known_hashes = None

        def analyze(self, profile, target, known_hashes, image_dir):
            item = self.items.pop(0)
            item.url = profile["url"]
            item.original_url = profile["url"]
            item.final_url = profile["url"]
            if item.image_hash and item.image_hash in known_hashes:
                item.reverse_image_match = True
            elif item.image_hash:
                known_hashes[item.image_hash] = item.url
            return item

    profiles = [ProfileResult(risk_score=0) for _ in profiles]

    class FakeLinker:
        def build_connections(self, profiles, target, known_hashes):
            return connections or []

    scanner = OSINTScanner(
        config=config,
        discovery_fn=lambda target: [
            {"title": f"R{i}", "url": f"https://x.example/{i}",
             "body": "", "source": "x.example"}
            for i in range(len(profiles))
        ],
        analyzer=FakeAnalyzer(profiles),
        entity_linker=FakeLinker(),
        report_manager=ReportManager(config.output["directory"]),
    )
    return scanner


def test_scan_complete_report(tmp_path):
    scanner = _scanner(tmp_path, [{"kw": True}, {"kw": False}])
    events = []

    report = scanner.scan("malakaji", on_progress=events.append)

    assert report is not None
    assert report["schema_version"] == "1.0"
    assert report["target"] == "malakaji"
    assert report["statistics"] == {
        "discovered": 2, "analyzed": 2, "matched": 0,
    }
    assert len(report["profiles"]) == 2

    kinds = [e["event"] for e in events]
    assert kinds == [
        "discovery_started",
        "discovery_done",
        "profile_analyzed",
        "profile_analyzed",
        "scan_completed",
    ]

    report_path = scanner.report_manager.report_path(
        report["scan_id"], "malakaji"
    )
    assert os.path.exists(report_path)
    with open(report_path, encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["profiles"] == report["profiles"]


def test_scan_autosave_partial_on_interrupt(tmp_path):
    scanner = _scanner(tmp_path, [{"kw": True}])

    class InterruptingAnalyzer(scanner.analyzer.__class__):
        def analyze(self, profile, target, known_hashes, image_dir):
            raise KeyboardInterrupt()

    scanner.analyzer = InterruptingAnalyzer(scanner.analyzer.items)
    scanner.analyzer.known_hashes = None

    import pytest

    with pytest.raises(KeyboardInterrupt):
        scanner.scan("malakaji", on_progress=lambda e: None)


def test_scan_status_file(tmp_path):
    scanner = _scanner(tmp_path, [{"kw": True}])
    status_file = str(tmp_path / "scan_status.json")

    scanner.scan("malakaji", on_progress=lambda e: None,
                 status_file=status_file)

    assert os.path.exists(status_file)
    with open(status_file, encoding="utf-8") as f:
        status = json.load(f)
    assert status["state"] == "completed"
    assert status["analyzed"] == 1


def test_scan_profile_failure_continues(tmp_path):
    scanner = _scanner(tmp_path, [{"kw": True}, {"kw": False}])

    class FlakyAnalyzer(scanner.analyzer.__class__):
        def __init__(self, items):
            super().__init__(items)
            self.calls = 0

        def analyze(self, profile, target, known_hashes, image_dir):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("boom")
            return super().analyze(
                profile, target, known_hashes, image_dir
            )

    scanner.analyzer = FlakyAnalyzer(scanner.analyzer.items)

    events = []
    report = scanner.scan("malakaji", on_progress=events.append)

    assert report["statistics"]["analyzed"] == 2
    failed = [
        p for p in report["profiles"]
        if p.get("analyze_status") == "failed"
    ]
    assert len(failed) == 1
    assert failed[0]["analyze_error"] == "boom"
    assert failed[0]["url"] == "https://x.example/0"
    assert any(e["event"] == "profile_failed" for e in events)


def test_discovery_failure_returns_none(tmp_path):
    scanner = _scanner(tmp_path, [])
    scanner.discovery_fn = lambda target: (_ for _ in ()).throw(
        RuntimeError("backend down")
    )
    events = []
    report = scanner.scan("malakaji", on_progress=events.append)
    assert report is None
    assert events[-1]["event"] == "scan_failed"


def test_legacy_fields_preserved_in_profile():
    profile = ProfileResult(url="u", risk_score=4).to_dict()
    assert set(profile.keys()) == {
        "url", "account_names", "keyword_detected", "profile_image",
        "image_hash", "ocr_text", "reverse_image_match", "risk_score",
        "platform", "original_url", "final_url", "match_details",
        "image_analysis", "ocr_analysis", "correlation", "risk_details",
        "analyze_status", "analyze_error", "evidence_image",
    }
    legacy = {
        k: profile[k]
        for k in [
            "url", "account_names", "keyword_detected", "profile_image",
            "image_hash", "ocr_text", "reverse_image_match", "risk_score",
        ]
    }
    assert legacy["risk_score"] == 4
    assert profile["analyze_status"] == "analyzed"


def test_failed_profile_factory():
    failed = ProfileResult.failed(
        "https://x.example/p", "boom", evidence_image="abc.png"
    )
    assert failed.analyze_status == "failed"
    assert failed.analyze_error == "boom"
    assert failed.url == "https://x.example/p"
    assert failed.risk_score == 0
    assert failed.evidence_image == "abc.png"


def test_scan_failure_captures_evidence(tmp_path):
    scanner = _scanner(tmp_path, [{"kw": True}])

    class FlakyAnalyzer(scanner.analyzer.__class__):
        def analyze(self, profile, target, known_hashes, image_dir):
            raise RuntimeError("boom")

    scanner.analyzer = FlakyAnalyzer(scanner.analyzer.items)

    captured = []

    def fake_screenshot(url, path):
        captured.append((url, path))
        with open(path, "wb") as f:
            f.write(b"png-bytes")
        return True

    scanner.screenshot_fn = fake_screenshot

    report = scanner.scan("malakaji", on_progress=lambda e: None)

    failed = report["profiles"][0]
    assert failed["analyze_status"] == "failed"
    assert failed["evidence_image"].endswith(".png")
    assert len(captured) == 1
    assert captured[0][0] == "https://x.example/0"

    images_dir = scanner.report_manager.images_dir(report["scan_id"])
    assert os.path.exists(
        os.path.join(images_dir, failed["evidence_image"])
    )


def test_scan_failure_without_screenshot_fn(tmp_path):
    scanner = _scanner(tmp_path, [{"kw": True}])

    class FlakyAnalyzer(scanner.analyzer.__class__):
        def analyze(self, profile, target, known_hashes, image_dir):
            raise RuntimeError("boom")

    scanner.analyzer = FlakyAnalyzer(scanner.analyzer.items)

    report = scanner.scan("malakaji", on_progress=lambda e: None)

    failed = report["profiles"][0]
    assert failed["evidence_image"] == ""
