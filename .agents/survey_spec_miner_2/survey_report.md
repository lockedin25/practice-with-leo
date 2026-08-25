# Specification Survey Report: Evaluator Models, Schemas & API Endpoints

**Target Systems Investigated:**
- `app/evaluator.py` (Evaluation engine, Pydantic models, Fallback heuristic generator, boundary guards)
- `app/main.py` (FastAPI router, evaluation and attempt endpoints)
- `app/models.py` (Core case manifest, essence, facts, issue-tree models)
- `app/store.py` (SQLite persistence for sessions, attempts, evaluations)
- `app/case_runtime.py` (Runtime session and case world state)
- `evaluation/rubric.yaml` (BCG 1.0–5.0 rubric definition and dimension weights)
- `evaluation/checklist.yaml` (Observed behaviors catalog and detection rules)
- `tests/test_evaluator_v2.py`, `tests/test_evaluator.py`, `tests/test_debrief_ui.py`, `tests/test_api.py`

---

## 1. Executive Summary of Backend Evaluator Architecture

The backend evaluator is an independent post-attempt service operating on a **BCG-calibrated 1.0–5.0 scale** across 5 core consulting dimensions (`structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`).

When an attempt completes (`POST /api/attempts/{id}/end` or on demand via `GET /api/attempts/{id}/evaluation`), the evaluator produces an `EvaluationReport` comprising 7 masterclass evaluation sections:
1. **Executive Summary & Overall BCG Rating** (1.0–5.0 overall score, MBB Rating Badge, Rubric Band, Executive Summary)
2. **"What The Case Wanted to Test" (Masterclass Reveal)** (Core economic mechanism, commercial concept, pivotal insight, candidate performance summary, candidate vs optimal gap)
3. **5 Core Dimension Breakdown** (Score 1.0–5.0, band, verbatim evidence citations with message indexes, observations, improvements, confidence level)
4. **Golden MBB Rewrites** (Opening and closing/synthesis turns comparing candidate verbatim vs top 1% MBB partner delivery with diagnostic notes)
5. **Headline Strengths** (Strengths with claims, quotes, and impact notes)
6. **Areas for Development / Priority Improvements** (Gaps, priorities [high/medium/low], and corrective guidance)
7. **Action Plan / Targeted Drills & Suggested Readings** (Targeted drill prompt/duration/focus area, plus curated methodology and industry readings)
8. **Observed Behaviors Checklist** (Stable behavioral markers with demonstrated/missed/not_applicable status and verbatim citations)

---

## 2. Exact Pydantic Schemas & Field Definitions

### 2.1 `Citation`
```python
class Citation(BaseModel):
    message_index: int = Field(description="Index into the attempt transcript.")
    quote: str = Field(description="Short verbatim excerpt from that message.")
```
- `message_index` (`int`): Zero-based integer index into session transcript messages (`session.messages`).
- `quote` (`str`): Verbatim excerpt string verified against transcript message content.

---

### 2.2 `DimensionScore` (and `RichDimensionScore`)
```python
class DimensionScore(BaseModel):
    name: str = Field(description="One of structuring, problem_solving, quantitative, synthesis, communication")
    score: float = Field(description="Score on BCG 1.0 to 5.0 scale")
    band: str = Field(description="Below Bar, Meets Bar, or Top 1% MBB")
    evidence: list[Citation] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    notes: str = Field(default="", description="Summary observation notes")
```
- `name` (`str`): Must be one of `DIMENSION_NAMES`:
  - `"structuring"` (weight: 0.25)
  - `"problem_solving"` (weight: 0.25)
  - `"quantitative"` (weight: 0.15)
  - `"synthesis"` (weight: 0.20)
  - `"communication"` (weight: 0.15)
- `score` (`float`): Float on 1.0–5.0 scale (e.g. `3.8`, `4.5`). Score `0.0` or `< 1.0` denotes unassessed dimension in partial runs.
- `band` (`str`): Band descriptor. Standard rubric bands: `"Below Bar"` (<2.5), `"Meets Bar"` (2.5–3.7), `"Top 1% MBB"` (≥3.8).
- `evidence` (`list[Citation]`): Default `[]`. List of citations pointing to exact turns.
- `observations` (`list[str]`): Default `[]`. Positive and descriptive observations ("What Leo saw").
- `improvements` (`list[str]`): Default `[]`. Specific corrective advice ("Do differently").
- `confidence` (`Literal["high", "medium", "low"]`): Default `"medium"`. Downgraded to `"low"` if unassessed or citations could not be verified.
- `notes` (`str`): Default `""`. Summary observation notes.

---

