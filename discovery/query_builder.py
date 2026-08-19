"""Search query generation (skills.md section 8)."""

import itertools

from utils.normalization import LEET_MAP, normalize_text

LEGACY_QUERY_TEMPLATES = [
    '"{keyword}" site:{site}',
    "inurl:{keyword} site:{site}",
    'intitle:"{keyword}" site:{site}',
]


def build_queries(keyword: str, site: str) -> list:
    return [
        template.format(keyword=keyword, site=site)
        for template in LEGACY_QUERY_TEMPLATES
    ]


def build_leet_variants(keyword: str, limit: int = 16) -> list:
    normalized = normalize_text(keyword)
    if not normalized:
        return []

    char_choices = []
    for ch in normalized:
        if ch == "a":
            char_choices.append([ch, "4", "@"])
        elif ch == "i":
            char_choices.append([ch, "1", "!"])
        elif ch == "e":
            char_choices.append([ch, "3"])
        elif ch == "o":
            char_choices.append([ch, "0"])
        elif ch == "s":
            char_choices.append([ch, "5", "$"])
        elif ch == "t":
            char_choices.append([ch, "7"])
        else:
            char_choices.append([ch])

    variants = []
    for combo in itertools.product(*char_choices):
        variant = "".join(combo)
        if variant != normalized:
            variants.append(variant)
            if len(variants) >= limit:
                break
    return variants


def build_all_queries(
    keyword: str,
    site: str,
    include_leet: bool = False,
    leet_limit: int = 16,
) -> list:
    queries = build_queries(keyword, site)
    if include_leet:
        for variant in build_leet_variants(keyword, limit=leet_limit):
            queries.append(f'"{variant}" site:{site}')
    return queries
