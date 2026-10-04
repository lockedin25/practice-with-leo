"""Small durable store for local and single-instance deployments.

Keeping attempts in SQLite means Uvicorn reloads do not discard an interview
between the browser creating an attempt and sending its next turn.
"""

from __future__ import annotations

from app import db

import json
import sqlite3
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.case_runtime import CaseCatalogue, CaseWorld, InterviewSession


@dataclass(frozen=True)
class VoiceSession:
    id: str
    attempt_id: str
    provider: str
    agent_id: str
    provider_conversation_id: str
    status: str
    case_started: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class ActiveVoiceSessionExists(RuntimeError):
    """An attempt may have only one live provider conversation."""


class SessionStore:
    SCHEMA_VERSION = 4

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    user_id TEXT,
                    session_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            attempt_columns = {row[1] for row in connection.execute("PRAGMA table_info(attempts)")}
            if "user_id" not in attempt_columns:
                connection.execute("ALTER TABLE attempts ADD COLUMN user_id TEXT")
            if "created_at" not in attempt_columns:
                connection.execute("ALTER TABLE attempts ADD COLUMN created_at TEXT")
                connection.execute("UPDATE attempts SET created_at = updated_at WHERE created_at IS NULL")
            if "case_version" not in attempt_columns:
                # Attempts written before case versioning ran against packages on
                # disk, which are all version 1, so backfilling that is accurate
                # rather than a guess.
                connection.execute(
                    "ALTER TABLE attempts ADD COLUMN case_version INTEGER NOT NULL DEFAULT 1"
                )
            connection.execute("CREATE INDEX IF NOT EXISTS attempts_user_updated ON attempts(user_id, updated_at DESC)")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS user_case_progress (
                    user_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('not_started', 'in_progress', 'solved')),
                    attempts_count INTEGER NOT NULL DEFAULT 0,
                    latest_attempt_id TEXT,
                    last_completed_at TEXT,
                    best_score REAL,
                    reset_at TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, case_id)
                );
                CREATE INDEX IF NOT EXISTS user_case_progress_user_updated
                    ON user_case_progress(user_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS voice_sessions (
                    id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    provider_conversation_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    case_started INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS voice_sessions_attempt ON voice_sessions(attempt_id);
                CREATE UNIQUE INDEX IF NOT EXISTS voice_sessions_one_live_attempt
                    ON voice_sessions(attempt_id)
                    WHERE status IN ('issued', 'connected');
                """
            )
            # Existing local databases predate the onboarding gate. SQLite
            # cannot add the column in CREATE TABLE IF NOT EXISTS, so make the
            # migration safe to run on every development startup.
            columns = {row[1] for row in connection.execute("PRAGMA table_info(voice_sessions)")}
            if "case_started" not in columns:
                connection.execute(
                    "ALTER TABLE voice_sessions ADD COLUMN case_started INTEGER NOT NULL DEFAULT 0"
                )

    def save(self, session: InterviewSession, *, user_id: str | None = None) -> None:
        payload = json.dumps(
            {
                "schema_version": self.SCHEMA_VERSION,
                "mode": session.mode,
                "stage": session.stage,
                "disclosed_ids": sorted(session.disclosed_ids),
                "messages": session.messages,
                "candidate_turns": session.candidate_turns,
                "substantive_turns": session.substantive_turns,
                "case_started": session.case_started,
                "ready_to_end": session.ready_to_end,
                "ended": session.ended,
                "disposition": session.disposition,
                "turn_results": session.turn_results,
                "release_credits": session.release_credits,
                "consecutive_precise_misses": session.consecutive_precise_misses,
                "turns_since_release": session.turns_since_release,
            }
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO attempts (id, case_id, case_version, user_id, session_json, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    session_json = excluded.session_json,
                    user_id = COALESCE(excluded.user_id, attempts.user_id),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session.id, session.case.id, session.case.version, user_id, payload),
            )

    def backfill_attempt_users(self) -> None:
        """Migrate legacy ownership links into the primary practice record."""
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    UPDATE attempts
                    SET user_id = (
                        SELECT user_id FROM attempt_owners owners
                        WHERE owners.attempt_id = attempts.id
                    )
                    WHERE user_id IS NULL
                      AND EXISTS (
                          SELECT 1 FROM attempt_owners owners
                          WHERE owners.attempt_id = attempts.id
                      )
                    """
                )
            except sqlite3.OperationalError:
                # AccountStore may not have initialized its compatibility
                # ownership table yet during isolated store tests.
                return

    def list_user_practice(self, user_id: str, *, limit: int = 100) -> list[dict[str, object]]:
        """Return one durable, user-scoped row per practiced case attempt.

        ``attempts`` is the canonical transcript/state record. Evaluations are
        versioned child rows, so this query selects the latest feedback without
        duplicating transcript or performance data in a second store.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT a.id, a.case_id, a.session_json, a.created_at, a.updated_at,
                       e.evaluator_version, e.report_json, e.created_at
                FROM attempts a
                LEFT JOIN evaluations e ON e.rowid = (
                    SELECT latest.rowid
                    FROM evaluations latest
                    WHERE latest.attempt_id = a.id
                    ORDER BY latest.created_at DESC, latest.rowid DESC
                    LIMIT 1
                )
                WHERE a.user_id = ?
                ORDER BY a.updated_at DESC, a.created_at DESC, a.id DESC
                LIMIT ?
                """,
                (user_id, max(1, min(limit, 250))),
            ).fetchall()
        records: list[dict[str, object]] = []
        records.extend(self._practice_record_from_row(row) for row in rows)
        return records

    # -- durable per-candidate case status --------------------------------

    def record_case_started(self, user_id: str, case_id: str, attempt_id: str) -> None:
        """Record a fresh attempt without erasing a completed-case history."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_case_progress
                    (user_id, case_id, status, attempts_count, latest_attempt_id, updated_at)
                VALUES (?, ?, 'in_progress', 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, case_id) DO UPDATE SET
                    status = CASE WHEN user_case_progress.status = 'solved'
                                  THEN 'solved' ELSE 'in_progress' END,
                    attempts_count = user_case_progress.attempts_count + 1,
                    latest_attempt_id = excluded.latest_attempt_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, case_id, attempt_id),
            )

    def mark_case_solved(self, user_id: str, case_id: str, attempt_id: str, *, score: float | None) -> None:
        """Mark an ended attempt as solved while preserving the best recorded score."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_case_progress
                    (user_id, case_id, status, attempts_count, latest_attempt_id, last_completed_at, best_score, updated_at)
                VALUES (?, ?, 'solved', 1, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, case_id) DO UPDATE SET
                    status = 'solved',
                    latest_attempt_id = excluded.latest_attempt_id,
                    last_completed_at = CURRENT_TIMESTAMP,
                    best_score = CASE
                        WHEN excluded.best_score IS NULL THEN user_case_progress.best_score
                        WHEN user_case_progress.best_score IS NULL THEN excluded.best_score
                        WHEN excluded.best_score > user_case_progress.best_score THEN excluded.best_score
                        ELSE user_case_progress.best_score
                    END,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, case_id, attempt_id, score),
            )

    def mark_case_abandoned(self, user_id: str, case_id: str, attempt_id: str) -> None:
        """Clear the temporary open-attempt marker while retaining its transcript."""
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE user_case_progress
                SET status = 'not_started', latest_attempt_id = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND case_id = ? AND latest_attempt_id = ?
                """,
                (user_id, case_id, attempt_id),
            )

    def reset_case_progress(self, user_id: str, case_id: str) -> bool:
        """Reset the library status only; historic transcripts and feedback remain intact."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE user_case_progress
                SET status = 'not_started', latest_attempt_id = NULL,
                    last_completed_at = NULL, reset_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND case_id = ?
                """,
                (user_id, case_id),
            )
        return cursor.rowcount == 1

    def list_user_case_progress(self, user_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT case_id, status, attempts_count, latest_attempt_id,
                       last_completed_at, best_score, reset_at, updated_at
                FROM user_case_progress WHERE user_id = ?
                ORDER BY updated_at DESC, case_id ASC
                """,
                (user_id,),
            ).fetchall()
        return [
            {
                "case_id": row[0], "status": row[1], "attempts_count": int(row[2]),
                "latest_attempt_id": row[3], "last_completed_at": row[4],
                "best_score": row[5], "reset_at": row[6], "updated_at": row[7],
            }
            for row in rows
        ]

    def get_user_case_progress(self, user_id: str, case_id: str) -> dict[str, object] | None:
        return next((item for item in self.list_user_case_progress(user_id) if item["case_id"] == case_id), None)

    def get_user_practice(self, user_id: str, attempt_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT a.id, a.case_id, a.session_json, a.created_at, a.updated_at,
                       e.evaluator_version, e.report_json, e.created_at
                FROM attempts a
                LEFT JOIN evaluations e ON e.rowid = (
                    SELECT latest.rowid
                    FROM evaluations latest
                    WHERE latest.attempt_id = a.id
                    ORDER BY latest.created_at DESC, latest.rowid DESC
                    LIMIT 1
                )
                WHERE a.user_id = ? AND a.id = ?
                """,
                (user_id, attempt_id),
            ).fetchone()
        return self._practice_record_from_row(row) if row else None

    @staticmethod
    def _practice_record_from_row(row: tuple[object, ...]) -> dict[str, object]:
        attempt_id, case_id, session_json, created_at, updated_at, version, report_json, feedback_created_at = row
        session = json.loads(str(session_json))
        report = json.loads(report_json) if isinstance(report_json, str) else None
        return {
            "id": attempt_id,
            "case_id": case_id,
            "mode": session.get("mode"),
            "stage": session.get("stage"),
            "candidate_turns": int(session.get("candidate_turns", 0)),
            "substantive_turns": int(session.get("substantive_turns", 0)),
            "ended": bool(session.get("ended", False)),
            "disposition": session.get("disposition") if session.get("disposition") in {"abandoned", "scored"} else None,
            "messages": list(session.get("messages", [])),
            "facts_released": len(session.get("disclosed_ids", [])),
            "started_at": created_at,
            "updated_at": updated_at,
            "feedback": (
                {
                    "evaluator_version": version,
                    "report": report,
                    "created_at": feedback_created_at,
                }
                if report is not None
                else None
            ),
        }

    def get(self, attempt_id: str, catalogue: CaseCatalogue) -> InterviewSession | None:
        """Restore an attempt against the case version recorded at creation time."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT case_id, session_json, case_version FROM attempts WHERE id = ?",
                (attempt_id,),
            ).fetchone()
        if row is None:
            return None

        case_id, session_json, case_version = row
        try:
            case = catalogue.get(case_id, case_version)
        except ValueError:
            # A retired or removed case should not be silently substituted, and
            # neither should a superseded version: resuming a candidate into an
            # edited world would score them on evidence they were never shown.
            return None
        payload = json.loads(session_json)
        # Attempts written before the schema marker was introduced have the
        # same core transcript fields as v2. Treat them as a supported legacy
        # shape so an old completed case can still receive its first debrief.
        schema_version = payload.get("schema_version", 1)
        if schema_version not in {1, 2, 3, self.SCHEMA_VERSION}:
            return None
        messages = payload.get("messages", [])
        candidate_turns = payload.get("candidate_turns")
        if not isinstance(candidate_turns, int):
            candidate_turns = sum(
                1
                for message in messages
                if isinstance(message, dict) and message.get("role") == "candidate"
            )
        substantive_turns = payload.get("substantive_turns")
        if not isinstance(substantive_turns, int):
            substantive_turns = max(candidate_turns - 1, 0) if payload.get("case_started") else 0
        disposition = payload.get("disposition")
        if disposition not in {"abandoned", "scored"}:
            disposition = None
        return InterviewSession(
            id=attempt_id,
            case=case,
            mode=payload["mode"],
            stage=payload["stage"],
            disclosed_ids=set(payload["disclosed_ids"]),
            messages=messages,
            candidate_turns=candidate_turns,
            substantive_turns=substantive_turns,
            case_started=bool(
                payload.get(
                    "case_started",
                    any(
                        message.get("role") == "interviewer" and message.get("content") == case.opening
                        for message in payload.get("messages", [])
                        if isinstance(message, dict)
                    ),
                )
            ),
            ready_to_end=bool(payload.get("ready_to_end", False)),
            ended=payload["ended"],
            disposition=disposition,
            turn_results=payload.get("turn_results", {}),
            # Attempts written before personas have no budget recorded. Zero is the
            # correct default: the next turn accrues the persona's rate before any
            # disclosure decision, so a resumed attempt is neither given a free
            # fact nor stalled.
            release_credits=float(payload.get("release_credits", 0.0)),
            consecutive_precise_misses=int(payload.get("consecutive_precise_misses", 0)),
            turns_since_release=int(payload.get("turns_since_release", 0)),
        )

    # -- voice transport metadata -----------------------------------------

    def create_voice_session(self, session: VoiceSession) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO voice_sessions
                        (id, attempt_id, provider, agent_id, provider_conversation_id, status, case_started)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.id,
                        session.attempt_id,
                        session.provider,
                        session.agent_id,
                        session.provider_conversation_id,
                        session.status,
                        int(session.case_started),
                    ),
                )
        except sqlite3.IntegrityError as error:
            if "voice_sessions_one_live_attempt" in str(error) or "voice_sessions.attempt_id" in str(error):
                raise ActiveVoiceSessionExists("A live voice session already exists") from error
            raise

    def get_voice_session(self, voice_session_id: str) -> VoiceSession | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, attempt_id, provider, agent_id, provider_conversation_id,
                       status, case_started, created_at, updated_at
                FROM voice_sessions WHERE id = ?
                """,
                (voice_session_id,),
            ).fetchone()
        return self._voice_session_from_row(row)

    def get_voice_session_by_provider_conversation(self, conversation_id: str) -> VoiceSession | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, attempt_id, provider, agent_id, provider_conversation_id,
                       status, case_started, created_at, updated_at
                FROM voice_sessions WHERE provider_conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()
        return self._voice_session_from_row(row)

    @staticmethod
    def _voice_session_from_row(row: tuple[object, ...] | None) -> VoiceSession | None:
        if row is None:
            return None
        return VoiceSession(*row[:6], case_started=bool(row[6]), created_at=row[7], updated_at=row[8])

    def mark_voice_case_started(self, voice_session_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE voice_sessions
                SET case_started = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (voice_session_id,),
            )
        return cursor.rowcount == 1

    def set_voice_session_status(self, voice_session_id: str, status: str) -> bool:
        if status not in {"issued", "connected", "disconnected", "ended", "failed", "reconciled"}:
            raise ValueError("Unsupported voice session status")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE voice_sessions
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, voice_session_id),
            )
        return cursor.rowcount == 1

    def reconcile_voice_session(self, voice_session_id: str) -> bool:
        """Record a verified post-call receipt without storing raw provider content."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE voice_sessions
                SET status = 'reconciled', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND status IN ('ended', 'disconnected', 'reconciled')
                """,
                (voice_session_id,),
            )
        return cursor.rowcount == 1

    def _connect(self) -> AbstractContextManager[sqlite3.Connection]:
        return db.transaction(self._database_path)


class EvaluationStore:
    """Versioned evaluation reports for ended attempts.

    Rows are keyed by attempt and evaluator version: re-running the evaluator
    under a new rubric, prompt, or model version adds a row instead of
    overwriting history, so scores stay comparable across versions.
    Evaluations are explicitly linked to both attempt_id and user_id.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluations (
                    attempt_id TEXT NOT NULL,
                    evaluator_version TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    PRIMARY KEY (attempt_id, evaluator_version)
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(evaluations)")}
            if "user_id" not in columns:
                connection.execute("ALTER TABLE evaluations ADD COLUMN user_id TEXT")
            connection.execute("CREATE INDEX IF NOT EXISTS evaluations_user ON evaluations(user_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS evaluations_attempt ON evaluations(attempt_id)")
            try:
                connection.execute(
                    """
                    UPDATE evaluations
                    SET user_id = (
                        SELECT user_id FROM attempts WHERE attempts.id = evaluations.attempt_id
                    )
                    WHERE user_id IS NULL
                      AND EXISTS (
                          SELECT 1 FROM attempts
                          WHERE attempts.id = evaluations.attempt_id
                            AND attempts.user_id IS NOT NULL
                      )
                    """
                )
            except sqlite3.OperationalError:
                pass

    def save(
        self,
        report_json: str,
        attempt_id: str,
        evaluator_version: str,
        *,
        user_id: str | None = None,
    ) -> None:
        with self._connect() as connection:
            if user_id is None:
                row = connection.execute(
                    "SELECT user_id FROM attempts WHERE id = ?", (attempt_id,)
                ).fetchone()
                if row and row[0]:
                    user_id = str(row[0])
            connection.execute(
                """
                INSERT INTO evaluations (attempt_id, evaluator_version, report_json, user_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(attempt_id, evaluator_version) DO UPDATE SET
                    report_json = excluded.report_json,
                    user_id = COALESCE(excluded.user_id, evaluations.user_id),
                    created_at = CURRENT_TIMESTAMP
                """,
                (attempt_id, evaluator_version, report_json, user_id),
            )

    def latest(self, attempt_id: str) -> dict[str, Any] | None:
        rows = self.history(attempt_id)
        return rows[0] if rows else None

    def get(self, attempt_id: str, evaluator_version: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT evaluator_version, report_json, created_at, user_id
                FROM evaluations WHERE attempt_id = ? AND evaluator_version = ?
                """,
                (attempt_id, evaluator_version),
            ).fetchone()
        if not row:
            return None
        return {
            "evaluator_version": row[0],
            "report": json.loads(row[1]),
            "created_at": row[2],
            "user_id": row[3],
        }

    def history(self, attempt_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT evaluator_version, report_json, created_at, user_id
                FROM evaluations WHERE attempt_id = ?
                ORDER BY created_at DESC, rowid DESC
                """,
                (attempt_id,),
            ).fetchall()
        return [
            {
                "evaluator_version": version,
                "report": json.loads(payload),
                "created_at": created,
                "user_id": uid,
            }
            for version, payload, created, uid in rows
        ]

    def list_by_user(self, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Return all evaluated reports linked to a specific user_id."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT attempt_id, evaluator_version, report_json, created_at, user_id
                FROM evaluations WHERE user_id = ?
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (user_id, max(1, min(limit, 250))),
            ).fetchall()
        return [
            {
                "attempt_id": attempt_id,
                "evaluator_version": version,
                "report": json.loads(payload),
                "created_at": created,
                "user_id": uid,
            }
            for attempt_id, version, payload, created, uid in rows
        ]

    def _connect(self) -> AbstractContextManager[sqlite3.Connection]:
        return db.transaction(self._database_path)


class CaseStore:
    """Durable storage for contributed cases and per-case aggregate counts.

    Authored packages deliberately stay on the filesystem and in git, where the
    rights discipline in ``corpus/README.md`` can review them. Only contributed
    cases live here, because they are user data, they arrive after start-up, and
    they must survive a deploy on the mounted volume rather than in the image.

    Versions are kept rather than overwritten. An admin editing a published case
    creates a new row, and the old one stays resolvable so an attempt pinned to it
    can still be resumed and scored against the world it actually saw.
    """

    SCHEMA_VERSION = 1

    STATUSES = ("draft", "submitted", "validated", "published", "needs_changes", "unpublished")

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id        TEXT NOT NULL,
                    version        INTEGER NOT NULL,
                    source         TEXT NOT NULL CHECK(source IN ('authored', 'contributed')),
                    status         TEXT NOT NULL CHECK(status IN
                                     ('draft','submitted','validated','published','needs_changes','unpublished')),
                    package_json   TEXT NOT NULL,
                    contributor_id TEXT,
                    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (case_id, version)
                );
                CREATE INDEX IF NOT EXISTS cases_published
                    ON cases(status, case_id, version DESC);
                CREATE INDEX IF NOT EXISTS cases_contributor
                    ON cases(contributor_id, updated_at DESC);

                CREATE TABLE IF NOT EXISTS case_stats (
                    case_id         TEXT PRIMARY KEY,
                    times_attempted INTEGER NOT NULL DEFAULT 0,
                    times_completed INTEGER NOT NULL DEFAULT 0,
                    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    # -- contributed case packages ---------------------------------------

    def next_version(self, case_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT MAX(version) FROM cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        return int((row[0] or 0)) + 1

    def save_package(
        self,
        case_id: str,
        package: dict[str, Any],
        *,
        status: str,
        contributor_id: str | None,
        version: int | None = None,
        source: str = "contributed",
    ) -> int:
        """Write one case version and return the version number used."""
        if status not in self.STATUSES:
            raise ValueError(f"Unknown case status: {status}")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            resolved = version if version is not None else int(connection.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM cases WHERE case_id = ?", (case_id,)
            ).fetchone()[0])
            connection.execute(
                """
                INSERT INTO cases (case_id, version, source, status, package_json, contributor_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id, version) DO UPDATE SET
                    status = excluded.status,
                    package_json = excluded.package_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (case_id, resolved, source, status, json.dumps(package), contributor_id),
            )
        return resolved

    def set_status(self, case_id: str, version: int, status: str) -> bool:
        if status not in self.STATUSES:
            raise ValueError(f"Unknown case status: {status}")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE cases SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE case_id = ? AND version = ?",
                (status, case_id, version),
            )
        return cursor.rowcount == 1

    def get_package(self, case_id: str, version: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT package_json FROM cases WHERE case_id = ? AND version = ?",
                (case_id, version),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def published_packages(self) -> list[dict[str, Any]]:
        """Every case the library should currently offer, latest version each.

        The window function picks one row per case rather than filtering in
        Python, so a case with several published versions cannot register twice
        and leave the registry's two indexes disagreeing.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT case_id, version, package_json, contributor_id
                FROM (
                    SELECT case_id, version, package_json, contributor_id,
                           ROW_NUMBER() OVER (PARTITION BY case_id ORDER BY version DESC) AS rank
                    FROM cases
                    WHERE status = 'published'
                )
                WHERE rank = 1
                ORDER BY case_id
                """
            ).fetchall()
        return [
            {
                "case_id": case_id,
                "version": version,
                "package": json.loads(package_json),
                "contributor_id": contributor_id,
            }
            for case_id, version, package_json, contributor_id in rows
        ]

    def list_all_versions(self) -> list[dict[str, Any]]:
        """Every stored case version and its status, newest first.

        The admin console needs the full history of a case, not only what is
        currently in the review queue, to see what was published and withdrawn.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT case_id, version, status, contributor_id, updated_at
                FROM cases
                ORDER BY updated_at DESC, case_id, version DESC
                """
            ).fetchall()
        return [
            {
                "case_id": case_id,
                "version": version,
                "status": status,
                "contributor_id": contributor_id,
                "updated_at": updated_at,
            }
            for case_id, version, status, contributor_id, updated_at in rows
        ]

    def list_for_review(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """The admin queue: everything awaiting a decision, oldest first."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT case_id, version, status, contributor_id, updated_at
                FROM cases
                WHERE status IN ('submitted', 'validated')
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (max(1, min(limit, 250)),),
            ).fetchall()
        return [
            {
                "case_id": case_id,
                "version": version,
                "status": status,
                "contributor_id": contributor_id,
                "updated_at": updated_at,
            }
            for case_id, version, status, contributor_id, updated_at in rows
        ]

    # -- aggregate counts -------------------------------------------------

    def record_attempt_started(self, case_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO case_stats (case_id, times_attempted)
                VALUES (?, 1)
                ON CONFLICT(case_id) DO UPDATE SET
                    times_attempted = case_stats.times_attempted + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (case_id,),
            )

    def record_attempt_completed(self, case_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO case_stats (case_id, times_attempted, times_completed)
                VALUES (?, 0, 1)
                ON CONFLICT(case_id) DO UPDATE SET
                    times_completed = case_stats.times_completed + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (case_id,),
            )

    def stats(self) -> dict[str, dict[str, int]]:
        """Attempt counts for every case, keyed by case ID.

        Read on every library page load, so it is one query returning the whole
        map rather than a lookup per card.
        """
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT case_id, times_attempted, times_completed FROM case_stats"
            ).fetchall()
        return {
            case_id: {"times_attempted": attempted, "times_completed": completed}
            for case_id, attempted, completed in rows
        }

    def _connect(self) -> AbstractContextManager[sqlite3.Connection]:
        return db.transaction(self._database_path)


