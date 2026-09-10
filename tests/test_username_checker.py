"""Unit tests: direct username existence check (skills.md section 8).
No network access - a fake session stands in for requests.Session."""

import requests

from discovery.username_checker import UsernameChecker

PLATFORMS = {
    "github": {
        "domain": "github.com",
        "profile_url_template": "https://github.com/{username}",
    },
    "gitlab": {
        "domain": "gitlab.com",
        "profile_url_template": "https://gitlab.com/{username}",
    },
    "no_template": {"domain": "example.com"},
}


class _FakeResponse:
    def __init__(self, status_code=200, text="", url=""):
        self.status_code = status_code
        self.text = text
        self.url = url


class _FakeSession:
    def __init__(self, responses: dict):
        self.responses = responses
        self.calls = []

    def get(self, url, headers=None, timeout=None, allow_redirects=None):
        self.calls.append(url)
        return self.responses[url]


def test_check_returns_existing_profiles():
    session = _FakeSession(
        {
            "https://github.com/malakaji": _FakeResponse(
                200, "<html>profile</html>", "https://github.com/malakaji"
            ),
            "https://gitlab.com/malakaji": _FakeResponse(
                404, "not found", "https://gitlab.com/malakaji"
            ),
        }
    )
    checker = UsernameChecker(session=session)
    results = checker.check("malakaji", PLATFORMS)

    assert len(results) == 1
    assert results[0]["source"] == "github"
    assert results[0]["url"] == "https://github.com/malakaji"


def test_check_skips_platforms_without_template():
    session = _FakeSession(
        {
            "https://github.com/malakaji": _FakeResponse(200, "ok"),
            "https://gitlab.com/malakaji": _FakeResponse(200, "ok"),
        }
    )
    checker = UsernameChecker(session=session)
    checker.check("malakaji", PLATFORMS)

    assert "no_template" not in [c for c in session.calls]


def test_check_treats_not_found_marker_as_missing():
    session = _FakeSession(
        {
            "https://github.com/ghostuser": _FakeResponse(
                200, "Sorry, this page isn't available."
            ),
            "https://gitlab.com/ghostuser": _FakeResponse(404, ""),
        }
    )
    checker = UsernameChecker(session=session)
    results = checker.check("ghostuser", PLATFORMS)

    assert results == []


def test_check_skips_multi_word_targets():
    session = _FakeSession({})
    checker = UsernameChecker(session=session)
    results = checker.check("jane doe", PLATFORMS)

    assert results == []
    assert session.calls == []


def test_check_handles_request_exception():
    class _BoomSession:
        def get(self, *args, **kwargs):
            raise requests.RequestException("network down")

    checker = UsernameChecker(session=_BoomSession())
    results = checker.check("malakaji", PLATFORMS)

    assert results == []
