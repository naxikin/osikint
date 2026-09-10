"""Direct username existence check across configured platforms
(skills.md section 8).

Search-engine discovery only finds profiles the backend has indexed,
which can lag or miss newer/less-popular accounts. This probes each
enabled platform's profile URL directly with the target as a username
(`https://github.com/{username}`, etc.), so an existing-but-unindexed
profile is still discovered.

This only reads a public profile page's existence/content - it never
attempts to bypass login, CAPTCHA, or any access control
(skills.md section 12/35).
"""

import requests

from core.logger import get_logger
from core.models import SearchResult

logger = get_logger("discovery")

NOT_FOUND_MARKERS = (
    "page not found",
    "sorry, this page isn't available",
    "content isn't available",
    "user not found",
    "profile not found",
    "doesn't exist",
    "does not exist",
    "this account doesn't exist",
)


class UsernameChecker:
    """Probes `{platform}/{username}`-style URLs for existence."""

    def __init__(
        self,
        headers: dict = None,
        timeout: int = 15,
        session: requests.Session = None,
    ):
        self.headers = headers or {}
        self.timeout = timeout
        self.session = session

    def _exists(self, url: str) -> tuple:
        requester = self.session or requests
        try:
            response = requester.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            logger.debug("username check failed for %s: %s", url, exc)
            return False, url

        if response.status_code != 200:
            return False, response.url

        lowered = response.text[:20000].lower()
        if any(marker in lowered for marker in NOT_FOUND_MARKERS):
            return False, response.url

        return True, response.url

    def check(self, username: str, platforms: dict) -> list:
        """`platforms`: {name: {domain, profile_url_template, ...}}.
        Returns SearchResult-shaped dicts for platforms where the
        username resolves to an existing profile."""
        results = []

        if not username or " " in username:
            # profile URLs never contain spaces; skip multi-word
            # targets (full names, phrases) instead of probing junk
            # URLs on every platform.
            return results

        for name, spec in platforms.items():
            template = spec.get("profile_url_template")
            if not template:
                continue

            url = template.format(username=username)
            exists, final_url = self._exists(url)
            if not exists:
                continue

            logger.info("[USERNAME CHECK] found %s -> %s", name, final_url)
            results.append(
                SearchResult(
                    title=f"{name}:{username}",
                    url=final_url,
                    body="direct username probe",
                    source=name,
                ).to_dict()
            )

        return results
