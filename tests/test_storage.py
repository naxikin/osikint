"""Characterization tests: JSON storage, autosave, Ctrl+C (legacy)."""

import json
import os
import sys

import pytest


def test_save_results_atomic(legacy, tmp_path):
    target = str(tmp_path / "report.json")
    legacy.save_results([{"url": "https://a.example"}], target)
    assert os.path.exists(target)
    assert not os.path.exists(target + ".tmp")
    with open(target, encoding="utf-8") as f:
        data = json.load(f)
    assert data == [{"url": "https://a.example"}]


def test_save_results_overwrites(legacy, tmp_path):
    target = str(tmp_path / "report.json")
    legacy.save_results([{"n": 1}], target)
    legacy.save_results([{"n": 2}], target)
    with open(target, encoding="utf-8") as f:
        assert json.load(f) == [{"n": 2}]


def test_autosave_accumulates(legacy, tmp_path):
    target = str(tmp_path / "report.json")
    results = []
    for profile in ({"url": "a"}, {"url": "b"}, {"url": "c"}):
        results.append(profile)
        legacy.save_results(results, target)
        with open(target, encoding="utf-8") as f:
            assert json.load(f) == results


def test_ctrl_c_saves_partial(legacy, tmp_path, monkeypatch):
    target = str(tmp_path / "partial.json")
    monkeypatch.setattr(legacy, "REPORT_FILE", target)
    legacy.final_results[:] = [{"url": "kept"}]

    with pytest.raises(SystemExit) as excinfo:
        legacy.signal_handler(None, None)

    assert excinfo.value.code == 0
    with open(target, encoding="utf-8") as f:
        assert json.load(f) == [{"url": "kept"}]


def test_ctrl_c_marks_status_stopped(legacy, tmp_path, monkeypatch):
    status_file = str(tmp_path / "scan_status.json")
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump({"state": "running", "discovered": 5}, f)

    monkeypatch.setattr(legacy, "REPORT_FILE", str(tmp_path / "r.json"))
    monkeypatch.setattr(legacy, "STATUS_FILE", status_file)

    with pytest.raises(SystemExit):
        legacy.signal_handler(None, None)

    with open(status_file, encoding="utf-8") as f:
        status = json.load(f)
    assert status["state"] == "stopped"
    assert status["completed_at"]


def test_legacy_profile_schema(legacy):
    profile = {
        "url": "https://example.com/p",
        "account_names": ["Example"],
        "keyword_detected": False,
        "profile_image": None,
        "image_hash": None,
        "ocr_text": "",
        "reverse_image_match": False,
        "risk_score": 0,
    }
    assert legacy.save_results(
        [profile], "schema.json"
    ) is None
    with open("schema.json", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded[0].keys() == profile.keys()
    os.remove("schema.json")
