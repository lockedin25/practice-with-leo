"""Point the application at a throwaway database before any test module imports it.

pytest_configure runs before collection, so app.main is rebound here rather than
in a fixture. Without this, tests would read and write the developer's own
data/casecall.db.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from app.accounts import SESSION_COOKIE, AccountStore, User
from app.store import SessionStore

_TEMPORARY_ROOT: Path | None = None


def pytest_configure(config: pytest.Config) -> None:
    global _TEMPORARY_ROOT
    _TEMPORARY_ROOT = Path(tempfile.mkdtemp(prefix="casecall-tests-"))
    database = _TEMPORARY_ROOT / "casecall.db"

    import app.main as main

    main.DATABASE_PATH = database
    main.ACCOUNTS = AccountStore(database)
    main.STORE = SessionStore(database)
    main.app.state.accounts = main.ACCOUNTS
    main.app.state.store = main.STORE
    main.app.state.database_path = database


def pytest_unconfigure(config: pytest.Config) -> None:
    if _TEMPORARY_ROOT is not None:
        shutil.rmtree(_TEMPORARY_ROOT, ignore_errors=True)


def sign_in(client, email: str, name: str = "Test Candidate") -> User:
    """Create the account Google would have created, then attach its session cookie."""
    import app.main as main

    user = main.ACCOUNTS.upsert_from_google({"sub": f"google-{email}", "email": email, "name": name})
    client.cookies.set(SESSION_COOKIE, main.ACCOUNTS.issue_session(user))
    return user


@pytest.fixture(autouse=True)
def _authentication_stays_real():
    """Guard against a module-level dependency override leaking across tests.

    Overriding require_user at import time disables authentication for every
    test collected afterwards, which quietly hides real regressions. Tests sign
    in through conftest.sign_in instead, which exercises the true cookie path.
    """
    import app.main as main
    from app.accounts import require_user

    main.app.dependency_overrides.pop(require_user, None)
    yield
    main.app.dependency_overrides.pop(require_user, None)


@pytest.fixture
def candidate_client():
    from fastapi.testclient import TestClient

    import app.main as main

    client = TestClient(main.app)
    user = sign_in(client, "candidate@casecall.test")
    return client, user


@pytest.fixture
def admin_client(monkeypatch):
    from fastapi.testclient import TestClient

    import app.main as main

    monkeypatch.setenv("ADMIN_EMAILS", "director@casecall.test")
    client = TestClient(main.app)
    user = sign_in(client, "director@casecall.test", name="Programme Director")
    return client, user


@pytest.fixture
def stub_interviewer(monkeypatch):
    """Replace the LLM interviewer with a scripted one that releases a known fact."""
    from app.interviewer import InterviewTurn

    class StubInterviewer:
        def respond(self, session, candidate_turn):
            session.record_candidate_turn(candidate_turn)
            facts = session.case.validate_fact_selection(
                ["customers.segment-mix"], session.stage, session.disclosed_ids
            )
            session.apply_director_decision(session.stage, facts)
            session.add_interviewer_turn("Noted.")
            return InterviewTurn(reply="Noted.", facts=facts)

    import app.main as main

    monkeypatch.setattr(main, "INTERVIEWER", StubInterviewer())