### 2.3 `WhatTheCaseWantedToTest` (Alias: `WhatCaseWantedToTestPayload`)
```python
class WhatTheCaseWantedToTest(BaseModel):
    core_mechanism: str = Field(default="", description="The fundamental economic/operational mechanism tested")
    commercial_concept: str = Field(default="", description="The commercial concept tested by the interviewer")
    pivotal_insight: str = Field(default="", description="The breakthrough 'Aha!' moment that unlocks the case")
    candidate_performance_summary: str = Field(default="", description="How the candidate performed against the crux")
    candidate_vs_optimal_gap: str = Field(default="", description="Gap between candidate's path and top 1% MBB path")
```
- `core_mechanism` (`str`): The underlying economic or operational breakdown (e.g. route density, mix shift, fixed cost absorption).
- `commercial_concept` (`str`): High-level commercial theme (e.g. capacity utilization economics, pricing indexation).
- `pivotal_insight` (`str`): The core "Aha!" realization required to solve the case.
- `candidate_performance_summary` (`str`): Assessment of how the candidate tackled the crux.
- `candidate_vs_optimal_gap` (`str`): Concrete contrast between candidate's path and top 1% MBB partner standard.

---

### 2.4 `GoldenRewriteTurn` (Alias: `GoldenRewritePayload`)
```python
class GoldenRewriteTurn(BaseModel):
    stage: Literal["opening", "closing", "synthesis"] = "opening"
    phase: Literal["opening", "closing", "synthesis"] = "opening"
    candidate_turn: str = Field(default="", description="Candidate turn verbatim from transcript")
    candidate_message_index: int | None = Field(default=None, description="Transcript index of candidate turn")
    mbb_partner_turn: str = Field(default="", description="How an MBB Partner / Top 1% candidate would deliver it")
    golden_mbb_turn: str = Field(default="", description="Alias for mbb_partner_turn")
    diagnostic_notes: list[str] = Field(default_factory=list, description="Specific consulting craft feedback")
    consulting_craft_delta: list[str] = Field(default_factory=list, description="Alias for diagnostic_notes")
```
- `stage` / `phase` (`Literal["opening", "closing", "synthesis"]`): Stage of the case turn. Default `"opening"`. Automatically synchronized by `_sync_fields` validator.
- `candidate_turn` (`str`): Verbatim excerpt of what candidate said. Default `""`.
- `candidate_message_index` (`int | None`): Transcript message index of candidate turn. Default `None`.
- `mbb_partner_turn` / `golden_mbb_turn` (`str`): Ideal top 1% MBB partner formulation. Automatically synchronized by `_sync_fields` validator.
- `diagnostic_notes` / `consulting_craft_delta` (`list[str]`): Craft critique points explaining why the partner delivery is superior. Automatically synchronized by `_sync_fields`.

---

### 2.5 `StrengthItem` & `DevelopmentAreaItem`
```python
class StrengthItem(BaseModel):
    claim: str
    verbatim_quote: str = ""
    impact: str = ""

class DevelopmentAreaItem(BaseModel):
    gap: str
    priority: Literal["high", "medium", "low"] = "high"
    corrective_guidance: str = ""
```
- `StrengthItem`:
  - `claim` (`str`): Headline strength.
  - `verbatim_quote` (`str`): Transcript quote supporting the strength. Default `""`.
  - `impact` (`str`): Consulting impact of demonstrating this strength. Default `""`.
- `DevelopmentAreaItem`:
  - `gap` (`str`): Identified weakness/gap.
  - `priority` (`Literal["high", "medium", "low"]`): Priority level. Default `"high"`.
  - `corrective_guidance` (`str`): Concrete guidance for improvement. Default `""`.

---

### 2.6 `TargetedDrillPayload`
```python
class TargetedDrillPayload(BaseModel):
    title: str = ""
    duration_seconds: int = 120
    prompt: str = ""
    focus_area: str = ""
```
- `title` (`str`): Drill title (e.g. `"2-Minute MECE Issue Tree Drill"`). Default `""`.
- `duration_seconds` (`int`): Target practice duration in seconds (default `120`, range 30–600).
- `prompt` (`str`): Concrete scenario or question prompt to practice. Default `""`.
- `focus_area` (`str`): Target consulting dimension or skill (e.g. `"structuring"`, `"problem_solving"`, `"quantitative"`). Default `""`.

---

