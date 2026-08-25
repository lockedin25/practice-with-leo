# Architectural Survey Report: Evaluator Engine, Rubrics & Backend Store

**Surveyor**: Explorer 2 (Evaluator Engine & Backend Store)  
**Date**: 2026-08-24  
**Project**: MBB Case Prep V2 (Leo)  
**Scope**: Evaluator Agent Architecture, BCG 1–5 Scoring Rubric, Evaluation Prompts & Schemas, Backend Database Persistence (SQLite), Attempt Lifecycle Hooks, Profile & Debrief APIs, and Test Infrastructure.

---

## 1. Executive Summary

This survey provides a complete architectural analysis of the evaluation subsystem, prompt engineering, data persistence, and API integration in MBB Case Prep V2.

Key findings:
1. **Scoring Scale & Dimension Discrepancy**: 
   - The current evaluator (`app/evaluator.py` & `evaluation/rubric.yaml`) uses a **0–10 scoring scale** across **4 dimensions** (`structuring`, `problem_solving`, `communication`, `quantitative`) and 4 performance bands (`Developing`, `Solid`, `Strong`, `Exceptional`).
   - The system must be upgraded to the **BCG-calibrated 1.0–5.0 scale** across **5 core consulting dimensions** (`structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`), aligning with `knowledge_base/evaluation_engine/detection_rubrics.yaml` and `ORIGINAL_REQUEST.md` (R2).
2. **Evaluation Report Payload Expansion**:
   - The current `EvaluationReport` Pydantic model (`app/evaluator.py:75-83`) only carries `dimensions`, `checklist`, `headline_strengths`, `priority_improvements`, `next_drill`, and `evaluator_version`.
   - The 10x Debrief Report specification requires a rich payload containing: `executive_summary`, `what_the_case_wanted_to_test`, `golden_rewrites` (Opening vs Top 1% MBB & Closing vs Top 1% MBB), `strengths`, `areas_for_development`, `targeted_drill`, `suggested_readings`, and calibrated `overall_score`.
3. **Storage & Persistence Architecture**:
   - `EvaluationStore` (`app/store.py:451-509`) persists reports in SQLite (`data/casecall.db`) in table `evaluations(attempt_id, evaluator_version, report_json, created_at)`.
   - Because reports are serialized as JSON in `report_json`, extending the `EvaluationReport` payload requires **zero destructive SQL schema migrations** to the `evaluations` table.
   - `SessionStore` (`app/store.py:34-450`) manages `attempts`, `user_case_progress`, and `voice_sessions`. Score aggregation functions (`_feedback_score`, `_report_score`, `_mean_feedback_score`) must be calibrated for 1.0–5.0.
4. **Lifecycle Trigger & Hooks**:
   - `POST /api/attempts/{attempt_id}/end` in `app/main.py:251-275` immediately triggers `_evaluate_and_store(session)` and updates `user_case_progress.best_score`.
   - `GET /api/attempts/{attempt_id}/evaluation` in `app/main.py:317-333` provides lazy fallback evaluation for ended attempts without existing reports.
5. **Test Infrastructure**:
   - Current test suite (`pytest tests/`) executes **101 tests, all currently passing**.
   - `tests/test_evaluator.py` contains 20 deterministic tests with fake LLM chains (`FakeWriter`, `FakeComparator`, `StubEvaluator`).

---

## 2. Evaluation Engine Deep-Dive (`app/evaluator.py` & `evaluation/`)

### 2.1 Current Architecture & Pipeline
The evaluator operates as a post-attempt offline service with a two-phase LLM pipeline plus deterministic boundary validation:

