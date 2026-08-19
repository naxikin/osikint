"""Characterization tests: profile extraction (legacy)."""

from bs4 import BeautifulSoup

HTML = """
<html>
<head>
    <title>Jane Doe (@jane) | Instagram</title>
    <meta property="og:title" content="Jane Doe Profile"/>
    <meta name="twitter:title" content="Jane Doe Twitter"/>
    <meta property="og:image" content="https://cdn.example.com/avatar.jpg"/>
</head>
<body>
    <h1>Jane Doe</h1>
    <h2>About</h2>
    <h3>Contact</h3>
</body>
</html>
"""


def test_extract_account_names_legacy(legacy):
    soup = BeautifulSoup(HTML, "html.parser")
    names = legacy.extract_account_names(soup)
    assert set(names) == {
        "Jane Doe (@jane) | Instagram",
        "Jane Doe Profile",
        "Jane Doe Twitter",
        "Jane Doe",
        "About",
        "Contact",
    }


def test_extract_profile_image_legacy(legacy):
    soup = BeautifulSoup(HTML, "html.parser")
    assert legacy.extract_profile_image(soup) == "https://cdn.example.com/avatar.jpg"


def test_extract_profile_image_missing(legacy):
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    assert legacy.extract_profile_image(soup) is None