### 2.7 `SuggestedReading` (Alias: `SuggestedReadingPayload`)
```python
class SuggestedReading(BaseModel):
    title: str
    path: str
    why_relevant: str = ""
    relevance_reason: str = ""
```
- `title` (`str`): Article title (e.g. `"02 Issue Tree Structuring"`).
- `path` (`str`): Relative markdown file path in repository (e.g. `"knowledge_base/methodology/02_issue_tree_structuring.md"` or `"industries/01_logistics_and_cold_chain.md"`).
- `why_relevant` / `relevance_reason` (`str`): Contextual explanation of relevance. Default `""`. Synchronized via `_sync_relevance` validator.

---

### 2.8 `ChecklistItem` (Alias: `ObservedBehaviorItem`)
```python
class ChecklistItem(BaseModel):
    id: str = ""
    marker_id: str = ""
    title: str = ""
    description: str = ""
    status: Literal["demonstrated", "missed", "partial", "not_applicable"] = "not_applicable"
    evidence: list[Citation] = Field(default_factory=list)
    note: str = ""
```
- `id` / `marker_id` (`str`): Stable identifier from `evaluation/checklist.yaml` (e.g. `"structure.restate-objective-first"`, `"structure.mece-by-construction"`, `"problem-solving.hypothesis-before-data"`). Synchronized via `_sync_ids`.
- `title` / `description` (`str`): Human-readable behavior title. Synchronized via `_sync_ids`.
- `status` (`Literal["demonstrated", "missed", "partial", "not_applicable"]`): Default `"not_applicable"`.
- `evidence` (`list[Citation]`): List of transcript citations when demonstrated. Default `[]`.
- `note` (`str`): Corrective note explaining how to demonstrate if missed, or why not applicable. Default `""`.

---

### 2.9 `EvaluationReport` (Core Backend Model)
```python
class EvaluationReport(BaseModel):
    attempt_id: str
    evaluator_version: str = ""
    overall_score: float = 0.0
    mbb_rating_badge: str = "Meets Bar"
    overall_band: str = "Meets Bar"
    executive_summary: str = ""
    what_the_case_wanted_to_test: WhatTheCaseWantedToTest | None = None
    dimensions: list[DimensionScore] = Field(default_factory=list)
    dimension_scores: dict[str, DimensionScore] = Field(default_factory=dict)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    observed_behaviors: list[ChecklistItem] = Field(default_factory=list)
    golden_rewrites: list[GoldenRewriteTurn] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    headline_strengths: list[str] = Field(default_factory=list)
    areas_for_development: list[str] = Field(default_factory=list)
    priority_improvements: list[str] = Field(default_factory=list)
    targeted_drill: str = ""
    next_drill: str = ""
    drill_detail: TargetedDrillPayload | None = None
    suggested_readings: list[SuggestedReading] = Field(default_factory=list)
```

**Bidirectional Synchronization in `_sync_report_data`:**
- `dimensions` ↔ `dimension_scores`: Populates dictionary from list or list from dictionary.
- `checklist` ↔ `observed_behaviors`: Keeps both arrays in sync.
- `strengths` ↔ `headline_strengths`: Synchronizes both string lists.
- `areas_for_development` ↔ `priority_improvements`: Synchronizes both string lists.
- `targeted_drill` ↔ `next_drill`: Synchronizes drill text strings.
- Auto-calculation: If `overall_score` is 0 but dimensions exist, calculates arithmetic mean; computes `mbb_rating_badge` and `overall_band`.

---

## 3. Scale, Badge, and Band Calculation Logic

### 3.1 Overall Score Scale
- **Scale:** 1.0 to 5.0 (BCG 5-point calibration).
- **Formula:** Weighted arithmetic mean across assessed dimensions:
  $$\text{Score} = \frac{\sum_{d \in \text{Assessed}} \text{Score}_d \times \text{Weight}_d}{\sum_{d \in \text{Assessed}} \text{Weight}_d}$$
  - Structuring: 0.25
  - Problem Solving: 0.25
  - Quantitative: 0.15
  - Synthesis: 0.20
  - Communication: 0.15

### 3.2 MBB Rating Badge (`compute_mbb_rating_badge(score)`)
| Score Range | MBB Rating Badge | Meaning |
|---|---|---|
| $\ge 4.5$ | `Distinction` | Exceptional partner-ready performance |
| $3.8 \le \text{Score} < 4.5$ | `Strong Pass` | Clear offer recommendation |
| $2.8 \le \text{Score} < 3.8$ | `Meets Bar` | Solid consulting baseline, passes round 1 |
| $2.0 \le \text{Score} < 2.8$ | `Developing` | Needs focused coaching before interviews |
| $< 2.0$ | `Needs Substantial Practice` | Critical fundamental casing gaps |

