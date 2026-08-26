"""Administrator views: every attempt, every transcript, and the metrics over them.

Reads the runtime's attempt table and joins it to the account and evaluation tables.
Nothing here writes to interview state, and the transcript view shows only what
the runtime actually released to the candidate, so the answer key stays private
even from an administrator.
"""

from __future__ import annotations

from app import db

import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.accounts import require_admin

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])

ROW_LIMIT = 2_000
TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f")


# --- Reading ---------------------------------------------------------------


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    for pattern in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _minutes_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None or end < start:
        return None
    return round((end - start).total_seconds() / 60, 1)


def _attempt_rows(database_path: Path) -> list[dict[str, Any]]:
    """Every attempt with its owner and evaluation, tolerant of runtime schema drift."""
    query = """
        SELECT a.id, a.case_id, a.session_json,
               a.created_at AS a_created_at,
               a.updated_at AS a_updated_at,
               COALESCE(a.user_id, o.user_id) AS effective_user_id,
               COALESCE(o.created_at, a.created_at, a.updated_at) AS effective_created_at,
               u.email, u.name, u.picture,
               e.evaluator_version, e.report_json, e.created_at AS evaluation_created_at
        FROM attempts a
        LEFT JOIN attempt_owners o ON o.attempt_id = a.id
        LEFT JOIN users u ON u.id = COALESCE(a.user_id, o.user_id)
        LEFT JOIN evaluations e ON e.rowid = (
            SELECT latest.rowid
            FROM evaluations latest
            WHERE latest.attempt_id = a.id
            ORDER BY latest.created_at DESC, latest.rowid DESC
            LIMIT 1
        )
        ORDER BY COALESCE(o.created_at, a.created_at, a.updated_at) DESC
        LIMIT ?
    """
    try:
        with db.connect(database_path) as connection:
            raw = connection.execute(query, (ROW_LIMIT,)).fetchall()
    except sqlite3.OperationalError:
        # Fallback if evaluations or user columns are structured differently
        fallback_query = """
            SELECT a.id, a.case_id, a.session_json, a.updated_at,
                   o.user_id, o.created_at, u.email, u.name, u.picture
            FROM attempts a
            LEFT JOIN attempt_owners o ON o.attempt_id = a.id
            LEFT JOIN users u ON u.id = o.user_id
            ORDER BY COALESCE(o.created_at, a.updated_at) DESC
            LIMIT ?
        """
        try:
            with db.connect(database_path) as connection:
                legacy_raw = connection.execute(fallback_query, (ROW_LIMIT,)).fetchall()
                raw = [
                    (r[0], r[1], r[2], r[5], r[3], r[4], r[5], r[6], r[7], r[8], None, None, None)
                    for r in legacy_raw
                ]
        except sqlite3.OperationalError:
            return []

    rows: list[dict[str, Any]] = []
    for (
        attempt_id,
        case_id,
        session_json,
        a_created_at,
        a_updated_at,
        user_id,
        created_at,
        email,
        name,
        picture,
        eval_version,
        report_json,
        eval_created_at,
    ) in raw:
        try:
            session = json.loads(session_json)
        except (ValueError, TypeError):
            session = {}

        try:
            report = json.loads(report_json) if report_json else None
        except (ValueError, TypeError):
            report = None

        messages = session.get("messages") or []
        started = _parse_timestamp(created_at or a_created_at)
        updated = _parse_timestamp(a_updated_at)

        feedback_score = None
        if report and isinstance(report.get("dimensions"), list):
            dim_scores = [
                float(d["score"])
                for d in report["dimensions"]
                if isinstance(d, dict) and isinstance(d.get("score"), (int, float))
            ]
            if dim_scores:
                feedback_score = round(sum(dim_scores) / len(dim_scores), 1)

        rows.append(
            {
                "id": attempt_id,
                "case_id": case_id,
                "mode": session.get("mode", "realistic"),
                "stage": session.get("stage", "unknown"),
                "ended": bool(session.get("ended")),
                "candidate_turns": int(session.get("candidate_turns") or 0),
                "messages": len(messages),
                "facts_released": len(session.get("disclosed_ids") or []),
                "started_at": created_at or a_created_at or a_updated_at,
                "updated_at": a_updated_at,
                "duration_minutes": _minutes_between(started, updated),
                "feedback_score": feedback_score,
                "evaluator_version": eval_version,
                "user": (
                    {"id": user_id, "email": email, "name": name, "picture": picture}
                    if user_id and email
                    else None
                ),
                "_messages": messages,
                "_disclosed": list(session.get("disclosed_ids") or []),
                "_report": report,
            }
        )
    return rows


