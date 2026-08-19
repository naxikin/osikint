"""Runs scans as isolated subprocesses (skills.md section 44)."""

import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid

from core.logger import get_logger

logger = get_logger("dashboard.scans")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_PATH = os.path.join(PROJECT_ROOT, "social_osint.py")

ACTIVE_STATUS_FILE = "scan_status.json"


class ScanManager:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.active = {}
        self.lock = threading.RLock()
        self._stop_flag = False

    def _env_for(self, options):
        env = dict(os.environ)

        region = options.get("region")
        if region:
            env["OSINT_REGION"] = region

        max_results = options.get("max_results")
        if max_results:
            env["OSINT_MAX_RESULTS"] = str(int(max_results))

        ocr_enabled = options.get("ocr_enabled", True)
        env["OSINT_OCR_ENABLED"] = "true" if ocr_enabled else "false"

        leet = options.get("leet_variants", True)
        env["OSINT_LEET_VARIANTS"] = "true" if leet else "false"

        return env

    def start(self, target, options):
        with self.lock:
            for scan in self.active.values():
                status = scan.get("status") or {}
                if status.get("state") in ("running", "queued"):
                    return None, "a scan is already running"

            platforms = options.get("platforms") or []

            command = [
                sys.executable,
                CLI_PATH,
                "--target",
                target,
                "--output",
                self.output_dir,
                "--status-file",
                os.path.join(self.output_dir, ACTIVE_STATUS_FILE),
            ]
            for platform in platforms:
                command += ["--platform", platform]

            config_path = options.get("config")
            if config_path:
                command += ["--config", config_path]

            handle = uuid.uuid4().hex[:12]

            process = subprocess.Popen(
                command,
                env=self._env_for(options),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            self.active[handle] = {
                "handle": handle,
                "process": process,
                "target": target,
                "platforms": platforms,
                "started_at": time.time(),
                "status": {"state": "queued", "target": target},
                "scan_id": None,
            }

            threading.Thread(
                target=self._reap,
                args=(handle, process),
                daemon=True,
            ).start()

            return handle, None

    def _reap(self, handle, process):
        output, _ = process.communicate()
        logger.info("scan %s exited with code %s", handle, process.returncode)
        with self.lock:
            scan = self.active.get(handle)
            if scan:
                scan["exit_code"] = process.returncode
                scan["output"] = output or ""
                status = self._read_status_file()
                if status:
                    scan["final_status"] = status
                    scan["scan_id"] = status.get("scan_id")
                    scan["status"] = status
        if self._stop_flag:
            return

    def _read_status_file(self):
        path = os.path.join(self.output_dir, ACTIVE_STATUS_FILE)
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def status(self, handle):
        with self.lock:
            scan = self.active.get(handle)
            if not scan:
                return None

            process = scan.get("process")
            if process is not None and process.poll() is None:
                status = self._read_status_file()
                if status:
                    scan["status"] = status
                    scan["scan_id"] = status.get("scan_id")
            else:
                final_status = scan.get("final_status")
                if final_status:
                    scan["status"] = final_status
                    scan["scan_id"] = final_status.get("scan_id")

            result = dict(scan)
            result.pop("process", None)

            if process is not None:
                result["is_running"] = process.poll() is None
                result["exit_code"] = process.returncode
            else:
                result["is_running"] = False
                result["exit_code"] = scan.get("exit_code")

            return result

    def running_scan_ids(self):
        """scan_id of every live subprocess. A None entry means a scan is
        running but its scan_id is not known yet."""
        with self.lock:
            ids = []
            for scan in self.active.values():
                process = scan.get("process")
                if process is None or process.poll() is not None:
                    continue
                ids.append(scan.get("scan_id"))
            return ids

    def list_scans(self):
        with self.lock:
            return [self.status(handle) for handle in list(self.active)]

    def stop(self, handle):
        with self.lock:
            scan = self.active.get(handle)
            if not scan:
                return False

            process = scan.get("process")
            if process is None or process.poll() is not None:
                return False

            logger.info("sending SIGINT to scan %s", handle)
            process.send_signal(signal.SIGINT)
            return True
