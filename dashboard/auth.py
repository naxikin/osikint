"""Dashboard authentication: multi-user session login.

User sources (in priority order):
1. OSINT_DASHBOARD_USERS_FILE -> YAML file with username/password_hash
2. <output_dir>/.dashboard_users.yaml -> persisted overrides
   (written by "change password" or default-credential bootstrap)
3. config/users.yaml
4. OSINT_DASHBOARD_USER + OSINT_DASHBOARD_PASSWORD(_HASH)
5. default admin/admin123 (persisted to (2), printed as a warning)

Passwords are only ever stored as werkzeug hashes; comparisons use
constant-time verification.
"""

import hmac
import os
import secrets
import sys

import yaml
from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from core.logger import get_logger

logger = get_logger("dashboard.auth")

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
DEFAULT_USERS_FILE = os.path.join(PROJECT_ROOT, "config", "users.yaml")

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"
MIN_PASSWORD_LENGTH = 8
AUTO_USERS_FILE = ".dashboard_users.yaml"
AUTO_SECRET_FILE = ".dashboard_secret"


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    if not password_hash:
        return False
    return check_password_hash(password_hash, password)


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(
        a.encode("utf-8"), b.encode("utf-8")
    )


def load_users_file(path: str) -> dict:
    """Returns {username: password_hash}."""
    if not path or not os.path.isfile(path):
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("cannot load users file %s: %s", path, exc)
        return {}

    users = {}
    for entry in data.get("users", []):
        username = entry.get("username")
        password_hash = entry.get("password_hash")
        if username and password_hash:
            users[username] = password_hash
    return users


def save_users_file(path: str, users: dict) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    data = {
        "users": [
            {"username": name, "password_hash": password_hash}
            for name, password_hash in sorted(users.items())
        ]
    }

    with open(path, "w", encoding="utf-8") as f:
        f.write("# Auto-generated dashboard credentials (passwords hashed)\n")
        yaml.safe_dump(data, f, sort_keys=True, default_flow_style=False)


def resolve_users(output_dir: str) -> dict:
    """Builds the user table from configured sources."""
    users_file = os.environ.get("OSINT_DASHBOARD_USERS_FILE")
    if users_file:
        users = load_users_file(users_file)
        if users:
            return users

    auto_file = os.path.join(output_dir, AUTO_USERS_FILE)
    users = load_users_file(auto_file)
    if users:
        return users

    local_file = DEFAULT_USERS_FILE
    users = load_users_file(local_file)
    if users:
        return users

    env_user = os.environ.get("OSINT_DASHBOARD_USER", "").strip()
    env_password = os.environ.get("OSINT_DASHBOARD_PASSWORD")
    env_hash = os.environ.get("OSINT_DASHBOARD_PASSWORD_HASH")

    if env_user and env_password:
        return {env_user: hash_password(env_password)}

    if env_user and env_hash:
        return {env_user: env_hash}

    username = env_user or DEFAULT_USERNAME
    users = {username: hash_password(DEFAULT_PASSWORD)}

    try:
        save_users_file(auto_file, users)
    except OSError as exc:
        logger.warning("cannot persist default credentials: %s", exc)

    logger.warning(
        "DASHBOARD AUTH: using default credentials "
        "user=%s password=%s. Change it after login "
        "(or via OSINT_DASHBOARD_PASSWORD / config/users.yaml).",
        username,
        DEFAULT_PASSWORD,
    )
    return users


def update_password(
    users: dict,
    username: str,
    new_password: str,
    output_dir: str,
) -> None:
    """Updates a user's password hash and persists it back to the
    originating users file."""
    users[username] = hash_password(new_password)

    env_file = os.environ.get("OSINT_DASHBOARD_USERS_FILE")
    if env_file:
        save_users_file(env_file, users)
        return

    local_file = DEFAULT_USERS_FILE
    if os.path.isfile(local_file):
        save_users_file(local_file, users)
        return

    save_users_file(os.path.join(output_dir, AUTO_USERS_FILE), users)


def resolve_secret_key(output_dir: str) -> str:
    env_secret = os.environ.get("OSINT_DASHBOARD_SECRET_KEY")
    if env_secret:
        return env_secret

    secret_path = os.path.join(output_dir, AUTO_SECRET_FILE)
    try:
        with open(secret_path, encoding="utf-8") as f:
            existing = f.read().strip()
        if existing:
            return existing
    except OSError:
        pass

    generated = secrets.token_hex(32)
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(secret_path, "w", encoding="utf-8") as f:
            f.write(generated)
    except OSError as exc:
        logger.warning("cannot persist secret key: %s", exc)
    return generated


def login_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user"):
            return view(*args, **kwargs)

        if request.path.startswith("/api/"):
            return jsonify({"error": "authentication required"}), 401

        return redirect(url_for("login_page", next=request.path))

    return wrapped


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv or argv[0] != "hash":
        print("usage: python -m dashboard.auth hash <password>")
        return 1

    password = argv[1] if len(argv) > 1 else ""
    if not password:
        print("usage: python -m dashboard.auth hash <password>")
        return 1

    print(hash_password(password))
    return 0


if __name__ == "__main__":
    sys.exit(main())
