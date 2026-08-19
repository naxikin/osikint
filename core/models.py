"""Core data models (skills.md sections 9, 19, 42)."""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class SearchResult:
    title: str
    url: str
    body: str
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormalizedIdentifier:
    original: str
    normalized: str


@dataclass
class MatchResult:
    matched: bool
    method: str
    score: float
    target: str
    candidate: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Evidence:
    signal: str
    score: float
    confidence: str
    evidence: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Connection:
    source: str
    target: str
    signal: str
    score: float
    confidence: str
    evidence: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OCRResult:
    text: str = ""
    engine: str = "tesseract"
    confidence: Optional[float] = None

    def to_dict(self) -> dict:
        return {"text": self.text, "engine": self.engine,
                "confidence": self.confidence}


@dataclass
class ImageAnalysis:
    average_hash: Optional[str] = None
    sha256: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskFactor:
    name: str
    weight: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskResult:
    score: int
    level: str
    factors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"score": self.score, "level": self.level,
                "factors": [f.to_dict() for f in self.factors]}


LEGACY_FIELDS = [
    "url",
    "account_names",
    "keyword_detected",
    "profile_image",
    "image_hash",
    "ocr_text",
    "reverse_image_match",
    "risk_score",
]


@dataclass
class ProfileResult:
    # legacy fields (skills.md section 42 - never removed)
    url: str = ""
    account_names: list = field(default_factory=list)
    keyword_detected: bool = False
    profile_image: Optional[str] = None
    image_hash: Optional[str] = None
    ocr_text: str = ""
    reverse_image_match: bool = False
    risk_score: int = 0

    # additional fields
    platform: str = ""
    original_url: str = ""
    final_url: str = ""
    match_details: dict = field(default_factory=dict)
    image_analysis: dict = field(default_factory=dict)
    ocr_analysis: dict = field(default_factory=dict)
    correlation: dict = field(default_factory=dict)
    risk_details: dict = field(default_factory=dict)
    analyze_status: str = "analyzed"
    analyze_error: str = ""
    evidence_image: str = ""

    def to_legacy_dict(self) -> dict:
        return {k: getattr(self, k) for k in LEGACY_FIELDS}

    def to_dict(self) -> dict:
        data = self.to_legacy_dict()
        data.update(
            {
                "platform": self.platform,
                "original_url": self.original_url,
                "final_url": self.final_url,
                "match_details": self.match_details,
                "image_analysis": self.image_analysis,
                "ocr_analysis": self.ocr_analysis,
                "correlation": self.correlation,
                "risk_details": self.risk_details,
                "analyze_status": self.analyze_status,
                "analyze_error": self.analyze_error,
                "evidence_image": self.evidence_image,
            }
        )
        return data

    @classmethod
    def failed(
        cls,
        url: str,
        error: str,
        platform: str = "",
        evidence_image: str = "",
    ) -> "ProfileResult":
        return cls(
            url=url,
            original_url=url,
            final_url=url,
            platform=platform,
            analyze_status="failed",
            analyze_error=error,
            evidence_image=evidence_image,
        )


@dataclass
class ScanStatistics:
    discovered: int = 0
    analyzed: int = 0
    matched: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Report:
    schema_version: str = "1.0"
    scan_id: str = ""
    target: str = ""
    started_at: str = ""
    completed_at: str = ""
    statistics: ScanStatistics = field(default_factory=ScanStatistics)
    profiles: list = field(default_factory=list)
    connections: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "scan_id": self.scan_id,
            "target": self.target,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "statistics": self.statistics.to_dict(),
            "profiles": self.profiles,
            "connections": self.connections,
        }