def _user_rows(database_path: Path) -> list[dict[str, Any]]:
    query = """
        SELECT id, email, name, picture, created_at, last_login_at
        FROM users
        ORDER BY last_login_at DESC
        LIMIT ?
    """
    try:
        with db.connect(database_path) as connection:
            raw = connection.execute(query, (ROW_LIMIT,)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [
        {
            "id": row[0],
            "email": row[1],
            "name": row[2],
            "picture": row[3],
            "created_at": row[4],
            "last_login_at": row[5],
        }
        for row in raw
    ]


def _database_path(request: Request) -> Path:
    return request.app.state.database_path


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


# --- Endpoints -------------------------------------------------------------


@router.get("/overview")
def overview(request: Request) -> dict[str, Any]:
    database_path = _database_path(request)
    attempts = _attempt_rows(database_path)
    users = _user_rows(database_path)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    ended = [row for row in attempts if row["ended"]]
    durations = [row["duration_minutes"] for row in attempts if row["duration_minutes"] is not None]
    recent_logins = [
        user for user in users if (_parse_timestamp(user["last_login_at"]) or now) >= week_ago
    ]
    recent_attempts = [
        row for row in attempts if (_parse_timestamp(row["started_at"]) or datetime.min.replace(tzinfo=timezone.utc)) >= week_ago
    ]

    return {
        "totals": {
            "users": len(users),
            "users_active_7d": len(recent_logins),
            "attempts": len(attempts),
            "attempts_7d": len(recent_attempts),
            "attempts_completed": len(ended),
            "attempts_in_progress": len(attempts) - len(ended),
            "completion_rate": _ratio(len(ended), len(attempts)),
            "candidate_turns": sum(row["candidate_turns"] for row in attempts),
            "facts_released": sum(row["facts_released"] for row in attempts),
            "avg_turns_per_attempt": _mean([row["candidate_turns"] for row in attempts]),
            "avg_facts_per_attempt": _mean([row["facts_released"] for row in attempts]),
            "avg_minutes_per_attempt": _mean(durations),
            "unattributed_attempts": sum(1 for row in attempts if row["user"] is None),
        },
        "stage_reached": _distribution(row["stage"] for row in attempts),
        "mode_mix": _distribution(row["mode"] for row in attempts),
        "case_mix": _distribution(row["case_id"] for row in attempts),
        "daily": _daily_activity(attempts, now, days=14),
        "truncated": len(attempts) >= ROW_LIMIT,
    }


@router.get("/users")
def list_users(request: Request) -> dict[str, Any]:
    database_path = _database_path(request)
    attempts = _attempt_rows(database_path)
    by_user: dict[str, list[dict[str, Any]]] = {}
    for row in attempts:
        if row["user"]:
            by_user.setdefault(row["user"]["id"], []).append(row)

    people = []
    for user in _user_rows(database_path):
        owned = by_user.get(user["id"], [])
        completed = [row for row in owned if row["ended"]]
        people.append(
            {
                **user,
                "is_admin": _is_admin(user["email"]),
                "attempts": len(owned),
                "attempts_completed": len(completed),
                "completion_rate": _ratio(len(completed), len(owned)),
                "avg_turns": _mean([row["candidate_turns"] for row in owned]),
                "facts_released": sum(row["facts_released"] for row in owned),
                "last_attempt_at": max((row["started_at"] or "" for row in owned), default=None),
            }
        )
    people.sort(key=lambda person: (person["attempts"], person["last_login_at"] or ""), reverse=True)
    return {"users": people}


@router.get("/attempts")
def list_attempts(request: Request, user_id: str | None = None, limit: int = 200) -> dict[str, Any]:
    rows = _attempt_rows(_database_path(request))
    if user_id:
        rows = [row for row in rows if (row["user"] or {}).get("id") == user_id]
    limit = max(1, min(limit, ROW_LIMIT))
    return {"attempts": [_public(row) for row in rows[:limit]], "total": len(rows)}


@router.get("/attempts/{attempt_id}")
def read_transcript(request: Request, attempt_id: str) -> dict[str, Any]:
    rows = _attempt_rows(_database_path(request))
    row = next((item for item in rows if item["id"] == attempt_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    catalogue = request.app.state.catalogue
    try:
        contents = {fact.id: fact.content for fact in catalogue.get(row["case_id"]).facts}
    except ValueError:
        contents = {}
    facts = [
        {"id": fact_id, "content": contents.get(fact_id, "(no longer in the case package)")}
        for fact_id in row["_disclosed"]
    ]

    scorecard = None
    session = request.app.state.store.get(attempt_id, catalogue)
    if session is not None:
        try:
            scorecard = session.scorecard()
        except Exception:  # a mid-flight runtime change must not break the transcript
            scorecard = None

    evaluation = None
    if row.get("_report"):
        evaluation = {
            "evaluator_version": row.get("evaluator_version"),
            "report": row.get("_report"),
        }

    return {
        "attempt": _public(row),
        "messages": row["_messages"],
        "facts": facts,
        "scorecard": scorecard,
        "evaluation": evaluation,
    }


@router.post("/attempts/{attempt_id}/evaluate")
def evaluate_attempt(request: Request, attempt_id: str) -> dict[str, Any]:
    """Re-run the evaluator under the current rubric, prompt, and model versions.

    Reports are keyed by evaluator version rather than overwritten, so this
    builds history instead of rewriting it.
    """
    catalogue = request.app.state.catalogue
    session = request.app.state.store.get(attempt_id, catalogue)
    if session is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if not session.ended:
        raise HTTPException(status_code=409, detail="The attempt has not ended yet")
    evaluator = request.app.state.evaluator
    if evaluator is None:
        raise HTTPException(status_code=503, detail="The evaluator is not configured")

    from app.evaluator import EvaluatorUnavailable

    try:
        report = evaluator.evaluate(session)
    except EvaluatorUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    payload = report.model_dump()
    payload["overall"] = evaluator.overall(report)
    request.app.state.evaluations.save(report.model_dump_json(), attempt_id, report.evaluator_version)
    return {
        "evaluation": payload,
        "versions": request.app.state.evaluations.history(attempt_id),
    }


# --- Aggregation helpers ---------------------------------------------------


def _is_admin(email: str) -> bool:
    from app.accounts import is_admin_email

    return is_admin_email(email)


def _ratio(part: int, whole: int) -> float:
    return round(part / whole, 3) if whole else 0.0


def _mean(values: list[float]) -> float:
    numbers = [value for value in values if value is not None]
    return round(sum(numbers) / len(numbers), 1) if numbers else 0.0


def _distribution(values: Any) -> list[dict[str, Any]]:
    counts = Counter(values)
    return [{"key": key, "count": count} for key, count in counts.most_common()]


def _daily_activity(attempts: list[dict[str, Any]], now: datetime, days: int) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in attempts:
        moment = _parse_timestamp(row["started_at"]) or _parse_timestamp(row["updated_at"])
        if moment:
            counts[moment.date().isoformat()] += 1
    span = [(now - timedelta(days=offset)).date().isoformat() for offset in reversed(range(days))]
    return [{"date": day, "count": counts.get(day, 0)} for day in span]
