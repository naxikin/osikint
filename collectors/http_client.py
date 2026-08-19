"""HTTP collector: lightweight first-pass fetching (skills.md section 11)."""

import re
from dataclasses import dataclass

import requests

from core.logger import get_logger
from utils.validators import is_valid_http_url

logger = get_logger("collectors")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

LOGIN_WALL_TITLES = {
    "instagram",
    "login \u2022 instagram",
    "log in",
    "login",
    "sign in",
    "sign up",
    "facebook",
    "x",
    "tiktok",
    "github",
    "linkedin",
    "gitlab",
    "checkpoint required",
    "attention required",
    "please wait",
}

LOGIN_WALL_MARKERS = (
    'action="/accounts/login"',
    'action="/login"',
    'id="loginform"',
    'class="loginform"',
    'name="login"',
    'id="login-form"',
)

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def looks_like_login_wall(html: str) -> bool:
    lowered = html.lower()[:400000]

    match = _TITLE_RE.search(lowered)
    if match:
        title = match.group(1).strip()
        if title in LOGIN_WALL_TITLES:
            return True

    return any(marker in lowered for marker in LOGIN_WALL_MARKERS)


@dataclass
class CollectResult:
    html: str = ""
    final_url: str = ""
    sufficient: bool = False

    def to_dict(self) -> dict:
        return {
            "html_length": len(self.html),
            "final_url": self.final_url,
            "sufficient": self.sufficient,
        }


class HTTPCollector:
    def __init__(
        self,
        timeout: int = 30,
        min_html_length: int = 2000,
        headers: dict = None,
        session: requests.Session = None,
    ):
        self.timeout = timeout
        self.min_html_length = min_html_length
        self.headers = headers or HEADERS
        self.session = session

    def fetch(self, url: str) -> CollectResult:
        if not is_valid_http_url(url):
            return CollectResult()

        try:
            requester = self.session or requests
            response = requester.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
            )
            html = response.text if response.ok else ""

            wall = looks_like_login_wall(html)
            result = CollectResult(
                html=html,
                final_url=response.url,
                sufficient=(
                    len(html) >= self.min_html_length and not wall
                ),
            )
            logger.debug(
                "http fetch %s -> %d chars (sufficient=%s, wall=%s)",
                url,
                len(html),
                result.sufficient,
                wall,
            )
            return result
        except requests.RequestException as exc:
            logger.warning("http fetch failed for %s: %s", url, exc)
            return CollectResult()
