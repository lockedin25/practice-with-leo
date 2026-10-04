"""User accounts, signed session cookies, and attempt ownership.

Deliberately separate from the case runtime. Authentication never touches the
private reservoir, and this module owns its own tables so the runtime's attempt
storage schema is never modified.

No third-party crypto dependency: session cookies are HMAC-SHA256 signed with
the standard library, which is sufficient for an opaque, server-issued token.
"""

from __future__ import annotations

from app import db

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request


SESSION_COOKIE = "casecall_session"
OAUTH_STATE_COOKIE = "casecall_oauth_state"
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
OAUTH_STATE_TTL_SECONDS = 10 * 60


@dataclass(frozen=True)
class User:
    id: str
    email: str
    name: str
    picture: str
    is_admin: bool
    created_at: str
    last_login_at: str

    def public_view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "is_admin": self.is_admin,
        }


class LoginNotPermitted(Exception):
    """The Google account is valid but this deployment does not admit it."""


# --- Configuration ---------------------------------------------------------


def _csv_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(item.strip().lower() for item in raw.split(",") if item.strip())


def admin_emails() -> tuple[str, ...]:
    return _csv_env("ADMIN_EMAILS")


def allowed_email_domains() -> tuple[str, ...]:
    return _csv_env("ALLOWED_EMAIL_DOMAINS")


def is_admin_email(email: str) -> bool:
    return email.strip().lower() in admin_emails()


def assert_login_permitted(email: str) -> None:
    domains = allowed_email_domains()
    if not domains:
        return
    domain = email.split("@")[-1].strip().lower()
    if domain not in domains:
        raise LoginNotPermitted(
            "This Leo deployment only accepts accounts from: " + ", ".join(domains)
        )


def secure_cookies() -> bool:
    """Only mark cookies Secure when the deployment is actually served over TLS."""
    return os.getenv("OAUTH_REDIRECT_URI", "").startswith("https://")


# --- Signing ---------------------------------------------------------------


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class Signer:
    """Signs short JSON payloads for cookies. The secret never leaves the host."""

    def __init__(self, secret: bytes) -> None:
        self._secret = secret

    def sign(self, payload: dict[str, Any], ttl_seconds: int) -> str:
        body = {**payload, "exp": int(time.time()) + ttl_seconds}
        encoded = _b64encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode())
        return f"{encoded}.{self._digest(encoded)}"

    def unsign(self, token: str | None) -> dict[str, Any] | None:
        if not token or "." not in token:
            return None
        encoded, _, signature = token.rpartition(".")
        if not hmac.compare_digest(signature, self._digest(encoded)):
            return None
        try:
            payload = json.loads(_b64decode(encoded))
        except (ValueError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload

    def _digest(self, encoded: str) -> str:
        return _b64encode(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())


def load_or_create_secret(path: Path) -> bytes:
    """Prefer SESSION_SECRET; otherwise keep a generated one so reloads do not sign users out."""
    configured = os.getenv("SESSION_SECRET", "").strip()
    if configured:
        return configured.encode()

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_bytes().strip()

    generated = secrets.token_hex(32).encode()
    path.write_bytes(generated)
    path.chmod(0o600)
    return generated


# --- Storage ---------------------------------------------------------------


class AccountStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self.signer = Signer(load_or_create_secret(database_path.parent / ".session_secret"))
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    google_sub TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    picture TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS users_email ON users(email);
                CREATE TABLE IF NOT EXISTS attempt_owners (
                    attempt_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS attempt_owners_user ON attempt_owners(user_id);
                """
            )

    # -- users

    def upsert_from_google(self, claims: dict[str, Any]) -> User:
        email = str(claims["email"]).strip()
        assert_login_permitted(email)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (id, google_sub, email, name, picture)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(google_sub) DO UPDATE SET
                    email = excluded.email,
                    name = excluded.name,
                    picture = excluded.picture,
                    last_login_at = CURRENT_TIMESTAMP
                """,
                (
                    str(uuid4()),
                    str(claims["sub"]),
                    email,
                    str(claims.get("name") or email.split("@")[0]),
                    str(claims.get("picture") or ""),
                ),
            )
            row = connection.execute(
                "SELECT id, email, name, picture, created_at, last_login_at FROM users WHERE google_sub = ?",
                (str(claims["sub"]),),
            ).fetchone()
        return _user_from_row(row)

    def get(self, user_id: str) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, email, name, picture, created_at, last_login_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return _user_from_row(row) if row else None

    # -- sessions

    def issue_session(self, user: User) -> str:
        return self.signer.sign({"uid": user.id}, SESSION_TTL_SECONDS)

    def user_from_session(self, token: str | None) -> User | None:
        payload = self.signer.unsign(token)
        if not payload or not isinstance(payload.get("uid"), str):
            return None
        return self.get(payload["uid"])

    # -- attempt ownership

    def claim_attempt(self, attempt_id: str, user_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO attempt_owners (attempt_id, user_id) VALUES (?, ?)",
                (attempt_id, user_id),
            )

    def owner_of(self, attempt_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT user_id FROM attempt_owners WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
        return row[0] if row else None

    def _connect(self) -> AbstractContextManager[sqlite3.Connection]:
        return db.transaction(self._database_path)


def _user_from_row(row: tuple[Any, ...]) -> User:
    return User(
        id=row[0],
        email=row[1],
        name=row[2],
        picture=row[3],
        is_admin=is_admin_email(row[1]),
        created_at=row[4],
        last_login_at=row[5],
    )


# --- Request dependencies --------------------------------------------------


def accounts_of(request: Request) -> AccountStore:
    return request.app.state.accounts


def current_user(request: Request) -> User | None:
    return accounts_of(request).user_from_session(request.cookies.get(SESSION_COOKIE))


def require_user(request: Request) -> User:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return user


def require_admin(request: Request) -> User:
    user = require_user(request)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="This view is restricted to Leo administrators")
    return user
