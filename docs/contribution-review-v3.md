# Case contribution and admin review, version 3

Implemented locally on 2026-09-09. This supersedes the 70% early-submission and optional Improve fidelity behavior described in the earlier answer-audit plan.

## Interview behavior

All 19 fields receive their own discussion, even when an overview already supplies their values. After a substantive answer, Leo asks for more detail about the active field. The discussion closes only when the contributor explicitly says they have nothing more, cannot recall, the field is not applicable, or they prefer not to share. The Improve fidelity button and endpoint have been removed.

The typed LangChain Answer Assessor captures every supported field in each reply, including tangential competitor information and multiple plausible wrong paths. Exact evidence quotes must occur in the latest contributor answer. Values, partial assessments, corrections, conflicts, and provenance are saved before the server selects the next question. The separate Question Framer receives that selection and the updated facts. A framing failure retains the accepted facts and uses a deterministic question.

The tracker distinguishes captured information from discussion progress. Each section contributes one nineteenth of review progress when explicitly closed. A rich first message can capture the core evidence while review progress remains zero. “Answer the question” does not fabricate facts or close a section. An explicit decline does not erase previously captured information. Corrections can reopen a previously closed section.

Submission requires all 19 discussions closed and credible client, situation, decision, and causal mechanism evidence. If the contributor cannot provide those core facts, the draft can be saved for later but cannot be submitted. Unsupported or conflicted fields are excluded from the synthesis input. Version 3 persistence migrates older drafts without discarding their facts, transcripts, or unsent text.

## Admin workflow

The admin overview links to /admin/contributions. Both this page and its API require an administrator account.

The queue shows contributor identity, firm, contribution time, version, and status. Opening a submission shows the 19 original sections and their evidence alongside an editable AI-generated case package. The full original conversation is available. Legacy submissions recover the original from their saved contribution session where possible; otherwise the UI explicitly says the original was not retained.

Admins can regenerate the AI draft, edit it, save a new version, approve it for the library, return it for changes, or withdraw it. Regeneration uses the original contribution rather than an already embellished draft. Every save or regeneration creates a new unpublished version; original answers and existing published/pinned versions remain intact. Revision checks reject stale edits and decisions. Approval reruns validation, compiles the case, records the reviewer and timestamp, and immediately reloads the case library. Validation errors prevent publication.

## Attribution and migration

New submissions record the account owner, account name, UTC contribution timestamp, consulting firm, and canonical firm tags including Bain, BCG, and McKinsey. Contributors can opt into public name credit. Admins retain owner visibility; the public library otherwise says “Community contributor.” Public library responses do not expose contributor IDs, email, or the private original transcript.

All 69 authored case manifests now contain the metadata fields. Missing historical identities, firms, and contribution dates remain explicitly not recorded. Stored submissions recover account names and the earliest stored case-version timestamp. Existing public-attribution preferences are preserved; older records do not acquire public-name consent retroactively. The idempotent database backfill runs at app startup. scripts/backfill_case_metadata.py also updates manifests and stored records when run directly.

## Verification

- Full regression suite: 453 passed, 1 expected failure. The remaining warning concerns the existing FastAPI/httpx test-client deprecation.
- Engine and authenticated API simulations cover rich first messages, all 19 field discussions, competitor accumulation, two wrong paths, explicit declines, misclassified declines, corrections, conflicts, evidence-quote validation, failed provider calls, ownership, migration, and state reload after each turn.
- Admin tests cover access control, original sections, validation failures, new draft versions, stale revisions, approval and immediate library visibility, withdrawal, public-name consent, private metadata, and legacy backfill.
- The real configured provider passed the 22-turn replay in scripts/eval_contribution.py; [the saved trace](evals/contribution-live-replay-v3.json) records its results. Early core capture did not unlock submission; only the nineteenth explicit section closure did. The older six-turn replay is historical and tests the superseded behavior.
- Browser QA used an isolated temporary database and scripted provider responses: rich overview capture, blocked early submission, explicit-decline progress, save/resume, 19 original review sections, AI regeneration, draft editing, approval, version history, and the published case with contributor/firm/date in library search. Contributor and admin pages fit a 375 px viewport without horizontal page overflow.
- JavaScript syntax checks and git diff --check passed.

Extraction and framing still involve model judgment; a successful replay is not a guarantee of perfect semantic extraction. Browser AI regeneration used a stub, while intake evaluation used the live provider. Changes are local; no push or deployment was performed.
