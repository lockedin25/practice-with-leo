from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.accounts import AccountStore, User, current_user, require_user
from app.admin import router as admin_router
from app.auth import router as auth_router
from app.case_runtime import CaseCatalogue, InterviewSession
from app.interviewer import InterviewerUnavailable, create_interviewer
from app.store import SessionStore


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"
load_dotenv(ROOT / ".env")
DATABASE_PATH = ROOT / "data" / "casecall.db"
CATALOGUE = CaseCatalogue.from_reservoir(ROOT)
INTERVIEWER = create_interviewer()
STORE = SessionStore(DATABASE_PATH)
ACCOUNTS = AccountStore(DATABASE_PATH)

app = FastAPI(title="Leo", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# The auth and admin routers read these off app state rather than importing this
# module, so account handling never reaches back into the interview API.
app.state.accounts = ACCOUNTS
app.state.store = STORE
app.state.catalogue = CATALOGUE
app.state.database_path = DATABASE_PATH
app.include_router(auth_router)
app.include_router(admin_router)


class StartAttemptRequest(BaseModel):
    case_id: str = CATALOGUE.default_case.id
    mode: str = Field(default="realistic", pattern="^(coached|realistic|pressure)$")
    duration_minutes: int = Field(default=30, ge=1)


class CandidateTurnRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8_000)
    turn_id: str = Field(min_length=1, max_length=128)


@app.get("/")
def home() -> FileResponse:
    """Serve the public product explanation, not an implicit practice session."""
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/practice")
def practice_room(request: Request) -> Response:
    """Keep the focused interview workspace separate from the public landing page."""
    if current_user(request) is None:
        # Preserve the chosen catalogue case across the sign-in boundary.
        next_path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(f"/login?{urlencode({'next': next_path})}", status_code=303)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/login")
def login_page(request: Request) -> Response:
    if current_user(request) is not None:
        return RedirectResponse("/practice", status_code=303)
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/admin")
def admin_console(request: Request) -> Response:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login?next=/admin", status_code=303)
    if not user.is_admin:
        return RedirectResponse("/practice", status_code=303)
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "interviewer": type(INTERVIEWER).__name__}


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

    session = InterviewSession(id=str(uuid4()), case=case, mode=request.mode)
    # The brief is the opening. Leo waits for the candidate to choose their
    # first question or structure instead of steering with a stock prompt.
    session.add_interviewer_turn(case.opening)
    STORE.save(session)
    ACCOUNTS.claim_attempt(session.id, user.id)
    return session.candidate_view()


@app.get("/api/attempts/{attempt_id}")
def get_attempt(attempt_id: str, user: User = Depends(require_user)) -> dict[str, object]:
    return _session(attempt_id, user).candidate_view()


@app.post("/api/attempts/{attempt_id}/turn")
def submit_turn(
    attempt_id: str, request: CandidateTurnRequest, user: User = Depends(require_user)
) -> dict[str, object]:
    session = _session(attempt_id, user)
    if session.ended:
        raise HTTPException(status_code=409, detail="This attempt has already ended")
    if cached_result := session.turn_results.get(request.turn_id):
        return {**cached_result, "attempt": session.candidate_view()}

    try:
        turn = INTERVIEWER.respond(session, request.content)
    except InterviewerUnavailable as error:
        raise HTTPException(status_code=503, detail="Leo is temporarily unavailable. Please resend your response.") from error

    result = {"reply": turn.reply, "new_facts": [{"id": fact.id, "content": fact.content} for fact in turn.facts]}
    session.turn_results[request.turn_id] = result
    STORE.save(session)
    return {**result, "attempt": session.candidate_view()}


@app.post("/api/attempts/{attempt_id}/end")
def end_attempt(attempt_id: str, user: User = Depends(require_user)) -> dict[str, object]:
    session = _session(attempt_id, user)
    session.ended = True
    STORE.save(session)
    return {"attempt": session.candidate_view(), "scorecard": session.scorecard()}


def _session(attempt_id: str, user: User) -> InterviewSession:
    # 404 rather than 403 on another candidate's attempt: the API must not confirm
    # that an attempt exists to anyone who does not own it.
    if ACCOUNTS.owner_of(attempt_id) != user.id and not user.is_admin:
        raise HTTPException(status_code=404, detail="Attempt not found")
    session = STORE.get(attempt_id, CATALOGUE)
    if session is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return session
