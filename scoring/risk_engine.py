"""Risk engine with configurable weights (skills.md section 20)."""

from core.logger import get_logger
from core.models import RiskFactor, RiskResult

logger = get_logger("scoring")

DEFAULT_WEIGHTS = {
    "keyword_detected": 4,
    "ocr_detected": 5,
    "reverse_image_match": 6,
}

DEFAULT_LEVELS = [
    {"max": 0, "level": "none"},
    {"max": 5, "level": "low"},
    {"max": 10, "level": "medium"},
    {"max": 999, "level": "high"},
]


class RiskEngine:
    def __init__(self, weights: dict = None, levels: list = None):
        self.weights = {**DEFAULT_WEIGHTS, **(weights or {})}
        self.levels = levels or DEFAULT_LEVELS

    def level_for(self, score: int) -> str:
        for entry in self.levels:
            if score <= entry["max"]:
                return entry["level"]
        return "high"

    def evaluate(
        self,
        keyword_detected: bool = False,
        ocr_detected: bool = False,
        reverse_image_match: bool = False,
    ) -> RiskResult:
        factors = []

        if keyword_detected:
            factors.append(
                RiskFactor(
                    name="keyword_detected",
                    weight=self.weights["keyword_detected"],
                )
            )

        if ocr_detected:
            factors.append(
                RiskFactor(
                    name="ocr_detected",
                    weight=self.weights["ocr_detected"],
                )
            )

        if reverse_image_match:
            factors.append(
                RiskFactor(
                    name="reverse_image_match",
                    weight=self.weights["reverse_image_match"],
                )
            )

        score = sum(f.weight for f in factors)

        return RiskResult(
            score=score,
            level=self.level_for(score),
            factors=factors,
        )