```
[InterviewSession (Ended)]
          │
          ▼
   1. AttemptContext Builder (app/evaluator.py:289-308)
      ├── Disclosed Facts, Case Metadata, Checklist Items
      └── Issue Tree + Private Comparator Callable
          │
          ▼
   2. LangChain Planner Agent (app/evaluator.py:506-545)
      ├── System Prompt: evaluation/prompts/planner_system.md
      ├── Read-only Tools: read_messages, get_released_facts, get_case_context,
      │                    get_checklist, compare_to_answer_key, verify_citation
      └── Gathers verbatim transcript citations & answers-key verdicts
          │
          ▼
   3. Structured Report Writer (app/evaluator.py:574-612)
      ├── System Prompt: evaluation/prompts/writer_system.md + rubric anchors
      ├── Writer LLM Chain with structured output: EvaluationReport
      └── Bounded retry loop (WRITER_RETRIES = 1)
          │
          ▼
   4. Deterministic Boundary Enforcement (app/evaluator.py:615-671)
      ├── Citation Verbatim Verification (quote_is_verbatim)
      ├── Completeness Checks (all dimensions & checklist IDs present)
      ├── Private Fact & Issue Tree Leakage Guard (find_leakage & _redact)
      ├── Automatic Em-Dash Sanitization (_strip_em_dashes)
      └── Graceful Degradation (_degrade_report / _placeholder_report)
          │
          ▼
[EvaluationReport + Version Stamp]
```

### 2.2 Current vs Required Dimensions & Scoring

| Attribute | Current Implementation (`app/evaluator.py`, `rubric.yaml`) | Required MBB Calibrated Target (`ORIGINAL_REQUEST.md`, `detection_rubrics.yaml`) |
|---|---|---|
| **Score Scale** | `0.0 – 10.0` (float) | **`1.0 – 5.0`** (BCG-calibrated float) |
| **Score Bands** | 4 bands: `Developing`, `Solid`, `Strong`, `Exceptional` | **3 MBB Rating Bands**: `Below Bar` (1.0–2.4), `Meets Bar` (2.5–3.7), `Top 1% MBB Distinction` (3.8–5.0) |
| **Dimensions Evaluated** | 4 dimensions: `structuring` (0.35), `problem_solving` (0.30), `communication` (0.20), `quantitative` (0.15) | **5 core dimensions**: `structuring` (0.25), `problem_solving` (0.25), `quantitative` (0.15), `synthesis` (0.20), `communication` (0.15) |
| **Dimension Focus** | Generic MECE and math checks | Explicit consulting craft criteria: MECE-by-construction, 80/20 hypothesis-first, mental math & "so what?", 4-part Pyramid synthesis, executive signposting |

### 2.3 Required Rich Report Data Structure (`EvaluationReport`)

To support the 10x Debrief UI and comprehensive candidate coaching, the Pydantic data contract in `app/evaluator.py` must be enriched:

```python
class Citation(BaseModel):
    message_index: int
    quote: str

class DimensionScore(BaseModel):
    name: str  # structuring, problem_solving, quantitative, synthesis, communication
    score: float  # 1.0 to 5.0
    band: str  # Below Bar, Meets Bar, Top 1% MBB
    evidence: list[Citation] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"

class WhatTheCaseWantedToTest(BaseModel):
    core_mechanism: str
    commercial_concept: str
    pivotal_insight: str
    candidate_performance_summary: str
    candidate_vs_optimal_gap: str

class GoldenRewriteTurn(BaseModel):
    phase: Literal["opening", "synthesis"]
    candidate_turn: str
    candidate_message_index: int | None = None
    golden_mbb_turn: str
    consulting_craft_delta: list[str] = Field(default_factory=list)

class SuggestedReading(BaseModel):
    title: str
    path: str
    relevance_reason: str

class ChecklistItem(BaseModel):
    id: str
    title: str
    status: Literal["demonstrated", "missed", "not_applicable"]
    evidence: list[Citation] = Field(default_factory=list)
    note: str = ""

class EvaluationReport(BaseModel):
    attempt_id: str
    evaluator_version: str = ""
    overall_score: float = 0.0  # 1.0 to 5.0
    overall_band: str = "Meets Bar"
    executive_summary: str = ""
    what_the_case_wanted_to_test: WhatTheCaseWantedToTest | None = None
    dimensions: list[DimensionScore] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    golden_rewrites: list[GoldenRewriteTurn] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    areas_for_development: list[str] = Field(default_factory=list)
    targeted_drill: str = ""
    suggested_readings: list[SuggestedReading] = Field(default_factory=list)
    
    # Backward compatibility aliases/properties:
    # headline_strengths -> strengths
    # priority_improvements -> areas_for_development
    # next_drill -> targeted_drill
```

