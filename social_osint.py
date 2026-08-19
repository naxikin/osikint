"""Social OSINT - CLI entry point.

Backward compatible with the legacy single-file implementation
(skills.md section 32): `python social_osint.py` must keep working.
"""

import argparse
import hashlib
import os
import signal
import sys

import imagehash
import pytesseract
import requests

from PIL import Image
from colorama import Fore, init
from ddgs import DDGS

from analyzers.extractor import extract_account_names, extract_profile_image
from analyzers.profile_analyzer import ProfileAnalyzer
from collectors.http_client import HEADERS
from collectors.playwright_client import BrowserSettings, PlaywrightCollector
from correlation.image_matcher import ImageMatcher
from correlation.username_matcher import contains_keyword, similarity
from core.config import load_config
from core.factory import build_scanner
from core.logger import setup_logging
from core.models import LEGACY_FIELDS, OCRResult
from discovery.search_engine import DDGSSearchEngine
from scoring.risk_engine import RiskEngine
from storage.json_storage import save_results
from utils.normalization import LEET_MAP, normalize_text

init(autoreset=True)

TARGET_SITES = [
    "instagram.com",
    "facebook.com",
    "x.com",
    "tiktok.com",
    "github.com",
    "linkedin.com",
    "gitlab.com",
]

final_results = []
REPORT_FILE = ""
STATUS_FILE = ""


def calculate_image_hash(path):
    try:
        image = Image.open(path)
        return str(imagehash.average_hash(image))
    except (OSError, ValueError) as e:
        print(Fore.RED + f"[HASH ERROR] {e}")
        return None


def extract_text_from_image(path):
    try:
        image = Image.open(path)
        text = pytesseract.image_to_string(image)
        return text
    except (OSError, pytesseract.TesseractError) as e:
        print(Fore.RED + f"[OCR ERROR] {e}")
        return ""


