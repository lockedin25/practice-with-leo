"""Small durable store for local and single-instance deployments.

Keeping attempts in SQLite means Uvicorn reloads do not discard an interview
between the browser creating an attempt and sending its next turn.
"""

from __future__ import annotations

from app import db

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

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
    SCHEMA_VERSION = 3

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
                "case_started": session.case_started,
                "ready_to_end": session.ready_to_end,
                "ended": session.ended,
                "turn_results": session.turn_results,
            }
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO attempts (id, case_id, user_id, session_json, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    session_json = excluded.session_json,
                    user_id = COALESCE(excluded.user_id, attempts.user_id),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session.id, session.case.id, user_id, payload),
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
            "ended": bool(session.get("ended", False)),
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
                "SELECT case_id, session_json FROM attempts WHERE id = ?",
                (attempt_id,),
            ).fetchone()
        if row is None:
            return None

        case_id, session_json = row
        try:
            case = catalogue.get(case_id)
        except ValueError:
            # A retired or removed case should not be silently substituted.
            return None
        payload = json.loads(session_json)
        # Attempts written before the schema marker was introduced have the
        # same core transcript fields as v2. Treat them as a supported legacy
        # shape so an old completed case can still receive its first debrief.
        schema_version = payload.get("schema_version", 1)
        if schema_version not in {1, 2, self.SCHEMA_VERSION}:
            return None
        messages = payload.get("messages", [])
        candidate_turns = payload.get("candidate_turns")
        if not isinstance(candidate_turns, int):
            candidate_turns = sum(
                1
                for message in messages
                if isinstance(message, dict) and message.get("role") == "candidate"
            )
        return InterviewSession(
            id=attempt_id,
            case=case,
            mode=payload["mode"],
            stage=payload["stage"],
            disclosed_ids=set(payload["disclosed_ids"]),
            messages=messages,
            candidate_turns=candidate_turns,
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
            turn_results=payload.get("turn_results", {}),
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

    def _connect(self) -> sqlite3.Connection:
        return db.connect(self._database_path)


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

    def _connect(self) -> sqlite3.Connection:
        return db.connect(self._database_path)
