"""Measure what a spoken turn actually costs, per model.

The number that matters for push-to-talk is not total latency, it is **time to
first speakable sentence**: the browser hands each completed clause to speech
synthesis, so audio starts as soon as one sentence exists. A model that reasons
silently and then emits its whole answer in one delta is unusable here however
fast its total is, because nothing can be spoken until the end.

Run this before changing VOICE_OPENROUTER_MODEL:

    uv run python scripts/bench_turn.py
    uv run python scripts/bench_turn.py --models openai/gpt-4o-mini,x-ai/grok-4-fast
    uv run python scripts/bench_turn.py --runs 3
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import app.main as main  # noqa: E402  (env must load first)
from app.case_runtime import InterviewSession  # noqa: E402
from app.spoken_interviewer import SpokenInterviewer, sentence_chunks  # noqa: E402


CANDIDATE_TURN = "What has happened to the cost per route recently?"

DEFAULT_MODELS = [
    "google/gemini-3.7-flash",
    "anthropic/claude-sonnet-4.6",
    "google/gemini-2.5-flash",
    "openai/gpt-4o-mini",
]


def one_run(model: str) -> dict[str, object]:
    """Time a single fused turn, reporting the streaming shape as well as totals."""
    from uuid import uuid4

    session = InterviewSession(
        id=str(uuid4()), case=main.CATALOGUE.default_case, mode="realistic"
    )
    session.case_started = True
    session.add_interviewer_turn("Welcome. When you are ready, tell me how you want to start.")

    interviewer = SpokenInterviewer()
    interviewer._model_name = model
    interviewer._client = interviewer._client.__class__(
        model=model,
        temperature=0.3,
        max_tokens=700,
        max_retries=1,
        reasoning={"exclude": True},
    )

    start = time.time()
    control_at = first_delta = first_sentence = None
    deltas = 0
    pending = ""
    spoken = ""
    facts: list[str] = []
    try:
        for event, payload in interviewer.respond_stream(session, CANDIDATE_TURN):
            now = time.time() - start
            if event == "control":
                control_at = now
                facts = [fact.id for fact in payload]
            elif event == "delta":
                deltas += 1
                if first_delta is None:
                    first_delta = now
                pending += payload
                spoken += payload
                chunks, pending = sentence_chunks(pending)
                if chunks and first_sentence is None:
                    first_sentence = now
    except Exception as error:
        return {"model": model, "error": f"{type(error).__name__}: {error}"[:70]}

    # A single delta means the model buffered its whole answer: there was never
    # an early sentence to speak, so first_sentence flatters it.
    return {
        "model": model,
        "control_s": control_at,
        "first_delta_s": first_delta,
        "first_sentence_s": first_sentence or (time.time() - start),
        "total_s": time.time() - start,
        "deltas": deltas,
        "facts": facts,
        "words": len(spoken.split()),
        "reply": spoken.strip(),
    }


def main_cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    # ~0.15s covers the warm synthesis socket returning its first audio chunk.
    tts = 0.15
    print(f"\nFused spoken turn, {args.runs} run(s) per model. TTS first byte assumed {tts}s.\n")
    header = (
        f"{'model':<30}{'1st sentence':>14}{'+audio':>9}{'total':>8}"
        f"{'deltas':>8}{'lead':>7}  head start"
    )
    print(header)
    print("-" * len(header))

    for model in models:
        samples = [one_run(model) for _ in range(args.runs)]
        failed = [s for s in samples if s.get("error")]
        if failed:
            print(f"{model:<30}{'—':>14}{'—':>9}{'—':>8}{'—':>8}{'—':>7}  {failed[0]['error']}")
            continue
        med = lambda key: statistics.median(float(s[key]) for s in samples)  # noqa: E731
        deltas = statistics.median(int(s["deltas"]) for s in samples)
        # How much of the reply is still being written once audio has begun.
        # Leo answers in one or two short sentences by design, so this is small
        # even on a well-streaming model: the fused single call, not sentence
        # streaming, is what carries the latency win at this reply length.
        lead = med("total_s") - med("first_sentence_s")
        print(
            f"{model:<30}{med('first_sentence_s'):>13.2f}s"
            f"{med('first_sentence_s') + tts:>8.2f}s"
            f"{med('total_s'):>7.2f}s{deltas:>8.0f}{lead:>6.2f}s"
            f"  {'overlapped' if lead > 0.25 else 'negligible'}"
        )

    print("\nSample replies\n" + "-" * 14)
    for model in models:
        sample = one_run(model)
        if sample.get("error"):
            continue
        print(f"{model}\n  facts={sample['facts']}  words={sample['words']}")
        print(f"  {sample['reply'][:160]}\n")


if __name__ == "__main__":
    main_cli()
