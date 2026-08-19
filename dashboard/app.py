"""Social OSINT dashboard (Flask).

Consumes JSON reports produced by the core scanner. The core engine is
never coupled to this web layer (skills.md sections 43, 44).
"""

import csv
import io
import os
import re
import shutil
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)

from core.config import load_config
from core.logger import get_logger, setup_logging

from dashboard import auth
from dashboard.report_utils import (
    build_graph,
    list_images,
    list_sessions,
    load_report,
    report_file_path,
    resolve_image,
    summary_of,
)
from dashboard.scanner_manager import ScanManager
from utils.hashing import image_filename

logger = get_logger("dashboard.app")

DEFAULT_PORT = int(os.environ.get("OSINT_DASHBOARD_PORT", "8000"))
STALE_STATUS_SECONDS = int(
    os.environ.get("OSINT_STALE_STATUS_SECONDS", "300")
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(PROJECT_ROOT, "config", "config.yaml")


def create_app(output_dir=None, config_path=None, auth_enabled=None):
    setup_logging(verbose=False)

    app = Flask(
        __name__,
        template_folder=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates"
        ),
        static_folder=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "static"
        ),
    )
    app.config["JSON_AS_ASCII"] = False

    config = load_config(config_path)
    app.config["OSINT_CONFIG"] = config

    output_dir = output_dir or os.path.abspath(
        os.path.join(
            PROJECT_ROOT, config.output.get("directory", "output")
        )
    )
    app.config["OUTPUT_DIR"] = output_dir

    manager = ScanManager(output_dir)
    app.config["SCAN_MANAGER"] = manager

    def get_manager():
        return app.config["SCAN_MANAGER"]

    # ---- authentication ------------------------------------------------
    dashboard_config = config.dashboard or {}
    auth_config = dashboard_config.get("auth", {}) or {}
    use_auth = (
        bool(auth_config.get("enabled", True))
        if auth_enabled is None
        else bool(auth_enabled)
    )
    app.config["AUTH_ENABLED"] = use_auth

    if use_auth:
        users = auth.resolve_users(output_dir)
        app.config["USERS"] = users
        app.secret_key = auth.resolve_secret_key(output_dir)

        @app.route("/login", methods=["GET", "POST"])
        def login_page():
            error = None

            if request.method == "POST":
                username = (request.form.get("username") or "").strip()
                password = request.form.get("password") or ""
                password_hash = users.get(username)

                if password_hash and auth.verify_password(
                    password_hash, password
                ):
                    session["user"] = username
                    target = request.args.get("next") or url_for("index")
                    if (
                        not target.startswith("/")
                        or target.startswith("//")
                    ):
                        target = url_for("index")
                    return redirect(target)

                error = "Invalid username or password"

            return render_template("login.html", error=error)

        @app.route("/logout")
        def logout_page():
            session.clear()
            return redirect(url_for("login_page"))

        @app.route("/change-password", methods=["GET", "POST"])
        def change_password_page():
            error = None
            message = None
            username = session.get("user") or ""

            if request.method == "POST":
                current = request.form.get("current_password") or ""
                new_password = request.form.get("new_password") or ""
                confirm = request.form.get("confirm_password") or ""

                if not auth.verify_password(
                    users.get(username), current
                ):
                    error = "Current password is incorrect"
                elif len(new_password) < auth.MIN_PASSWORD_LENGTH:
                    error = (
                        "New password must be at least "
                        f"{auth.MIN_PASSWORD_LENGTH} characters"
                    )
                elif new_password != confirm:
                    error = "New passwords do not match"
                else:
                    auth.update_password(
                        users, username, new_password, output_dir
                    )
                    message = "Password changed successfully"

            return render_template(
                "change_password.html",
                error=error,
                message=message,
                min_length=auth.MIN_PASSWORD_LENGTH,
            )

        @app.before_request
        def _require_auth():
            if request.endpoint in (
                "login_page", "logout_page", "healthz", "assets_alias",
            ):
                return None
            if request.path.startswith("/static/"):
                return None
            if session.get("user"):
                return None

            if request.path.startswith("/api/"):
                return jsonify({"error": "authentication required"}), 401
            return redirect(url_for("login_page", next=request.path))
    else:
        app.secret_key = auth.resolve_secret_key(output_dir)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/sessions")
    def sessions_page():
        return render_template("sessions.html")

    @app.route("/profiles")
    def profiles_page():
        return render_template("profiles.html")

    @app.route("/profiles/detail")
    def profile_detail_page():
        return render_template("profile_detail.html")

    @app.route("/new-scan")
    def new_scan_page():
        return render_template("new_scan.html")

    @app.route("/link-analysis")
    def link_analysis_page():
        return render_template("link_analysis.html")

    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    @app.route("/assets/<path:filename>")
    def assets_alias(filename):
        """Template JS references ../assets/... relative to the page URL;
        serve those from the static assets folder."""
        return send_from_directory(
            os.path.join(app.static_folder, "assets"), filename
        )

    @app.route("/api/config")
    def api_config():
        return jsonify(
            {
                "platforms": list(
                    config.platforms.keys()
                ),
                "defaults": {
                    "region": config.search.get("region", "id-id"),
                    "max_results": config.search.get("max_results", 30),
                    "ocr_enabled": config.ocr.get("enabled", True),
                    "leet_variants": config.search.get(
                        "leet_variants", True
                    ),
                },
            }
        )

    @app.route("/api/sessions")
    def api_sessions():
        sessions = list_sessions(output_dir)
        existing = {s["scan_id"] for s in sessions}

        live_scan_ids = set(get_manager().running_scan_ids())
        now = time.time()

        for session in sessions:
            if session["state"] != "running":
                continue
            scan_id = session["scan_id"]
            if scan_id in live_scan_ids:
                continue
            status_path = os.path.join(
                output_dir, scan_id, "scan_status.json"
            )
            try:
                age = now - os.path.getmtime(status_path)
            except OSError:
                age = None
            if age is not None and age > STALE_STATUS_SECONDS:
                session["state"] = "stopped"

        for scan in get_manager().list_scans():
            status = scan.get("status") or {}
            scan_id = status.get("scan_id")
            if not scan_id or scan_id in existing:
                continue
            if status.get("state") not in ("running", "queued"):
                continue
            sessions.insert(0, {
                "scan_id": scan_id,
                "target": status.get("target", ""),
                "schema_version": "-",
                "started_at": status.get("started_at", ""),
                "completed_at": "",
                "state": status.get("state", "running"),
                "statistics": {
                    "discovered": status.get("discovered", 0),
                    "analyzed": status.get("analyzed", 0),
                    "matched": status.get("matched", 0),
                },
                "risk_distribution": {},
                "platforms": {},
                "connections_count": 0,
                "ocr_hits": 0,
                "reverse_matches": 0,
            })

        def _sort_key(session):
            started = session.get("started_at") or ""
            try:
                return datetime.fromisoformat(started).timestamp()
            except (TypeError, ValueError):
                pass
            scan_id = session.get("scan_id") or ""
            try:
                return datetime.strptime(
                    scan_id, "session_%Y%m%d_%H%M%S"
                ).timestamp()
            except ValueError:
                return 0.0

        sessions.sort(key=_sort_key, reverse=True)
        return jsonify({"sessions": sessions})

    def _running_scan_ids():
        ids = get_manager().running_scan_ids()
        if any(scan_id is None for scan_id in ids):
            return {"*"}
        return {scan_id for scan_id in ids if scan_id}

    def _delete_session_dir(scan_id):
        if not re.fullmatch(r"session_\d{8}_\d{6}", scan_id):
            return "invalid session id", 400
        running = _running_scan_ids()
        if "*" in running:
            return "a scan is currently running", 409
        if scan_id in running:
            return "scan is still running", 409
        session_dir = os.path.join(output_dir, scan_id)
        if not os.path.isdir(session_dir):
            return "session not found", 404
        shutil.rmtree(session_dir)
        logger.info("deleted session %s", scan_id)
        return None, None

    @app.route("/api/sessions/<scan_id>", methods=["DELETE"])
    def api_session_delete(scan_id):
        error, code = _delete_session_dir(scan_id)
        if error:
            return jsonify({"error": error}), code
        return jsonify({"deleted": scan_id})

    @app.route("/api/sessions", methods=["DELETE"])
    def api_sessions_clear():
        deleted = []
        for entry in os.listdir(output_dir):
            if not re.fullmatch(r"session_\d{8}_\d{6}", entry):
                continue
            error, code = _delete_session_dir(entry)
            if error:
                return jsonify({"error": error, "deleted": deleted}), code
            deleted.append(entry)
        return jsonify({"deleted": deleted})

    @app.route("/api/reports/<scan_id>")
    def api_report(scan_id):
        report = load_report(output_dir, scan_id)
        if report is None:
            return jsonify({"error": "report not found"}), 404
        return jsonify(report)

    @app.route("/reports/<scan_id>")
    def report_page(scan_id):
        report = load_report(output_dir, scan_id)
        if report is None:
            return render_template("report.html", report=None), 404
        return render_template(
            "report.html",
            report=report,
            summary=summary_of(report),
        )

    @app.route("/api/reports/<scan_id>/download")
    def api_report_download(scan_id):
        path = report_file_path(output_dir, scan_id)
        if path is None:
            return jsonify({"error": "report not found"}), 404
        return send_file(
            path,
            as_attachment=True,
            download_name=os.path.basename(path),
        )

    CSV_FIELDS = [
        ("url", "url"),
        ("platform", "platform"),
        ("account_names", "account_names"),
        ("keyword_detected", "keyword_detected"),
        ("profile_image", "profile_image"),
        ("image_hash", "image_hash"),
        ("ocr_text", "ocr_text"),
        ("reverse_image_match", "reverse_image_match"),
        ("risk_score", "risk_score"),
        ("analyze_status", "analyze_status"),
        ("analyze_error", "analyze_error"),
    ]

    @app.route("/api/reports/<scan_id>/export.csv")
    def api_report_csv(scan_id):
        report = load_report(output_dir, scan_id)
        if report is None:
            return jsonify({"error": "report not found"}), 404

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([header for _, header in CSV_FIELDS])

        for profile in report.get("profiles", []):
            row = []
            for key, _ in CSV_FIELDS:
                value = profile.get(key, "")
                if isinstance(value, list):
                    value = "; ".join(str(v) for v in value)
                row.append(value)
            writer.writerow(row)

        response = Response(buffer.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = (
            f'attachment; filename="osint_report_{scan_id}.csv"'
        )
        return response

    @app.route("/api/reports/<scan_id>/graph")
    def api_graph(scan_id):
        report = load_report(output_dir, scan_id)
        if report is None:
            return jsonify({"error": "report not found"}), 404
        return jsonify(build_graph(report))

    @app.route("/api/images/<scan_id>/<filename>")
    def api_image(scan_id, filename):
        path = resolve_image(output_dir, scan_id, filename)
        if path is None:
            return jsonify({"error": "image not found"}), 404
        return send_file(path, mimetype="image/jpeg")

    @app.route("/api/images/<scan_id>/resolve")
    def api_image_resolve(scan_id):
        image_url = request.args.get("url", "")
        if not image_url:
            return jsonify({"error": "url param required"}), 400
        filename = image_filename(image_url)
        return jsonify({"filename": filename, "exists": bool(
            resolve_image(output_dir, scan_id, filename)
        )})

    @app.route("/api/scans", methods=["GET"])
    def api_scans_list():
        return jsonify({"scans": get_manager().list_scans()})

    @app.route("/api/scans", methods=["POST"])
    def api_scans_start():
        data = request.get_json(silent=True) or {}
        target = (data.get("target") or "").strip()
        if not target:
            return jsonify({"error": "target keyword required"}), 400

        options = {
            "platforms": data.get("platforms") or [],
            "region": data.get("region"),
            "max_results": data.get("max_results"),
            "ocr_enabled": data.get("ocr_enabled", True),
            "leet_variants": data.get("leet_variants", True),
            "config": data.get("config"),
        }

        handle, error = get_manager().start(target, options)
        if error:
            return jsonify({"error": error}), 409

        return jsonify({"scan_id": handle}), 202

    @app.route("/api/scans/<handle>", methods=["GET"])
    def api_scan_status(handle):
        status = get_manager().status(handle)
        if status is None:
            return jsonify({"error": "scan not found"}), 404
        return jsonify(status)

    @app.route("/api/scans/<handle>/stop", methods=["POST"])
    def api_scan_stop(handle):
        if get_manager().stop(handle):
            return jsonify({"stopped": True})
        return jsonify({"stopped": False}), 409

    return app


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="osint-dashboard",
        description="Social OSINT dashboard",
    )
    parser.add_argument(
        "--output",
        help="directory containing scan reports (default: config output)",
    )
    parser.add_argument(
        "--config",
        help="config yaml path",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="listen port (default: %(default)s)",
    )
    args = parser.parse_args()

    app = create_app(
        output_dir=args.output,
        config_path=args.config,
    )
    app.run(
        host="0.0.0.0",
        port=args.port,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
