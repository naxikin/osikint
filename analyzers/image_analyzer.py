"""Image analysis: average hash + sha256 (skills.md sections 15, 16)."""

from PIL import Image
import imagehash

from core.logger import get_logger
from core.models import ImageAnalysis
from utils.hashing import sha256_hex

logger = get_logger("analyzers")


def calculate_average_hash(path: str) -> str:
    image = Image.open(path)
    return str(imagehash.average_hash(image))


def calculate_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_hex(f.read())


class ImageAnalyzer:
    def __init__(self, algorithms: list = None):
        self.algorithms = algorithms or ["average", "sha256"]

    def analyze(self, path: str) -> ImageAnalysis:
        result = ImageAnalysis()

        try:
            if "average" in self.algorithms:
                result.average_hash = calculate_average_hash(path)
        except (OSError, ValueError) as exc:
            logger.warning("average hash failed for %s: %s", path, exc)

        try:
            if "sha256" in self.algorithms:
                result.sha256 = calculate_sha256(path)
        except (OSError, ValueError) as exc:
            logger.warning("sha256 failed for %s: %s", path, exc)

        return result