### 3.3 Rubric Band (`compute_overall_band(score)`)
| Score Range | Rubric Band |
|---|---|
| $\ge 3.8$ | `Top 1% MBB` |
| $2.5 \le \text{Score} < 3.8$ | `Meets Bar` |
| $< 2.5$ | `Below Bar` |

---

## 4. API Endpoints & Response Payloads

### 4.1 `GET /api/attempts/{attempt_id}/evaluation`
- **Authentication:** Cookie session (`require_user`).
- **HTTP Statuses:**
  - `200 OK`: Returns full evaluation payload.
  - `401 Unauthorized`: Redirect / re-authenticate.
  - `404 Not Found`: Attempt not found or not owned by user.
  - `409 Conflict`: Attempt has not ended yet (`session.ended == False`).
  - `503 Service Unavailable`: Evaluator offline/busy.
- **Top-Level JSON Structure:**
```json
{
  "evaluator_version": "evaluator-v2|rubric=rubric-v2|checklist=checklist-v2|model=anthropic/claude-sonnet-4.6",
  "created_at": "2026-08-24 09:28:00",
  "user_id": "usr_abc123",
  "debrief_url": "/attempts/eval-fixture/debrief",
  "overall": {
    "overall": 3.9,
    "assessed_dimensions": ["structuring", "problem_solving", "quantitative", "synthesis", "communication"],
    "excluded_dimensions": []
  },
  "report": {
    "attempt_id": "eval-fixture",
    "evaluator_version": "evaluator-v2|rubric=rubric-v2|checklist=checklist-v2|model=anthropic/claude-sonnet-4.6",
    "overall_score": 3.9,
    "mbb_rating_badge": "Strong Pass",
    "overall_band": "Top 1% MBB",
    "executive_summary": "Candidate demonstrated solid structuring and hypothesis-driven problem solving.",
    "what_the_case_wanted_to_test": {
      "core_mechanism": "Adverse product/customer mix shift into pharmaceutical cold chain...",
      "commercial_concept": "Capacity utilization economics in specialized asset logistics...",
      "pivotal_insight": "Pharma routes consume capacity without generating unit contribution...",
      "candidate_performance_summary": "Candidate structured well and identified mix shift.",
      "candidate_vs_optimal_gap": "Could have computed contract contribution faster."
    },
    "dimensions": [
      {
        "name": "structuring",
        "score": 4.0,
        "band": "Top 1% MBB",
        "evidence": [
          {
            "message_index": 1,
            "quote": "a price versus volume split of revenue"
          }
        ],
        "observations": ["Structured the opening around price and volume."],
        "improvements": ["Tie each branch to a concrete metric."],
        "confidence": "high",
        "notes": ""
      },
      {
        "name": "problem_solving",
        "score": 3.5,
        "band": "Meets Bar",
        "evidence": [
          {
            "message_index": 3,
            "quote": "mix shift toward pharma could be dragging contribution down"
          }
        ],
        "observations": ["Hypothesis-driven inquiry into segment mix."],
        "improvements": ["State explicit ex-ante hypothesis earlier."],
        "confidence": "high",
        "notes": ""
      },
      {
        "name": "quantitative",
        "score": 3.0,
        "band": "Meets Bar",
        "evidence": [],
        "observations": ["Handled calculations accurately."],
        "improvements": ["Always state the 'so what?' after arithmetic."],
        "confidence": "medium",
        "notes": ""
      },
      {
        "name": "synthesis",
        "score": 4.0,
        "band": "Top 1% MBB",
        "evidence": [
          {
            "message_index": 4,
            "quote": "recommendation is to renegotiate pharma contracts"
          }
        ],
        "observations": ["Answer-first Pyramid Principle structure."],
        "improvements": ["Include a 100-day tactical roadmap."],
        "confidence": "high",
        "notes": ""
      },
      {
        "name": "communication",
        "score": 4.5,
        "band": "Top 1% MBB",
        "evidence": [],
        "observations": ["Top-down delivery with crisp executive presence."],
        "improvements": ["Signpost branch transitions explicitly."],
        "confidence": "high",
        "notes": ""
      }
    ],
    "dimension_scores": {
      "structuring": { "name": "structuring", "score": 4.0, "band": "Top 1% MBB", "evidence": [...], "observations": [...], "improvements": [...], "confidence": "high", "notes": "" },
      "problem_solving": { "name": "problem_solving", "score": 3.5, "band": "Meets Bar", "evidence": [...], "observations": [...], "improvements": [...], "confidence": "high", "notes": "" },
      "quantitative": { "name": "quantitative", "score": 3.0, "band": "Meets Bar", "evidence": [], "observations": [...], "improvements": [...], "confidence": "medium", "notes": "" },
      "synthesis": { "name": "synthesis", "score": 4.0, "band": "Top 1% MBB", "evidence": [...], "observations": [...], "improvements": [...], "confidence": "high", "notes": "" },
      "communication": { "name": "communication", "score": 4.5, "band": "Top 1% MBB", "evidence": [], "observations": [...], "improvements": [...], "confidence": "high", "notes": "" }
    },
    "checklist": [
      {
        "id": "structure.restate-objective-first",
        "marker_id": "structure.restate-objective-first",
        "title": "Restate the objective, metrics, and time horizon before structuring",
        "description": "Restate the objective, metrics, and time horizon before structuring",
        "status": "demonstrated",
        "evidence": [
          {
            "message_index": 1,
            "quote": "restate the objective: explain why EBITDA margin fell"
          }
        ],
        "note": ""
      },
      {
        "id": "structure.mece-by-construction",
        "marker_id": "structure.mece-by-construction",
        "title": "Use a cut that is MECE by construction (formula, segments, process, or segmentation with a catch-all)",
        "description": "Use a cut that is MECE by construction (formula, segments, process, or segmentation with a catch-all)",
        "status": "demonstrated",
        "evidence": [
          {
            "message_index": 1,
            "quote": "a price versus volume split of revenue"
          }
        ],
        "note": ""
      },
      {
        "id": "problem-solving.hypothesis-before-data",
        "marker_id": "problem-solving.hypothesis-before-data",
        "title": "State an ex-ante hypothesis before requesting evidence or data",
        "description": "State an ex-ante hypothesis before requesting evidence or data",
        "status": "demonstrated",
        "evidence": [
          {
            "message_index": 3,
            "quote": "mix shift toward pharma could be dragging contribution down"
          }
        ],
        "note": ""
      },
      {
        "id": "synthesis.pyramid-principle-answer-first",
        "marker_id": "synthesis.pyramid-principle-answer-first",
        "title": "Lead the synthesis with a clear, definitive recommendation (Answer First)",
        "description": "Lead the synthesis with a clear, definitive recommendation (Answer First)",
        "status": "demonstrated",
        "evidence": [
          {
            "message_index": 4,
            "quote": "recommendation is to renegotiate pharma contracts"
          }
        ],
        "note": ""
      },
      {
        "id": "synthesis.4-part-closing",
        "marker_id": "synthesis.4-part-closing",
        "title": "Deliver a complete 4-part synthesis (Recommendation, 2-3 Pillars, Risks/Mitigations, 100-Day Plan)",
        "description": "Deliver a complete 4-part synthesis (Recommendation, 2-3 Pillars, Risks/Mitigations, 100-Day Plan)",
        "status": "missed",
        "evidence": [],
        "note": "Deliver all 4 parts: Recommendation, Pillars, Risks/Mitigations, and Next Steps."
      }
    ],
    "observed_behaviors": [ ... ],
    "golden_rewrites": [
      {
        "stage": "opening",
        "phase": "opening",
        "candidate_turn": "Let me restate the objective: explain why EBITDA margin fell from 18 to 11 percent...",
        "candidate_message_index": 1,
        "mbb_partner_turn": "To ensure full alignment: our objective is to explain why EBITDA margin fell...",
        "golden_mbb_turn": "To ensure full alignment: our objective is to explain why EBITDA margin fell...",
        "diagnostic_notes": [
          "MBB Partner opening restates the objective with quantified constraints upfront.",
          "Decomposes into MECE-by-construction pillars tailored to the business model.",
          "States an explicit starting commercial hypothesis."
        ],
        "consulting_craft_delta": [
          "Confirm constraints before drawing the tree.",
          "Avoid generic textbook buckets in favor of client value-chain levers."
        ]
      },
      {
        "stage": "closing",
        "phase": "closing",
        "candidate_turn": "My recommendation is to renegotiate pharma contracts with backhaul indexing.",
        "candidate_message_index": 4,
        "mbb_partner_turn": "We recommend that the client immediately execute a focused turnaround strategy...",
        "golden_mbb_turn": "We recommend that the client immediately execute a focused turnaround strategy...",
        "diagnostic_notes": [
          "Top 1% MBB synthesis leads with an unambiguous recommendation in sentence 1.",
          "Structures support into 3 quantified pillars.",
          "Includes paired risk-mitigation vectors and a 100-day tactical roadmap."
        ],
        "consulting_craft_delta": [
          "Use the 4-part closing architecture (Answer, Pillars, Risks, Next Steps).",
          "Quantify pillar impacts using numbers derived in the case."
        ]
      }
    ],
    "strengths": [
      "Paraphrased and confirmed the case objective upfront.",
      "Demonstrated hypothesis-driven problem solving across inquiry turns."
    ],
    "headline_strengths": [
      "Paraphrased and confirmed the case objective upfront.",
      "Demonstrated hypothesis-driven problem solving across inquiry turns."
    ],
    "areas_for_development": [
      "Always follow arithmetic calculations with a commercial 'so what?' interpretation.",
      "Pair key strategic recommendations with implementation risks and concrete mitigations."
    ],
    "priority_improvements": [
      "Always follow arithmetic calculations with a commercial 'so what?' interpretation.",
      "Pair key strategic recommendations with implementation risks and concrete mitigations."
    ],
    "targeted_drill": "Write out algebraic formulas and units before executing mental math; state the 'so what?' immediately.",
    "next_drill": "Write out algebraic formulas and units before executing mental math; state the 'so what?' immediately.",
    "drill_detail": {
      "title": "Algebraic Sanity Check Drill",
      "duration_seconds": 120,
      "prompt": "Write out algebraic formulas and units before executing mental math; state the 'so what?' immediately.",
      "focus_area": "quantitative"
    },
    "suggested_readings": [
      {
        "title": "02 Issue Tree Structuring",
        "path": "knowledge_base/methodology/02_issue_tree_structuring.md",
        "why_relevant": "Essential guide for mastering quantitative in MBB interviews.",
        "relevance_reason": "Essential guide for mastering quantitative in MBB interviews."
      },
      {
        "title": "05 Synthesis And Recommendation",
        "path": "knowledge_base/methodology/05_synthesis_and_recommendation.md",
        "why_relevant": "Essential guide for mastering quantitative in MBB interviews.",
        "relevance_reason": "Essential guide for mastering quantitative in MBB interviews."
      }
    ]
  }
}
```

