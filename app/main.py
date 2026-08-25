from __future__ import annotations

import hmac
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.accounts import AccountStore, User, current_user, require_user
from app.admin import router as admin_router
from app.attempt_service import AttemptAlreadyEnded, AttemptTurnService, TurnSubmission
from app.auth import router as auth_router
from app.case_runtime import CaseCatalogue, InterviewSession
from app.evaluator import FallbackCaseEvaluator, EvaluatorUnavailable, create_evaluator, load_rubric
from app.interviewer import InterviewerUnavailable, create_interviewer
from app.store import ActiveVoiceSessionExists, EvaluationStore, SessionStore, VoiceSession
from app.voice import (
    ElevenLabsProvider,
    VoiceConfigurationError,
    VoiceProviderError,
    VoiceSettings,
    clean_spoken_text,
    latest_candidate_utterance,
    voice_session_id_from_request,
)
from app.voice_onboarding import VoiceOnboardingUnavailable, create_voice_onboarding
from app.voice_realtime import (
    SCRIBE_TOKEN,
    TTS_TOKEN,
    ElevenLabsRealtimeProvider,
    RealtimeVoiceSettings,
    case_keyterms,
    speech_to_text_url,
    text_to_speech_url,
)
from app.spoken_interviewer import (
    ControlBlockMissing,
    audit_spoken_turn_in_background,
    create_spoken_auditor,
    create_spoken_interviewer,
)


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"
TEMPLATES = Jinja2Templates(directory=str(ROOT / "app" / "templates"))
RESERVOIR_DIR = ROOT / "reservoir"
load_dotenv(ROOT / ".env")
DATABASE_PATH = ROOT / "data" / "casecall.db"
CATALOGUE = CaseCatalogue.from_reservoir(ROOT)
INTERVIEWER = create_interviewer()
STORE = SessionStore(DATABASE_PATH)
ACCOUNTS = AccountStore(DATABASE_PATH)
STORE.backfill_attempt_users()
ATTEMPT_TURNS = AttemptTurnService()
VOICE_PROVIDER = ElevenLabsProvider()
REALTIME_VOICE_PROVIDER = ElevenLabsRealtimeProvider()
# One fused streaming call per spoken turn, on the same OpenRouter key as
# typed chat. None when no key exists, in which case realtime voice reports
# itself unready and the candidate keeps typed chat.
SPOKEN_INTERVIEWER = create_spoken_interviewer()
# Runs after the words are spoken, never before. Reports a reply that
# under-delivered a fact the ledger has already marked released.
SPOKEN_AUDITOR = create_spoken_auditor()
# Built only when the candidate replies to Leo's welcome. Readiness is shared
# by typed chat and voice, and remains LLM-led rather than keyword-driven.
VOICE_ONBOARDING = None


def _create_evaluator_safely():
    """The evaluator enriches the debrief but must never block the product.

    A missing OpenRouter key disables evaluation and the attempt API falls
    back to the heuristic scorecard, mirroring how voice degrades to chat.
    """
    try:
        # CaseCatalogue accepts the project root and appends ``reservoir``
        # itself. The evaluator's content loaders, however, expect the
        # reservoir directory directly. Passing ROOT here made every live
        # evaluation fail before any LLM call because it could not find the
        # case package, while the end endpoint swallowed that error.
        return create_evaluator(RESERVOIR_DIR)
    except RuntimeError as error:
        logging.getLogger(__name__).warning("Evaluator disabled: %s", error)
        return None


EVALUATOR = _create_evaluator_safely()
EVALUATIONS = EvaluationStore(DATABASE_PATH)

app = FastAPI(title="Leo", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# The auth and admin routers read these off app state rather than importing this
# module, so account handling never reaches back into the interview API.
app.state.accounts = ACCOUNTS
app.state.store = STORE
app.state.catalogue = CATALOGUE
app.state.database_path = DATABASE_PATH
app.state.evaluator = EVALUATOR
app.state.evaluations = EVALUATIONS
app.include_router(auth_router)
app.include_router(admin_router)


class StartAttemptRequest(BaseModel):
    case_id: str = CATALOGUE.default_case.id
    mode: str = Field(default="realistic", pattern="^(coached|realistic|pressure)$")
    duration_minutes: int = Field(default=30, ge=1)


class CandidateTurnRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8_000)
    turn_id: str = Field(min_length=1, max_length=128)


class VoiceLifecycleRequest(BaseModel):
    """Present for an explicit, versionable lifecycle contract."""


class VoiceTranscriptRequest(BaseModel):
    """One final message emitted by ElevenLabs' browser SDK."""

    role: Literal["candidate", "interviewer"]
    content: str = Field(min_length=1, max_length=8_000)
    event_id: str | None = Field(default=None, max_length=128)


class VoiceFactRequest(BaseModel):
    """Allow-listed request shape for ElevenLabs' native-agent webhook tool."""

    voice_session_id: str = Field(min_length=1, max_length=128)
    fact_ids: list[str] = Field(default_factory=list, max_length=2)
    proposed_phase: str | None = Field(default=None, max_length=128)


class VoiceCustomLLMRequest(BaseModel):
    model: str = "leo"
    messages: list[dict[str, object]]
    # ElevenLabs' dashboard connection check has no live conversation binding.
    # Real WebRTC conversations include this opaque provider participant ID.
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    # Sent by the browser through ElevenLabs' Custom LLM extra-body contract.
    # It carries a signed, attempt-scoped binding rather than case content.
    elevenlabs_extra_body: dict[str, object] | None = None


def _shell_context(request: Request) -> dict[str, object]:
    """Auth state for the shared shell, resolved server side.

    The shell used to discover the signed-in user with a client-side /api/me
    request on every page. That produced a 401 in the browser console on every
    public page, four duplicate requests on the profile page, and a visible
    flash of the signed-out header before the response arrived.
    """
    user = current_user(request)
    return {"user": user.public_view() if user else None}


@app.get("/")
def home(request: Request) -> Response:
    """Serve the public product explanation, not an implicit practice session."""
    return TEMPLATES.TemplateResponse(request, "landing.html", _shell_context(request))


@app.get("/cases")
def cases_page(request: Request) -> Response:
    """Dedicated case library catalogue for discovering and selecting cases."""
    return TEMPLATES.TemplateResponse(request, "cases.html", _shell_context(request))


@app.get("/practice")
def practice_room(request: Request) -> Response:
    """Keep the focused interview workspace separate from the public landing page."""
    if current_user(request) is None:
        # Preserve the chosen catalogue case across the sign-in boundary.
        next_path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(f"/login?{urlencode({'next': next_path})}", status_code=303)
    return TEMPLATES.TemplateResponse(request, "practice.html", _shell_context(request))


