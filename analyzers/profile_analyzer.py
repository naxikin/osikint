"""Profile analyzer orchestrator with injected services
(skills.md section 14)."""

from core.logger import get_logger
from core.models import ProfileResult
from correlation.image_matcher import ImageMatcher
from correlation.username_matcher import contains_keyword
from utils.validators import platform_from_url

logger = get_logger("analyzers")


class ProfileAnalyzer:
    def __init__(
        self,
        collector,
        extractor,
        matcher=None,
        image_analyzer=None,
        ocr_engine=None,
        correlation_engine=None,
        risk_engine=None,
        image_downloader=None,
        platform_domains: dict = None,
        image_dir_factory=None,
    ):
        self.collector = collector
        self.extractor = extractor
        self.matcher = matcher
        self.image_analyzer = image_analyzer
        self.ocr_engine = ocr_engine
        self.correlation_engine = correlation_engine or ImageMatcher()
        self.risk_engine = risk_engine
        self.image_downloader = image_downloader
        self.platform_domains = platform_domains or {}
        self.image_dir_factory = image_dir_factory

    def analyze(
        self,
        profile: dict,
        keyword: str,
        known_hashes: dict,
        image_dir: str,
    ) -> ProfileResult:
        url = profile["url"]

        html, final_url = self.collector.fetch(url)

        if not html:
            return None

        extraction = self.extractor.extract(html, final_url or url)

        account_names = extraction.account_names

        keyword_detected = False
        for name in account_names:
            if contains_keyword(name, keyword):
                keyword_detected = True
                logger.info("[ACCOUNT NAME DETECTED] %s", name)

        if contains_keyword(extraction.page_text, keyword):
            keyword_detected = True

        profile_image = extraction.profile_image

        image_hash = None
        reverse_match = False
        ocr_text = ""
        image_analysis = {}
        ocr_analysis = {}

        if profile_image and self.image_downloader is not None:
            filename = self.image_downloader.download(
                profile_image, image_dir
            )

            if filename:
                if self.image_analyzer is not None:
                    analysis = self.image_analyzer.analyze(filename)
                    image_analysis = analysis.to_dict()
                    image_hash = analysis.average_hash

                if self.ocr_engine is not None:
                    ocr_result = self.ocr_engine.extract_text(filename)
                    ocr_text = ocr_result.text
                    ocr_analysis = ocr_result.to_dict()

                if contains_keyword(ocr_text, keyword):
                    logger.info("[OCR DETECTED]")

                if self.correlation_engine.reverse_match(
                    image_hash, known_hashes
                ):
                    reverse_match = True
                    logger.info("[REVERSE IMAGE MATCH]")
                elif image_hash:
                    known_hashes[image_hash] = final_url or url

        match_details = {}
        if self.matcher is not None:
            match_details = self.matcher.match_details(keyword, url)

        risk_result = None
        if self.risk_engine is not None:
            risk_result = self.risk_engine.evaluate(
                keyword_detected=keyword_detected,
                ocr_detected=bool(
                    ocr_text and contains_keyword(ocr_text, keyword)
                ),
                reverse_image_match=reverse_match,
            )

        platform = platform_from_url(url, self.platform_domains)

        result = ProfileResult(
            url=final_url or url,
            account_names=account_names,
            keyword_detected=keyword_detected,
            profile_image=profile_image,
            image_hash=image_hash,
            ocr_text=ocr_text,
            reverse_image_match=reverse_match,
            risk_score=risk_result.score if risk_result else 0,
            platform=platform,
            original_url=url,
            final_url=final_url or url,
            match_details=match_details,
            image_analysis=image_analysis,
            ocr_analysis=ocr_analysis,
            correlation={},
            risk_details=(
                risk_result.to_dict() if risk_result else {}
            ),
        )

        return result
