"""Repository search for GitHub/GitLab (skills.md section 8).

Username-checking (discovery/username_checker.py) only probes a user's
profile page - it never finds a matching repository owned by someone
else, or named after the keyword under a different account. This hits
each platform's public REST API directly (structured JSON, no
scraping), which is both more complete and more reliable than the
DDGS backend for this specific case.

Only public search endpoints are used - no authentication, no access
to private repositories (skills.md section 12/35).
"""

import requests

from core.logger import get_logger
from core.models import SearchResult

logger = get_logger("discovery")


class RepoSearch:
    def search(self, keyword: str, limit: int) -> list:
        raise NotImplementedError


class GitHubRepoSearch(RepoSearch):
    API_URL = "https://api.github.com/search/repositories"

    def __init__(self, headers: dict = None, timeout: int = 15,
                 session: requests.Session = None):
        self.headers = {
            **(headers or {}),
            "Accept": "application/vnd.github+json",
        }
        self.timeout = timeout
        self.session = session

    def search(self, keyword: str, limit: int = 10) -> list:
        if not keyword:
            return []

        requester = self.session or requests
        try:
            response = requester.get(
                self.API_URL,
                params={"q": keyword, "per_page": limit},
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning(
                "github repo search failed for %r: %s", keyword, exc
            )
            return []

        results = []
        for item in (data.get("items") or [])[:limit]:
            results.append(
                SearchResult(
                    title=item.get("full_name", ""),
                    url=item.get("html_url", ""),
                    body=item.get("description") or "",
                    source="github",
                ).to_dict()
            )
        logger.info(
            "[REPO SEARCH] github -> %d repositories for %r",
            len(results), keyword,
        )
        return results


class GitLabRepoSearch(RepoSearch):
    API_URL = "https://gitlab.com/api/v4/projects"

    def __init__(self, headers: dict = None, timeout: int = 15,
                 session: requests.Session = None):
        self.headers = headers or {}
        self.timeout = timeout
        self.session = session

    def search(self, keyword: str, limit: int = 10) -> list:
        if not keyword:
            return []

        requester = self.session or requests
        try:
            response = requester.get(
                self.API_URL,
                params={
                    "search": keyword,
                    "per_page": limit,
                    "order_by": "last_activity_at",
                },
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning(
                "gitlab repo search failed for %r: %s", keyword, exc
            )
            return []

        results = []
        for item in (data or [])[:limit]:
            results.append(
                SearchResult(
                    title=item.get(
                        "path_with_namespace", item.get("name", "")
                    ),
                    url=item.get("web_url", ""),
                    body=item.get("description") or "",
                    source="gitlab",
                ).to_dict()
            )
        logger.info(
            "[REPO SEARCH] gitlab -> %d repositories for %r",
            len(results), keyword,
        )
        return results
