"""Unit tests: HTTP collector + login wall detection (no network)."""

from collectors.http_client import (
    HTTPCollector,
    looks_like_login_wall,
)


def test_login_wall_title_detected():
    html = "<html><head><title>Instagram</title></head><body>login form</body></html>" * 100
    assert looks_like_login_wall(html) is True


def test_login_wall_marker_detected():
    html = (
        "<html><head><title>Some Site</title></head>"
        '<body><form action="/accounts/login" method="post"></form>'
        "</body></html>"
    ) * 50
    assert looks_like_login_wall(html) is True


def test_real_profile_not_wall():
    html = (
        "<html><head><title>LinkAja Indonesia (@linkaja) \u2022 "
        "Instagram photos and videos</title></head>"
        "<body><h1>LinkAja</h1></body></html>"
    ) * 100
    assert looks_like_login_wall(html) is False


class FakeResponse:
    def __init__(self, html, ok=True, url="https://a.example/final"):
        self.text = html
        self.ok = ok
        self.url = url


class FakeSession:
    def __init__(self, response):
        self.response = response

    def get(self, url, headers=None, timeout=None):
        return self.response


def test_http_collector_wall_is_insufficient():
    wall_html = (
        "<html><head><title>Instagram</title></head>"
        "<body>" + "x" * 5000 + "</body></html>"
    )
    collector = HTTPCollector(
        session=FakeSession(FakeResponse(wall_html))
    )
    result = collector.fetch("https://www.instagram.com/linkaja/")
    assert result.sufficient is False


def test_http_collector_real_page_is_sufficient():
    real_html = (
        "<html><head><title>LinkAja Indonesia (@linkaja)</title></head>"
        "<body>" + "y" * 5000 + "</body></html>"
    )
    collector = HTTPCollector(
        session=FakeSession(FakeResponse(real_html))
    )
    result = collector.fetch("https://www.instagram.com/linkaja/")
    assert result.sufficient is True
    assert result.final_url == "https://a.example/final"
