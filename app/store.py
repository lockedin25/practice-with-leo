"""Small durable store for local and single-instance deployments.

Keeping attempts in SQLite means Uvicorn reloads do not discard an interview
between the browser creating an attempt and sending its next turn.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.case_runtime import CaseCatalogue, CaseWorld, InterviewSession


class SessionStore:
    SCHEMA_VERSION = 2

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    session_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save(self, session: InterviewSession) -> None:
        payload = json.dumps(
            {
                "schema_version": self.SCHEMA_VERSION,
                "mode": session.mode,
                "stage": session.stage,
                "disclosed_ids": sorted(session.disclosed_ids),
                "messages": session.messages,
                "candidate_turns": session.candidate_turns,
                "ended": session.ended,
                "turn_results": session.turn_results,
            }
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO attempts (id, case_id, session_json)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    session_json = excluded.session_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session.id, session.case.id, payload),
            )

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
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            return None
        return InterviewSession(
            id=attempt_id,
            case=case,
            mode=payload["mode"],
            stage=payload["stage"],
            disclosed_ids=set(payload["disclosed_ids"]),
            messages=payload["messages"],
            candidate_turns=payload["candidate_turns"],
            ended=payload["ended"],
            turn_results=payload.get("turn_results", {}),
        )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path, timeout=5)