---

### 4.2 `GET /api/attempts/{attempt_id}`
- **Authentication:** Cookie session (`require_user`).
- **Response Format:**
```json
{
  "id": "attempt-uuid",
  "case": {
    "id": "meridian-cold-chain-v1",
    "title": "Meridian Cold Chain",
    "category": "profitability",
    "industry": "temperature_controlled_logistics",
    "difficulty": "foundation",
    "supported_durations": [30],
    "skills_tested": ["clarification", "tailored structure", "unit economics", "synthesis"],
    "phases": ["clarification", "drill_down", "synthesis"]
  },
  "mode": "realistic",
  "stage": "synthesis",
  "messages": [
    {"role": "interviewer", "content": "Welcome..."},
    {"role": "candidate", "content": "I'm ready..."},
    {"role": "interviewer", "content": "Case opening brief..."},
    {"role": "candidate", "content": "Let me restate the objective..."}
  ],
  "facts": [
    {"id": "customers.segment-mix", "content": "Segment mix has shifted toward pharma..."}
  ],
  "case_started": true,
  "ended": true,
  "debrief_url": "/attempts/attempt-uuid/debrief",
  "evaluation_url": "/api/attempts/attempt-uuid/evaluation",
  "score": 3.9,
  "mbb_rating_badge": "Strong Pass",
  "evaluation": {
    "evaluator_version": "evaluator-v2|rubric=rubric-v2|...",
    "report": { ... },
    "created_at": "2026-08-24 09:28:00",
    "user_id": "usr_123"
  }
}
```
*Note:* When the attempt is ongoing (`ended == False`), `score`, `mbb_rating_badge`, and `evaluation` are omitted/null; `debrief_url` and `evaluation_url` are only populated if an evaluation exists or `ended == True`.

