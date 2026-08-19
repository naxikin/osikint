"""Playwright dynamic page collector (skills.md section 12)."""

import time
from dataclasses import dataclass

from core.logger import get_logger
from utils.validators import is_valid_http_url

logger = get_logger("collectors")


@dataclass
class BrowserSettings:
    headless: bool = True
    timeout: int = 60000
    locale: str = "en-US"
    viewport: dict = None
    wait_until: str = "networkidle"
    settle_seconds: int = 3

    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1920, "height": 1080}


class PlaywrightCollector:
    def __init__(
        self,
        settings: BrowserSettings = None,
        user_agent: str = None,
        fetch_fn=None,
    ):
        self.settings = settings or BrowserSettings()
        self.user_agent = user_agent
        self.fetch_fn = fetch_fn

    def fetch(self, url: str):
        if not is_valid_http_url(url):
            return None, None

        if self.fetch_fn is not None:
            return self.fetch_fn(url)

        from playwright.sync_api import sync_playwright

        settings = self.settings

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=settings.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled"
                    ],
                )

                context_kwargs = {
                    "viewport": settings.viewport,
                    "locale": settings.locale,
                }
                if self.user_agent:
                    context_kwargs["user_agent"] = self.user_agent

                context = browser.new_context(**context_kwargs)

                page = context.new_page()
                page.add_init_script(
                    """
                    Object.defineProperty(
                        navigator,
                        'webdriver',
                        {
                            get: () => undefined
                        }
                    );
                    """
                )

                page.goto(
                    url,
                    wait_until=settings.wait_until,
                    timeout=settings.timeout,
                )

                if settings.settle_seconds:
                    time.sleep(settings.settle_seconds)

                html = page.content()
                final_url = page.url

                browser.close()

                return html, final_url
        except Exception as exc:
            logger.warning("playwright fetch failed for %s: %s", url, exc)
            return None, None

    def screenshot(self, url: str, filename: str,
                   timeout: int = 30000) -> bool:
        """Captures a page screenshot as evidence for failed profiles."""
        if not is_valid_http_url(url):
            return False

        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.settings.headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(
                    viewport=self.settings.viewport,
                    locale=self.settings.locale,
                )
                page = context.new_page()

                try:
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=timeout,
                    )
                except Exception as exc:
                    logger.warning(
                        "screenshot goto failed for %s: %s", url, exc
                    )

                page.wait_for_timeout(1500)
                page.screenshot(path=filename)
                browser.close()

                logger.info("evidence screenshot saved for %s", url)
                return True
        except Exception as exc:
            logger.warning("screenshot failed for %s: %s", url, exc)
            return False


class FallbackCollector:
    """HTTP first, Playwright only when content is insufficient
    (skills.md section 11)."""

    def __init__(
        self,
        http_collector,
        playwright_collector,
        http_first: bool = True,
    ):
        self.http_collector = http_collector
        self.playwright_collector = playwright_collector
        self.http_first = http_first

    def fetch(self, url: str):
        if self.http_first:
            result = self.http_collector.fetch(url)
            if result.sufficient:
                return result.html, result.final_url

        return self.playwright_collector.fetch(url)
