"""Dashboard API tests (Flask test client, no network)."""

import json
import os

import pytest

from dashboard.app import create_app


@pytest.fixture()
def output_dir(tmp_path):
    session_dir = tmp_path / "session_20200101_000000"
    (session_dir / "images").mkdir(parents=True)

    report = {
        "schema_version": "1.0",
        "scan_id": "session_20200101_000000",
        "target": "malakaji",
        "started_at": "2020-01-01T00:00:00+00:00",
        "completed_at": "2020-01-01T00:01:00+00:00",
        "statistics": {
            "discovered": 2, "analyzed": 2, "matched": 1,
        },
        "profiles": [
            {
                "url": "https://instagram.com/malakaji/",
                "account_names": ["Malakaji (@malakaji)"],
                "keyword_detected": True,
                "profile_image": "https://cdn.example.com/a.jpg",
                "image_hash": "abcd1234",
                "ocr_text": "",
                "reverse_image_match": False,
                "risk_score": 4,
                "platform": "instagram",
            },
            {
                "url": "https://instagram.com/other/",
                "account_names": ["Other"],
                "keyword_detected": False,
                "profile_image": None,
                "image_hash": None,
                "ocr_text": "",
                "reverse_image_match": False,
                "risk_score": 0,
                "platform": "instagram",
            },
        ],
        "connections": [
            {
                "source": "keyword:malakaji",
                "target": "https://instagram.com/malakaji/",
                "signal": "keyword_match",
                "score": 1.0,
                "confidence": "high",
                "evidence": "malakaji",
            }
        ],
    }
    with open(session_dir / "osint_report_malakaji.json", "w",
              encoding="utf-8") as f:
        json.dump(report, f)

    with open(session_dir / "scan_status.json", "w",
              encoding="utf-8") as f:
        json.dump({"state": "completed", "scan_id": "session_20200101_000000"}, f)

    return str(tmp_path)


@pytest.fixture()
def legacy_output_dir(tmp_path):
    session_dir = tmp_path / "session_20191231_235959"
    (session_dir / "images").mkdir(parents=True)

    legacy = [
        {
            "url": "https://github.com/old/",
            "account_names": ["Old"],
            "keyword_detected": True,
            "profile_image": None,
            "image_hash": None,
            "ocr_text": "",
            "reverse_image_match": False,
            "risk_score": 4,
        }
    ]
    with open(session_dir / "osint_report_old.json", "w",
              encoding="utf-8") as f:
        json.dump(legacy, f)

    return str(tmp_path)


@pytest.fixture()
def client(output_dir):
    app = create_app(output_dir=output_dir, auth_enabled=False)
    app.config["TESTING"] = True
    return app.test_client()


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


def test_pages_render(client):
    for page in ["/", "/sessions", "/profiles", "/profiles/detail",
                 "/new-scan", "/link-analysis"]:
        res = client.get(page)
        assert res.status_code == 200, page


def test_api_sessions(client):
    res = client.get("/api/sessions")
    data = res.get_json()
    assert len(data["sessions"]) == 1
    session = data["sessions"][0]
    assert session["scan_id"] == "session_20200101_000000"
    assert session["statistics"]["matched"] == 1
    assert session["state"] == "completed"


def test_api_report(client):
    res = client.get("/api/reports/session_20200101_000000")
    data = res.get_json()
    assert data["schema_version"] == "1.0"
    assert len(data["profiles"]) == 2


def test_api_report_missing(client):
    res = client.get("/api/reports/nope")
    assert res.status_code == 404


def test_api_graph(client):
    res = client.get("/api/reports/session_20200101_000000/graph")
    data = res.get_json()
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 1
    assert data["nodes"][0]["id"] == "keyword:malakaji"


def test_legacy_report_normalized(output_dir, tmp_path):
    app = create_app(output_dir=output_dir, auth_enabled=False)
    app.config["TESTING"] = True
    client = app.test_client()

    legacy_dir = tmp_path / "session_20191231_235959"
    (legacy_dir / "images").mkdir(parents=True)
    (legacy_dir / "osint_report_old.json").write_text(
        json.dumps([
            {
                "url": "https://github.com/old/",
                "account_names": ["Old"],
                "keyword_detected": True,
                "profile_image": None,
                "image_hash": None,
                "ocr_text": "",
                "reverse_image_match": False,
                "risk_score": 4,
            }
        ])
    )

    res = client.get("/api/reports/session_20191231_235959")
    data = res.get_json()
    assert data["schema_version"] == "legacy"
    assert data["statistics"]["analyzed"] == 1

    res = client.get("/api/reports/session_20191231_235959/graph")
    graph = res.get_json()
    assert any(
        node["id"] == "keyword:old" for node in graph["nodes"]
    )
    assert len(graph["edges"]) == 1


def test_scan_start_validation(client):
    res = client.post("/api/scans", json={})
    assert res.status_code == 400

    res = client.post("/api/scans", json={"target": "   "})
    assert res.status_code == 400


def test_scan_status_missing(client):
    res = client.get("/api/scans/does-not-exist")
    assert res.status_code == 404


def test_scan_stop_missing(client):
    res = client.post("/api/scans/does-not-exist/stop")
    assert res.status_code == 409


def test_api_config(client):
    res = client.get("/api/config")
    data = res.get_json()
    assert "gitlab" in data["platforms"]
    assert data["defaults"]["region"] == "id-id"


def test_image_resolve(client):
    res = client.get(
        "/api/images/session_20200101_000000/resolve",
        query_string={"url": "https://cdn.example.com/a.jpg"},
    )
    data = res.get_json()
    assert data["filename"].endswith(".jpg")


