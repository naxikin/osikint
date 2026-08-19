"""Deterministic hashing helpers (skills.md section 16)."""

import hashlib


def sha256_hex(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_url(url: str) -> str:
    return sha256_hex(url)


def image_filename(url: str, extension: str = ".jpg") -> str:
    return sha256_url(url) + extension
