"""Builds a fully wired OSINTScanner from configuration."""

from functools import partial

from analyzers.extractor import ProfileExtractor
from analyzers.image_analyzer import ImageAnalyzer
from analyzers.ocr_analyzer import OCREngine
from analyzers.profile_analyzer import ProfileAnalyzer
from collectors.http_client import HEADERS, HTTPCollector
from collectors.image_downloader import ImageDownloader
from collectors.playwright_client import (
    BrowserSettings,
    FallbackCollector,
    PlaywrightCollector,
)
from correlation.entity_linker import EntityLinker
from correlation.image_matcher import ImageMatcher
from correlation.username_matcher import UsernameMatcher
from discovery.search_engine import DDGSSearchEngine, search_social_accounts
from scoring.risk_engine import RiskEngine
from storage.report_manager import ReportManager

from core.scanner import OSINTScanner


def build_scanner(config, platform_filter=None):
    platform_domains = config.enabled_platform_domains(platform_filter)
    sites = list(platform_domains.values())

    search_config = config.search or {}
    matching_config = config.matching or {}
    browser_config = config.browser or {}
    collector_config = config.collector or {}
    image_config = config.image or {}
    ocr_config = config.ocr or {}

    engine = DDGSSearchEngine(
        region=search_config.get("region", "id-id"),
        max_results=search_config.get("max_results", 30),
    )

    discovery_fn = partial(
        search_social_accounts,
        sites=sites,
        engine=engine,
        include_leet=bool(search_config.get("leet_variants", False)),
    )

    matcher = UsernameMatcher(
        thresholds={
            "partial_ratio": matching_config.get(
                "partial_ratio_threshold", 80
            ),
            "sequence_similarity": matching_config.get(
                "sequence_threshold", 80
            ),
            "fuzzy": matching_config.get("fuzzy_threshold", 80),
        }
    )

    browser_settings = BrowserSettings(
        headless=browser_config.get("headless", True),
        timeout=browser_config.get("timeout", 60000),
        locale=browser_config.get("locale", "en-US"),
        viewport=browser_config.get(
            "viewport", {"width": 1920, "height": 1080}
        ),
        wait_until=browser_config.get("wait_until", "networkidle"),
        settle_seconds=browser_config.get("settle_seconds", 3),
    )

    http_collector = HTTPCollector(
        timeout=collector_config.get("http_timeout", 30),
        min_html_length=collector_config.get("min_html_length", 2000),
        headers=HEADERS,
    )

    playwright_collector = PlaywrightCollector(
        settings=browser_settings,
        user_agent=HEADERS.get("User-Agent"),
    )

    collector = FallbackCollector(
        http_collector,
        playwright_collector,
        http_first=collector_config.get("http_first", True),
    )

    analyzer = ProfileAnalyzer(
        collector=collector,
        extractor=ProfileExtractor(),
        matcher=matcher,
        image_analyzer=ImageAnalyzer(
            algorithms=image_config.get(
                "hash_algorithms", ["average", "sha256"]
            )
        ),
        ocr_engine=OCREngine(
            enabled=ocr_config.get("enabled", True),
            engine=ocr_config.get("engine", "tesseract"),
        ),
        correlation_engine=ImageMatcher(
            distances=config.image_match_states
        ),
        risk_engine=RiskEngine(
            weights=config.risk,
            levels=config.levels,
        ),
        image_downloader=ImageDownloader(
            headers=HEADERS,
            max_bytes=image_config.get("max_bytes", 10485760),
        ),
        platform_domains=platform_domains,
    )

    entity_linker = EntityLinker(
        sequence_threshold=matching_config.get("sequence_threshold", 80),
    )

    output_config = config.output or {}
    report_manager = ReportManager(
        output_dir=output_config.get("directory", "output")
    )

    return OSINTScanner(
        config=config,
        discovery_fn=discovery_fn,
        analyzer=analyzer,
        entity_linker=entity_linker,
        report_manager=report_manager,
        screenshot_fn=playwright_collector.screenshot,
    )
