"""Google sign-in over the OAuth 2.0 authorization-code flow.

The browser never sees the client secret and never handles a token: the code is
exchanged server side and the result is an opaque, signed session cookie.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.accounts import (
    OAUTH_STATE_COOKIE,
    OAUTH_STATE_TTL_SECONDS,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    LoginNotPermitted,
    User,
    accounts_of,
    allowed_email_domains,
    current_user,
    require_user,
    secure_cookies,
)

logger = logging.getLogger("casecall.auth")
router = APIRouter()

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8000/auth/google/callback"


def client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "").strip()


def redirect_uri() -> str:
    return os.getenv("OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()


def google_configured() -> bool:
    return bool(client_id() and client_secret())


def _safe_next(value: str | None) -> str:
    """Only ever redirect back into this application."""
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


def _fail(reason: str, detail: str = "") -> RedirectResponse:
    if detail:
        logger.warning("Google sign-in failed (%s): %s", reason, detail)
    response = RedirectResponse(f"/login?error={reason}", status_code=303)
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    return response


@router.get("/api/auth/config")
def auth_config() -> dict[str, Any]:
    return {
        "google_configured": google_configured(),
        "allowed_domains": list(allowed_email_domains()),
    }


@router.get("/api/me")
def read_me(request: Request) -> dict[str, Any]:
    user: User = require_user(request)
    return {"user": user.public_view()}


@router.get("/auth/google/start")
def start_google_login(request: Request, next: str = "/") -> RedirectResponse:
    if not google_configured():
        return _fail("not_configured")

    nonce = secrets.token_urlsafe(24)
    state = accounts_of(request).signer.sign(
        {"nonce": nonce, "next": _safe_next(next)}, OAUTH_STATE_TTL_SECONDS
    )
    query = urlencode(
        {
            "client_id": client_id(),
            "redirect_uri": redirect_uri(),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )
    response = RedirectResponse(f"{GOOGLE_AUTHORIZE_URL}?{query}", status_code=303)
    # Double-submit: the same signed state must come back in both the query and the cookie.
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure_cookies(),
        path="/",
    )
    return response


@router.get("/auth/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        return _fail("denied", error)
    if not code or not state:
        return _fail("invalid_response")

    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not cookie_state or not secrets.compare_digest(cookie_state, state):
        return _fail("state_mismatch")

    payload = accounts_of(request).signer.unsign(state)
    if payload is None:
        return _fail("state_expired")

    try:
        claims = await _exchange_code_for_claims(code)
    except HTTPException as failure:
        return _fail("google_error", str(failure.detail))

    try:
        user = accounts_of(request).upsert_from_google(claims)
    except LoginNotPermitted as refusal:
        return _fail("domain_not_allowed", str(refusal))

    response = RedirectResponse(_safe_next(payload.get("next")), status_code=303)
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    response.set_cookie(
        SESSION_COOKIE,
        accounts_of(request).issue_session(user),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure_cookies(),
        path="/",
    )
    logger.info("Signed in %s", user.email)
    return response


@router.post("/auth/logout")
def logout(response: Response) -> Response:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.status_code = 204
    return response


async def _exchange_code_for_claims(code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        exchange = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id(),
                "client_secret": client_secret(),
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
    if exchange.status_code != 200:
        raise HTTPException(status_code=502, detail=f"token endpoint returned {exchange.status_code}")

    id_token = exchange.json().get("id_token")
    if not id_token:
        raise HTTPException(status_code=502, detail="token endpoint returned no id_token")
    return decode_google_id_token(id_token, client_id())


def decode_google_id_token(id_token: str, expected_audience: str) -> dict[str, Any]:
    """Read the claims of an ID token that came straight from Google's token endpoint.

    Signature verification is intentionally omitted: this token was just fetched
    over TLS from Google in a server-to-server call authenticated with the client
    secret, which Google documents as sufficient. The audience, issuer, expiry and
    verified-email claims are still checked, because those are what authorise the
    session. An ID token arriving by any other route must not be trusted here.
    """
    parts = id_token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=502, detail="malformed id_token")

    try:
        segment = parts[1]
        claims = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
    except (ValueError, json.JSONDecodeError) as failure:
        raise HTTPException(status_code=502, detail="unreadable id_token") from failure

    if claims.get("aud") != expected_audience:
        raise HTTPException(status_code=502, detail="id_token audience mismatch")
    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(status_code=502, detail="id_token issuer mismatch")
    if int(claims.get("exp", 0)) <= int(time.time()):
        raise HTTPException(status_code=502, detail="id_token expired")
    if not claims.get("sub") or not claims.get("email"):
        raise HTTPException(status_code=502, detail="id_token missing identity claims")
    if claims.get("email_verified") is False:
        raise HTTPException(status_code=502, detail="Google has not verified this email address")
    return claims


__all__ = ["router", "google_configured", "decode_google_id_token", "current_user"]
