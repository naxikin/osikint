"""Normalization engine (skills.md section 6)."""

import re
from dataclasses import dataclass

LEET_MAP = {
    "4": "a",
    "@": "a",
    "3": "e",
    "1": "i",
    "!": "i",
    "0": "o",
    "$": "s",
    "5": "s",
    "7": "t",
}


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()

    for k, v in LEET_MAP.items():
        text = text.replace(k, v)

    text = re.sub(r"[^a-z0-9]", "", text)

    return text


@dataclass
class NormalizedIdentifier:
    original: str
    normalized: str


def normalize_identifier(text: str) -> NormalizedIdentifier:
    return NormalizedIdentifier(
        original=text or "",
        normalized=normalize_text(text),
    )
