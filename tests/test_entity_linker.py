"""Unit tests: entity linker connections."""

from correlation.entity_linker import (
    SIGNAL_IMAGE_HASH,
    SIGNAL_KEYWORD,
    SIGNAL_USERNAME,
    EntityLinker,
    extract_handles,
)


def _profile(url, **kwargs):
    profile = {
        "url": url,
        "account_names": [],
        "keyword_detected": False,
        "profile_image": None,
        "image_hash": None,
        "ocr_text": "",
        "reverse_image_match": False,
        "risk_score": 0,
    }
    profile.update(kwargs)
    return profile


def test_extract_handles_from_names():
    handles = extract_handles(
        ["JOMBIE_420 (@stending_malakaji) • Instagram"],
        "https://instagram.com/stending_malakaji/",
    )
    assert handles == ["stending_malakaji"]


def test_extract_handles_from_url():
    handles = extract_handles([], "https://instagram.com/nk_99malakaji/")
    assert handles == ["nk_99malakaji"]


def test_keyword_connection():
    linker = EntityLinker()
    profiles = [
        _profile("https://a.example/u1", keyword_detected=True),
        _profile("https://b.example/u2", keyword_detected=False),
    ]
    connections = linker.build_connections(profiles, "malakaji", {})

    keyword_edges = [
        c for c in connections if c.signal == SIGNAL_KEYWORD
    ]
    assert len(keyword_edges) == 1
    assert keyword_edges[0].target == "https://a.example/u1"
    assert keyword_edges[0].source == "keyword:malakaji"


def test_image_hash_connection():
    linker = EntityLinker()
    profiles = [
        _profile("https://a.example/u1", image_hash="abcd1234"),
        _profile("https://b.example/u2", image_hash="abcd1234"),
        _profile("https://c.example/u3", image_hash="zzzz9999"),
    ]
    connections = linker.build_connections(profiles, "kw", {})

    image_edges = [
        c for c in connections if c.signal == SIGNAL_IMAGE_HASH
    ]
    assert len(image_edges) == 1
    assert image_edges[0].evidence == "abcd1234"


def test_username_similarity_connection():
    linker = EntityLinker()
    profiles = [
        _profile(
            "https://instagram.com/malakaji/",
            account_names=["malakaji"],
        ),
        _profile(
            "https://instagram.com/malakaji99/",
            account_names=["malakaji99"],
        ),
    ]
    connections = linker.build_connections(profiles, "kw", {})

    username_edges = [
        c for c in connections if c.signal == SIGNAL_USERNAME
    ]
    assert len(username_edges) >= 1
    assert all(c.score >= 0.8 for c in username_edges)


def test_connection_schema():
    linker = EntityLinker()
    connections = linker.build_connections(
        [_profile("https://a.example/u", keyword_detected=True)],
        "malakaji",
        {},
    )
    conn = connections[0].to_dict()
    assert set(conn.keys()) == {
        "source", "target", "signal", "score", "confidence", "evidence",
    }
