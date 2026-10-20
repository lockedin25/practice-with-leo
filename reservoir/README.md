# Case data reservoir

This directory is the private, versioned source of truth for a playable CaseCall
case. It is deliberately separate from the conversational runtime: the runtime
may retrieve and speak from a reservoir, but it may not change the reservoir
during a live interview.

Each case is split by subject area so an interviewer can answer a broad business
question without having to expose a later exhibit or the diagnosis. The files
are designed for both human review and future compilation into a retrieval
index.

## V1 rules

- Meridian Cold Chain is the only playable reservoir.
- The supplied case diagnosis is immutable.
- Augmentation fills missing qualitative context only. It does not add live
  facts, new numbers, a competing root cause, or a shortcut to the answer.
- Candidate-visible information is controlled by `release_level`, not by a
  hard-coded dialogue script.
- The hidden issue tree is private during the interview and visible only in the
  post-case debrief.

## Files

| File | Purpose |
|---|---|
| `case.yaml` | Identity, opening context, and objective function. |
| `facts.yaml` | Atomic company, customer, market, commercial, and operating facts. |
| `issue-tree.yaml` | Canonical causal map and acceptable routes through the case. |
| `conversation-policy.yaml` | Retrieval, disclosure, challenge, and redirection policy for a realistic interviewer. |
| `validation.md` | The consistency contract the compiler must enforce before this reservoir is playable. |

`provenance` is an internal integrity field. It is not candidate-facing and
does not need to be surfaced in a future author interface.