@app.get("/profile")
def profile_page(request: Request) -> Response:
    if current_user(request) is None:
        return RedirectResponse("/login?next=/profile", status_code=303)
    return TEMPLATES.TemplateResponse(request, "profile.html", _shell_context(request))


@app.get("/attempts/{attempt_id}/debrief")
def debrief_page(attempt_id: str, request: Request) -> Response:
    """The evidence-based evaluation report for one ended attempt.

    The page shell is public to signed-in candidates; the data behind it stays
    owner-scoped because the browser can only fetch it through the attempt API.
    """
    next_path = f"/attempts/{attempt_id}/debrief"
    if current_user(request) is None:
        return RedirectResponse(f"/login?{urlencode({'next': next_path})}", status_code=303)
    return TEMPLATES.TemplateResponse(request, "debrief.html", _shell_context(request))


@app.get("/login")
def login_page(request: Request) -> Response:
    if current_user(request) is not None:
        return RedirectResponse("/practice", status_code=303)
    return TEMPLATES.TemplateResponse(request, "login.html", _shell_context(request))


@app.get("/admin")
def admin_console(request: Request) -> Response:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login?next=/admin", status_code=303)
    if not user.is_admin:
        return RedirectResponse("/practice", status_code=303)
    return TEMPLATES.TemplateResponse(request, "admin.html", _shell_context(request))


@app.get("/health")
def health() -> dict[str, str | None]:
    return {
        "status": "ok",
        "interviewer": type(INTERVIEWER).__name__,
        "evaluator": type(EVALUATOR).__name__ if EVALUATOR else None,
    }


@app.get("/api/cases")
def list_cases() -> dict[str, list[dict[str, object]]]:
    """Expose candidate-safe library metadata for the public landing page."""
    return {"cases": CATALOGUE.catalogue_items()}


