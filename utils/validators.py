"""URL validation and canonicalization (skills.md section 10)."""

from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_source", "fbclid", "gclid", "ref", "ref_src", "igshid",
}


def is_valid_http_url(url: str) -> bool:
    if not url:
        return False
    parts = urlsplit(url)
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    path = parts.path
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")

    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(query_pairs)

    return urlunsplit((scheme, netloc, path, query, ""))


def platform_from_url(url: str, platform_domains: dict) -> str:
    if not url:
        return ""
    netloc = urlsplit(url).netloc.lower()
    for name, domain in platform_domains.items():
        if netloc == domain or netloc.endswith("." + domain):
            return name
    return "unknown"
