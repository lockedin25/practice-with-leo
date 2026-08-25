# Project: MBB Case Prep V2 — 10x Debrief Report Engine & Multi-School Corpus

## Architecture
MBB Case Prep V2 is a full-stack, AI-powered consulting interview simulator and debrief platform.
- **Corpus & Reservoir Layer** (`reservoir/`, `corpus/`, `knowledge_base/`): Authoritative case packages with verified facts, objective functions, private causal issue trees (`issue-tree.yaml`), structured `case_essence` (mechanism, pivotal insight, traps, takeaways, knowledge base links), and multi-school case catalog (IIM Ahmedabad, IIM Bangalore, IIM Calcutta, ISB).
- **Evaluation Engine Layer** (`app/evaluator.py`, `evaluation/`): BCG-calibrated 1.0–5.0 scoring scale across 5 core consulting dimensions (`structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`), generating rich report payloads (Executive Summary, What Case Really Wanted to Test, Golden MBB Rewrites for Opening and Closing, Verbatim Strengths, Prioritized Development Areas, Targeted 2-minute Drills, Clickable Readings).
- **Backend & Persistence Layer** (`app/store.py`, `app/main.py`, `app/attempt_service.py`): SQLite persistence for rich evaluation reports, automated generation on attempt completion, enhanced profile metrics (1-5 scale trends, repeated development areas, debrief links), and evaluation endpoints.
- **Frontend Presentation Layer** (`app/static/debrief.html`, `app/static/debrief.css`, `app/static/debrief.js`): Interactive 10x Debrief web UI featuring 7 masterclass cards, responsive design, and full integration with design system tokens and light/dark theme switching.