class ContributionStore:
    """One live extraction conversation per contributor, and its drafts.

    Kept separate from ``attempts`` because a contribution is not an interview:
    it has no case, no disclosure ledger and no score, and folding it into the
    attempt table would mean every attempt query had to start excluding rows.
    """

    STATUSES = ("in_progress", "abandoned", "submitted")

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS contribution_sessions (
                    id          TEXT PRIMARY KEY,
                    user_id     TEXT NOT NULL,
                    status      TEXT NOT NULL CHECK(status IN ('in_progress', 'abandoned', 'submitted')),
                    state_json  TEXT NOT NULL,
                    case_id     TEXT,
                    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS contribution_user
                    ON contribution_sessions(user_id, updated_at DESC);
                -- One live conversation per contributor. A partial index rather
                -- than an application check, so two racing requests cannot both
                -- pass the check and create a second session.
                CREATE UNIQUE INDEX IF NOT EXISTS contribution_one_live_per_user
                    ON contribution_sessions(user_id)
                    WHERE status = 'in_progress';
                """
            )

    def create(self, session_id: str, user_id: str, state: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO contribution_sessions (id, user_id, status, state_json)
                VALUES (?, ?, 'in_progress', ?)
                """,
                (session_id, user_id, json.dumps(state)),
            )

    def save_state(self, session_id: str, state: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE contribution_sessions
                SET state_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (json.dumps(state), session_id),
            )

    def restart(
        self,
        session_id: str,
        user_id: str,
        new_session_id: str,
        state: dict[str, Any],
    ) -> None:
        """Abandon one live draft and create its replacement atomically."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE contribution_sessions
                SET status = 'abandoned', updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND status = 'in_progress'
                """,
                (session_id, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Contribution is not available to restart")
            connection.execute(
                """
                INSERT INTO contribution_sessions (id, user_id, status, state_json)
                VALUES (?, ?, 'in_progress', ?)
                """,
                (new_session_id, user_id, json.dumps(state)),
            )

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, user_id, status, state_json, case_id FROM contribution_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "user_id": row[1],
            "status": row[2],
            "state": json.loads(row[3]),
            "case_id": row[4],
        }

    def live_for_user(self, user_id: str) -> dict[str, Any] | None:
        """The contributor's open conversation, so a reload resumes it."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id FROM contribution_sessions
                WHERE user_id = ? AND status = 'in_progress'
                """,
                (user_id,),
            ).fetchone()
        return self.get(row[0]) if row else None

    def finish(self, session_id: str, *, status: str, case_id: str | None = None) -> None:
        if status not in self.STATUSES:
            raise ValueError(f"Unknown contribution status: {status}")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE contribution_sessions
                SET status = ?, case_id = COALESCE(?, case_id), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, case_id, session_id),
            )

    def _connect(self) -> AbstractContextManager[sqlite3.Connection]:
        return db.transaction(self._database_path)
