"""URL deduplication via canonicalization (skills.md section 10)."""

from utils.validators import canonicalize_url


def deduplicate(results: list) -> list:
    unique = []
    seen = set()

    for item in results:
        url = item.url if hasattr(item, "url") else item.get("url", "")
        canonical = canonicalize_url(url)

        if canonical in seen:
            continue

        seen.add(canonical)
        unique.append(item)

    return unique