@app.post("/api/attempts")
def start_attempt(request: StartAttemptRequest, user: User = Depends(require_user)) -> dict[str, object]:
    try:
        case = CATALOGUE.get(request.case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found")
    if request.duration_minutes not in case.supported_durations:
        raise HTTPException(status_code=422, detail="This duration is not available for the selected case")

    progress = STORE.get_user_case_progress(user.id, case.id)
    if progress and progress["status"] != "not_started":
        if progress["status"] == "in_progress":
            detail = "This case already has an open attempt. Resume it or reset the test before starting again."
        else:
            detail = "You have already completed this case. Reset the test before attempting it again."
        raise HTTPException(status_code=409, detail=detail)

    session = InterviewSession(id=str(uuid4()), case=case, mode=request.mode)
    session.add_interviewer_turn(_voice_intro_transcript(session))
    STORE.save(session, user_id=user.id)
    ACCOUNTS.claim_attempt(session.id, user.id)
    STORE.record_case_started(user.id, case.id, session.id)
    return session.candidate_view()


@app.get("/api/attempts/{attempt_id}")
def get_attempt(attempt_id: str, user: User = Depends(require_user)) -> dict[str, object]:
    session = _session(attempt_id, user)
    view = session.candidate_view()
    latest_eval = EVALUATIONS.latest(attempt_id)
    if latest_eval:
        view["evaluation"] = latest_eval
        view["debrief_url"] = f"/attempts/{attempt_id}/debrief"
        view["evaluation_url"] = f"/api/attempts/{attempt_id}/evaluation"
        view["score"] = _report_score(latest_eval)
        rep = latest_eval.get("report") if isinstance(latest_eval.get("report"), dict) else latest_eval
        if isinstance(rep, dict):
            view["mbb_rating_badge"] = rep.get("mbb_rating_badge")
    elif session.ended:
        view["debrief_url"] = f"/attempts/{attempt_id}/debrief"
        view["evaluation_url"] = f"/api/attempts/{attempt_id}/evaluation"
    return view


@app.post("/api/attempts/{attempt_id}/turn")
def submit_turn(
    attempt_id: str, request: CandidateTurnRequest, user: User = Depends(require_user)
) -> dict[str, object]:
    session = _session(attempt_id, user)
    try:
        result = (
            _submit_pre_case_turn(session, content=request.content, turn_id=request.turn_id)
            if not session.case_started
            else ATTEMPT_TURNS.submit(
                session,
                content=request.content,
                turn_id=request.turn_id,
                transport="chat",
                interviewer=INTERVIEWER,
                store=STORE,
            )
        )
    except AttemptAlreadyEnded as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (RuntimeError, VoiceOnboardingUnavailable) as error:
        raise HTTPException(status_code=503, detail="Leo is temporarily unavailable. Please resend your response.") from error
    except InterviewerUnavailable as error:
        raise HTTPException(status_code=503, detail="Leo is temporarily unavailable. Please resend your response.") from error
    return {**result.candidate_result(), "attempt": session.candidate_view()}


def _overall_for(report_payload: dict[str, object]) -> dict[str, object]:
    from app.evaluator import EvaluationReport, weighted_overall

    return weighted_overall(EvaluationReport.model_validate(report_payload), load_rubric())


def _evaluate_and_store(session: InterviewSession, user_id: str | None = None) -> dict[str, object]:
    """Generate and persist one complete report for an ended attempt.

    A debrief is the learning product, not an optional side effect of ending a
    case. The LLM evaluator provides the richest report when available, but a
    deterministic evaluator produces the same complete schema whenever the
    provider, prompt, or model is unavailable. This keeps every completed
    attempt reviewable and makes historical debrief links self-healing.
    """
    stored = EVALUATIONS.latest(session.id)
    if stored and isinstance(stored.get("report"), dict):
        return stored["report"]

    evaluator = EVALUATOR
    if evaluator is None:
        logging.getLogger(__name__).warning(
            "LLM evaluator is unavailable for attempt %s; using deterministic debrief",
            session.id,
        )
        report = FallbackCaseEvaluator(RESERVOIR_DIR).evaluate(session)
    else:
        try:
            report = evaluator.evaluate(session)
        except Exception:
            # Preserve the full post-case learning loop even when the provider
            # fails. The fallback works entirely from the stored transcript,
            # released evidence, authored case essence, and rubric.
            logging.getLogger(__name__).exception(
                "LLM evaluation failed for attempt %s; using deterministic debrief",
                session.id,
            )
            report = FallbackCaseEvaluator(RESERVOIR_DIR).evaluate(session)
    payload = report.model_dump()
    # Weighting is deterministic and shared by both report engines. Do not
    # call a failed primary evaluator again merely to calculate this field.
    payload["overall"] = _overall_for(payload)
    EVALUATIONS.save(report.model_dump_json(), session.id, report.evaluator_version, user_id=user_id)
    return payload


@app.post("/api/attempts/{attempt_id}/end")
def end_attempt(attempt_id: str, user: User = Depends(require_user)) -> dict[str, object]:
    session = _session(attempt_id, user)
    session.ended = True
    STORE.save(session, user_id=user.id)
    # _evaluate_and_store is deliberately resilient and persists either the
    # LLM report or a full deterministic report before this response returns.
    # Do not silently complete an attempt without a debrief.
    evaluation = _evaluate_and_store(session, user_id=user.id)
    report = evaluation
    STORE.mark_case_solved(
        user.id,
        session.case.id,
        session.id,
        score=_report_score(report),
    )
    return {
        "attempt": session.candidate_view(),
        "evaluation": evaluation,
        "scorecard": session.scorecard(),
        "debrief_url": f"/attempts/{session.id}/debrief",
        "evaluation_url": f"/api/attempts/{session.id}/evaluation",
    }



@app.get("/api/me/case-progress")
def case_progress(user: User = Depends(require_user)) -> dict[str, object]:
    """Library-friendly, persistent status for every case this user has touched."""
    return {"progress": STORE.list_user_case_progress(user.id)}


@app.post("/api/cases/{case_id}/reset")
def reset_case(case_id: str, user: User = Depends(require_user)) -> dict[str, object]:
    """Clear the current solved marker without deleting the user's learning history."""
    try:
        CATALOGUE.get(case_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Case not found") from error
    progress = STORE.get_user_case_progress(user.id, case_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="No case progress to reset")
    STORE.reset_case_progress(user.id, case_id)
    return {"progress": STORE.get_user_case_progress(user.id, case_id)}


@app.get("/api/me/cases/{case_id}/performance")
def case_performance(case_id: str, user: User = Depends(require_user)) -> dict[str, object]:
    """Return the signed-in candidate's attempts and evaluation history for one case."""
    try:
        case = CATALOGUE.get(case_id).catalogue_item()
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Case not found") from error
    attempts = [
        _practice_summary(record)
        for record in STORE.list_user_practice(user.id, limit=250)
        if record["case_id"] == case_id
    ]
    return {
        "case": case,
        "progress": STORE.get_user_case_progress(user.id, case_id)
        or {"case_id": case_id, "status": "not_started", "attempts_count": 0},
        "attempts": attempts,
    }


@app.get("/api/attempts/{attempt_id}/evaluation")
def get_evaluation(attempt_id: str, user: User = Depends(require_user)) -> dict[str, object]:
    """Fetch the stored report, or generate one lazily for an ended attempt."""
    session = _session(attempt_id, user)
    if not session.ended:
        raise HTTPException(status_code=409, detail="The attempt has not ended yet")
    stored = EVALUATIONS.latest(attempt_id)
    if stored is None:
        # Historical completed attempts from before report persistence are
        # repaired when their owner opens the debrief.
        _evaluate_and_store(session, user_id=user.id)
        stored = EVALUATIONS.latest(attempt_id)
    if stored is None or not isinstance(stored.get("report"), dict):
        raise HTTPException(status_code=503, detail="The debrief could not be stored. Please try again.")
    report_dict = stored["report"]
    overall = _overall_for(report_dict) if isinstance(report_dict, dict) else {}
    return {
        **stored,
        "overall": stored.get("overall") or overall,
        "debrief_url": f"/attempts/{attempt_id}/debrief",
    }


@app.get("/api/me/practice-history")
def practice_history(
    limit: int = 50, user: User = Depends(require_user)
) -> dict[str, object]:
    """List the signed-in candidate's durable practice record only.

    The response is deliberately user-scoped rather than accepting a user ID,
    so a candidate cannot enumerate another person's transcript or feedback.
    Full transcripts remain available through the detail endpoint below.
    """
    records = STORE.list_user_practice(user.id, limit=limit)
    completed = [record for record in records if record["ended"]]
    reviewed = [record for record in records if record["feedback"] is not None]
    scores = [
        _feedback_score(record["feedback"])
        for record in reviewed
        if _feedback_score(record["feedback"]) is not None
    ]
    return {
        "summary": {
            "attempts": len(records),
            "completed": len(completed),
            "in_progress": len(records) - len(completed),
            "feedback_available": len(reviewed),
            "average_feedback_score": round(sum(scores) / len(scores), 2) if scores else None,
        },
        "attempts": [_practice_summary(record) for record in records],
    }


@app.get("/api/me/practice-history/{attempt_id}")
def practice_history_detail(attempt_id: str, user: User = Depends(require_user)) -> dict[str, object]:
    """Return one owned transcript plus the latest and versioned feedback."""
    record = STORE.get_user_practice(user.id, attempt_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Practice record not found")
    try:
        case = CATALOGUE.get(str(record["case_id"])).catalogue_item()
    except ValueError:
        case = {"id": record["case_id"], "title": "Retired case"}
    feedback_history = EVALUATIONS.history(attempt_id)
    return {
        "attempt": {**_practice_summary(record), "case": case},
        "transcript": record["messages"],
        "feedback": record["feedback"],
        "feedback_history": feedback_history,
    }


@app.get("/api/me/profile")
@app.get("/api/profile")
def profile(user: User = Depends(require_user)) -> dict[str, object]:
    """Derived, candidate-safe progress view over one person's own history."""
    records = STORE.list_user_practice(user.id, limit=250)
    completed = [record for record in records if record["ended"]]
    assessed = [record for record in records if isinstance(record["feedback"], dict)]

    dimensions: dict[str, list[float]] = {}
    improvements: dict[str, int] = {}
    strengths: dict[str, int] = {}
    for record in assessed:
        feedback = record["feedback"]
        assert isinstance(feedback, dict)
        report = feedback.get("report")
        if not isinstance(report, dict):
            continue
        report_dimensions = report.get("dimensions", [])
        if not report_dimensions and isinstance(report.get("dimension_scores"), dict):
            report_dimensions = list(report["dimension_scores"].values())
        for dimension in report_dimensions:
            if not isinstance(dimension, dict) or not isinstance(dimension.get("name"), str):
                continue
            score = dimension.get("score")
            if isinstance(score, (int, float)):
                dimensions.setdefault(dimension["name"], []).append(float(score))
        raw_improvements = (
            report.get("areas_for_development")
            or report.get("priority_improvements")
            or []
        )
        for item in raw_improvements:
            if isinstance(item, str) and item.strip():
                improvements[item.strip()] = improvements.get(item.strip(), 0) + 1
            elif isinstance(item, dict) and item.get("gap"):
                text = str(item["gap"]).strip()
                if text:
                    improvements[text] = improvements.get(text, 0) + 1
        raw_strengths = (
            report.get("strengths")
            or report.get("headline_strengths")
            or []
        )
        for item in raw_strengths:
            if isinstance(item, str) and item.strip():
                strengths[item.strip()] = strengths.get(item.strip(), 0) + 1
            elif isinstance(item, dict) and item.get("claim"):
                text = str(item["claim"]).strip()
                if text:
                    strengths[text] = strengths.get(text, 0) + 1

    dimension_rows = [
        {"name": name, "average_score": round(sum(scores) / len(scores), 2), "assessments": len(scores)}
        for name, scores in dimensions.items()
    ]
    dimension_rows.sort(key=lambda item: (item["average_score"], item["name"]))
    return {
        "user": user.public_view(),
        "summary": {
            "attempts": len(records),
            "completed": len(completed),
            "in_progress": len(records) - len(completed),
            "candidate_turns": sum(int(record["candidate_turns"]) for record in records),
            "feedback_available": len(assessed),
            "average_feedback_score": _mean_feedback_score(assessed),
        },
        "performance": dimension_rows,
        "development_areas": [
            {"text": text, "occurrences": count}
            for text, count in sorted(improvements.items(), key=lambda item: (-item[1], item[0]))[:5]
        ],
        "strengths": [
            {"text": text, "occurrences": count}
            for text, count in sorted(strengths.items(), key=lambda item: (-item[1], item[0]))[:5]
        ],
        "recent_attempts": [_practice_summary(record) for record in records[:12]],
        "performance_history": [_practice_summary(record) for record in records],
    }


def _feedback_score(feedback: object) -> float | None:
    if not isinstance(feedback, dict) or not isinstance(feedback.get("report"), dict):
        return None
    report = feedback["report"]
    if isinstance(report.get("overall_score"), (int, float)) and float(report["overall_score"]) > 0:
        return round(float(report["overall_score"]), 2)
    dimensions = report.get("dimensions")
    if not dimensions and isinstance(report.get("dimension_scores"), dict):
        dimensions = list(report["dimension_scores"].values())
    values = [
        float(item["score"])
        for item in dimensions or []
        if isinstance(item, dict) and isinstance(item.get("score"), (int, float))
    ]
    return round(sum(values) / len(values), 2) if values else None


def _report_score(report: object) -> float | None:
    """Extract an average from either a live evaluator payload or stored report wrapper."""
    if isinstance(report, dict) and isinstance(report.get("report"), dict):
        return _feedback_score(report)
    if not isinstance(report, dict):
        return None
    if isinstance(report.get("overall_score"), (int, float)) and float(report["overall_score"]) > 0:
        return round(float(report["overall_score"]), 2)
    dimensions = report.get("dimensions")
    if not dimensions and isinstance(report.get("dimension_scores"), dict):
        dimensions = list(report["dimension_scores"].values())
    values = [
        float(item["score"])
        for item in dimensions or []
        if isinstance(item, dict) and isinstance(item.get("score"), (int, float))
    ]
    return round(sum(values) / len(values), 2) if values else None


def _mean_feedback_score(records: list[dict[str, object]]) -> float | None:
    scores = [_feedback_score(record["feedback"]) for record in records]
    present = [score for score in scores if score is not None]
    return round(sum(present) / len(present), 2) if present else None


def _practice_summary(record: dict[str, object]) -> dict[str, object]:
    try:
        case = CATALOGUE.get(str(record["case_id"])).catalogue_item()
    except ValueError:
        case = {"id": record["case_id"], "title": "Retired case"}
    feedback = record["feedback"]
    attempt_id = str(record["id"])
    return {
        "id": attempt_id,
        "case": case,
        "mode": record["mode"],
        "stage": record["stage"],
        "candidate_turns": record["candidate_turns"],
        "facts_released": record["facts_released"],
        "ended": record["ended"],
        "started_at": record["started_at"],
        "updated_at": record["updated_at"],
        "debrief_url": f"/attempts/{attempt_id}/debrief",
        "evaluation_url": f"/api/attempts/{attempt_id}/evaluation",
        "feedback": (
            {
                "evaluator_version": feedback["evaluator_version"],
                "created_at": feedback["created_at"],
                "overall_score": _feedback_score(feedback),
                "mbb_rating_badge": (
                    feedback.get("report", {}).get("mbb_rating_badge")
                    if isinstance(feedback.get("report"), dict)
                    else None
                ),
            }
            if isinstance(feedback, dict)
            else None
        ),
    }


def _submit_pre_case_turn(
    session: InterviewSession,
    *,
    content: str,
    turn_id: str,
    voice_session: VoiceSession | None = None,
) -> TurnSubmission:
    """Persist the LLM-led readiness exchange before releasing any case content.

    There is intentionally no phrase matcher here. Leo interprets the candidate's
    intent through the onboarding model, then writes a fresh conversational bridge
    before the authored case opening is appended.
    """
    if session.ended:
        raise AttemptAlreadyEnded("This attempt has already ended")
    if cached_result := session.turn_results.get(turn_id):
        return TurnSubmission(
            reply=str(cached_result["reply"]),
            facts=list(cached_result.get("new_facts", [])),
            cached=True,
        )
    onboarding = _voice_onboarding().respond(content)
    reply = onboarding.reply.strip()
    if not reply:
        raise VoiceOnboardingUnavailable("Leo did not produce an onboarding response")

    session.record_candidate_turn(content)
    if onboarding.ready_to_begin:
        session.case_started = True
        # The LLM supplies the conversational transition. The authored opening
        # stays canonical, so no hidden case details can be invented here.
        reply = f"{reply}\n\n{session.case.opening}"
        if voice_session is not None:
            STORE.mark_voice_case_started(voice_session.id)
    session.add_interviewer_turn(reply)
    session.turn_results[turn_id] = {"reply": reply, "new_facts": []}
    STORE.save(session)
    return TurnSubmission(reply=reply, facts=[])

# --- Voice transport ------------------------------------------------------


def _voice_settings() -> VoiceSettings:
    settings = VoiceSettings.from_environment()
    if not settings.enabled:
        # Do not expose a half-configured paid capability to the browser.
        raise HTTPException(status_code=404, detail="Voice practice is not enabled")
    return settings


def _voice_intro(session: InterviewSession) -> str:
    """The shared Leo welcome, with generic case metadata only.

    The detailed brief is intentionally held back until the candidate opts in,
    regardless of whether they are using typed chat or voice.
    """
    return _voice_intro_transcript(session)


def _voice_intro_transcript(session: InterviewSession) -> str:
    """The canonical text for both the visible and spoken welcome."""
    case_type = session.case.category.replace("-", " ").replace("_", " ")
    return (
        f"Hi, I'm Leo. I'll be your case interviewer today, and we're working through a {case_type} case. "
        "Think aloud, keep your reasoning structured, and ask for the information you need. "
        "When you're ready, just say so and we'll get started."
    )



def _native_voice_variables(session: InterviewSession, voice_session: VoiceSession) -> dict[str, str]:
    """Return the narrow, per-session context sent to the native voice agent.

    The full reservoir and answer key remain on this server. The LLM receives
    the public brief plus a fact *index* (not fact contents) and must call the
    authenticated tool below to obtain any newly approved evidence.
    """
    case = session.case
    phases = "\n".join(
        f"- {phase.id}: {phase.interviewer_goal}" for phase in case.phases
    )
    fact_index = "\n".join(f"- {fact.id} | {fact.domain}" for fact in case.facts)
    return {
        "voice_session_id": voice_session.id,
        "voice_intro": _voice_intro(session),
        "case_title": case.title,
        "case_category": case.category.replace("-", " "),
        "case_objective": case.objective,
        "case_opening": case.opening,
        "case_phase_guide": phases,
        "case_fact_index": fact_index,
        "case_current_phase": session.stage,
    }


def _voice_onboarding():
    global VOICE_ONBOARDING
    if VOICE_ONBOARDING is None:
        VOICE_ONBOARDING = create_voice_onboarding()
    return VOICE_ONBOARDING


def _owned_voice_session(voice_session_id: str, user: User) -> VoiceSession:
    voice_session = STORE.get_voice_session(voice_session_id)
    # Voice controls are intentionally stricter than the read-only admin view.
    # An administrator must not be able to join or end a candidate's live call.
    if voice_session is None or ACCOUNTS.owner_of(voice_session.attempt_id) != user.id:
        raise HTTPException(status_code=404, detail="Voice session not found")
    return voice_session


@app.post("/api/attempts/{attempt_id}/voice-sessions")
def create_voice_session(attempt_id: str, user: User = Depends(require_user)) -> dict[str, object]:
    """Issue a browser-safe, attempt-bound WebRTC credential.

    The ElevenLabs API key remains on this server.  The random local session ID
    becomes the provider participant ID and later binds Custom LLM callbacks to
    this exact attempt.
    """
    settings = _voice_settings()
    session = _session(attempt_id, user)
    if session.ended:
        raise HTTPException(status_code=409, detail="This attempt has already ended")

    voice_session_id = str(uuid4())
    try:
        provider_session = VOICE_PROVIDER.issue_token(settings, participant_name=voice_session_id)
        voice_session = VoiceSession(
            id=voice_session_id,
            attempt_id=session.id,
            provider="elevenlabs",
            agent_id=settings.agent_id,
            provider_conversation_id=provider_session.conversation_id,
            status="issued",
        )
        STORE.create_voice_session(voice_session)
    except VoiceConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VoiceProviderError as error:
        raise HTTPException(status_code=503, detail="Leo voice is temporarily unavailable. Please use chat.") from error
    except ActiveVoiceSessionExists as error:
        raise HTTPException(status_code=409, detail="A voice session is already active for this attempt") from error
    payload: dict[str, object] = {
        "voice_session_id": voice_session.id,
        "conversation_token": provider_session.token,
        "transport": "webrtc",
        "voice_mode": settings.mode,
        # The same onboarding gate applies to voice and typed chat.
        "voice_intro": _voice_intro(session),
        "case_opening": session.case.opening,
    }
    if settings.mode == "custom":
        payload["custom_llm_extra_body"] = {
            "voice_session_id": voice_session.id,
            "voice_session_binding": _voice_session_binding(voice_session.id, settings),
        }
    if settings.uses_native_agent:
        payload["dynamic_variables"] = _native_voice_variables(session, voice_session)
    return payload


@app.get("/api/voice/status")
def voice_status(_: User = Depends(require_user)) -> dict[str, object]:
    """Expose capability state, never credentials or agent configuration."""
    settings = VoiceSettings.from_environment()
    if settings.uses_realtime_speech:
        realtime = RealtimeVoiceSettings.from_environment()
        return {
            "enabled": settings.enabled,
            "mode": settings.mode,
            # Push-to-talk needs a voice and a fused interviewer. Without either
            # the browser must not offer a control that cannot complete a turn.
            "ready": bool(
                settings.enabled and realtime.is_configured and SPOKEN_INTERVIEWER is not None
            ),
        }
    adapter_ready = bool(settings.custom_llm_secret) if not settings.uses_native_agent else bool(settings.case_tool_secret)
    return {
        "enabled": settings.enabled,
        "mode": settings.mode,
        "ready": bool(
            settings.enabled
            and settings.uses_agent
            and settings.api_key
            and settings.agent_id
            and adapter_ready
        ),
    }


# --- Realtime push-to-talk ------------------------------------------------


def _realtime_voice_settings() -> RealtimeVoiceSettings:
    settings = _voice_settings()
    if not settings.uses_realtime_speech:
        raise HTTPException(status_code=404, detail="Realtime voice practice is not enabled")
    return RealtimeVoiceSettings.from_environment()


def _realtime_socket_urls(
    realtime: RealtimeVoiceSettings, session: InterviewSession
) -> dict[str, str]:
    """Mint one fresh credential per socket and return the URLs that carry them.

    ElevenLabs single-use tokens are consumed by the connection that uses them,
    so a pair cannot be handed out once and reused for the rest of the case: the
    second utterance would open a socket that closes immediately. The browser
    therefore asks for a new pair before every utterance, and the two mints run
    concurrently behind the microphone warming up, which is why this costs
    nothing the candidate can hear.
    """
    tokens = REALTIME_VOICE_PROVIDER.mint_tokens(realtime, SCRIBE_TOKEN, TTS_TOKEN)
    return {
        "stt_url": speech_to_text_url(
            realtime, tokens[SCRIBE_TOKEN], keyterms=case_keyterms(session.case)
        ),
        "tts_url": text_to_speech_url(realtime, tokens[TTS_TOKEN]),
    }


def _realtime_session(attempt_id: str, user: User) -> tuple[RealtimeVoiceSettings, InterviewSession]:
    realtime = _realtime_voice_settings()
    session = _session(attempt_id, user)
    if session.ended:
        raise HTTPException(status_code=409, detail="This attempt has already ended")
    if SPOKEN_INTERVIEWER is None:
        raise HTTPException(
            status_code=503, detail="Leo voice is temporarily unavailable. Please use chat."
        )
    return realtime, session


@app.post("/api/attempts/{attempt_id}/voice-realtime/session")
def create_realtime_voice_session(
    attempt_id: str, user: User = Depends(require_user)
) -> dict[str, object]:
    """Describe the transport once, without issuing anything spendable.

    The workspace API key stays here. Credentials are per utterance and come
    from the sockets route below; this response is only the shape of the
    session, so it can be cached by the browser for the whole case.
    """
    realtime, session = _realtime_session(attempt_id, user)
    return {
        "attempt_id": session.id,
        "transport": "realtime",
        "sample_rate": realtime.sample_rate,
        "tts_output_format": realtime.tts_output_format,
        "sockets_url": f"/api/attempts/{session.id}/voice-realtime/sockets",
        "turn_stream_url": f"/api/attempts/{session.id}/turn/stream",
        "voice_intro": _voice_intro(session),
        "case_started": session.case_started,
    }


@app.post("/api/attempts/{attempt_id}/voice-realtime/sockets")
def issue_realtime_sockets(
    attempt_id: str, user: User = Depends(require_user)
) -> dict[str, object]:
    """Issue a fresh, single-use socket pair for one utterance."""
    realtime, session = _realtime_session(attempt_id, user)
    try:
        return _realtime_socket_urls(realtime, session)
    except VoiceConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VoiceProviderError as error:
        raise HTTPException(
            status_code=503, detail="Leo voice is temporarily unavailable. Please use chat."
        ) from error


def _sse_event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


@app.post("/api/attempts/{attempt_id}/turn/stream")
def stream_turn(
    attempt_id: str, request: CandidateTurnRequest, user: User = Depends(require_user)
) -> StreamingResponse:
    """Stream one spoken turn as server-sent events.

    The control event carries the facts the runtime approved, so the side panel
    fills before Leo has finished speaking. Every later delta is speakable text
    the browser forwards to synthesis a clause at a time, which is what lets
    audio begin on the first sentence instead of the last token.
    """
    _realtime_voice_settings()
    session = _session(attempt_id, user)
    if SPOKEN_INTERVIEWER is None:
        raise HTTPException(
            status_code=503, detail="Leo is temporarily unavailable. Please switch to chat."
        )

    def events():
        # The pre-case readiness exchange is not a case turn. It stays on the
        # shared onboarding path so voice and chat gate identically, and is
        # emitted as one delta because it is already complete.
        if not session.case_started:
            try:
                result = _submit_pre_case_turn(
                    session, content=request.content, turn_id=request.turn_id
                )
            except (RuntimeError, VoiceOnboardingUnavailable):
                yield _sse_event("error", {"detail": "Leo is temporarily unavailable."})
                return
            yield _sse_event("control", {"facts": []})
            yield _sse_event("delta", {"text": result.reply})
            yield _sse_event("done", {"attempt": session.candidate_view(), "new_facts": []})
            return

        new_facts: list[dict[str, str]] = []
        try:
            for event, payload in ATTEMPT_TURNS.submit_stream(
                session,
                content=request.content,
                turn_id=request.turn_id,
                spoken_interviewer=SPOKEN_INTERVIEWER,
                store=STORE,
            ):
                if event == "control":
                    new_facts = payload  # type: ignore[assignment]
                    yield _sse_event("control", {"facts": new_facts})
                elif event == "delta":
                    yield _sse_event("delta", {"text": payload})
                else:
                    yield _sse_event(
                        "done",
                        {"attempt": session.candidate_view(), "new_facts": new_facts},
                    )
                    # Started only after the reply has been fully delivered, so
                    # it can never delay speech. It reports; it never rewrites.
                    submission: TurnSubmission = payload  # type: ignore[assignment]
                    released = {fact["id"] for fact in new_facts}
                    audit_spoken_turn_in_background(
                        SPOKEN_AUDITOR,
                        session_id=session.id,
                        candidate_turn=request.content,
                        reply=submission.reply,
                        facts=[fact for fact in session.case.facts if fact.id in released],
                    )
        except AttemptAlreadyEnded as error:
            yield _sse_event("error", {"detail": str(error)})
        except (ControlBlockMissing, InterviewerUnavailable):
            # The fused call did not produce a usable turn. Fall back to the
            # chat pipeline, which is slower but is the path typed attempts
            # already rely on, then emit its reply as one delta.
            logging.getLogger(__name__).warning(
                "Fused spoken turn failed; falling back to the chat pipeline"
            )
            try:
                result = ATTEMPT_TURNS.submit(
                    session,
                    content=request.content,
                    turn_id=request.turn_id,
                    transport="voice",
                    interviewer=INTERVIEWER,
                    store=STORE,
                )
            except (AttemptAlreadyEnded, InterviewerUnavailable) as error:
                yield _sse_event("error", {"detail": str(error)})
                return
            yield _sse_event("control", {"facts": result.facts})
            yield _sse_event("delta", {"text": result.reply})
            yield _sse_event(
                "done", {"attempt": session.candidate_view(), "new_facts": result.facts}
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/voice-sessions/{voice_session_id}/lifecycle/{event}")
def update_voice_session(
    voice_session_id: str,
    event: str,
    _: VoiceLifecycleRequest,
    user: User = Depends(require_user),
) -> dict[str, str]:
    _voice_settings()
    if event not in {"connected", "disconnected", "ended"}:
        raise HTTPException(status_code=404, detail="Voice event not found")
    voice_session = _owned_voice_session(voice_session_id, user)
    STORE.set_voice_session_status(voice_session_id, event)
    return {"status": event}


@app.post("/api/voice-sessions/{voice_session_id}/transcript")
def record_native_voice_transcript(
    voice_session_id: str,
    request: VoiceTranscriptRequest,
    user: User = Depends(require_user),
) -> dict[str, object]:
    """Persist an exact final native-agent turn from the authenticated browser.

    ElevenLabs' browser SDK emits final agent and user messages separately. By
    storing those messages directly, the chat transcript is the exact text
    spoken/heard in the call rather than a later provider export or an LLM
    rewrite. This endpoint is intentionally unavailable in Custom LLM mode,
    whose server adapter remains the canonical writer.
    """
    settings = _voice_settings()
    if not settings.uses_native_agent:
        raise HTTPException(status_code=409, detail="Native ElevenLabs voice mode is not enabled")
    voice_session = _owned_voice_session(voice_session_id, user)
    session = STORE.get(voice_session.attempt_id, CATALOGUE)
    if session is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    # Defensive reconciliation for provider sessions created before the
    # persisted runtime acquired its own case_started marker. Normal sessions
    # transition both records atomically in _submit_pre_case_turn.
    if voice_session.case_started and not session.case_started:
        session.case_started = True
        STORE.save(session)

    content = request.content.strip()
    event_key = request.event_id or hashlib.sha256(
        f"{request.role}:{content}".encode()
    ).hexdigest()
    turn_id = f"voice-native:{voice_session.id}:{request.role}:{event_key}"
    if turn_id not in session.turn_results:
        if request.role == "candidate":
            session.record_candidate_turn(content)
        elif not (
            content == _voice_intro_transcript(session)
            and session.messages
            and session.messages[0] == {"role": "interviewer", "content": content}
        ):
            session.add_interviewer_turn(content)

        # The native workflow speaks the authored opening exactly after its
        # readiness gate. Marking the transition lets a later return to chat
        # resume the same case rather than replaying its welcome.
        if request.role == "interviewer" and content == session.case.opening:
            session.case_started = True
            STORE.mark_voice_case_started(voice_session.id)
        session.turn_results[turn_id] = {"reply": "", "new_facts": []}
        STORE.save(session)
    STORE.set_voice_session_status(voice_session.id, "connected")
    return {"attempt": session.candidate_view()}


@app.post("/api/voice-sessions/{voice_session_id}/final-candidate-transcript")
def reconcile_custom_voice_candidate_transcript(
    voice_session_id: str,
    request: VoiceTranscriptRequest,
    user: User = Depends(require_user),
) -> dict[str, object]:
    """Replace a Custom LLM's provisional ASR text with ElevenLabs' final text.

    Custom LLM callbacks may arrive while ElevenLabs is still settling a
    spoken turn. Leo must answer that callback promptly, but the browser SDK
    later emits the provider's final user transcript. Reconcile only the most
    recent candidate message, never an interviewer reply or case state, so the
    visible case record reflects exactly what ElevenLabs heard.
    """
    settings = _voice_settings()
    if settings.uses_native_agent:
        raise HTTPException(status_code=409, detail="Custom LLM voice mode is not enabled")
    if request.role != "candidate":
        raise HTTPException(status_code=422, detail="Only a final candidate transcript may be reconciled")
    voice_session = _owned_voice_session(voice_session_id, user)
    session = STORE.get(voice_session.attempt_id, CATALOGUE)
    if session is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    content = request.content.strip()
    for index in range(len(session.messages) - 1, -1, -1):
        message = session.messages[index]
        if message["role"] != "candidate":
            continue
        if message["content"] != content:
            session.messages[index] = {"role": "candidate", "content": content}
            STORE.save(session)
        STORE.set_voice_session_status(voice_session.id, "connected")
        return {"attempt": session.candidate_view()}

    # The final client event can occasionally race the initial Custom LLM
    # callback. The browser retries this recoverable response shortly.
    raise HTTPException(status_code=409, detail="No candidate turn is ready for transcript reconciliation")


def _custom_llm_authorized(request: Request, settings: VoiceSettings) -> None:
    if not settings.custom_llm_secret:
        raise HTTPException(status_code=503, detail="Leo voice adapter is not configured")
    authorization = request.headers.get("authorization", "")
    accepted_values = (settings.custom_llm_secret, f"Bearer {settings.custom_llm_secret}")
    if not any(hmac.compare_digest(authorization, expected) for expected in accepted_values):
        raise HTTPException(status_code=401, detail="Invalid voice adapter credentials")


def _voice_session_binding(voice_session_id: str, settings: VoiceSettings) -> str:
    """Return a signed browser-carried binding for Custom LLM callbacks.

    ElevenLabs forwards Custom LLM extra body values on every model call. The
    opaque session ID is not sufficient on its own because browser-provided
    values are editable, so pair it with a server-verifiable HMAC.
    """
    return hmac.new(
        settings.custom_llm_secret.encode(),
        f"leo-voice-session:{voice_session_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _voice_session_id_from_custom_payload(payload: VoiceCustomLLMRequest, settings: VoiceSettings) -> str | None:
    extra = payload.elevenlabs_extra_body
    if isinstance(extra, dict):
        session_id = extra.get("voice_session_id")
        binding = extra.get("voice_session_binding")
        if isinstance(session_id, str) and session_id and isinstance(binding, str):
            if not hmac.compare_digest(binding, _voice_session_binding(session_id, settings)):
                raise HTTPException(status_code=401, detail="Invalid voice session binding")
            return session_id
    return voice_session_id_from_request(payload.messages, payload.user_id)



def _case_tool_authorized(request: Request, settings: VoiceSettings) -> None:
    """Authenticate the dashboard-configured native-agent tool, not a user."""
    if not settings.case_tool_secret:
        raise HTTPException(status_code=503, detail="Leo case tool is not configured")
    received = request.headers.get("authorization", "")
    # ElevenLabs' Secret-header control sends the selected secret as the raw
    # header value. Accept it alongside the conventional Bearer format so the
    # dashboard needs no unsafe hard-coded prefix or duplicate secret.
    accepted_values = (settings.case_tool_secret, f"Bearer {settings.case_tool_secret}")
    if not any(hmac.compare_digest(received, expected) for expected in accepted_values):
        raise HTTPException(status_code=401, detail="Invalid case tool credentials")


@app.post("/api/elevenlabs/case-facts")
def elevenlabs_case_facts(request: Request, payload: VoiceFactRequest) -> dict[str, object]:
    """Return only runtime-approved evidence to a native ElevenLabs agent.

    The agent receives fact IDs and their purposes at session start, not fact
    contents. It may request up to two IDs through this endpoint; the runtime
    validates phase and dependency rules before a fact is ever returned.
    """
    settings = _voice_settings()
    if not settings.uses_native_agent:
        raise HTTPException(status_code=404, detail="Native ElevenLabs voice mode is not enabled")
    _case_tool_authorized(request, settings)
    voice_session = STORE.get_voice_session(payload.voice_session_id)
    if voice_session is None or voice_session.status in {"ended", "failed", "reconciled"}:
        raise HTTPException(status_code=404, detail="Voice session not found")
    session = STORE.get(voice_session.attempt_id, CATALOGUE)
    if session is None or session.ended:
        raise HTTPException(status_code=404, detail="Attempt not found")

    proposed_phase = payload.proposed_phase or session.stage
    facts = session.case.validate_fact_selection(
        payload.fact_ids,
        session.stage,
        session.disclosed_ids,
        max_facts=2,
    )
    session.apply_director_decision(proposed_phase, facts)
    STORE.save(session)
    return {
        "phase": session.stage,
        "facts": [{"id": fact.id, "content": fact.content} for fact in facts],
        "instruction": (
            "Use only the returned facts. If no facts were returned, say that the requested "
            "detail is not available yet and guide the candidate to the next useful analysis."
        ),
    }


def _verify_elevenlabs_webhook(request: Request, raw_body: bytes, secret: str) -> None:
    """Validate ElevenLabs' timestamped HMAC before reading callback data."""
    if not secret:
        raise HTTPException(status_code=404, detail="Webhook endpoint is not configured")
    values: dict[str, list[str]] = {}
    for item in request.headers.get("elevenlabs-signature", "").split(","):
        key, separator, value = item.strip().partition("=")
        if separator and key and value:
            values.setdefault(key, []).append(value)
    timestamp = next(iter(values.get("t", [])), "")
    try:
        # Reject stale deliveries as well as forged bodies. The provider sends
        # a delivery timestamp, not the call timestamp, so this remains safe
        # for normal asynchronous post-call processing.
        if abs(time.time() - int(timestamp)) > 15 * 60:
            raise ValueError
    except ValueError as error:
        raise HTTPException(status_code=401, detail="Invalid webhook signature") from error
    signed_payload = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed_payload, "sha256").hexdigest()
    if not any(hmac.compare_digest(signature, expected) for signature in values.get("v0", [])):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _sse_reply(reply: str, model: str):
    """Emit the small OpenAI-compatible stream ElevenLabs expects from Custom LLMs."""
    reply = clean_spoken_text(reply)
    completion_id = f"chatcmpl-leo-{uuid4().hex}"
    created = int(time.time())
    first_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": reply}, "finish_reason": None}],
    }
    last_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(first_chunk)}\n\n"
    yield f"data: {json.dumps(last_chunk)}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
def elevenlabs_custom_llm(
    request: Request, payload: VoiceCustomLLMRequest
) -> StreamingResponse:
    """Translate a provider turn into the same runtime mutation used by chat.

    ElevenLabs sends the provider participant ID as ``user_id``.  We set that
    value to our opaque voice-session ID when issuing the WebRTC token, so a
    callback can be matched without accepting an attempt ID from the browser.
    """
    settings = _voice_settings()
    _custom_llm_authorized(request, settings)
    voice_session_id = _voice_session_id_from_custom_payload(payload, settings)
    if voice_session_id is None:
        # A connection check is not a candidate turn. Return a safe synthetic
        # response so the dashboard can validate the URL and API-key secret
        # without gaining access to any attempt or case content.
        return StreamingResponse(
            _sse_reply("Leo's voice connection is ready.", payload.model),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    voice_session = STORE.get_voice_session(voice_session_id)
    if voice_session is None or voice_session.status in {"ended", "failed"}:
        raise HTTPException(status_code=404, detail="Voice session not found")
    session = STORE.get(voice_session.attempt_id, CATALOGUE)
    if session is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    try:
        candidate_utterance, candidate_index = latest_candidate_utterance(payload.messages)
    except ValueError:
        # Some provider clients request the first agent turn through the Custom
        # LLM rather than playing the configured first message directly. In
        # either path, welcome the candidate without starting the case.
        return StreamingResponse(
            _sse_reply(_voice_intro(session), payload.model),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    onboarding_turn_id = f"voice-onboarding:{voice_session.id}:{candidate_index}"
    if cached := session.turn_results.get(onboarding_turn_id):
        # Provider retries must replay the original onboarding answer rather
        # than treating the same "I'm ready" as a new case interview turn.
        reply = str(cached["reply"])
        STORE.set_voice_session_status(voice_session.id, "connected")
        return StreamingResponse(
            _sse_reply(reply, payload.model),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    is_case_started = session.case_started or (voice_session is not None and voice_session.case_started) or len(session.messages) > 1
    if not is_case_started:
        try:
            result = _submit_pre_case_turn(
                session,
                content=candidate_utterance,
                turn_id=onboarding_turn_id,
                voice_session=voice_session,
            )
        except (RuntimeError, VoiceOnboardingUnavailable) as error:
            raise HTTPException(
                status_code=503,
                detail="Leo is temporarily unavailable. Please switch to chat.",
            ) from error
        STORE.set_voice_session_status(voice_session.id, "connected")
        return StreamingResponse(
            _sse_reply(result.reply, payload.model),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    try:
        result = ATTEMPT_TURNS.submit(
            session,
            content=candidate_utterance,
            turn_id=f"voice:{voice_session.id}:{candidate_index}",
            transport="voice",
            interviewer=INTERVIEWER,
            store=STORE,
        )
        STORE.set_voice_session_status(voice_session.id, "connected")
    except AttemptAlreadyEnded as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except InterviewerUnavailable as error:
        raise HTTPException(status_code=503, detail="Leo is temporarily unavailable. Please switch to chat.") from error

    return StreamingResponse(
        # The canonical reply is the sole source for both the transcript and
        # speech. Never give the provider a second, voice-only rewrite.
        _sse_reply(result.reply, payload.model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/webhooks/elevenlabs/post-call")
async def elevenlabs_post_call_webhook(request: Request) -> dict[str, str]:
    """Accept a verified post-call receipt without importing provider transcripts.

    Leo's persisted attempt remains the canonical transcript and fact ledger.
    The provider callback supplies operational confirmation only, which keeps
    raw audio and duplicate transcript copies out of the initial release.
    """
    settings = VoiceSettings.from_environment()
    raw_body = await request.body()
    _verify_elevenlabs_webhook(request, raw_body, settings.webhook_secret)
    try:
        payload = json.loads(raw_body)
        conversation_id = payload.get("data", {}).get("conversation_id")
    except (AttributeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from error
    if not isinstance(conversation_id, str) or not conversation_id:
        raise HTTPException(status_code=400, detail="Webhook conversation is missing")

    voice_session = STORE.get_voice_session_by_provider_conversation(conversation_id)
    if voice_session is not None:
        STORE.reconcile_voice_session(voice_session.id)
    # Always acknowledge an authenticated callback. An old provider delivery
    # must not be able to trigger retries or mutate a newer attempt.
    return {"status": "received"}


def _session(attempt_id: str, user: User) -> InterviewSession:
    # 404 rather than 403 on another candidate's attempt: the API must not confirm
    # that an attempt exists to anyone who does not own it.
    owner_id = ACCOUNTS.owner_of(attempt_id)
    if not owner_id:
        with STORE._connect() as conn:
            row = conn.execute("SELECT user_id FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
            if row and row[0]:
                owner_id = str(row[0])
    if owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=404, detail="Attempt not found")
    session = STORE.get(attempt_id, CATALOGUE)
    if session is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return session
