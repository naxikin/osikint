"""Image matching: hash comparison with evidence states
(skills.md section 18)."""

from dataclasses import dataclass

from core.logger import get_logger

logger = get_logger("correlation")

NO_MATCH = "NO_MATCH"
POSSIBLE_MATCH = "POSSIBLE_MATCH"
PROBABLE_MATCH = "PROBABLE_MATCH"
HIGH_SIMILARITY = "HIGH_SIMILARITY"

DEFAULT_DISTANCES = {
    "high_similarity_distance": 0,
    "probable_match_distance": 5,
    "possible_match_distance": 10,
}


@dataclass
class ImageMatchResult:
    matched: bool
    method: str
    distance: int = 0
    similarity: float = 1.0
    state: str = NO_MATCH

    def to_dict(self) -> dict:
        return {
            "matched": self.matched,
            "method": self.method,
            "distance": self.distance,
            "similarity": self.similarity,
            "state": self.state,
        }


def _hamming_distance_hex(hash_a: str, hash_b: str) -> int:
    if len(hash_a) != len(hash_b):
        return 64
    return sum(bin(int(a, 16) ^ int(b, 16)).count("1") for a, b in zip(hash_a, hash_b))


class ImageMatcher:
    def __init__(self, distances: dict = None):
        self.distances = {**DEFAULT_DISTANCES, **(distances or {})}

    def state_for_distance(self, distance: int) -> str:
        if distance <= self.distances["high_similarity_distance"]:
            return HIGH_SIMILARITY
        if distance <= self.distances["probable_match_distance"]:
            return PROBABLE_MATCH
        if distance <= self.distances["possible_match_distance"]:
            return POSSIBLE_MATCH
        return NO_MATCH

    def compare(self, hash_a: str, hash_b: str) -> ImageMatchResult:
        distance = _hamming_distance_hex(hash_a, hash_b)
        similarity = max(0.0, 1.0 - distance / 64.0)
        state = self.state_for_distance(distance)
        return ImageMatchResult(
            matched=state != NO_MATCH,
            method="ahash",
            distance=distance,
            similarity=round(similarity, 4),
            state=state,
        )

    def reverse_match(self, profile_hash: str, known_hashes: dict) -> bool:
        if not profile_hash:
            return False
        return profile_hash in known_hashes
