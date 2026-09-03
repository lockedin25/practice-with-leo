"""Write contention has one safe, proven failure mode.

An ordinary overlapping turn once took the whole API down with bare 500s
(feedback P0-2). The busy timeout absorbs ordinary contention, so a write that
reaches the request path as an error waited out ``busy_timeout`` entirely. For
exactly that case the API must answer with a structured, retryable 503, readers
must keep working (that is what WAL buys us), and a retry after the lock clears
must succeed. These tests hold a real SQLite write lock so that contract is
regression-tested rather than assumed.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from uuid import uuid4

from fastapi.testclient import TestClient

import app.db
import app.main as main
from conftest import sign_in


@contextmanager
def held_write_lock():
    """One raw writer holding the database's single write lock.

    ``BEGIN IMMEDIATE`` takes the write lock up front; the no-op write makes
    that hold explicit. Releasing happens by rollback, so a failing assertion
    inside the block can never leave the shared test database locked.
    """
    connection = app.db.connect(main.DATABASE_PATH)
    connection.isolation_level = None
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE attempts SET updated_at = updated_at")
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _begin_case_attempt(client: TestClient) -> str:
    started = client.post("/api/attempts", json={})
    assert started.status_code == 200
    attempt_id = started.json()["id"]
    ready = client.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "I'm ready to begin.", "turn_id": "ready"},
    )
    assert ready.status_code == 200
    return attempt_id


def test_turn_under_write_lock_answers_503_with_a_retryable_detail(
    candidate_client, stub_interviewer, monkeypatch
) -> None:
    client, _ = candidate_client
    attempt_id = _begin_case_attempt(client)

    # 50ms keeps the test fast; production keeps its 5s busy timeout untouched.
    monkeypatch.setattr(app.db, "BUSY_TIMEOUT_MS", 50)
    with held_write_lock():
        response = client.post(
            f"/api/attempts/{attempt_id}/turn",
            json={"content": "Let me split revenue into price times volume.", "turn_id": "contended"},
        )

    assert response.status_code == 503, response.text
    body = response.json()
    assert body["error"] == "database_busy"
    assert body["retryable"] is True
    # The browser renders detail verbatim, so it must stay a readable string
    # even though the rest of the body is structured.
    assert isinstance(body["detail"], str) and body["detail"]
    assert response.headers.get("retry-after") == "1"


def test_readers_stay_served_while_a_writer_holds_the_lock(monkeypatch) -> None:
    bystander = TestClient(main.app)

    monkeypatch.setattr(app.db, "BUSY_TIMEOUT_MS", 50)
    with held_write_lock():
        health = bystander.get("/health")
        cases = bystander.get("/api/cases")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert cases.status_code == 200
    assert cases.json()["cases"]


def test_turn_recovers_once_the_lock_clears(
    candidate_client, stub_interviewer, monkeypatch
) -> None:
    client, _ = candidate_client
    attempt_id = _begin_case_attempt(client)
    turn = {"content": "Let me examine the cost base next.", "turn_id": "contended"}

    monkeypatch.setattr(app.db, "BUSY_TIMEOUT_MS", 50)
    with held_write_lock():
        blocked = client.post(f"/api/attempts/{attempt_id}/turn", json=turn)

    assert blocked.status_code == 503
    # The blocked save wrote nothing, so resending the same turn is safe.
    recovered = client.post(f"/api/attempts/{attempt_id}/turn", json=turn)
    assert recovered.status_code == 200
    assert recovered.json()["attempt"]["id"] == attempt_id


def test_normal_concurrent_saves_both_succeed(candidate_client, stub_interviewer) -> None:
    client_a, _ = candidate_client
    client_b = TestClient(main.app)
    sign_in(client_b, f"candidate-{uuid4()}@casecall.test")
    attempt_a = _begin_case_attempt(client_a)
    attempt_b = _begin_case_attempt(client_b)

    barrier = threading.Barrier(2)
    status_codes: dict[str, int] = {}

    def submit(client: TestClient, attempt_id: str, tag: str) -> None:
        barrier.wait()
        response = client.post(
            f"/api/attempts/{attempt_id}/turn",
            json={"content": f"Structuring my {tag} approach.", "turn_id": f"turn-{tag}"},
        )
        status_codes[tag] = response.status_code

    threads = [
        threading.Thread(target=submit, args=(client_a, attempt_a, "a")),
        threading.Thread(target=submit, args=(client_b, attempt_b, "b")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    # Ordinary overlap is the busy timeout's job, not the 503's: both saves land.
    assert status_codes == {"a": 200, "b": 200}


def test_only_exhausted_locks_are_translated() -> None:
    """A missing table must stay a 500-class fault, never a mislabelled retry."""
    assert app.db.is_busy_error(sqlite3.OperationalError("database is locked"))
    assert not app.db.is_busy_error(sqlite3.OperationalError("no such table: attempts"))