---

## 3. Backend Database Persistence (`app/store.py`)

### 3.1 SQLite Schema & Table Definitions

The SQLite database at `data/casecall.db` currently contains 4 core tables:

1. `attempts`:
   ```sql
   CREATE TABLE attempts (
       id TEXT PRIMARY KEY,
       case_id TEXT NOT NULL,
       user_id TEXT,
       session_json TEXT NOT NULL,
       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
   );
   CREATE INDEX attempts_user_updated ON attempts(user_id, updated_at DESC);
   ```
2. `evaluations`:
   ```sql
   CREATE TABLE evaluations (
       attempt_id TEXT NOT NULL,
       evaluator_version TEXT NOT NULL,
       report_json TEXT NOT NULL,
       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY (attempt_id, evaluator_version)
   );
   ```
3. `user_case_progress`:
   ```sql
   CREATE TABLE user_case_progress (
       user_id TEXT NOT NULL,
       case_id TEXT NOT NULL,
       status TEXT NOT NULL CHECK(status IN ('not_started', 'in_progress', 'solved')),
       attempts_count INTEGER NOT NULL DEFAULT 0,
       latest_attempt_id TEXT,
       last_completed_at TEXT,
       best_score REAL,
       reset_at TEXT,
       updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY (user_id, case_id)
   );
   CREATE INDEX user_case_progress_user_updated ON user_case_progress(user_id, updated_at DESC);
   ```
4. `voice_sessions`:
   ```sql
   CREATE TABLE voice_sessions (
       id TEXT PRIMARY KEY,
       attempt_id TEXT NOT NULL,
       provider TEXT NOT NULL,
       agent_id TEXT NOT NULL,
       provider_conversation_id TEXT NOT NULL UNIQUE,
       status TEXT NOT NULL,
       case_started INTEGER NOT NULL DEFAULT 0,
       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
   );
   ```

### 3.2 Evaluation Persistence Mechanics
- `EvaluationStore.save(report_json, attempt_id, evaluator_version)` inserts or updates rows in `evaluations`.
- `EvaluationStore.latest(attempt_id)` fetches the most recent evaluation report.
- `EvaluationStore.history(attempt_id)` returns all evaluation versions for an attempt, supporting admin re-evaluations under upgraded rubrics.
- In `SessionStore.list_user_practice(user_id, limit=100)`, a correlated subquery joins each attempt to its latest evaluation row:
  ```sql
  LEFT JOIN evaluations e ON e.rowid = (
      SELECT latest.rowid FROM evaluations latest
      WHERE latest.attempt_id = a.id
      ORDER BY latest.created_at DESC, latest.rowid DESC
      LIMIT 1
  )
  ```
- No SQL table alterations are required for `evaluations`, as `report_json` encapsulates all new rich fields in valid JSON.

---

## 4. API Endpoints & Request Flow

### 4.1 Attempt Lifecycle & Evaluation Trigger

