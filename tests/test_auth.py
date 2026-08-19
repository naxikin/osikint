"""Dashboard authentication tests (multi-user, session login)."""

import os

import pytest

from dashboard.app import create_app
from dashboard.auth import (
    hash_password,
    resolve_secret_key,
    verify_password,
)


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_DASHBOARD_USER", "admin")
    monkeypatch.setenv("OSINT_DASHBOARD_PASSWORD", "secret123")
    monkeypatch.delenv("OSINT_DASHBOARD_USERS_FILE", raising=False)
    monkeypatch.setenv("OSINT_DASHBOARD_SECRET_KEY", "test-secret")

    application = create_app(
        output_dir=str(tmp_path), auth_enabled=True
    )
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def test_login_page_renders(client):
    res = client.get("/login")
    assert res.status_code == 200
    assert b"Login" in res.data


def test_healthz_public(client):
    res = client.get("/healthz")
    assert res.status_code == 200


def test_static_public(client):
    res = client.get("/static/js/app.js")
    assert res.status_code == 200


def test_assets_alias_public(client):
    # template JS references ../assets/... relative to the page URL
    res = client.get("/assets/images/logo.png")
    assert res.status_code == 200

    res = client.get("/assets/images/avatar.png")
    assert res.status_code == 200


def test_protected_page_redirects_to_login(client):
    res = client.get("/")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

    res = client.get("/sessions", follow_redirects=False)
    assert res.status_code == 302


def test_api_requires_auth(client):
    res = client.get("/api/sessions")
    assert res.status_code == 401
    assert res.get_json() == {"error": "authentication required"}


def test_login_wrong_password(client):
    res = client.post(
        "/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert res.status_code == 200
    assert b"Invalid username or password" in res.data

    assert client.get("/api/sessions").status_code == 401


def test_login_success_and_logout(client):
    res = client.post(
        "/login",
        data={"username": "admin", "password": "secret123"},
    )
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/")

    res = client.get("/api/sessions")
    assert res.status_code == 200

    res = client.get("/")
    assert res.status_code == 200

    client.get("/logout")

    assert client.get("/api/sessions").status_code == 401


def test_login_redirects_to_next(client):
    res = client.post(
        "/login?next=/sessions",
        data={"username": "admin", "password": "secret123"},
    )
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/sessions")


def test_login_blocks_open_redirect(client):
    res = client.post(
        "/login?next=//evil.example",
        data={"username": "admin", "password": "secret123"},
    )
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/")
    assert "evil.example" not in res.headers["Location"]


def test_multi_user_file(tmp_path, monkeypatch):
    users_file = tmp_path / "users.yaml"
    users_file.write_text(
        "users:\n"
        "  - username: admin\n"
        f"    password_hash: {hash_password('adminpass')}\n"
        "  - username: analyst\n"
        f"    password_hash: {hash_password('analystpass')}\n"
    )
    monkeypatch.setenv("OSINT_DASHBOARD_USERS_FILE", str(users_file))
    monkeypatch.delenv("OSINT_DASHBOARD_PASSWORD", raising=False)
    monkeypatch.setenv("OSINT_DASHBOARD_SECRET_KEY", "test-secret")

    application = create_app(
        output_dir=str(tmp_path), auth_enabled=True
    )
    application.config["TESTING"] = True
    client = application.test_client()

    res = client.post(
        "/login",
        data={"username": "analyst", "password": "analystpass"},
    )
    assert res.status_code == 302
    assert client.get("/api/sessions").status_code == 200

    client.get("/logout")

    res = client.post(
        "/login",
        data={"username": "analyst", "password": "adminpass"},
    )
    assert res.status_code == 200
    assert b"Invalid" in res.data


def test_auth_disabled_no_protection(tmp_path):
    application = create_app(
        output_dir=str(tmp_path), auth_enabled=False
    )
    application.config["TESTING"] = True
    client = application.test_client()

    assert client.get("/").status_code == 200
    assert client.get("/api/sessions").status_code == 200
    assert client.get("/login").status_code == 404


def test_password_hash_helpers():
    password_hash = hash_password("hunter2")
    assert password_hash.startswith(("pbkdf2:", "scrypt:"))
    assert verify_password(password_hash, "hunter2") is True
    assert verify_password(password_hash, "wrong") is False
    assert verify_password("", "x") is False


def test_secret_key_persisted(tmp_path, monkeypatch):
    monkeypatch.delenv("OSINT_DASHBOARD_SECRET_KEY", raising=False)
    first = resolve_secret_key(str(tmp_path))
    second = resolve_secret_key(str(tmp_path))
    assert first == second
    assert len(first) >= 32


def test_default_credentials_admin123(tmp_path, monkeypatch):
    monkeypatch.delenv("OSINT_DASHBOARD_USER", raising=False)
    monkeypatch.delenv("OSINT_DASHBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("OSINT_DASHBOARD_USERS_FILE", raising=False)
    monkeypatch.setenv("OSINT_DASHBOARD_SECRET_KEY", "test-secret")

    from dashboard.auth import resolve_users

    users = resolve_users(str(tmp_path))
    assert "admin" in users
    assert verify_password(users["admin"], "admin123") is True
    assert verify_password(users["admin"], "wrong") is False

    auto_file = tmp_path / ".dashboard_users.yaml"
    assert auto_file.exists()

    users_again = resolve_users(str(tmp_path))
    assert users_again == users


def test_change_password_flow(tmp_path, monkeypatch):
    monkeypatch.delenv("OSINT_DASHBOARD_USER", raising=False)
    monkeypatch.delenv("OSINT_DASHBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("OSINT_DASHBOARD_USERS_FILE", raising=False)
    monkeypatch.setenv("OSINT_DASHBOARD_SECRET_KEY", "test-secret")

    application = create_app(
        output_dir=str(tmp_path), auth_enabled=True
    )
    application.config["TESTING"] = True
    client = application.test_client()

    res = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert res.status_code == 302

    res = client.get("/change-password")
    assert res.status_code == 200

    res = client.post(
        "/change-password",
        data={
            "current_password": "nope",
            "new_password": "newpass99",
            "confirm_password": "newpass99",
        },
    )
    assert b"Current password is incorrect" in res.data

    res = client.post(
        "/change-password",
        data={
            "current_password": "admin123",
            "new_password": "short",
            "confirm_password": "short",
        },
    )
    assert b"at least 8 characters" in res.data

    res = client.post(
        "/change-password",
        data={
            "current_password": "admin123",
            "new_password": "newpass99",
            "confirm_password": "different",
        },
    )
    assert b"do not match" in res.data

    res = client.post(
        "/change-password",
        data={
            "current_password": "admin123",
            "new_password": "newpass99",
            "confirm_password": "newpass99",
        },
    )
    assert b"Password changed successfully" in res.data

    assert client.get("/api/sessions").status_code == 200

    client.get("/logout")

    res = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert b"Invalid" in res.data

    res = client.post(
        "/login",
        data={"username": "admin", "password": "newpass99"},
    )
    assert res.status_code == 302


def test_change_password_requires_login(client):
    res = client.get("/change-password")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
