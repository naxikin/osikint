"""Versioned report management (skills.md sections 22, 23)."""

import os
from datetime import datetime, timezone

from core.logger import get_logger
from core.models import ProfileResult, Report, ScanStatistics
from storage.json_storage import load_json, save_json

logger = get_logger("storage")

SCHEMA_VERSION = "1.0"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_scan_id(now: datetime = None) -> str:
    now = now or datetime.now()
    return "session_" + now.strftime("%Y%m%d_%H%M%S")


class ReportManager:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def new_scan_id(self, now: datetime = None) -> str:
        now = now or datetime.now()
        return "session_" + now.strftime("%Y%m%d_%H%M%S")

    def session_dir(self, scan_id: str) -> str:
        return os.path.join(self.output_dir, scan_id)

    def images_dir(self, scan_id: str) -> str:
        return os.path.join(self.session_dir(scan_id), "images")

    def report_path(self, scan_id: str, target: str) -> str:
        return os.path.join(
            self.session_dir(scan_id),
            f"osint_report_{target}.json",
        )

    def status_path(self, scan_id: str) -> str:
        return os.path.join(self.session_dir(scan_id), "scan_status.json")

    def ensure_dirs(self, scan_id: str) -> str:
        images_dir = self.images_dir(scan_id)
        os.makedirs(images_dir, exist_ok=True)
        return images_dir

    def build_report(
        self,
        scan_id: str,
        target: str,
        started_at: str,
        completed_at: str,
        profiles: list,
        connections: list,
        statistics: ScanStatistics,
    ) -> dict:
        report = Report(
            schema_version=SCHEMA_VERSION,
            scan_id=scan_id,
            target=target,
            started_at=started_at,
            completed_at=completed_at,
            statistics=statistics,
            profiles=profiles,
            connections=connections,
        )
        return report.to_dict()

    def save(self, report: dict, path: str) -> None:
        save_json(report, path)

    def load(self, path: str):
        return load_json(path)