def download_image(url, filename):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
            stream=True,
        )

        if response.status_code != 200:
            return False

        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type:
            return False

        with open(filename, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        return True
    except requests.RequestException as e:
        print(Fore.RED + f"[DOWNLOAD ERROR] {e}")
        return False


def fetch_dynamic_page(url):
    collector = PlaywrightCollector(
        settings=BrowserSettings(timeout=60000),
        user_agent=HEADERS["User-Agent"],
    )
    return collector.fetch(url)


def search_social_accounts(keyword):
    engine = DDGSSearchEngine(ddgs_cls=DDGS, region="id-id", max_results=30)
    return _legacy_discovery(keyword, TARGET_SITES, engine)


def _legacy_discovery(keyword, sites, engine):
    from discovery.search_engine import search_social_accounts as _search

    return _search(keyword, list(sites), engine, include_leet=False)


class _CompatCollector:
    def fetch(self, url):
        return fetch_dynamic_page(url)


class _CompatImageAnalysis:
    def __init__(self, average_hash):
        self.average_hash = average_hash

    def to_dict(self):
        return {"average_hash": self.average_hash, "sha256": None}


class _CompatImageAnalyzer:
    def analyze(self, path):
        return _CompatImageAnalysis(calculate_image_hash(path))


class _CompatOCREngine:
    def extract_text(self, path):
        return OCRResult(
            text=extract_text_from_image(path),
            engine="tesseract",
            confidence=None,
        )


class _CompatImageDownloader:
    def download(self, url, image_dir):
        filename = os.path.join(
            image_dir,
            hashlib.sha256(url.encode("utf-8")).hexdigest() + ".jpg",
        )
        if download_image(url, filename):
            return filename
        return ""


class _CompatExtractor:
    def extract(self, html, final_url=""):
        from bs4 import BeautifulSoup

        from analyzers.extractor import ExtractionResult

        soup = BeautifulSoup(html, "html.parser")
        return ExtractionResult(
            account_names=extract_account_names(soup),
            profile_image=extract_profile_image(soup),
            page_text=soup.get_text(),
            final_url=final_url,
        )


def analyze_profile(profile, keyword, known_hashes, image_dir):
    analyzer = ProfileAnalyzer(
        collector=_CompatCollector(),
        extractor=_CompatExtractor(),
        matcher=None,
        image_analyzer=_CompatImageAnalyzer(),
        ocr_engine=_CompatOCREngine(),
        correlation_engine=ImageMatcher(),
        risk_engine=RiskEngine(),
        image_downloader=_CompatImageDownloader(),
        platform_domains={},
    )

    result = analyzer.analyze(profile, keyword, known_hashes, image_dir)

    if result is None:
        return None

    print(Fore.GREEN + f"Risk Score: {result.risk_score}")
    return result.to_legacy_dict()


def signal_handler(sig, frame):
    print(Fore.RED + "\n\n[CTRL+C DETECTED]")
    print(Fore.YELLOW + "[SAVING PARTIAL RESULTS]")

    if REPORT_FILE:
        save_results(final_results, REPORT_FILE)
        print(Fore.GREEN + "[REPORT SAVED]")
        print(Fore.CYAN + REPORT_FILE)
    else:
        print(Fore.RED + "[NO REPORT FILE YET - NOTHING SAVED]")

    if STATUS_FILE:
        import json as _json
        from datetime import datetime, timezone

        try:
            with open(STATUS_FILE, encoding="utf-8") as f:
                status = _json.load(f)
        except (OSError, ValueError):
            status = {}

        status["state"] = "stopped"
        status["completed_at"] = datetime.now(timezone.utc).isoformat()

        save_results(status, STATUS_FILE)

    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def _build_arg_parser():
    parser = argparse.ArgumentParser(
        prog="social_osint",
        description="Social OSINT scanner",
    )
    parser.add_argument("--target", help="target keyword")
    parser.add_argument("--output", help="output directory")
    parser.add_argument("--config", help="config yaml path")
    parser.add_argument(
        "--platform",
        action="append",
        help="restrict platform (repeatable)",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--status-file", help="write scan status JSON here")
    return parser


def _on_progress(event, scanner):
    global final_results, REPORT_FILE

    kind = event["event"]

    if kind == "discovery_started":
        scan_id = event["scan_id"]
        REPORT_FILE = scanner.report_manager.report_path(
            scan_id, event["target"]
        )

    elif kind == "discovery_done":
        print(
            Fore.GREEN
            + f"\n[DISCOVERED] {event['discovered']} profiles"
        )

    elif kind == "profile_analyzed":
        legacy = {
            key: event["profile"].get(key)
            for key in LEGACY_FIELDS
        }
        final_results.append(legacy)

        print(
            Fore.CYAN
            + f"\n[{event['analyzed']}/{event['total']}]"
        )
        print(
            Fore.CYAN
            + f"[ANALYZE] {event['url']}"
        )
        print(
            Fore.GREEN
            + f"Risk Score: {event['risk_score']}"
        )

    elif kind == "profile_failed":
        print(
            Fore.RED
            + f"[ERROR] {event.get('url')}: {event.get('error')}"
        )


def main(argv=None):
    global final_results, REPORT_FILE, STATUS_FILE

    args = _build_arg_parser().parse_args(argv)
    setup_logging(args.verbose)

    if args.target:
        keyword = args.target.strip()
    else:
        keyword = input("Target keyword: ").strip()

    if not keyword:
        print(Fore.RED + "[ERROR] empty target keyword")
        return 1

    config = load_config(args.config, platform_filter=args.platform)

    if args.output:
        config.output["directory"] = args.output

    scanner = build_scanner(config, platform_filter=args.platform)

    final_results = []
    REPORT_FILE = ""
    STATUS_FILE = args.status_file or ""

    print(Fore.CYAN + "\n[STARTING DISCOVERY]")

    try:
        report = scanner.scan(
            keyword,
            on_progress=lambda event: _on_progress(event, scanner),
            status_file=args.status_file or None,
        )
    except KeyboardInterrupt:
        signal_handler(None, None)
        return 0

    if report is None:
        print(Fore.RED + "[SCAN FAILED]")
        return 1

    print(Fore.GREEN + "\n[SCAN COMPLETED]")
    print(Fore.CYAN + "Report saved:")
    print(Fore.YELLOW + REPORT_FILE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