1. **Attempt Completion (`POST /api/attempts/{attempt_id}/end`)** in `app/main.py:251-275`:
   - Validates ownership via `_session(attempt_id, user)`.
   - Sets `session.ended = True` and calls `STORE.save(session)`.
   - Calls `_evaluate_and_store(session)`:
     - Evaluator executes `evaluate(session)`.
     - Calculates deterministic weighted overall score.
     - Saves to `EVALUATIONS.save(report.model_dump_json(), session.id, report.evaluator_version)`.
   - Calls `STORE.mark_case_solved(user.id, session.case.id, session.id, score=_report_score(report))`.
   - Returns `{ "attempt": ..., "evaluation": payload, "scorecard": ... }`.

2. **Debrief Evaluation Retrieval (`GET /api/attempts/{attempt_id}/evaluation`)** in `app/main.py:317-333`:
   - Checks `session.ended` (returns HTTP 409 if active).
   - Fetches `EVALUATIONS.latest(attempt_id)`.
   - If not yet evaluated, runs lazy evaluation via `_evaluate_and_store(session)`.
   - Returns `{ "evaluator_version": ..., "report": <EvaluationReport JSON>, "created_at": ..., "overall": ... }`.

3. **User Profile (`GET /api/me/profile`)** in `app/main.py:384-440`:
   - Aggregates over all completed and evaluated attempts for `user.id`.
   - Computes:
     - `summary`: attempts, completed, in_progress, candidate_turns, feedback_available, average_feedback_score.
     - `performance`: average scores across each dimension (5 dimensions on 1.0–5.0 scale).
     - `development_areas`: top 3 repeated improvement gaps with occurrence counts.
     - `strengths`: top 3 repeated strengths with occurrence counts.
     - `recent_attempts`: list of recent attempts with scores and timestamps.

4. **Practice History (`GET /api/me/practice-history` & `GET /api/me/practice-history/{attempt_id}`)**:
   - `practice_history` returns user-scoped summary and list of attempts.
   - `practice_history_detail` returns full transcript, latest feedback report, and versioned feedback history.

5. **Admin Re-evaluation (`POST /api/admin/attempts/{attempt_id}/evaluate`)** in `app/admin.py:319-350`:
   - Allows administrators to re-evaluate an ended attempt under the latest prompt/rubric without overwriting previous evaluation rows.

---

## 5. Existing Test Infrastructure & Coverage Analysis

Running the test suite via `.venv/bin/pytest` confirmed:
- **101 tests collected, 101 passed** in ~1.06s.

### Test Breakdown by Subsystem:

| Test File | Test Count | Scope & Focus |
|---|---|---|
| `tests/test_evaluator.py` | 20 | Planner tool boundaries, transcript window clamping, citation verbatim verification, private fact & issue tree leakage guards, completeness validation, deterministic weighted overall calculation, degradation/placeholder handling, em-dash sanitization, and API debrief integration. |
| `tests/test_store.py` | 1 | `SessionStore` persistence and retrieval across fresh instances. |
| `tests/test_practice_history.py` | 4 | User-scoped practice history isolation, unauthorized access blocks, profile progress derivation (strengths/development areas), and profile auth gate. |
| `tests/test_api.py` | 10 | Public catalogue, attempt creation, candidate turns, turn idempotency, and fact disclosure. |
| `tests/test_admin.py` | 14 | Admin authentication, overview metrics, transcript access, and versioned re-evaluation. |
| `tests/test_auth.py` | 24 | Google OAuth flow, HMAC session cookie signing/unsigning, TTL enforcement, and domain allowlists. |
| `tests/test_case_progress.py` | 2 | Voice onboarding readiness gate, case progress tracking (`in_progress` -> `solved`), and case progress resets. |
| `tests/test_case_library.py` | 3 | Case package parsing, unique IDs, and catalogue compilation. |
| `tests/test_knowledge_base.py` | 6 | Knowledge base markdown parsing, metadata indexing, and file availability. |
| `tests/test_voice.py` | 17 | ElevenLabs provider integration, WebRTC session tokens, custom LLM streaming, and webhook signature verification. |

