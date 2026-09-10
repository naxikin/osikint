"""Unit tests: GitHub/GitLab repository search (skills.md section 8).
No network access - a fake session stands in for requests.Session."""

import requests

from discovery.repo_search import GitHubRepoSearch, GitLabRepoSearch


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params))
        return self.response


def test_github_repo_search_parses_items():
    session = _FakeSession(_FakeResponse({
        "items": [
            {
                "full_name": "malakaji/awesome-project",
                "html_url": "https://github.com/malakaji/awesome-project",
                "description": "an awesome project",
            },
            {
                "full_name": "other/unrelated",
                "html_url": "https://github.com/other/unrelated",
                "description": None,
            },
        ]
    }))
    searcher = GitHubRepoSearch(session=session)
    results = searcher.search("malakaji", limit=10)

    assert len(results) == 2
    assert results[0]["title"] == "malakaji/awesome-project"
    assert results[0]["url"] == "https://github.com/malakaji/awesome-project"
    assert results[0]["source"] == "github"
    assert results[1]["body"] == ""


def test_github_repo_search_respects_limit():
    items = [
        {"full_name": f"x/repo{i}", "html_url": f"https://github.com/x/repo{i}"}
        for i in range(5)
    ]
    session = _FakeSession(_FakeResponse({"items": items}))
    searcher = GitHubRepoSearch(session=session)
    results = searcher.search("x", limit=2)

    assert len(results) == 2


def test_github_repo_search_handles_request_exception():
    class _BoomSession:
        def get(self, *args, **kwargs):
            raise requests.RequestException("network down")

    searcher = GitHubRepoSearch(session=_BoomSession())
    assert searcher.search("malakaji") == []


def test_github_repo_search_handles_http_error_status():
    session = _FakeSession(_FakeResponse({}, status_code=403))
    searcher = GitHubRepoSearch(session=session)
    assert searcher.search("malakaji") == []


def test_github_repo_search_empty_keyword():
    session = _FakeSession(_FakeResponse({"items": []}))
    searcher = GitHubRepoSearch(session=session)
    assert searcher.search("") == []
    assert session.calls == []


def test_gitlab_repo_search_parses_projects():
    session = _FakeSession(_FakeResponse([
        {
            "path_with_namespace": "malakaji/tools",
            "web_url": "https://gitlab.com/malakaji/tools",
            "description": "cli tools",
        },
    ]))
    searcher = GitLabRepoSearch(session=session)
    results = searcher.search("malakaji", limit=10)

    assert len(results) == 1
    assert results[0]["title"] == "malakaji/tools"
    assert results[0]["url"] == "https://gitlab.com/malakaji/tools"
    assert results[0]["source"] == "gitlab"


def test_gitlab_repo_search_handles_request_exception():
    class _BoomSession:
        def get(self, *args, **kwargs):
            raise requests.RequestException("network down")

    searcher = GitLabRepoSearch(session=_BoomSession())
    assert searcher.search("malakaji") == []
