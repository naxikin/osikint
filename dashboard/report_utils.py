"""Report reading, session listing, and graph building for the dashboard."""

import glob
import json
import os

from core.logger import get_logger
from correlation.entity_linker import EntityLinker, extract_handles
from correlation.username_matcher import contains_keyword

logger = get_logger("dashboard")

SCHEMA_VERSION = "1.0"
LEGACY_FIELDS = [
    "url", "account_names", "keyword_detected", "profile_image",
    "image_hash", "ocr_text", "reverse_image_match", "risk_score",
]


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        logger.warning("cannot load %s: %s", path, exc)
        return None


def find_report_file(session_dir):
    pattern = os.path.join(session_dir, "osint_report_*.json")
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None


def report_file_path(output_dir, scan_id):
    session_dir = os.path.join(output_dir, scan_id)
    if not os.path.isdir(session_dir):
        return None
    return find_report_file(session_dir)


def load_report(output_dir, scan_id):
    session_dir = os.path.join(output_dir, scan_id)
    report_file = find_report_file(session_dir)
    if not report_file:
        return None

    data = load_json(report_file)
    if data is None:
        return None

    return normalize_report(data, scan_id, report_file)


def _target_from_filename(report_file):
    base = os.path.basename(report_file)
    prefix = "osint_report_"
    if base.startswith(prefix) and base.endswith(".json"):
        return base[len(prefix):-len(".json")]
    return ""


def normalize_report(data, scan_id, report_file=None):
    if isinstance(data, list):
        return {
            "schema_version": "legacy",
            "scan_id": scan_id,
            "target": _target_from_filename(report_file or ""),
            "started_at": "",
            "completed_at": "",
            "statistics": {
                "discovered": len(data),
                "analyzed": len(data),
                "matched": sum(
                    1 for p in data if p.get("keyword_detected")
                ),
            },
            "profiles": [
                {k: p.get(k) for k in LEGACY_FIELDS}
                for p in data
            ],
            "connections": [],
        }
    if "profiles" not in data:
        data["profiles"] = []
    if "connections" not in data:
        data["connections"] = []
    data.setdefault("statistics", {})
    data.setdefault("schema_version", "legacy")
    data.setdefault("scan_id", scan_id)
    return data


def _risk_level(score):
    if score <= 0:
        return "none"
    if score <= 5:
        return "low"
    if score <= 10:
        return "medium"
    return "high"


def summary_of(report):
    profiles = report.get("profiles", [])
    stats = report.get("statistics", {})
    risk = {}
    platforms = {}
    for profile in profiles:
        level = _risk_level(profile.get("risk_score", 0))
        risk[level] = risk.get(level, 0) + 1
        platform = profile.get("platform", "") or "unknown"
        platforms[platform] = platforms.get(platform, 0) + 1

    return {
        "scan_id": report.get("scan_id", ""),
        "target": report.get("target", ""),
        "schema_version": report.get("schema_version", ""),
        "started_at": report.get("started_at", ""),
        "completed_at": report.get("completed_at", ""),
        "statistics": {
            "discovered": stats.get("discovered", len(profiles)),
            "analyzed": stats.get("analyzed", len(profiles)),
            "matched": stats.get(
                "matched",
                sum(1 for p in profiles if p.get("keyword_detected")),
            ),
        },
        "risk_distribution": risk,
        "platforms": platforms,
        "connections_count": len(report.get("connections", [])),
        "ocr_hits": sum(
            1 for p in profiles
            if p.get("ocr_text") and contains_keyword(p["ocr_text"], report.get("target", ""))
        ) if report.get("target") else 0,
        "reverse_matches": sum(
            1 for p in profiles if p.get("reverse_image_match")
        ),
    }


def list_sessions(output_dir):
    sessions = []

    if not os.path.isdir(output_dir):
        return sessions

    for entry in sorted(
        os.listdir(output_dir),
        key=lambda name: os.path.getmtime(
            os.path.join(output_dir, name)
        ),
        reverse=True,
    ):
        if not entry.startswith("session_"):
            continue
        session_dir = os.path.join(output_dir, entry)
        if not os.path.isdir(session_dir):
            continue

        report_file = find_report_file(session_dir)
        if not report_file:
            continue

        report = load_report(output_dir, entry)
        if report is None:
            continue

        item = summary_of(report)
        item["state"] = _session_state(session_dir, item)
        sessions.append(item)

    return sessions


def _session_state(session_dir, item):
    status_file = os.path.join(session_dir, "scan_status.json")
    status = load_json(status_file)
    if status:
        return status.get("state", "completed")
    if item.get("completed_at"):
        return "completed"
    return "unknown"


def list_images(output_dir, scan_id):
    images_dir = os.path.join(output_dir, scan_id, "images")
    if not os.path.isdir(images_dir):
        return []
    return sorted(os.listdir(images_dir))


def resolve_image(output_dir, scan_id, filename):
    images_dir = os.path.join(output_dir, scan_id, "images")
    images_dir = os.path.realpath(images_dir)
    path = os.path.realpath(os.path.join(images_dir, filename))
    if not path.startswith(images_dir + os.sep):
        return None
    return path if os.path.isfile(path) else None


def build_graph(report):
    """Nodes: profiles + keyword root. Edges: connections.
    Falls back to computing connections for legacy reports."""
    profiles = report.get("profiles", [])
    target = report.get("target", "")
    connections = report.get("connections", [])

    if not connections and profiles:
        linker = EntityLinker()
        connections = [
            c.to_dict()
            for c in linker.build_connections(profiles, target, {})
        ]

    url_index = {}
    for index, profile in enumerate(profiles):
        url_index[profile.get("url")] = index

    nodes = []
    node_ids = set()

    def add_node(node_id, label, group, extra=None):
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        node = {
            "id": node_id,
            "label": label,
            "group": group,
        }
        if extra:
            node.update(extra)
        nodes.append(node)

    if target:
        add_node(
            f"keyword:{target}", target, "keyword",
            {"shape": "star", "color": "#f6c343"},
        )

    for profile in profiles:
        add_node(
            profile.get("url"),
            (profile.get("account_names") or [profile.get("url")])[0],
            profile.get("platform", "") or "unknown",
            {
                "risk_score": profile.get("risk_score", 0),
                "matched": bool(profile.get("keyword_detected")),
                "profile_image": profile.get("profile_image"),
            },
        )

    edges = []
    for conn in connections:
        if conn.get("source") not in node_ids:
            continue
        if conn.get("target") not in node_ids:
            continue
        edges.append({
            "from": conn["source"],
            "to": conn["target"],
            "label": conn.get("signal", ""),
            "signal": conn.get("signal", ""),
            "value": round(float(conn.get("score", 0.5)), 2),
            "evidence": conn.get("evidence", ""),
            "confidence": conn.get("confidence", ""),
        })

    return {"nodes": nodes, "edges": edges}
