"""Unit tests: config, query builder, deduplicator, risk engine."""

import os

from core.config import load_config
from discovery.deduplicator import deduplicate
from discovery.query_builder import (
    build_all_queries,
    build_leet_variants,
    build_queries,
)
from scoring.risk_engine import RiskEngine


def test_load_config_defaults():
    config = load_config()
    assert config.search["region"] == "id-id"
    assert config.search["max_results"] == 30
    assert config.risk["keyword_detected"] == 4
    assert config.risk["ocr_detected"] == 5
    assert config.risk["reverse_image_match"] == 6
    assert config.platforms["gitlab"]["domain"] == "gitlab.com"
    assert len(config.enabled_platform_domains()) == 7


def test_load_config_env_overrides(monkeypatch):
    monkeypatch.setenv("OSINT_REGION", "us-en")
    monkeypatch.setenv("OSINT_MAX_RESULTS", "10")
    monkeypatch.setenv("OSINT_OCR_ENABLED", "false")
    config = load_config()
    assert config.search["region"] == "us-en"
    assert config.search["max_results"] == 10
    assert config.ocr["enabled"] is False


def test_platform_filter():
    config = load_config()
    domains = config.enabled_platform_domains(["github"])
    assert domains == {"github": "github.com"}


def test_build_queries_legacy():
    queries = build_queries("malakaji", "instagram.com")
    assert queries == [
        '"malakaji" site:instagram.com',
        "inurl:malakaji site:instagram.com",
        'intitle:"malakaji" site:instagram.com',
    ]


def test_build_leet_variants():
    variants = build_leet_variants("maka")
    assert "m4k4" in variants
    assert "m@k@" in variants


def test_build_all_queries_with_leet():
    queries = build_all_queries(
        "maka", "instagram.com", include_leet=True
    )
    assert len(queries) > 3
    assert queries[:3] == build_queries("maka", "instagram.com")


def test_deduplicator_tracking_params():
    results = [
        {"url": "https://a.example/p?utm_source=x", "title": "A"},
        {"url": "https://a.example/p", "title": "A dup"},
    ]
    unique = deduplicate(results)
    assert len(unique) == 1


def test_deduplicator_fragment_and_slash():
    results = [
        {"url": "https://a.example/p/", "title": "A"},
        {"url": "https://a.example/p#frag", "title": "A dup"},
    ]
    unique = deduplicate(results)
    assert len(unique) == 1


def test_deduplicator_distinct_paths():
    results = [
        {"url": "https://a.example/p1", "title": "A"},
        {"url": "https://a.example/p2", "title": "B"},
    ]
    assert len(deduplicate(results)) == 2


def test_risk_engine_legacy_weights():
    engine = RiskEngine()
    result = engine.evaluate(
        keyword_detected=True,
        ocr_detected=True,
        reverse_image_match=True,
    )
    assert result.score == 15
    assert result.level == "high"


def test_risk_engine_levels():
    engine = RiskEngine()
    assert engine.evaluate().score == 0
    assert engine.evaluate().level == "none"
    assert engine.evaluate(keyword_detected=True).level == "low"
    assert engine.evaluate(
        keyword_detected=True, ocr_detected=True
    ).level == "medium"


def test_risk_engine_configurable():
    engine = RiskEngine(weights={"keyword_detected": 10})
    result = engine.evaluate(keyword_detected=True)
    assert result.score == 10
    assert result.factors[0].to_dict() == {
        "name": "keyword_detected", "weight": 10,
    }
