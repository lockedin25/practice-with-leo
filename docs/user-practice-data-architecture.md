# User Practice Data Architecture

Leo stores a candidate's practice history in one SQLite database. The design
keeps the runtime's durable attempt state as the source of truth instead of
creating competing transcript copies.

```text
users (one person)
  └── attempts (one practiced case, user_id scoped)
        ├── session_json (canonical transcript, runtime stage, disclosed facts)
        ├── attempt_owners (compatibility ownership link for existing auth)
        ├── evaluations (versioned feedback reports)
        └── voice_sessions (optional provider transport metadata)
```

## Tables and responsibility

| Table | Key columns | Responsibility |
|---|---|---|
| `users` | `id`, Google identity, profile fields | Identity and sign-in metadata. |
| `attempts` | `id`, `user_id`, `case_id`, `session_json`, `created_at`, `updated_at` | Canonical record of every case a person practises. `session_json` contains the transcript, mode, stage, disclosed facts, completion state, and idempotency ledger. |
| `attempt_owners` | `attempt_id`, `user_id` | Existing compatibility ownership relation. It remains enforced by authorization while `attempts.user_id` is the query-optimized practice-history link. |
| `evaluations` | `attempt_id`, `evaluator_version`, `report_json`, `created_at` | Immutable, versioned performance feedback. Re-evaluation adds a row rather than overwriting previous feedback. |
| `voice_sessions` | `attempt_id`, provider conversation ID, status | Operational voice metadata only. It contains neither audio nor a duplicate provider transcript. |

## Lifecycle

1. On creating an attempt, Leo persists `attempts.user_id` and the legacy
   ownership row together.
2. Every chat or voice turn updates the same `attempts.session_json`, so the
   transcript is durable across browser reloads and service restarts.
3. Ending an attempt writes an `evaluations` report when the evaluator is
   available. The raw report includes dimension-level evidence and improvement
   actions.
4. Existing databases are migrated in place: historical `attempt_owners` rows
   backfill the new `attempts.user_id` column at startup.

## Candidate APIs

- `GET /api/me/practice-history` returns the signed-in candidate's case list,
  completion status, stage reached, latest-feedback availability, and an
  aggregate performance score.
- `GET /api/me/practice-history/{attempt_id}` returns that candidate's full
  transcript and the latest plus historical feedback versions.

Both routes derive the user from the authenticated cookie. They never accept a
candidate-supplied user ID, so one person cannot retrieve another person's
practice history.

## Retention and evolution

The current single-instance SQLite layout is appropriate for local and beta
deployments. At multi-instance scale, migrate these tables unchanged to
PostgreSQL, move `session_json` and `report_json` to JSONB, retain the
`attempts(user_id, updated_at)` index, and add a foreign key from `attempts`
and `evaluations` to their parent records. Do not split transcript storage by
transport: chat and voice must remain one chronological record for reliable
feedback and replay.