### Key Test Fixtures & Doubles:
- `conftest.py`:
  - `pytest_configure` sets up an isolated temporary SQLite database for each test run (`tempfile.mkdtemp`), preventing pollution of `data/casecall.db`.
  - `sign_in(client, email)` provides authenticated session cookies for tests.
  - `candidate_client` and `admin_client` fixtures supply pre-authenticated test clients.
  - `stub_interviewer` replaces LLM interviewer with deterministic responses.
- `tests/test_evaluator.py`:
  - `StubEvaluator`, `FakeWriter`, `FakeComparator` allow testing all deterministic evaluator rules, leak guards, and API endpoints without calling external LLM providers.

---

## 6. Implementation Gap Analysis & Required Modifications

To fulfill the requirements of R2 (BCG 1-5 Evaluator Engine), R3 (Backend Persistence & Profile Linking), and R4 (Debrief UI Backend Integration), the following changes are required:

### 1. `app/evaluator.py`:
- Update `DIMENSION_NAMES`: `("structuring", "problem_solving", "quantitative", "synthesis", "communication")`.
- Update `BAND_NAMES`: `("Below Bar", "Meets Bar", "Top 1% MBB")`.
- Update `DimensionScore`: scores calibrated from 1.0 to 5.0.
- Update `EvaluationReport` model with rich payload fields:
  - `overall_score: float` (1.0–5.0)
  - `overall_band: str`
  - `executive_summary: str`
  - `what_the_case_wanted_to_test: WhatTheCaseWantedToTest`
  - `golden_rewrites: list[GoldenRewriteTurn]`
  - `strengths: list[str]`
  - `areas_for_development: list[str]`
  - `targeted_drill: str`
  - `suggested_readings: list[SuggestedReading]`
- Ensure backward-compatible properties for existing consumers (`headline_strengths`, `priority_improvements`, `next_drill`).
- Update `AttemptContext` and `build_tools` to pass `case_essence` (from case package) to evaluator tools (`get_case_context`).
- Update `completeness_violations` and `_degrade_report` to validate 5 dimensions and the new fields.
- Update `weighted_overall` to use 5 BCG dimensions and 1.0–5.0 scale.

### 2. `evaluation/rubric.yaml` & `evaluation/checklist.yaml`:
- Calibrate `evaluation/rubric.yaml` for the 5 BCG dimensions on the 1.0–5.0 scale.
- Update dimension weights: structuring (0.25), problem_solving (0.25), quantitative (0.15), synthesis (0.20), communication (0.15).
- Ensure anchors define observable behaviors for Below Bar (1.0–2.4), Meets Bar (2.5–3.7), and Top 1% MBB (3.8–5.0).
- Update checklist items to align with detection markers in `knowledge_base/evaluation_engine/detection_rubrics.yaml`.

### 3. `evaluation/prompts/`:
- `writer_system.md`: Instruct the LLM writer to score on 1.0–5.0 scale across 5 dimensions, formulate the executive summary, compare against what the case wanted to test, generate Opening and Closing Golden Rewrites, cite verbatim strengths, provide targeted drills, and link suggested readings from `knowledge_base/`.
- `planner_system.md`: Update investigation guidance to look for synthesis and communication markers.

### 4. `app/main.py`:
- Update `_report_score`, `_feedback_score`, and `_mean_feedback_score` to handle 1.0–5.0 scores.
- Update `profile` endpoint (`GET /api/me/profile`) to aggregate the 5 BCG dimensions and return rich development areas and strengths.
- Ensure `GET /api/attempts/{attempt_id}/evaluation` returns the full rich report payload.

### 5. `tests/`:
- Update `tests/test_evaluator.py`, `tests/test_practice_history.py`, and `tests/test_admin.py` to reflect 5 dimensions (`structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`) and the 1.0–5.0 score scale.
- Add test coverage verifying the generation, validation, and retrieval of `what_the_case_wanted_to_test`, `golden_rewrites`, `targeted_drill`, and `suggested_readings`.
