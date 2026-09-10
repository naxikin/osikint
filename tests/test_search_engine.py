"""Unit tests: DDGSSearchEngine retry on transient backend failures.

The free DDGS/DuckDuckGo backend intermittently fails TLS/connection
handshakes independent of the query - a short bounded retry recovers
most of those instead of silently dropping a platform from discovery.
"""

from discovery.search_engine import DDGSSearchEngine


class _FlakyDDGS:
    """Fails `fail_times` calls, then returns `results`."""

    def __init__(self, fail_times, results):
        self.fail_times = fail_times
        self.results = results
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, region=None, max_results=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ConnectionError("transient TLS failure")
        return self.results


def test_search_retries_and_recovers_from_transient_failure():
    fake = _FlakyDDGS(
        fail_times=1,
        results=[{"href": "https://x.com/linkaja", "title": "t", "body": "b"}],
    )
    engine = DDGSSearchEngine(
        ddgs_cls=lambda: fake, retries=2, retry_delay=0
    )

    results = engine.search("linkaja site:x.com")

    assert fake.calls == 2
    assert len(results) == 1
    assert results[0]["url"] == "https://x.com/linkaja"


def test_search_gives_up_after_exhausting_retries():
    fake = _FlakyDDGS(fail_times=99, results=[])
    engine = DDGSSearchEngine(
        ddgs_cls=lambda: fake, retries=2, retry_delay=0
    )

    results = engine.search("linkaja site:gitlab.com")

    assert results == []
    assert fake.calls == 3  # initial attempt + 2 retries


def test_search_succeeds_on_first_try_without_retrying():
    fake = _FlakyDDGS(fail_times=0, results=[])
    engine = DDGSSearchEngine(
        ddgs_cls=lambda: fake, retries=2, retry_delay=0
    )

    engine.search("linkaja site:instagram.com")

    assert fake.calls == 1
