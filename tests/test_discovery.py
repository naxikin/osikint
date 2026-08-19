"""Characterization tests: discovery, query generation, dedup (legacy)."""


class FakeDDGS:
    def __init__(self, results_by_query):
        self.results_by_query = results_by_query

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, region=None, max_results=None):
        return self.results_by_query.get(query, [])


def _site(legacy):
    return legacy.TARGET_SITES[0]


def test_query_generation(legacy, monkeypatch):
    monkeypatch.setattr(legacy, "TARGET_SITES", ["instagram.com"])

    fake = FakeDDGS(
        {
            '"malakaji" site:instagram.com': [],
            "inurl:malakaji site:instagram.com": [],
            'intitle:"malakaji" site:instagram.com': [],
        }
    )
    monkeypatch.setattr(legacy, "DDGS", lambda: fake)

    legacy.search_social_accounts("malakaji")

    assert set(fake.results_by_query.keys()) == {
        '"malakaji" site:instagram.com',
        "inurl:malakaji site:instagram.com",
        'intitle:"malakaji" site:instagram.com',
    }


def test_search_filters_and_dedup(legacy, monkeypatch):
    fake = FakeDDGS(
        {
            '"malakaji" site:instagram.com': [
                {
                    "href": "https://instagram.com/malakaji",
                    "title": "Malakaji Official",
                    "body": "the official malakaji account",
                },
                {
                    "href": "https://instagram.com/malakaji",
                    "title": "Malakaji Official",
                    "body": "duplicate url",
                },
                {
                    "href": "https://instagram.com/other",
                    "title": "Unrelated",
                    "body": "nothing here",
                },
            ],
            "inurl:malakaji site:instagram.com": [],
            'intitle:"malakaji" site:instagram.com': [],
        }
    )
    monkeypatch.setattr(legacy, "DDGS", lambda: fake)
    monkeypatch.setattr(legacy, "TARGET_SITES", ["instagram.com"])

    results = legacy.search_social_accounts("malakaji")

    assert len(results) == 1
    assert results[0]["url"] == "https://instagram.com/malakaji"
    assert results[0]["source"] == "instagram.com"
    assert set(results[0].keys()) == {"title", "url", "body", "source"}


def test_search_error_does_not_raise(legacy, monkeypatch):
    class BrokenDDGS(FakeDDGS):
        def text(self, query, region=None, max_results=None):
            raise RuntimeError("search backend down")

    monkeypatch.setattr(legacy, "DDGS", lambda: BrokenDDGS({}))
    monkeypatch.setattr(legacy, "TARGET_SITES", ["instagram.com"])

    assert legacy.search_social_accounts("malakaji") == []
