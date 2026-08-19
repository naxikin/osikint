"""Profile extraction from HTML (skills.md section 13)."""

from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from core.logger import get_logger

logger = get_logger("analyzers")


@dataclass
class ExtractionResult:
    account_names: list = field(default_factory=list)
    profile_image: str = None
    page_text: str = ""
    final_url: str = ""


def extract_account_names(soup: BeautifulSoup) -> list:
    names = []

    if soup.title and soup.title.string:
        names.append(soup.title.string.strip())

    og_title = soup.find("meta", property="og:title")
    if og_title:
        names.append(og_title.get("content", ""))

    twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
    if twitter_title:
        names.append(twitter_title.get("content", ""))

    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            names.append(text)

    return list(set(names))


def extract_profile_image(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", property="og:image")
    if meta:
        return meta.get("content")
    return None


def extract_page_text(soup: BeautifulSoup) -> str:
    return soup.get_text()


class ProfileExtractor:
    def extract(
        self,
        html: str,
        final_url: str = "",
    ) -> ExtractionResult:
        soup = BeautifulSoup(html, "html.parser")

        return ExtractionResult(
            account_names=extract_account_names(soup),
            profile_image=extract_profile_image(soup),
            page_text=extract_page_text(soup),
            final_url=final_url,
        )
