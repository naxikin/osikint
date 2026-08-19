"""Matching engine: exact, normalized, partial_ratio, sequence, fuzzy
(skills.md section 7)."""

from dataclasses import dataclass
from difflib import SequenceMatcher

from rapidfuzz import fuzz

from core.logger import get_logger
from utils.normalization import normalize_text

logger = get_logger("correlation")

METHOD_EXACT = "exact"
METHOD_NORMALIZED = "normalized"
METHOD_PARTIAL_RATIO = "partial_ratio"
METHOD_SEQUENCE = "sequence_similarity"
METHOD_FUZZY = "fuzzy"

METHOD_ORDER = [
    METHOD_EXACT,
    METHOD_NORMALIZED,
    METHOD_PARTIAL_RATIO,
    METHOD_SEQUENCE,
    METHOD_FUZZY,
]

DEFAULT_THRESHOLDS = {
    METHOD_EXACT: 100,
    METHOD_NORMALIZED: 100,
    METHOD_PARTIAL_RATIO: 80,
    METHOD_SEQUENCE: 80,
    METHOD_FUZZY: 80,
}


@dataclass
class MatchResult:
    matched: bool
    method: str
    score: float
    target: str
    candidate: str

    def to_dict(self) -> dict:
        return {
            "matched": self.matched,
            "method": self.method,
            "score": round(self.score, 2),
            "target": self.target,
            "candidate": self.candidate,
        }


def sequence_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def similarity(a: str, b: str) -> float:
    return sequence_similarity(a, b)


def contains_keyword(text, keyword, threshold: int = 80) -> bool:
    if not text:
        return False

    score = fuzz.partial_ratio(
        normalize_text(text),
        normalize_text(keyword),
    )

    return score >= threshold


class UsernameMatcher:
    def __init__(self, thresholds: dict = None):
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    def _scores(self, target: str, candidate: str) -> list:
        target_norm = normalize_text(target)
        candidate_norm = normalize_text(candidate)

        scores = [
            (METHOD_EXACT, 100.0 if target == candidate else 0.0),
            (METHOD_NORMALIZED, 100.0 if target_norm == candidate_norm else 0.0),
            (
                METHOD_PARTIAL_RATIO,
                round(float(fuzz.partial_ratio(target_norm, candidate_norm)), 2),
            ),
            (
                METHOD_SEQUENCE,
                round(sequence_similarity(target_norm, candidate_norm) * 100, 2),
            ),
            (METHOD_FUZZY, round(float(fuzz.ratio(target_norm, candidate_norm)), 2)),
        ]
        return scores

    def match(self, target: str, candidate: str) -> MatchResult:
        best = None

        for method, score in self._scores(target, candidate):
            threshold = self.thresholds.get(method, 100)
            if best is None or score > best.score:
                best = MatchResult(
                    matched=False,
                    method=method,
                    score=score,
                    target=target,
                    candidate=candidate,
                )

        best.matched = best.score >= self.thresholds.get(best.method, 100)
        return best

    def match_details(self, target: str, candidate: str) -> dict:
        return self.match(target, candidate).to_dict()
