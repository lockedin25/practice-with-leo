"""Authentication boundaries: session integrity, sign-in gating, and isolation."""

from __future__ import annotations

import base64
import json
import time

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.accounts import OAUTH_STATE_COOKIE, SESSION_COOKIE, Signer
from app.auth import decode_google_id_token
from conftest import sign_in


def _id_token(**overrides) -> str:
    claims = {
        "sub": "google-user-1",
        "email": "candidate@casecall.test",
        "email_verified": True,
        "name": "Candidate",
        "aud": "test-client-id",
        "iss": "https://accounts.google.com",
        "exp": int(time.time()) + 600,
        **overrides,
    }
    encode = lambda payload: base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{encode({'alg': 'RS256'})}.{encode(claims)}.not-a-real-signature"


# --- Session cookies -------------------------------------------------------


def test_a_signed_session_round_trips() -> None:
    signer = Signer(b"secret")
    token = signer.sign({"uid": "abc"}, 60)
    assert signer.unsign(token) == {"uid": "abc", "exp": pytest.approx(int(time.time()) + 60, abs=2)}


def test_a_tampered_session_is_rejected() -> None:
    signer = Signer(b"secret")
    payload, _, signature = signer.sign({"uid": "abc"}, 60).rpartition(".")
    forged = base64.urlsafe_b64encode(b'{"uid":"admin","exp":9999999999}').decode().rstrip("=")
    assert signer.unsign(f"{forged}.{signature}") is None


def test_a_session_signed_with_another_secret_is_rejected() -> None:
    token = Signer(b"secret-one").sign({"uid": "abc"}, 60)
    assert Signer(b"secret-two").unsign(token) is None


def test_an_expired_session_is_rejected() -> None:
    signer = Signer(b"secret")
    assert signer.unsign(signer.sign({"uid": "abc"}, -1)) is None


# --- Gating ----------------------------------------------------------------


def test_the_interview_api_requires_a_signed_in_user() -> None:
    client = TestClient(main.app)
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/attempts", json={}).status_code == 401
    # The case catalogue stays public: it is candidate-safe metadata that the
    # landing page shows before anyone signs in.
    assert client.get("/api/cases").status_code == 200


def test_the_practice_room_sends_anonymous_visitors_to_sign_in() -> None:
    client = TestClient(main.app)
    response = client.get("/practice", follow_redirects=False)
    assert response.status_code == 303
    # Starlette percent-encodes the redirect target.
    assert response.headers["location"] in ("/login?next=/practice", "/login?next=%2Fpractice")


def test_the_sign_in_page_sends_signed_in_candidates_to_practice(candidate_client) -> None:
    client, _ = candidate_client
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/practice"


def test_a_signed_in_candidate_can_start_and_read_their_own_attempt(candidate_client) -> None:
    client, _ = candidate_client
    started = client.post("/api/attempts", json={})
    assert started.status_code == 200
    attempt_id = started.json()["id"]
    assert client.get(f"/api/attempts/{attempt_id}").status_code == 200


# --- Isolation -------------------------------------------------------------


def test_one_candidate_cannot_read_another_candidates_attempt(candidate_client) -> None:
    owner_client, _ = candidate_client
    attempt_id = owner_client.post("/api/attempts", json={}).json()["id"]

    intruder = TestClient(main.app)
    sign_in(intruder, "intruder@casecall.test")

    # 404, not 403: the API must not confirm that the attempt exists.
    assert intruder.get(f"/api/attempts/{attempt_id}").status_code == 404
    assert intruder.post(
        f"/api/attempts/{attempt_id}/turn", json={"content": "hello", "turn_id": "t1"}
    ).status_code == 404
    assert intruder.post(f"/api/attempts/{attempt_id}/end").status_code == 404


def test_an_unclaimed_attempt_is_not_readable_by_a_signed_in_stranger(candidate_client) -> None:
    client, _ = candidate_client
    orphan = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/attempts/{orphan}").status_code == 404


# --- Google ID tokens ------------------------------------------------------


def test_a_valid_google_id_token_yields_its_claims() -> None:
    claims = decode_google_id_token(_id_token(), "test-client-id")
    assert claims["email"] == "candidate@casecall.test"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "someone-elses-client-id"},
        {"iss": "https://evil.example.com"},
        {"exp": int(time.time()) - 5},
        {"email_verified": False},
        {"email": ""},
    ],
    ids=["wrong-audience", "wrong-issuer", "expired", "unverified-email", "no-email"],
)
def test_an_untrustworthy_id_token_is_refused(overrides) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        decode_google_id_token(_id_token(**overrides), "test-client-id")


def test_a_malformed_id_token_is_refused() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        decode_google_id_token("not.a.jwt.at.all", "test-client-id")


# --- Callback --------------------------------------------------------------


def test_the_callback_refuses_a_state_that_does_not_match_the_browser() -> None:
    client = TestClient(main.app)
    client.cookies.set(OAUTH_STATE_COOKIE, "cookie-state")
    response = client.get(
        "/auth/google/callback?code=abc&state=query-state", follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login?error=state_mismatch"


def test_the_callback_reports_a_cancelled_sign_in() -> None:
    client = TestClient(main.app)
    response = client.get("/auth/google/callback?error=access_denied", follow_redirects=False)
    assert response.headers["location"] == "/login?error=denied"


def test_sign_in_is_unavailable_until_google_credentials_are_configured(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    client = TestClient(main.app)
    assert client.get("/api/auth/config").json()["google_configured"] is False
    response = client.get("/auth/google/start", follow_redirects=False)
    assert response.headers["location"] == "/login?error=not_configured"


def test_sign_in_redirects_to_google_once_configured(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    client = TestClient(main.app)
    response = client.get("/auth/google/start?next=/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "scope=openid+email+profile" in response.headers["location"]
    assert client.cookies.get(OAUTH_STATE_COOKIE)


def test_an_open_redirect_cannot_be_smuggled_through_next(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    from app.auth import _safe_next

    assert _safe_next("//evil.example.com") == "/"
    assert _safe_next("https://evil.example.com") == "/"
    assert _safe_next("/admin") == "/admin"


def test_a_domain_outside_the_allow_list_cannot_sign_in(monkeypatch) -> None:
    from app.accounts import LoginNotPermitted

    monkeypatch.setenv("ALLOWED_EMAIL_DOMAINS", "joinef.com")
    with pytest.raises(LoginNotPermitted):
        main.ACCOUNTS.upsert_from_google(
            {"sub": "outsider", "email": "someone@gmail.com", "name": "Outsider"}
        )


def test_signing_out_clears_the_session(candidate_client) -> None:
    client, _ = candidate_client
    assert client.get("/api/me").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    client.cookies.clear()
    assert client.get("/api/me").status_code == 401
