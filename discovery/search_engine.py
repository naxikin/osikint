"""Search engine wrapper and account discovery (skills.md section 8)."""

from core.exceptions import DiscoveryError
from core.logger import get_logger
from core.models import SearchResult
from correlation.username_matcher import contains_keyword
from discovery.deduplicator import deduplicate
from discovery.query_builder import build_all_queries

logger = get_logger("discovery")


class SearchEngine:
    def search(self, query: str, region: str, max_results: int) -> list:
        raise NotImplementedError


class DDGSSearchEngine(SearchEngine):
    def __init__(self, ddgs_cls=None, region: str = "id-id",
                 max_results: int = 30):
        self.ddgs_cls = ddgs_cls
        self.region = region
        self.max_results = max_results

    def _ddgs(self):
        if self.ddgs_cls is None:
            from ddgs import DDGS

            return DDGS()
        return self.ddgs_cls()

    def search(self, query: str, region=None, max_results=None) -> list:
        region = region or self.region
        max_results = max_results or self.max_results

        try:
            with self._ddgs() as ddgs:
                raw = ddgs.text(
                    query,
                    region=region,
                    max_results=max_results,
                )
        except Exception as exc:  # backend instability is expected
            logger.warning("search backend failed for %r: %s", query, exc)
            return []

        results = []
        for r in raw:
            results.append(
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    body=r.get("body", ""),
                    source=r.get("source", "") or "",
                ).to_dict()
            )
        return results


def search_social_accounts(
    keyword: str,
    sites: list,
    engine: SearchEngine,
    include_leet: bool = False,
) -> list:
    discovered = []

    for site in sites:
        queries = build_all_queries(
            keyword, site, include_leet=include_leet
        )

        for query in queries:
            logger.info("[SEARCH] %s", query)

            for result in engine.search(query):
                detected = False

                if contains_keyword(result.get("title", ""), keyword):
                    detected = True

                if contains_keyword(result.get("body", ""), keyword):
                    detected = True

                if contains_keyword(result.get("url", ""), keyword):
                    detected = True

                if detected:
                    result["source"] = site
                    discovered.append(result)

    return deduplicate(discovered)