---

## 5. Discovered Features & Edge Cases

## Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Scoring | BCG 1.0–5.0 Scale | Calibrated grading on 1.0 to 5.0 scale across 5 dimensions | Dimension scores (1.0–5.0) | `overall_score`, `DimensionScore.score` | Scores clamped/validated to 1.0–5.0; unassessed can be 0.0 in partial | `app/evaluator.py`, `evaluation/rubric.yaml` |
| 2 | Rating | MBB Rating Badge | 5-tier badge derived from overall score: Distinction (≥4.5), Strong Pass (≥3.8), Meets Bar (≥2.8), Developing (≥2.0), Needs Substantial Practice (<2.0) | `overall_score: float` | `mbb_rating_badge: str` | Defaults to `"Meets Bar"` if score is 0.0 | `app/evaluator.py:62` |
| 3 | Rating | Rubric Overall Band | 3-tier band: Top 1% MBB (≥3.8), Meets Bar (≥2.5), Below Bar (<2.5) | `overall_score: float` | `overall_band: str` | Defaults to `"Meets Bar"` if score is 0.0 | `app/evaluator.py:75` |
| 4 | Masterclass Reveal | What The Case Wanted to Test | Core mechanism, commercial concept, pivotal insight, candidate summary, candidate vs optimal gap | Authored `case_essence` + transcript analysis | `WhatTheCaseWantedToTest` object | Defaults to empty strings or case objective if essence missing | `app/evaluator.py:103`, `app/models.py:15` |
| 5 | Masterclass Reveal | Golden MBB Rewrites | Side-by-side Opening & Closing comparisons of Candidate Turn vs Top 1% MBB Partner Turn | Candidate opening/closing turns + essence | `list[GoldenRewriteTurn]` | Defaults to empty list if no candidate turns recorded | `app/evaluator.py:114` |
| 6 | Action Plan | Targeted 2-Min Drill | Tailored 120s practice drill on weakest dimension with title, prompt, and focus area | Weakest evaluated dimension | `TargetedDrillPayload` (`drill_detail`) + `targeted_drill` string | Defaults to generic casing drill if no dimensions assessed | `app/evaluator.py:156`, `app/evaluator.py:1145` |
| 7 | Action Plan | Suggested Readings | Curated list of reading paths and reasons from knowledge base | Case essence `suggested_readings` | `list[SuggestedReading]` | Defaults to issue tree and synthesis guides if none authored | `app/evaluator.py:163`, `app/evaluator.py:1229` |
| 8 | Feedback | Headline Strengths & Dev Areas | Strengths (claim, quote, impact) and prioritized development areas (gap, priority, corrective guidance) | Transcript observations and missed checklist items | `strengths`/`headline_strengths`, `areas_for_development`/`priority_improvements` | Capped at top 5 priority items; sanitized prose | `app/evaluator.py:144-154` |
| 9 | Checklist | Observed Behaviors | 12 stable behavioral markers evaluated against transcript | Checklist items + transcript | `list[ChecklistItem]` | Marked `"not_applicable"` if phase or calculation unreached | `app/evaluator.py:181`, `evaluation/checklist.yaml` |
| 10 | Security | Verbatim Citation Verifier | Checks that every citation quote matches transcript content verbatim | `message_index`, `quote`, `session.messages` | `bool` valid | Unverified citations stripped; confidence downgraded to `"low"` | `app/evaluator.py:379, 715` |
| 11 | Security | Answer-Key Leakage Redaction | Scans report text against hidden facts and issue-tree conclusions | Report prose + private strings | Redacted report | Leaked phrases replaced with `"[withheld by leakage guard]"` | `app/evaluator.py:385, 701` |
| 12 | Formatting | Em-Dash Sanitizer | Replaces all em-dashes (`\u2014`) with comma-space (`", "`) | Report text strings | Sanitized text | Runs on all prose fields in report before persistence | `app/evaluator.py:625-669` |
| 13 | Fallback | Deterministic Fallback Evaluator | Genuine heuristic evaluator producing full 1.0–5.0 report when LLM offline | Completed `InterviewSession` | `EvaluationReport` | Produces full report without external API dependencies | `app/evaluator.py:798-1262` |
| 14 | API | Lazy Evaluation Generation | Generates and persists evaluation on-demand when fetching `/api/attempts/{id}/evaluation` if not already stored | `attempt_id` | Full stored evaluation wrapper + `overall` | Returns 409 if attempt not ended; 503 if generation fails | `app/main.py:351` |
| 15 | Model Sync | Bidirectional Schema Synchronizer | Model validator syncing list/dict pairs (`dimensions`/`dimension_scores`, `checklist`/`observed_behaviors`, etc.) | Pydantic model initialization | Uniformly accessible properties | Automatically populates counterpart fields | `app/evaluator.py:228-273` |

