"""Entity linker: builds connection evidence between profiles
(skills.md sections 18, 19)."""

import re

from core.logger import get_logger
from core.models import Connection
from correlation.username_matcher import contains_keyword, sequence_similarity
from utils.normalization import normalize_text

logger = get_logger("correlation")

SIGNAL_KEYWORD = "keyword_match"
SIGNAL_IMAGE_HASH = "image_hash"
SIGNAL_USERNAME = "username_similarity"
SIGNAL_NAME_OVERLAP = "name_overlap"
SIGNAL_OCR_OVERLAP = "ocr_overlap"
SIGNAL_REVERSE_MATCH = "reverse_image_match"

HANDLE_RE = re.compile(r"@([A-Za-z0-9_.]{2,})")

NAME_STOPLIST = {
    normalize_text(s)
    for s in {
        "top posts", "top post", "instagram", "log in", "login",
        "sign up", "signup", "footer", "about", "contact", "menu",
        "search", "home", "profile", "this profile is private",
    }
}


def _confidence(score: float) -> str:
    if score >= 0.9:
        return "high"
    if score >= 0.8:
        return "medium"
    return "low"


def extract_handles(account_names: list, url: str = "") -> list:
    handles = []

    for name in account_names:
        for match in HANDLE_RE.findall(name):
            handles.append(match)

    if url:
        path_segments = [s for s in url.rstrip("/").split("/") if s]
        if path_segments:
            last = path_segments[-1]
            if not last.startswith("http") and 1 < len(last) <= 64:
                candidate = re.sub(r"\?.*$", "", last)
                if re.fullmatch(r"[A-Za-z0-9_.]{2,64}", candidate):
                    handles.append(candidate)

    unique = []
    for handle in handles:
        if handle not in unique:
            unique.append(handle)
    return unique


class EntityLinker:
    def __init__(self, sequence_threshold: float = 80.0):
        self.sequence_threshold = sequence_threshold

    def build_connections(
        self,
        profiles: list,
        target_keyword: str,
        known_hash_owners: dict = None,
    ) -> list:
        connections = []
        known_hash_owners = known_hash_owners or {}

        keyword_node = f"keyword:{target_keyword}"

        for profile in profiles:
            if profile.get("keyword_detected"):
                connections.append(
                    Connection(
                        source=keyword_node,
                        target=profile["url"],
                        signal=SIGNAL_KEYWORD,
                        score=1.0,
                        confidence="high",
                        evidence=target_keyword,
                    )
                )

            if profile.get("reverse_image_match") and profile.get("image_hash"):
                owner = known_hash_owners.get(profile["image_hash"])
                if owner and owner != profile["url"]:
                    connections.append(
                        Connection(
                            source=owner,
                            target=profile["url"],
                            signal=SIGNAL_REVERSE_MATCH,
                            score=1.0,
                            confidence="high",
                            evidence=profile["image_hash"],
                        )
                    )

        hash_groups = {}
        for profile in profiles:
            image_hash = profile.get("image_hash")
            if image_hash:
                hash_groups.setdefault(image_hash, []).append(profile["url"])

        for image_hash, urls in hash_groups.items():
            for i in range(len(urls)):
                for j in range(i + 1, len(urls)):
                    connections.append(
                        Connection(
                            source=urls[i],
                            target=urls[j],
                            signal=SIGNAL_IMAGE_HASH,
                            score=1.0,
                            confidence="high",
                            evidence=image_hash,
                        )
                    )

        handle_map = {
            profile["url"]: extract_handles(
                profile.get("account_names", []), profile["url"]
            )
            for profile in profiles
        }

        urls = [p["url"] for p in profiles]
        for i in range(len(urls)):
            for j in range(i + 1, len(urls)):
                handles_a = handle_map[urls[i]]
                handles_b = handle_map[urls[j]]

                for handle_a in handles_a:
                    for handle_b in handles_b:
                        norm_a = normalize_text(handle_a)
                        norm_b = normalize_text(handle_b)

                        if not norm_a or not norm_b:
                            continue

                        if norm_a == norm_b:
                            connections.append(
                                Connection(
                                    source=urls[i],
                                    target=urls[j],
                                    signal=SIGNAL_USERNAME,
                                    score=1.0,
                                    confidence="high",
                                    evidence=f"@{handle_a}",
                                )
                            )
                            continue

                        score = round(
                            sequence_similarity(norm_a, norm_b), 4
                        )
                        if score * 100 >= self.sequence_threshold:
                            connections.append(
                                Connection(
                                    source=urls[i],
                                    target=urls[j],
                                    signal=SIGNAL_USERNAME,
                                    score=score,
                                    confidence=_confidence(score),
                                    evidence=f"@{handle_a}~@{handle_b}",
                                )
                            )

        name_sets = {
            p["url"]: {
                normalize_text(name)
                for name in p.get("account_names", [])
                if normalize_text(name)
                and normalize_text(name) not in NAME_STOPLIST
                and len(normalize_text(name)) >= 3
            }
            for p in profiles
        }

        for i in range(len(urls)):
            for j in range(i + 1, len(urls)):
                overlap = name_sets[urls[i]] & name_sets[urls[j]]
                if overlap:
                    connections.append(
                        Connection(
                            source=urls[i],
                            target=urls[j],
                            signal=SIGNAL_NAME_OVERLAP,
                            score=1.0,
                            confidence="high",
                            evidence=sorted(overlap)[0],
                        )
                    )

        for i in range(len(urls)):
            ocr_text = profiles[i].get("ocr_text", "")
            if not ocr_text or not normalize_text(ocr_text):
                continue
            for j in range(len(urls)):
                if i == j:
                    continue
                for name in profiles[j].get("account_names", []):
                    if name and contains_keyword(ocr_text, name):
                        connections.append(
                            Connection(
                                source=urls[i],
                                target=urls[j],
                                signal=SIGNAL_OCR_OVERLAP,
                                score=0.8,
                                confidence="medium",
                                evidence=name,
                            )
                        )

        deduped = []
        seen = set()
        for conn in connections:
            key = (conn.source, conn.target, conn.signal)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(conn)

        deduped.sort(
            key=lambda c: (c.source, c.target, c.signal, -c.score)
        )
        return deduped
