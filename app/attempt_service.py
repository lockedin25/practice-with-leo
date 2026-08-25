"""One canonical mutation path for chat and voice interview turns.

Transport adapters may collect a candidate's final words differently, but only
this service is allowed to ask Leo for a response and persist the approved case
state.  Keeping it small makes chat regression behaviour explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Literal

from app.case_runtime import InterviewSession
from app.interviewer import InterviewTurn, Interviewer, InterviewerUnavailable
from app.store import SessionStore


Transport = Literal["chat", "voice"]


class AttemptAlreadyEnded(RuntimeError):
    """Raised before an adapter can mutate a completed attempt."""


@dataclass(frozen=True)
class TurnSubmission:
    reply: str
    facts: list[dict[str, str]]
    spoken_reply: str | None = None
    cached: bool = False

    def candidate_result(self) -> dict[str, object]:
        return {"reply": self.reply, "new_facts": self.facts}


class AttemptTurnService:
    """Submit one final candidate utterance through the existing runtime."""

    def submit(
        self,
        session: InterviewSession,
        *,
        content: str,
        turn_id: str,
        transport: Transport,
        interviewer: Interviewer,
        store: SessionStore,
    ) -> TurnSubmission:
        if session.ended:
            raise AttemptAlreadyEnded("This attempt has already ended")
        if transport not in {"chat", "voice"}:
            raise ValueError("Unsupported interview transport")

        if cached_result := session.turn_results.get(turn_id):
            return TurnSubmission(
                reply=str(cached_result["reply"]),
                facts=list(cached_result.get("new_facts", [])),
                spoken_reply=(
                    str(cached_result["spoken_reply"])
                    if isinstance(cached_result.get("spoken_reply"), str)
                    else None
                ),
                cached=True,
            )

        turn: InterviewTurn = interviewer.respond(session, content, spoken=transport == "voice")
        result = {
            "reply": turn.reply,
            "new_facts": [{"id": fact.id, "content": fact.content} for fact in turn.facts],
        }
        if turn.spoken_reply:
            result["spoken_reply"] = turn.spoken_reply
        # Keep this legacy payload unchanged so existing chat attempts, API
        # clients, and stored idempotency results remain compatible.
        session.turn_results[turn_id] = result
        store.save(session)
        return TurnSubmission(reply=turn.reply, facts=result["new_facts"], spoken_reply=turn.spoken_reply)

    def submit_stream(
        self,
        session: InterviewSession,
        *,
        content: str,
        turn_id: str,
        spoken_interviewer: Any,
        store: SessionStore,
    ) -> Iterator[tuple[str, object]]:
        """Stream one spoken turn, persisting exactly what ``submit`` would.

        Yields ``('control', facts)``, then ``('delta', text)`` repeatedly, then
        ``('done', TurnSubmission)``. The stored ``turn_results`` payload is the
        same shape the chat path writes, so a spoken attempt and a typed one
        remain indistinguishable to the evaluator and the transcript API.
        """
        if session.ended:
            raise AttemptAlreadyEnded("This attempt has already ended")

        if cached_result := session.turn_results.get(turn_id):
            # A provider or browser retry must replay, not re-charge. The cached
            # reply is emitted as one delta so the caller's speech path needs no
            # special case for a replayed turn.
            reply = str(cached_result["reply"])
            facts = list(cached_result.get("new_facts", []))
            yield ("control", facts)
            yield ("delta", reply)
            yield ("done", TurnSubmission(reply=reply, facts=facts, spoken_reply=reply, cached=True))
            return

        turn: InterviewTurn | None = None
        for event, payload in spoken_interviewer.respond_stream(session, content):
            if event == "done":
                turn = payload  # type: ignore[assignment]
                break
            if event == "control":
                yield (
                    "control",
                    [{"id": fact.id, "content": fact.content} for fact in payload],  # type: ignore[union-attr]
                )
                continue
            yield (event, payload)

        if turn is None:
            raise InterviewerUnavailable("The spoken interviewer produced no turn")

        result: dict[str, object] = {
            "reply": turn.reply,
            "new_facts": [{"id": fact.id, "content": fact.content} for fact in turn.facts],
        }
        if turn.spoken_reply:
            result["spoken_reply"] = turn.spoken_reply
        session.turn_results[turn_id] = result
        store.save(session)
        yield (
            "done",
            TurnSubmission(
                reply=turn.reply,
                facts=result["new_facts"],  # type: ignore[arg-type]
                spoken_reply=turn.spoken_reply,
            ),
        )


class AttemptLifecycleService:
    """Coordinates attempt completion, automatic evaluation, and database persistence."""

    def complete_attempt(
        self,
        session: InterviewSession,
        *,
        store: SessionStore,
        evaluations: EvaluationStore,
        evaluator: Any,
        user_id: str | None = None,
    ) -> dict[str, object]:
        """Mark attempt as ended, trigger evaluator, persist report and update progress."""
        session.ended = True
        store.save(session, user_id=user_id)
        evaluation_payload: dict[str, object] | None = None
        if evaluator is not None:
            try:
                report = evaluator.evaluate(session)
                evaluation_payload = report.model_dump()
                evaluation_payload["overall"] = evaluator.overall(report)
                evaluations.save(
                    report.model_dump_json(),
                    session.id,
                    report.evaluator_version,
                    user_id=user_id,
                )
            except Exception:
                evaluation_payload = None

        report_wrapper = evaluation_payload or evaluations.latest(session.id)
        score: float | None = None
        if report_wrapper:
            rep = report_wrapper.get("report") if isinstance(report_wrapper.get("report"), dict) else report_wrapper
            if isinstance(rep, dict) and isinstance(rep.get("overall_score"), (int, float)) and rep["overall_score"] > 0:
                score = float(rep["overall_score"])
            elif isinstance(rep, dict) and rep.get("dimensions"):
                dims = [float(d["score"]) for d in rep["dimensions"] if isinstance(d, dict) and isinstance(d.get("score"), (int, float))]
                score = round(sum(dims) / len(dims), 2) if dims else None

        if user_id:
            store.mark_case_solved(
                user_id,
                session.case.id,
                session.id,
                score=score,
            )

        return {
            "attempt": session.candidate_view(),
            "evaluation": evaluation_payload,
            "scorecard": session.scorecard(),
            "debrief_url": f"/attempts/{session.id}/debrief",
            "evaluation_url": f"/api/attempts/{session.id}/evaluation",
        }