## Code Layout
```
MBB Case Prep V2/
├── app/
│   ├── attempt_service.py       # Attempt lifecycle and evaluation triggering
│   ├── case_loader.py           # Case package parsing and essence schema loading
│   ├── evaluator.py             # BCG 1-5 Evaluator Agent Engine & Pydantic models
│   ├── main.py                  # FastAPI application routes & API endpoints
│   ├── models.py                # Core domain schemas and CaseMetadata
│   ├── store.py                 # SQLite database storage & EvaluationStore
│   └── static/
│       ├── debrief.html         # 10x Debrief Web Interface template
│       ├── debrief.css          # Debrief styling, cards, responsive layout
│       ├── debrief.js           # Debrief controller, API fetch, interactive UI
│       ├── tokens.css           # Design tokens (colors, typography, spacing)
│       └── theme.js             # Theme switcher (light/dark mode)
├── reservoir/                   # Active simulation case packages (5-file standard)
├── corpus/                      # Multi-school casebook library (IIMA, IIMB, IIMC, ISB)
├── knowledge_base/              # Industry playbooks, case archetypes, methodology
├── evaluation/                  # Evaluator prompts, BCG rubrics, and few-shot exemplars
└── tests/                       # Unit, integration, and E2E test suites
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Case Essence Schema | Add `case_essence` (core_mechanism, what_the_case_wanted_to_test, pivotal_insight, common_traps, takeaway_lesson, suggested_readings) to case schema & loader | M1 | ORIGINAL_REQUEST §R1.1 |
| 2 | Reservoir 12-Case Enrichment | Enrich all 12 reservoir cases with full 5-file packages (`case_essence`, `issue-tree.yaml`, `facts.yaml` with hidden diagnosis, `conversation-policy.yaml`, `validation.md`) | M1 | ORIGINAL_REQUEST §R1.1, R1.2 |
| 3 | Multi-School Case Corpus Expansion | Curate and ingest ~50-60 structured cases across IIM-A, IIM-B, IIM-C, and ISB with essence metadata and issue trees | M1 | ORIGINAL_REQUEST §R1.1, R1.2 |
| 4 | Knowledge Base Linkages | Link case essence to `knowledge_base/industries/` and `knowledge_base/methodology/` modules | M1 | ORIGINAL_REQUEST §R1.1 |
| 5 | BCG 1.0–5.0 5-Dimension Rubric | Define 1.0–5.0 scoring scale across structuring, problem_solving, quantitative, synthesis, communication | M2 | ORIGINAL_REQUEST §R2.1 |
| 6 | Rich Evaluator Pydantic Schema | Update `EvaluationReport` with executive_summary, what_the_case_wanted_to_test, golden_rewrites, strengths, areas_for_development, targeted_drill, suggested_readings | M2 | ORIGINAL_REQUEST §R2.2 |
| 7 | Evaluator Engine Prompt & Fallback | Implement BCG-calibrated LLM prompt with few-shot exemplars and deterministic fallback evaluator | M2 | ORIGINAL_REQUEST §R2.1, R2.2 |
| 8 | Database Persistence | Persist full rich `EvaluationReport` JSON in SQLite `evaluations` table linked to `attempt_id` | M3 | ORIGINAL_REQUEST §R3.1 |
| 9 | Attempt Lifecycle Auto-Trigger | Trigger report generation and storage upon attempt completion in `attempt_service.py` | M3 | ORIGINAL_REQUEST §R3.2 |
| 10 | Profile & Attempt API Endpoints | Update `/api/profile`, `/api/attempts/{id}`, and `/api/attempts/{id}/evaluation` for 1-5 scale scores, history, and rich reports | M3 | ORIGINAL_REQUEST §R3.3, R3.4 |
| 11 | Executive Header Card | Render overall score out of 5.0, MBB rating badge (Strong Pass / Meets Bar / etc.), 2-sentence executive summary | M4 | ORIGINAL_REQUEST §R4.1 |
| 12 | What Case Wanted to Test Card | Render core business mechanism, pivotal insight, and candidate comparison | M4 | ORIGINAL_REQUEST §R4.2 |
| 13 | 5 Core Dimension Cards | Render 1-5 score bars, band labels, verbatim evidence blockquotes, and observation notes | M4 | ORIGINAL_REQUEST §R4.3 |
| 14 | Golden MBB Rewrites Card | Render side-by-side comparison for Opening and Closing (Candidate Turn vs Top 1% MBB Partner Turn) with diagnostic notes | M4 | ORIGINAL_REQUEST §R4.4 |
| 15 | Strengths & Development Split-Card | Render verbatim strengths and prioritized development areas with actionable guidance | M4 | ORIGINAL_REQUEST §R4.5 |
| 16 | Action Plan & Suggested Readings | Render 2-minute drill card and clickable links to knowledge base files | M4 | ORIGINAL_REQUEST §R4.6 |
| 17 | Observed Behaviors Checklist | Interactive checklist of demonstrated vs missed behavioral markers | M4 | ORIGINAL_REQUEST §R4.7 |
| 18 | E2E Test Suite (Tiers 1-4) | Comprehensive opaque-box test suite validating all R1-R4 requirements | Final | ORIGINAL_REQUEST §Acceptance Criteria |
| 19 | Adversarial Hardening (Tier 5) | White-box stress tests, boundary conditions, malformed input resilience | Final | Project Pattern Phase 2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Test infra, harness, Tiers 1-4 opaque-box test suite, `TEST_READY.md` | none | IN_PROGRESS |
| M1 | Case Corpus Expansion & Essence Enrichment | R1: `reservoir/`, `corpus/`, `knowledge_base/`, case models/loaders | none | IN_PROGRESS |
| M2 | BCG-Calibrated 1–5 Evaluator Engine | R2: `app/evaluator.py`, `evaluation/`, prompts, rubrics, models | none | IN_PROGRESS |
| M3 | Backend DB Persistence & Profile Linking | R3: `app/store.py`, `app/main.py`, `app/attempt_service.py` | M2 | PLANNED |
| M4 | Interactive 10x Debrief Web Interface | R4: `app/static/debrief.html`, `.css`, `.js` | M2, M3 | PLANNED |
| Final | Final Milestone: 100% E2E Pass & Adversarial Hardening | Pass 100% E2E tests, Tier 5 adversarial tests, auditor verification | E2E, M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### Evaluator ↔ Backend Store (`app/evaluator.py` ↔ `app/store.py`)
- `EvaluationReport`:
  - `overall_score`: float (1.0–5.0)
  - `mbb_rating_badge`: str ("Distinction" | "Strong Pass" | "Meets Bar" | "Developing" | "Needs Substantial Practice")
  - `executive_summary`: str (2-sentence partner assessment)
  - `what_the_case_wanted_to_test`: `WhatCaseWantedToTestPayload` (core_mechanism, pivotal_insight, candidate_performance_summary)
  - `dimension_scores`: Dict[str, `DimensionScorePayload`] (`structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication` with score 1.0–5.0, band, evidence, notes)
  - `golden_rewrites`: List[`GoldenRewritePayload`] (stage: opening | closing, candidate_turn, mbb_partner_turn, diagnostic_notes)
  - `strengths`: List[`StrengthItem`] (claim, verbatim_quote, impact)
  - `areas_for_development`: List[`DevelopmentAreaItem`] (gap, priority, corrective_guidance)
  - `targeted_drill`: `TargetedDrillPayload` (title, duration_seconds, prompt, focus_area)
  - `suggested_readings`: List[`SuggestedReadingPayload`] (title, path, why_relevant)
  - `observed_behaviors`: List[`ObservedBehaviorItem`] (marker_id, description, status: demonstrated | missed | partial, evidence)

### Case Loader ↔ Evaluator (`app/case_loader.py` ↔ `app/evaluator.py`)
- `CasePackage.essence`: `CaseEssenceModel` containing `core_mechanism`, `what_the_case_wanted_to_test`, `pivotal_insight`, `common_traps`, `takeaway_lesson`, `suggested_readings`.
- Evaluator injects `case_essence` into the evaluation prompt context to calibrate candidate evaluation against what the case wanted to test.

### Backend ↔ Frontend API (`/api/attempts/{id}/evaluation`)
- Returns JSON serialization of `EvaluationReport`.
- Status 200 with full payload when ready.