---

## 6. Edge Cases & Resilience Behaviors

## Edge Cases
| # | Feature | Input / Condition | Observed Behavior |
|---|---------|-------------------|-------------------|
| 1 | Attempt without candidate turns | Candidate started attempt and ended without typing any messages | Evaluator generates honest floor report: `overall_score = 1.0`, `mbb_rating_badge = "Needs Substantial Practice"`, `overall_band = "Below Bar"`, all 5 dimensions score `1.0` with `confidence = "low"`, checklist marked `"not_applicable"`, `golden_rewrites = []`, `strengths = []`. |
| 2 | Quantitative calculation omitted | Case attempt had qualitative discussion only (no math) | `quantitative` dimension scored with `confidence = "low"`, `evidence = []`, `observations = ["No explicit quantitative calculations were performed in this attempt."]`. In `weighted_overall`, quantitative is excluded (`excluded_dimensions = ["quantitative"]`) and its 0.15 weight is redistributed across the other 4 dimensions. |
| 3 | Partial or unassessed dimensions | Dimension has score `0.0` or no evidence citations | `weighted_overall` calculates score using only dimensions with evidence/scores; excluded dimensions listed in `excluded_dimensions`. |
| 4 | Attempt still in progress | `GET /api/attempts/{id}/evaluation` called on active attempt | Returns HTTP `409 Conflict` (`"The attempt has not ended yet"`). |
| 5 | Non-existent or unauthorized attempt | Accessing another candidate's attempt ID | Returns HTTP `404 Not Found`. |
| 6 | LLM Evaluator API failure / offline | OpenRouter API down or key missing during attempt end | Fallback engine or stored scorecard invoked; `GET /api/attempts/{id}/evaluation` serves fallback or returns HTTP `503 Service Unavailable` with retry flag. |
| 7 | Hallucinated citation quote | LLM writer invents a quote not in transcript | Deterministic boundary guard strips the invalid citation; marks dimension `confidence = "low"` and appends `"Citations for this dimension could not be verified against the transcript."`. |
| 8 | Leakage of private case facts / issue tree | LLM writer includes private diagnosis in report | Leakage scanner redacts text containing undisclosed facts or private causal DAG conclusions to `"[withheld by leakage guard]"`. |
| 9 | Null / Missing masterclass sections | Legacy or partial evaluator version omitting `what_the_case_wanted_to_test`, `golden_rewrites`, or `drill_detail` | Fields default to `None`, `[]`, or `""`. Frontend must check for existence before rendering without throwing JS errors. |
| 10 | Top-level payload format differences | API response returns `payload.report` wrapper (stored) vs flat report | `main.py` wraps stored report in `{"evaluator_version": ..., "created_at": ..., "report": {...}, "overall": {...}}`. Frontend handles both `payload.report` and flat `payload`. |
| 11 | Em-dash characters in model prose | Writer produces `\u2014` in feedback or drill prompts | `_sanitize` replaces all `\u2014` with `", "` before persistence and serialization. |

