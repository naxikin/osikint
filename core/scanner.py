"""OSINTScanner: public API boundary for CLI and dashboard
(skills.md section 44)."""

import os

from core.config import load_config
from core.logger import get_logger
from core.models import ProfileResult, ScanStatistics
from storage.json_storage import save_json
from storage.report_manager import ReportManager, utc_now_iso

logger = get_logger("scanner")


class OSINTScanner:
    def __init__(
        self,
        config,
        discovery_fn=None,
        analyzer=None,
        entity_linker=None,
        report_manager: ReportManager = None,
        screenshot_fn=None,
    ):
        self.config = config
        self.discovery_fn = discovery_fn
        self.analyzer = analyzer
        self.entity_linker = entity_linker
        self.report_manager = report_manager
        self.screenshot_fn = screenshot_fn

    def capture_evidence(self, url: str, image_dir: str) -> str:
        """Takes an evidence screenshot for a failed profile. Returns the
        stored filename ("" when unavailable)."""
        if self.screenshot_fn is None:
            return ""

        from utils.hashing import sha256_url

        filename = sha256_url(url) + ".png"
        path = os.path.join(image_dir, filename)

        try:
            if self.screenshot_fn(url, path):
                return filename
        except Exception as exc:
            logger.warning(
                "evidence screenshot failed for %s: %s", url, exc
            )
        return ""

    def discover(self, target: str):
        if self.discovery_fn is None:
            raise RuntimeError("discovery_fn not configured")
        return self.discovery_fn(target)

    def analyze(self, profile, target: str, known_hashes: dict,
                image_dir: str):
        if self.analyzer is None:
            raise RuntimeError("analyzer not configured")
        return self.analyzer.analyze(profile, target, known_hashes,
                                     image_dir)

    def scan(self, target: str, on_progress=None, status_file: str = None):
        on_progress = on_progress or (lambda event: None)

        scan_id = self.report_manager.new_scan_id()
        images_dir = self.report_manager.ensure_dirs(scan_id)
        report_path = self.report_manager.report_path(scan_id, target)
        started_at = utc_now_iso()

        status = {
            "scan_id": scan_id,
            "target": target,
            "state": "running",
            "discovered": 0,
            "analyzed": 0,
            "matched": 0,
            "current_url": "",
            "report_path": report_path,
            "started_at": started_at,
            "completed_at": None,
            "error": None,
        }

        def emit(event):
            on_progress(event)
            if status_file:
                save_json(status, status_file)
            save_json(status, self.report_manager.status_path(scan_id))

        emit({"event": "discovery_started", "scan_id": scan_id,
              "target": target})

        try:
            discovered = self.discover(target)
        except KeyboardInterrupt:
            status["state"] = "stopped"
            status["completed_at"] = utc_now_iso()
            emit({"event": "scan_interrupted", "scan_id": scan_id,
                  "analyzed": 0})
            raise
        except Exception as exc:
            logger.error("discovery failed for %r: %s", target, exc)
            status["state"] = "failed"
            status["error"] = str(exc)
            status["completed_at"] = utc_now_iso()
            emit({"event": "scan_failed", "scan_id": scan_id,
                  "error": str(exc)})
            return None

        status["discovered"] = len(discovered)
        emit({"event": "discovery_done", "scan_id": scan_id,
              "discovered": len(discovered)})

        known_hashes = {}
        analyzed_profiles = []

        def _platform_for(url):
            from utils.validators import platform_from_url

            return platform_from_url(
                url, self.config.enabled_platform_domains()
            )

        def _autosave():
            if self.config.autosave.get("enabled", True):
                report = self._build_partial_report(
                    scan_id, target, started_at, analyzed_profiles,
                    status, completed=False,
                )
                self.report_manager.save(report, report_path)

        try:
            for idx, profile in enumerate(discovered, start=1):
                status["current_url"] = profile["url"]

                try:
                    result = self.analyze(profile, target, known_hashes,
                                          images_dir)
                except Exception as exc:
                    logger.warning("profile analyze failed %s: %s",
                                   profile.get("url"), exc)
                    evidence = self.capture_evidence(
                        profile.get("url"), images_dir
                    )
                    failed = ProfileResult.failed(
                        profile.get("url"),
                        str(exc),
                        platform=_platform_for(profile.get("url")),
                        evidence_image=evidence,
                    )
                    analyzed_profiles.append(failed.to_dict())
                    status["analyzed"] = len(analyzed_profiles)
                    emit({"event": "profile_failed", "scan_id": scan_id,
                          "url": profile.get("url"), "error": str(exc)})
                    _autosave()
                    continue

                if result is None:
                    evidence = self.capture_evidence(
                        profile.get("url"), images_dir
                    )
                    failed = ProfileResult.failed(
                        profile.get("url"),
                        "no content returned",
                        platform=_platform_for(profile.get("url")),
                        evidence_image=evidence,
                    )
                    analyzed_profiles.append(failed.to_dict())
                    status["analyzed"] = len(analyzed_profiles)
                    emit({"event": "profile_failed", "scan_id": scan_id,
                          "url": profile.get("url"),
                          "error": "no content returned"})
                    _autosave()
                    continue

                analyzed_profiles.append(result.to_dict())
                status["analyzed"] = len(analyzed_profiles)
                status["matched"] = sum(
                    1 for p in analyzed_profiles if p["keyword_detected"]
                )
                status["current_url"] = result.url

                emit({
                    "event": "profile_analyzed",
                    "scan_id": scan_id,
                    "analyzed": status["analyzed"],
                    "total": len(discovered),
                    "url": result.url,
                    "matched": result.keyword_detected,
                    "risk_score": result.risk_score,
                    "profile": result.to_legacy_dict(),
                })

                _autosave()
        except KeyboardInterrupt:
            report = self._build_partial_report(
                scan_id, target, started_at, analyzed_profiles, status,
                completed=False,
            )
            self.report_manager.save(report, report_path)
            status["state"] = "stopped"
            status["completed_at"] = utc_now_iso()
            emit({"event": "scan_interrupted", "scan_id": scan_id,
                  "analyzed": len(analyzed_profiles)})
            raise

        connections = []
        if self.entity_linker is not None:
            connections = [
                c.to_dict()
                for c in self.entity_linker.build_connections(
                    analyzed_profiles, target, known_hashes
                )
            ]

        statistics = ScanStatistics(
            discovered=len(discovered),
            analyzed=len(analyzed_profiles),
            matched=status["matched"],
        )

        report = self.report_manager.build_report(
            scan_id=scan_id,
            target=target,
            started_at=started_at,
            completed_at=utc_now_iso(),
            profiles=analyzed_profiles,
            connections=connections,
            statistics=statistics,
        )
        self.report_manager.save(report, report_path)

        status["state"] = "completed"
        status["completed_at"] = utc_now_iso()
        emit({
            "event": "scan_completed",
            "scan_id": scan_id,
            "report_path": report_path,
            "analyzed": len(analyzed_profiles),
        })

        return report

    def _build_partial_report(self, scan_id, target, started_at, profiles,
                              status, completed: bool) -> dict:
        statistics = ScanStatistics(
            discovered=status.get("discovered", 0),
            analyzed=len(profiles),
            matched=sum(1 for p in profiles if p.get("keyword_detected")),
        )
        return self.report_manager.build_report(
            scan_id=scan_id,
            target=target,
            started_at=started_at,
            completed_at=utc_now_iso() if completed else "",
            profiles=profiles,
            connections=[],
            statistics=statistics,
        )

    def save_report(self, report: dict, output_file: str) -> None:
        save_json(report, output_file)
