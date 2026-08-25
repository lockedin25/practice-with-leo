"""Completion budget policy for every OpenRouter call in the application.

A reasoning-capable provider spends part of each completion budget on private
reasoning before it emits any visible text, and that share grows with the
transcript. Live probes against google/gemini-3.7-flash on a mid-case
interviewer turn measured 230 to 700 reasoning tokens. Under the previous
512-token cap the provider returned finish_reason="length" on every call, the
visible reply was cut mid-clause, the fact-delivery audit correctly rejected
the fragment, and the candidate's turn surfaced as a 503.

Response length belongs to the prompts, which already ask for one or two short
sentences. Every cap here therefore leaves generous room for reasoning plus a
complete answer rather than trying to shape the answer with the budget.
"""

from __future__ import annotations

# Roughly five times the largest reasoning burn measured on a mid-case turn,
# so a longer transcript reasoning further still has room for its answer.
COMPLETION_TOKENS = 4096

# One escalation for the rare completion whose reasoning still fills the
# budget, so a knowable truncation costs a regeneration and not the turn.
TRUNCATED_RETRY_TOKENS = 8192

# The evaluator writes a long structured report rather than one short turn.
REPORT_COMPLETION_TOKENS = 8192


def was_truncated(message: object) -> bool:
    """True when the provider stopped because the completion budget ran out."""
    metadata = getattr(message, "response_metadata", None) or {}
    return metadata.get("finish_reason") == "length"


def message_text(message: object) -> str:
    """Read visible text from a provider message, or pass a plain reply through."""
    content = getattr(message, "content", message)
    return content if isinstance(content, str) else str(content)