def test_report_page(client):
    res = client.get("/reports/session_20200101_000000")
    assert res.status_code == 200
    assert b"OSINT Sosmed Report" in res.data
    assert b"malakaji" in res.data

    res = client.get("/reports/session_19990101_000000")
    assert res.status_code == 404


def test_report_json_download(client):
    res = client.get("/api/reports/session_20200101_000000/download")
    assert res.status_code == 200
    assert "attachment" in res.headers["Content-Disposition"]
    data = json.loads(res.data)
    assert data["schema_version"] == "1.0"


def test_report_csv_export(client):
    res = client.get("/api/reports/session_20200101_000000/export.csv")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    assert "attachment" in res.headers["Content-Disposition"]

    lines = res.data.decode("utf-8").strip().splitlines()
    assert lines[0].startswith("url,platform,account_names")
    assert len(lines) == 3  # header + 2 profiles
    assert "instagram.com/malakaji" in lines[1]


def test_report_csv_404(client):
    res = client.get("/api/reports/session_19990101_000000/export.csv")
    assert res.status_code == 404


def test_report_csv_failed_profile_included(output_dir, tmp_path):
    report_path = os.path.join(
        output_dir, "session_20200101_000000",
        "osint_report_malakaji.json",
    )
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    report["profiles"].append({
        "url": "https://github.com/failed/",
        "account_names": [],
        "keyword_detected": False,
        "profile_image": None,
        "image_hash": None,
        "ocr_text": "",
        "reverse_image_match": False,
        "risk_score": 0,
        "platform": "github",
        "analyze_status": "failed",
        "analyze_error": "timeout",
    })
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f)

    app = create_app(output_dir=output_dir, auth_enabled=False)
    app.config["TESTING"] = True
    client = app.test_client()

    res = client.get("/api/reports/session_20200101_000000/export.csv")
    lines = res.data.decode("utf-8").strip().splitlines()
    assert len(lines) == 4
    assert "failed" in lines[3]
    assert "timeout" in lines[3]


def test_session_delete(client, output_dir):
    res = client.delete("/api/sessions/session_20200101_000000")
    assert res.status_code == 200
    assert res.get_json() == {"deleted": "session_20200101_000000"}
    assert not os.path.isdir(
        os.path.join(output_dir, "session_20200101_000000")
    )

    res = client.get("/api/reports/session_20200101_000000")
    assert res.status_code == 404


def test_session_delete_invalid_id(client):
    res = client.delete("/api/sessions/foo")
    assert res.status_code == 400

    res = client.delete("/api/sessions/..%2f..%2fetc")
    assert res.status_code in (400, 404)


def test_session_delete_missing(client):
    res = client.delete("/api/sessions/session_19990101_000000")
    assert res.status_code == 404


def test_sessions_clear_all(client, output_dir, tmp_path):
    os.makedirs(os.path.join(output_dir, "session_20200202_000000"))
    res = client.delete("/api/sessions")
    assert res.status_code == 200
    deleted = res.get_json()["deleted"]
    assert set(deleted) == {
        "session_20200101_000000",
        "session_20200202_000000",
    }
    assert not os.path.isdir(
        os.path.join(output_dir, "session_20200101_000000")
    )


def test_sessions_clear_skips_non_session_dirs(client, output_dir):
    os.makedirs(os.path.join(output_dir, "not_a_session"))
    res = client.delete("/api/sessions")
    assert res.status_code == 200
    assert os.path.isdir(os.path.join(output_dir, "not_a_session"))


def test_sessions_include_running_scan(output_dir):
    class FakeManager:
        def running_scan_ids(self):
            return ["session_20200303_000000"]

        def list_scans(self):
            return [
                {
                    "handle": "h1",
                    "is_running": True,
                    "status": {
                        "state": "running",
                        "scan_id": "session_20200303_000000",
                        "target": "kw",
                        "started_at": "2020-03-03T00:00:00+00:00",
                        "discovered": 5,
                        "analyzed": 2,
                        "matched": 1,
                    },
                }
            ]

    app = create_app(output_dir=output_dir, auth_enabled=False)
    app.config["TESTING"] = True
    app.config["SCAN_MANAGER"] = FakeManager()
    client = app.test_client()

    res = client.get("/api/sessions")
    data = res.get_json()
    scan_ids = [s["scan_id"] for s in data["sessions"]]
    assert "session_20200303_000000" in scan_ids

    running = next(
        s for s in data["sessions"]
        if s["scan_id"] == "session_20200303_000000"
    )
    assert running["state"] == "running"
    assert running["statistics"]["analyzed"] == 2


def test_delete_blocked_while_scan_running(output_dir):
    class FakeManager:
        def running_scan_ids(self):
            return ["session_20200101_000000"]

        def list_scans(self):
            return []

    app = create_app(output_dir=output_dir, auth_enabled=False)
    app.config["TESTING"] = True
    app.config["SCAN_MANAGER"] = FakeManager()
    client = app.test_client()

    res = client.delete("/api/sessions/session_20200101_000000")
    assert res.status_code == 409
    assert os.path.isdir(
        os.path.join(output_dir, "session_20200101_000000")
    )


def test_delete_blocked_when_scan_id_unknown(output_dir):
    class FakeManager:
        def running_scan_ids(self):
            return [None]

        def list_scans(self):
            return []

    app = create_app(output_dir=output_dir, auth_enabled=False)
    app.config["TESTING"] = True
    app.config["SCAN_MANAGER"] = FakeManager()
    client = app.test_client()

    res = client.delete("/api/sessions/session_19990101_000000")
    assert res.status_code == 409
