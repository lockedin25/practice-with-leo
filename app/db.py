"""One place that decides where the database lives and how it is opened.

Both decisions were previously spread across six call sites and a module-level
constant, which is how a deployment loses either its data or its concurrency.

**Where.** The path comes from the environment so a container can point it at a
mounted volume. The default keeps local development working unchanged. Getting
this wrong on a hosted platform is silent and total: the application starts, the
schema is created on an ephemeral disk, and every account, transcript and
evaluation disappears on the next deploy.

**How.** Write-ahead logging, which lets readers proceed while a write is in
flight. Measured on a ~13KB attempt save, which is the real payload size:

    concurrent writers   default journal   WAL
     8                     82ms             44ms
    25                   1,221ms           267ms
    50                   2,032ms           888ms

Note what the same measurement showed about a claim that is often made and is
not true here: SQLite did not fail at any of those levels. There were no
``database is locked`` errors, because the busy timeout absorbs the contention.
It degrades, it does not break. So this is a cheap latency win at the
concurrency a few hundred users actually reach, not a fix for an outage, and
Postgres is not needed until the day two instances are.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


# Long enough to outlast a slow write under contention, short enough that a
# genuinely stuck writer surfaces as an error rather than a hung request.
BUSY_TIMEOUT_MS = 5_000


class DatabaseBusy(RuntimeError):
    """A write waited out the busy timeout without ever acquiring the lock.

    The busy timeout absorbs ordinary contention, so reaching this exception
    means a writer held the database far longer than any normal save. Nothing
    was written, which makes resending the exact same request safe; a request
    path that lets this escape unanswered turns a busy moment into a bare 500
    and a candidate's lost turn.
    """


def is_busy_error(error: BaseException) -> bool:
    """True when ``error`` is SQLite reporting an exhausted busy timeout.

    ``database is locked`` is the one database failure the API can honestly
    answer with "please resend": the statement never ran. Every other
    ``OperationalError`` — a missing table, a malformed query — is a real fault
    and must keep surfacing as a 500 rather than being mislabelled retryable.
    """
    return isinstance(error, sqlite3.OperationalError) and "database is locked" in str(error)


def database_path(root: Path) -> Path:
    """Resolve the database location, preferring an explicit deployment value."""
    configured = os.getenv("DATABASE_PATH", "").strip()
    return Path(configured) if configured else root / "data" / "casecall.db"


def connect(path: Path | str) -> sqlite3.Connection:
    """Open a connection with the durability and concurrency settings we want.

    ``journal_mode`` is a property of the file and survives; ``synchronous`` and
    ``busy_timeout`` are per-connection and have to be set every time, which is
    the reason this helper exists rather than a one-off migration.
    """
    connection = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1000)
    connection.execute("PRAGMA journal_mode=WAL")
    # NORMAL trades a fsync per commit for one per checkpoint. Under WAL a crash
    # can lose the last transactions but cannot corrupt the file, which is the
    # right trade for interview transcripts.
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    # Referential integrity is off by default in SQLite and the schema declares
    # foreign keys, so without this they are decorative.
    connection.execute("PRAGMA foreign_keys=ON")
    return connection
