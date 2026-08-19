"""OCR engine, isolated from profile analysis (skills.md section 17)."""

import pytesseract
from PIL import Image

from core.logger import get_logger
from core.models import OCRResult

logger = get_logger("analyzers")


class OCREngine:
    def __init__(self, enabled: bool = True, engine: str = "tesseract"):
        self.enabled = enabled
        self.engine = engine

    def extract_text(self, image_path: str) -> OCRResult:
        if not self.enabled:
            return OCRResult(text="", engine=self.engine, confidence=None)

        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return OCRResult(text=text, engine=self.engine, confidence=None)
        except (OSError, pytesseract.TesseractError) as exc:
            logger.warning("OCR failed for %s: %s", image_path, exc)
            return OCRResult(text="", engine=self.engine, confidence=None)