---

## 7. Frontend Integration Checklist for Debrief Upgrade

To render the full 10x Masterclass Debrief Report:
1. **Scale Update:** Update overall score display from `/10` to `/5`. Dimension meters must use `aria-valuemin="1"`, `aria-valuemax="5"`, `aria-valuenow="score"`, and width percentage `(score / 5) * 100%`.
2. **Dimension Labels Map:** Ensure `DIMENSION_LABELS` in `debrief.js` includes all 5 keys:
   - `structuring`: `"Structuring"`
   - `problem_solving`: `"Problem Solving"`
   - `quantitative`: `"Quantitative Ability"`
   - `synthesis`: `"Synthesis & Recommendation"`
   - `communication`: `"Executive Communication"`
3. **7 Masterclass Sections Rendering Pipeline:**
   - **Section 1 (Executive Header):** Overall score badge (`X.X / 5`), `mbb_rating_badge` chip, `overall_band`, `executive_summary` paragraph.
   - **Section 2 ("What This Case Really Wanted to Test"):** Card showing `core_mechanism`, `pivotal_insight`, `commercial_concept`, `candidate_performance_summary`, and `candidate_vs_optimal_gap`.
   - **Section 3 (5 Core Dimension Cards):** 5 cards each with score (out of 5.0), band chip, confidence chip, score bar, verbatim blockquotes (`Citation`), observations list, and improvements list.
   - **Section 4 (Golden MBB Rewrites):** Side-by-side or stacked comparative cards for Opening and Closing: "What You Said" (`candidate_turn`) vs "How an MBB Partner Would Deliver It" (`mbb_partner_turn`), plus `diagnostic_notes` bullets.
   - **Section 5 (Headline Strengths):** Render `strengths` / `headline_strengths` (claim + quote + impact).
   - **Section 6 (Areas for Development):** Render `areas_for_development` / `priority_improvements` with priority chips (`high`, `medium`, `low`) and corrective guidance.
   - **Section 7 (Action Plan & Suggested Readings):** Render `drill_detail` / `targeted_drill` (title, 120s duration, prompt, focus area) and `suggested_readings` list (title, path, why relevant).
   - **Section 8 (Observed Behaviors Checklist):** Keep the existing checklist at the bottom with demonstrated/missed/not_applicable markers and citations.
4. **Defensive Parsing:** Always use safe access (`report.what_the_case_wanted_to_test?.core_mechanism`, `report.golden_rewrites || []`, etc.) and set text using `textContent` for XSS safety.
