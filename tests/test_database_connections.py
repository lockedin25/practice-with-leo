"""Every connection this application opens is closed when its block ends.

A ``sqlite3.Connection`` used as a context manager commits or rolls back; it
does not close. Every store here was written that way, and because a connection
sits in a reference cycle it was reclaimed by the cyclic collector rather than
by refcount, so descriptors accumulated for an unbounded number of requests.
The failure that reached a contributor was not "too many open files" but

    sqlite3.OperationalError: unable to open database file

raised against a healthy database, from whichever request happened to be next
rather than from any of the ones that leaked. macOS gives a launchd-started
process a soft limit of 256 descriptors, which one contribution conversation
reaches comfortably.

These tests pin the lifetime rather than the symptom: connections are closed,
descriptors do not grow across many operations, and a real API conversation run
under a deliberately tight descriptor budget still completes.
"""

from __future__ import annotations

import os
import resource
import sqlite3
from pathlib import Path

import pytest

import app.db as db
import app.main as main
from app.store import ContributionStore


HAS_PROC_FD = os.path.isdir("/dev/fd")


def descriptors_held() -> int:
    return len(os.listdir("/dev/fd"))


def is_closed(connection: sqlite3.Connection) -> bool:
    """A closed connection refuses even a trivial statement."""
    try:
        connection.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        return True
    return False


@pytest.fixture
def store(tmp_path: Path) -> ContributionStore:
    return ContributionStore(tmp_path / "casecall.db")


@pytest.fixture
def opened(monkeypatch) -> list[sqlite3.Connection]:
    """Record every connection the application opens during a test."""
    connections: list[sqlite3.Connection] = []
    real_connect = db.connect

    def recording_connect(path):
        connection = real_connect(path)
        connections.append(connection)
        return connection

    monkeypatch.setattr(db, "connect", recording_connect)
    return connections


def test_transaction_closes_the_connection_it_opened(tmp_path: Path) -> None:
    with db.transaction(tmp_path / "casecall.db") as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
        assert not is_closed(connection)
    assert is_closed(connection)


def test_transaction_closes_even_when_the_block_raises(tmp_path: Path) -> None:
    """A failing write must not be the one that leaks the descriptor."""
    escaped: sqlite3.Connection | None = None
    with pytest.raises(sqlite3.OperationalError):
        with db.transaction(tmp_path / "casecall.db") as connection:
            escaped = connection
            connection.execute("SELECT * FROM no_such_table")
    assert escaped is not None and is_closed(escaped)


def test_transaction_still_commits_and_rolls_back(tmp_path: Path) -> None:
    """Closing is added to the existing transaction semantics, not instead of it."""
    path = tmp_path / "casecall.db"
    with db.transaction(path) as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
    with db.transaction(path) as connection:
        connection.execute("INSERT INTO t VALUES (1)")
    with pytest.raises(sqlite3.OperationalError):
        with db.transaction(path) as connection:
            connection.execute("INSERT INTO t VALUES (2)")
            connection.execute("SELECT * FROM no_such_table")
    with db.transaction(path) as connection:
        assert connection.execute("SELECT a FROM t").fetchall() == [(1,)]


def test_store_operations_leave_no_connection_open(store, opened) -> None:
    store.create("session-1", "user-1", {"turns": 0})
    store.save_state("session-1", {"turns": 1})
    store.get("session-1")
    store.live_for_user("user-1")
    store.finish("session-1", status="submitted", case_id="case-1")

    assert opened, "the store did not go through app.db.connect"
    assert [is_closed(connection) for connection in opened] == [True] * len(opened)


@pytest.mark.skipif(not HAS_PROC_FD, reason="no /dev/fd to count descriptors on")
def test_descriptors_do_not_grow_across_many_store_operations(store) -> None:
    store.create("warmup", "warmup-user", {"turns": 0})
    store.get("warmup")
    baseline = descriptors_held()

    for index in range(150):
        store.create(f"session-{index}", f"user-{index}", {"turns": 0})
        store.save_state(f"session-{index}", {"turns": index})
        store.get(f"session-{index}")
        store.live_for_user(f"user-{index}")

    # Before the fix this grew by one per operation, so 600 operations put the
    # process past any soft limit it is likely to have been given.
    assert descriptors_held() == baseline


@pytest.mark.skipif(not HAS_PROC_FD, reason="no /dev/fd to count descriptors on")
def test_a_contribution_conversation_survives_a_tight_descriptor_budget(
    candidate_client, monkeypatch
) -> None:
    """The reported failure, reproduced end to end and then required to pass.

    The budget is set just above what the process already holds, which is the
    condition a 256-descriptor limit creates after an hour of ordinary use. A
    leaking request path exhausts it within a few turns and answers
    ``unable to open database file``; a closing one never approaches it.
    """
    from tests.test_contribution_loop import author

    client, _ = candidate_client
    monkeypatch.setattr(main, "CASE_AUTHOR", author(*({} for _ in range(40))))

    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (descriptors_held() + 20, hard))
    try:
        session = client.post("/api/contributions").json()["id"]
        for _ in range(15):
            response = client.post(
                f"/api/contributions/{session}/turn", json={"content": "I do not recall"}
            )
            assert response.status_code == 200, response.text
            assert client.get(f"/api/contributions/{session}").status_code == 200
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))


def test_an_unopenable_database_names_the_reason_it_could_not_open() -> None:
    """The bare six-word message sends the reader to the wrong place.

    A missing directory, an unwritable one and an exhausted descriptor limit are
    all reported as "unable to open database file" against a database that has
    nothing wrong with it, so the resolved path and the descriptor census are
    attached to the error rather than left to be guessed at.
    """
    error = db._explain_open_failure(
        sqlite3.OperationalError("unable to open database file"), Path("/nope/casecall.db")
    )
    message = str(error)
    assert "/nope/casecall.db" in message
    assert "parent directory exists: False" in message
    assert "file descriptors" in message and "held of" in message


def test_enrichment_leaves_other_failures_and_busy_detection_alone() -> None:
    """Only the ambiguous message is rewritten, and never at retry logic's expense."""
    original = sqlite3.OperationalError("no such table: attempts")
    assert db._explain_open_failure(original, Path("/tmp/casecall.db")) is original

    busy = db._explain_open_failure(
        sqlite3.OperationalError("database is locked, unable to open database file"),
        Path("/tmp/casecall.db"),
    )
    assert db.is_busy_error(busy)
