# Comprehensive Frontend Survey & Architecture Report: 10x Masterclass Debrief Report UI

**Agent**: `survey_explorer_1`  
**Date**: 2026-08-24  
**Project**: MBB Case Prep V2  
**Target Files**:
- `app/static/debrief.html`
- `app/static/debrief.js`
- `app/static/debrief.css`
- `app/static/tokens.css`
- `app/static/theme.js`
- `app/static/styles.css`
- `app/evaluator.py` & `app/main.py` (API Contract)
- `tests/test_debrief_ui.py`

---

## 1. Executive Summary & Context

The backend evaluation engine (`app/evaluator.py`), database persistence (`app/store.py`), evaluation API endpoints (`GET /api/attempts/{id}/evaluation`), and multi-school case corpus are fully built, calibrated to the BCG 1.0–5.0 scale, and validated by 175 passing tests.

However, the interactive debrief web frontend (`app/static/debrief.html`, `app/static/debrief.js`, `app/static/debrief.css`) currently reflects a legacy v1 format:
1. **Scoring Scale Discrepancy**: Displays scores out of `10` (`/10`) instead of the calibrated BCG `1.0–5.0` scale (`/5`).
2. **Missing Dimension**: `DIMENSION_LABELS` in `debrief.js` only maps 4 dimensions (`structuring`, `problem_solving`, `quantitative`, `communication`), omitting `synthesis`.
3. **Missing Masterclass Sections**: Out of the 7 core sections returned by the evaluator API, 4 sections are entirely missing or rendered as simplistic flat text:
   - *Missing*: Section 2 — "What This Case Really Wanted to Test" (core economic mechanism, commercial concept, pivotal insight, candidate performance summary, and candidate-vs-optimal gap).
   - *Missing*: Section 4 — "Golden MBB Rewrites" (side-by-side candidate turn vs. MBB partner turn with diagnostic notes).
   - *Under-rendered*: Section 5 & 6 — "Headline Strengths" and "Areas for Development" render flat strings rather than rich structured objects (`claim`, `verbatim_quote`, `impact`; and `gap`, `priority`, `corrective_guidance`).
   - *Under-rendered*: Section 7 — "Action Plan" only renders a single string instead of the structured `TargetedDrillPayload` (title, duration, prompt, focus area) and `SuggestedReading` list.
4. **Missing Executive Badges**: Executive header does not render the MBB Rating Badge (`Distinction`, `Strong Pass`, `Meets Bar`, `Developing`, `Needs Substantial Practice`) or the 2-sentence partner `executive_summary`.

This survey report provides an exhaustive map of the existing frontend codebase, backend API contracts, exact element hierarchies, CSS token architecture, and precise implementation specifications to upgrade the debrief interface to a 10x Masterclass Debrief Report.

---

## 2. Current Frontend Architecture & Inventory

### 2.1 HTML Structure (`app/static/debrief.html`)

#### Current Hierarchy & Landmarks:
- `<!doctype html>` -> `<html lang="en">` -> `<head>` (links `tokens.css`, `styles.css`, `debrief.css`, Google Fonts)
- `<body class="debrief-body">`:
  - `<header class="topbar">`:
    - Brand link: logo SVG + `<span class="brand-name">Leo</span>`
    - Separator: `<span class="rule" aria-hidden="true"></span>`
    - View chip: `<span class="profile-chip">Case debrief</span>`
    - Topbar actions: Case library button, `#transcript-link` ("View transcript"), `#theme-toggle` (Sun/Moon icon switcher), `#sign-out` button.
  - `<main class="debrief">`:
    - `#debrief-state` (`<section class="debrief-state hidden">`): Spinner, `#state-title`, `#state-note`, `#state-actions` (with `#state-retry` button).
    - `#debrief-report` (`<div class="debrief-report hidden">`):
      - `<header class="debrief-head">`:
        - Left: Eyebrow + `#case-title` (`<h1>`) + `#report-subtitle` (`<p class="muted">`).
        - Right: `.overall-card` with `#overall-score`, hardcoded `<span class="overall-out-of">/10</span>`, and `#overall-note`.
      - `<section class="debrief-takeaways">`:
        - `.takeaway-card`: `#strength-list` (`<ul class="takeaway-list is-strengths">`)
        - `.takeaway-card`: `#priority-list` (`<ul class="takeaway-list is-priorities">`) + `.next-drill` (`#drill-text`)
      - `<section class="dimension-grid" id="dimension-grid">`: Dynamically populated container for dimension cards.
      - `<article class="card checklist-card" id="checklist-card">`: Observed behaviours header, `.checklist-legend` (Demonstrated, Missed, Not applicable), and `#checklist` (`<ul>`).
      - `<footer class="debrief-foot">`: `#version-note` (`<p class="muted">`).
      - `<div class="debrief-bottom-actions">`: "Practise another case" (`/cases`) & "Your practice history" (`/profile`).
  - `#toasts` (`<div class="toasts" role="status" aria-live="polite">`): Toast notifications live region.
  - `<template id="evidence-template">`:
    - `<figure class="evidence"><blockquote class="evidence-quote"></blockquote><figcaption class="evidence-ref"></figcaption></figure>`
  - Scripts: `<script src="/static/theme.js"></script>`, `<script src="/static/debrief.js"></script>`.

#### Missing Elements in HTML:
1. Executive Header: `#executive-summary` paragraph and `#mbb-rating-badge` badge container.
2. Section 2: Dedicated container for "What This Case Really Wanted to Test" (`#essence-card` / `#what-case-tested`).
3. Section 4: Dedicated container for Golden MBB Rewrites (`#rewrites-container` / `#rewrites-list`).
4. Section 5 & 6: Semantic card wrappers for rich Strengths (`#strengths-card`) and Development Areas (`#priorities-card`).
5. Section 7: Dedicated container for Action Plan (`#action-plan-card`), including `#drill-card` with duration/focus chips and `#readings-list` for suggested readings.

---

### 2.2 JavaScript Architecture (`app/static/debrief.js`)

#### State & DOM Elements:
- `const state = { attemptId: null };`
- `const DIMENSION_LABELS`:
  ```javascript
  const DIMENSION_LABELS = {
    structuring: "Structuring",
    problem_solving: "Problem solving",
    communication: "Communication",
    quantitative: "Quantitative ability",
  };
  // MISSING: synthesis: "Synthesis & recommendation" (or "Synthesis")
  ```
- `const el`: Object querying all static DOM IDs.

#### API Ingestion & Authentication:
- `request(url, options)`: Handles 401 redirects to `/login?next=...`, extracts JSON error details, throws `ApiError`.
- `load()`: Runs `Promise.all([request('/api/attempts/${id}'), request('/api/attempts/${id}/evaluation')])`.
  - Handles HTTP status codes:
    - `409`: "This practice has not ended yet."
    - `404`: "Debrief not found."
    - `503`: "Leo is still marking this case." (enables `#state-retry`).
    - General errors: Displays error note with retry button.

#### Current Rendering Pipeline:
- `renderHeader(attempt)`: Sets `#case-title`, document title, turn count, mode, and difficulty in `#report-subtitle`.
- `renderOverall(overall)`: Sets `#overall-score` and `#overall-note`.
  - *Defect*: Assumes legacy `/10` scale in DOM.
  - *Defect*: Does not display `report.mbb_rating_badge` or `report.executive_summary`.
- `renderDimension(dimension)`:
  - *Defect*: Hardcodes `/10` in `node("span", "dimension-out-of", "/10")`.
  - *Defect*: Math `fill.style.width = Math.max(0, Math.min(10, dimension.score)) * 10 + "%"`.
  - *Defect*: `track.setAttribute("aria-valuemax", "10")`.
  - Appends observations, improvements, and evidence citations.
- `renderChecklist(items)`: Renders demonstrated, missed, and not_applicable items with SVG icons and evidence blocks.
- `renderReport(attempt, payload)`: Unpacks `report = payload.report` and coordinates render steps.
  - *Defect*: Calls `fillList(el.strengths, report.headline_strengths || [])` which only handles string arrays, dropping rich `claim`, `verbatim_quote`, and `impact` properties.
  - *Defect*: Calls `fillList(el.priorities, report.priority_improvements || [])` which drops `priority` badge and `corrective_guidance`.
  - *Defect*: Does not invoke renderers for `what_the_case_wanted_to_test`, `golden_rewrites`, `targeted_drill`, or `suggested_readings`.

---

### 2.3 CSS & Design Token System (`app/static/tokens.css`, `debrief.css`, `styles.css`)

#### Design Tokens (`tokens.css`):
- **Typography**:
  - `--font-sans`: "Plus Jakarta Sans", sans-serif
  - `--font-serif`: "Newsreader", serif (Used for quotes, partner speeches, headings)
  - `--font-mono`: "JetBrains Mono", monospace (Used for transcript refs, file paths, numbers)
- **Light Palette**:
  - `--bg-base`: `#fbfaf7`, `--bg-surface`: `#ffffff`, `--bg-subtle`: `#f4f0e6`, `--bg-sunken`: `#ede8dc`, `--bg-elevated`: `#ffffff`
  - `--ink-primary`: `#111a18`, `--ink-secondary`: `#43514c`, `--ink-muted`: `#6b7a74`, `--ink-faint`: `#98a5a0`
  - `--line-subtle`: `rgba(17, 26, 24, 0.07)`, `--line-base`: `rgba(17, 26, 24, 0.12)`, `--line-strong`: `rgba(17, 26, 24, 0.18)`, `--line-dashed`: `rgba(17, 26, 24, 0.14)`
  - `--brand-primary`: `#0e453a`, `--brand-deep`: `#082e27`, `--brand-lift`: `#185a4d`, `--brand-light`: `#e6f3ee`, `--brand-tint`: `rgba(14, 69, 58, 0.08)`
  - `--gold-primary`: `#c98838`, `--gold-deep`: `#9d6420`, `--gold-light`: `#fdf6ec`, `--gold-soft`: `#f4e3cd`
  - Status tokens:
    - Success: `--status-success` (`#15803d`), `--status-success-bg` (`#edfbf2`)
    - Warning: `--status-warning` (`#b45309`), `--status-warning-bg` (`#fffbeb`)
    - Danger: `--status-danger` (`#b91c1c`), `--status-danger-bg` (`#fef2f2`)
    - Info: `--status-info` (`#0369a1`), `--status-info-bg` (`#f0f9ff`)
- **Dark Mode Palette (`data-theme="dark"` / `prefers-color-scheme: dark`)**:
  - `--bg-base`: `#0b0f10`, `--bg-surface`: `#121819`, `--bg-subtle`: `#192123`, `--bg-sunken`: `#070a0b`
  - `--ink-primary`: `#f2f6f4`, `--ink-secondary`: `#b3c0bc`, `--ink-muted`: `#80908b`
  - `--brand-primary`: `#45bf9f`, `--brand-deep`: `#2fa587`, `--brand-light`: `rgba(69, 191, 159, 0.15)`
  - `--gold-primary`: `#e6b162`, `--gold-light`: `rgba(230, 177, 98, 0.15)`
  - Status tokens adapt with translucent dark tints (`rgba(...)`).
- **Theme Switching Mechanism (`theme.js`)**:
  - Stores selection in `localStorage.getItem("casecall:theme")`.
  - Toggles `document.documentElement.dataset.theme = "light" | "dark"`.
  - Synchronizes sun/moon SVG icons via CSS display rules.

---

## 3. Backend API Contract & Pydantic Schema Mapping

The evaluation endpoint `GET /api/attempts/{attempt_id}/evaluation` returns:
```json
{
  "report": {
    "attempt_id": "string",
    "evaluator_version": "evaluator-v2|rubric=rubric-v2|...",
    "overall_score": 3.9,
    "mbb_rating_badge": "Strong Pass",
    "overall_band": "Top 1% MBB",
    "executive_summary": "Candidate demonstrated strong structuring...",
    "what_the_case_wanted_to_test": {
      "core_mechanism": "...",
      "commercial_concept": "...",
      "pivotal_insight": "...",
      "candidate_performance_summary": "...",
      "candidate_vs_optimal_gap": "..."
    },
    "dimensions": [
      {
        "name": "structuring",
        "score": 3.4,
        "band": "Meets Bar",
        "evidence": [{"message_index": 2, "quote": "..."}],
        "observations": ["..."],
        "improvements": ["..."],
        "confidence": "high",
        "notes": "..."
      }
    ],
    "golden_rewrites": [
      {
        "phase": "opening",
        "candidate_turn": "...",
        "candidate_message_index": 1,
        "mbb_partner_turn": "...",
        "diagnostic_notes": ["..."]
      }
    ],
    "strengths": [
      {
        "claim": "Tailored Structuring",
        "verbatim_quote": "price versus volume split",
        "impact": "Quickly narrowed down revenue drivers."
      }
    ],
    "areas_for_development": [
      {
        "gap": "Backhaul Unit Cost Quantification",
        "priority": "high",
        "corrective_guidance": "Always calculate round-trip asset utilization in transportation cases."
      }
    ],
    "targeted_drill": {
      "title": "Logistics Route Density Mental Math",
      "duration_seconds": 120,
      "prompt": "A reefer truck runs 500km outbound...",
      "focus_area": "Route Unit Economics"
    },
    "suggested_readings": [
      {
        "title": "Logistics & Cold Chain Playbook",
        "path": "knowledge_base/methodology/02_issue_tree_structuring.md",
        "why_relevant": "Deep dive into reefer route economics."
      }
    ],
    "checklist": [
      {
        "id": "c1",
        "title": "Structured initial framework",
        "status": "demonstrated",
        "note": "",
        "evidence": [{"message_index": 1, "quote": "..."}]
      }
    ]
  },
  "overall": {
    "overall": 3.9,
    "assessed_dimensions": ["structuring", "problem_solving", "quantitative", "synthesis", "communication"],
    "excluded_dimensions": []
  },
  "debrief_url": "/attempts/{id}/debrief"
}
```

### Fallback / Legacy Key Aliases Handled by Schema:
- `what_the_case_wanted_to_test` <-> `what_case_wanted_to_test`
- `golden_rewrites[i].phase` <-> `stage`
- `golden_rewrites[i].mbb_partner_turn` <-> `golden_mbb_turn`
- `golden_rewrites[i].diagnostic_notes` <-> `consulting_craft_delta`
- `strengths` <-> `headline_strengths` (can be list of objects or list of strings)
- `areas_for_development` <-> `priority_improvements` (can be list of objects or list of strings)
- `targeted_drill` <-> `drill_detail` <-> `next_drill` (can be object or string)
- `suggested_readings[i].why_relevant` <-> `relevance_reason` (can be object or string path)
- `checklist` <-> `observed_behaviors`

---

## 4. Section-by-Section Gap Analysis & Required Upgrades

| # | Section Name | Current State in Frontend | Required Target State | Files to Modify |
|---|---|---|---|---|
| **1** | **Executive Header** | Shows `/10` score, no rating badge, no executive summary. | Shows BCG score `/5`, MBB Rating Badge (Distinction / Strong Pass / Meets Bar / Developing / Needs Practice), and partner `executive_summary` block. | `debrief.html`<br>`debrief.js`<br>`debrief.css` |
| **2** | **"What This Case Really Wanted to Test"** | Completely absent. | Masterclass reveal card with 5 structured insight cards: Core Mechanism, Commercial Concept, Pivotal Insight, Candidate Performance, and Optimal Gap. | `debrief.html`<br>`debrief.js`<br>`debrief.css` |
| **3** | **5 Core Dimension Cards** | 4 dimensions only, score `/10`, score fill width formula assumes max 10. | All 5 dimensions (`structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`), score `/5`, fill width `(score/5)*100%`, `aria-valuemax="5"`. | `debrief.html`<br>`debrief.js`<br>`debrief.css` |
| **4** | **Golden MBB Rewrites** | Completely absent. | Side-by-side or stacked dual cards per phase ("What You Said" vs. "How an MBB Partner Would Deliver It") + Diagnostic Notes. | `debrief.html`<br>`debrief.js`<br>`debrief.css` |
| **5** | **Headline Strengths** | Flat string bullet list (`fillList`). | Rich cards/list items rendering `claim`, verbatim quoted excerpt (`verbatim_quote`), and `impact` explanation. | `debrief.html`<br>`debrief.js`<br>`debrief.css` |
| **6** | **Areas for Development** | Flat string numbered list. | Rich cards/list items with `gap` title, `priority` badge (High/Medium/Low), and `corrective_guidance` text. | `debrief.html`<br>`debrief.js`<br>`debrief.css` |
| **7** | **Action Plan (Drill + Readings)** | Flat string in `#drill-text`, no suggested readings. | Structured Action Plan card: Targeted Drill box (title, duration chip, focus area tag, prompt) + Suggested Readings list with title, path badge, and relevance explanation. | `debrief.html`<br>`debrief.js`<br>`debrief.css` |
| **+** | **Observed Behaviours Checklist** | Implemented but needs container alignment. | Preserve existing checklist and evidence citations cleanly below Section 7. | `debrief.html`<br>`debrief.js` |

---

## 5. Precise Technical Specifications

### 5.1 HTML Specification (`app/static/debrief.html`)

Structure of `#debrief-report`:
```html
<div class="debrief-report hidden" id="debrief-report">
  <!-- SECTION 1: Executive Header -->
  <header class="debrief-head" id="debrief-header">
    <div class="debrief-head-main">
      <p class="eyebrow"><span class="eyebrow-mark" aria-hidden="true"></span> Evidence-based debrief</p>
      <h1 id="case-title">Your case</h1>
      <p class="muted" id="report-subtitle"></p>
      <div class="executive-summary-box hidden" id="executive-summary-box">
        <p class="executive-summary" id="executive-summary"></p>
      </div>
    </div>
    <div class="overall-card" aria-label="Weighted overall score">
      <p class="micro-label">Overall</p>
      <p class="overall-value"><span id="overall-score">–</span><span class="overall-out-of">/5</span></p>
      <div class="mbb-rating-container" id="mbb-rating-container">
        <span class="mbb-badge" id="mbb-rating-badge">–</span>
      </div>
      <p class="overall-note" id="overall-note"></p>
    </div>
  </header>

  <!-- SECTION 2: What This Case Really Wanted to Test -->
  <section class="card essence-card hidden" id="essence-card" aria-label="What this case really wanted to test">
    <header class="card-head">
      <div>
        <p class="eyebrow"><span class="eyebrow-mark is-gold" aria-hidden="true"></span> Masterclass reveal</p>
        <h2 class="section-title">What This Case Really Wanted to Test</h2>
        <p class="card-subtitle">The commercial crux, pivotal mechanism, and candidate-vs-optimal benchmark.</p>
      </div>
    </header>
    <div class="essence-grid">
      <div class="essence-block">
        <span class="essence-label">Core Mechanism</span>
        <p class="essence-text" id="essence-mechanism"></p>
      </div>
      <div class="essence-block">
        <span class="essence-label">Commercial Concept</span>
        <p class="essence-text" id="essence-concept"></p>
      </div>
      <div class="essence-block is-highlight">
        <span class="essence-label">Pivotal Breakthrough Insight</span>
        <p class="essence-text" id="essence-insight"></p>
      </div>
      <div class="essence-block">
        <span class="essence-label">Candidate Performance Summary</span>
        <p class="essence-text" id="essence-performance"></p>
      </div>
      <div class="essence-block">
        <span class="essence-label">Candidate vs. Optimal Gap</span>
        <p class="essence-text" id="essence-gap"></p>
      </div>
    </div>
  </section>

  <!-- SECTION 3: 5 Core Dimension Cards -->
  <section class="dimension-section" aria-label="Dimension breakdown">
    <header class="section-header">
      <p class="eyebrow">Rubric evaluation</p>
      <h2 class="section-title">Core Performance Dimensions</h2>
    </header>
    <div class="dimension-grid" id="dimension-grid"></div>
  </section>

  <!-- SECTION 4: Golden MBB Rewrites -->
  <section class="card rewrites-card hidden" id="golden-rewrites-section" aria-label="Golden MBB rewrites">
    <header class="card-head">
      <div>
        <p class="eyebrow"><span class="eyebrow-mark is-gold" aria-hidden="true"></span> Consulting craft</p>
        <h2 class="section-title">Golden MBB Rewrites</h2>
        <p class="card-subtitle">Direct comparison between your phrasing and a Top 1% MBB Partner delivery.</p>
      </div>
    </header>
    <div class="rewrites-list" id="golden-rewrites-list"></div>
  </section>

  <!-- SECTION 5 & 6: Headline Strengths & Areas for Development -->
  <section class="debrief-takeaways">
    <article class="card takeaway-card strengths-card" id="strengths-card">
      <p class="micro-label">Headline strengths</p>
      <ul class="takeaway-list is-strengths" id="strength-list"></ul>
    </article>
    <article class="card takeaway-card priorities-card" id="priorities-card">
      <p class="micro-label">Areas for development</p>
      <ul class="takeaway-list is-priorities" id="priority-list"></ul>
    </article>
  </section>

  <!-- SECTION 7: Action Plan (Targeted Drill & Suggested Readings) -->
  <section class="card action-plan-card" id="action-plan-card" aria-label="Action plan and readings">
    <header class="card-head">
      <div>
        <p class="eyebrow">Next steps</p>
        <h2 class="section-title">Personalized Action Plan</h2>
        <p class="card-subtitle">High-yield drill and recommended reading tailored to this attempt.</p>
      </div>
    </header>
    <div class="action-plan-grid">
      <div class="drill-container" id="drill-container">
        <div class="drill-header">
          <span class="micro-label">Targeted Drill</span>
          <div class="drill-meta">
            <span class="drill-tag" id="drill-focus">General</span>
            <span class="drill-duration" id="drill-duration">120s drill</span>
          </div>
        </div>
        <h3 class="drill-title" id="drill-title">Recommended Drill</h3>
        <p class="drill-prompt" id="drill-text"></p>
      </div>
      <div class="readings-container" id="readings-container">
        <span class="micro-label">Suggested Readings</span>
        <ul class="readings-list" id="readings-list"></ul>
      </div>
    </div>
  </section>

  <!-- Observed Behaviours Checklist -->
  <article class="card checklist-card" id="checklist-card" aria-label="Observed behaviours">
    <header class="card-head">
      <div>
        <p class="eyebrow">Observed behaviours</p>
        <p class="card-subtitle">Every marker checked against what you said.</p>
      </div>
      <div class="checklist-legend">
        <span class="legend-item">Demonstrated</span>
        <span class="legend-item">Missed</span>
        <span class="legend-item">Not applicable</span>
      </div>
    </header>
    <ul class="checklist" id="checklist"></ul>
  </article>

  <footer class="debrief-foot">
    <p class="muted" id="version-note"></p>
  </footer>

  <div class="debrief-bottom-actions">
    <a class="button button-solid" href="/cases">Practise another case</a>
    <a class="button button-ghost" href="/profile">Your practice history</a>
  </div>
</div>
```

---

### 5.2 JavaScript Specification (`app/static/debrief.js`)

1. **Update Dimension Labels**:
```javascript
const DIMENSION_LABELS = {
  structuring: "Structuring",
  problem_solving: "Problem solving",
  quantitative: "Quantitative ability",
  synthesis: "Synthesis & recommendation",
  communication: "Communication",
};
```

2. **MBB Badge Helper**:
```javascript
function getMbbBadgeClass(badge) {
  const normalized = String(badge || "").toLowerCase().replace(/[\s_]+/g, "-");
  if (normalized.includes("distinction")) return "badge-distinction";
  if (normalized.includes("strong-pass") || normalized.includes("strong")) return "badge-strong-pass";
  if (normalized.includes("meets-bar") || normalized.includes("meets")) return "badge-meets-bar";
  if (normalized.includes("developing")) return "badge-developing";
  if (normalized.includes("practice") || normalized.includes("below")) return "badge-needs-practice";
  return "badge-meets-bar";
}
```

3. **Section 1: Executive Header Renderer**:
```javascript
function renderExecutiveHeader(attempt, report, overall) {
  const caseInfo = attempt.case || {};
  el.caseTitle.textContent = caseInfo.title || "Your case";
  document.title = `Debrief · ${caseInfo.title || "Leo"}`;

  const turns = attempt.messages?.filter((m) => m.role === "candidate").length ?? 0;
  const parts = [
    `${turns} candidate turn${turns === 1 ? "" : "s"}`,
    `${titleCase(attempt.mode)} mode`,
    caseInfo.difficulty ? `${titleCase(caseInfo.difficulty)} difficulty` : null,
  ].filter(Boolean);
  el.subtitle.textContent = parts.join(" · ");

  if (report?.executive_summary) {
    el.executiveSummaryBox.classList.remove("hidden");
    el.executiveSummary.textContent = report.executive_summary;
  } else {
    el.executiveSummaryBox.classList.add("hidden");
  }

  // Overall Score (out of 5)
  const score = overall?.overall ?? report?.overall_score;
  if (score === null || score === undefined || isNaN(score) || score <= 0) {
    el.overallScore.textContent = "–";
    el.overallNote.textContent = "Not enough assessable work in this attempt.";
    el.mbbRatingBadge.textContent = "Not Assessed";
    el.mbbRatingBadge.className = "mbb-badge";
    return;
  }

  const scoreNum = Number(score);
  el.overallScore.textContent = scoreNum.toFixed(1);

  const badgeText = report?.mbb_rating_badge || computeMbbRatingBadge(scoreNum);
  el.mbbRatingBadge.textContent = badgeText;
  el.mbbRatingBadge.className = `mbb-badge ${getMbbBadgeClass(badgeText)}`;

  const assessed = overall?.assessed_dimensions || [];
  const excluded = overall?.excluded_dimensions || [];
  const assessedLabels = assessed.map((name) => DIMENSION_LABELS[name] || name).join(", ");
  const excludedNote = excluded.length
    ? ` Weight redistributed across assessed dimensions; ${excluded.map((n) => DIMENSION_LABELS[n] || n).join(", ")} had no assessable work.`
    : "";
  el.overallNote.textContent = assessed.length
    ? `Weighted mean of ${assessedLabels}.${excludedNote}`
    : "Calibrated BCG 1.0–5.0 evaluation score.";
}
```

4. **Section 2: What The Case Wanted To Test Renderer**:
```javascript
function renderCaseEssence(essence) {
  if (!essence || typeof essence !== "object" || Object.keys(essence).length === 0) {
    el.essenceCard.classList.add("hidden");
    return;
  }
  const hasContent = Boolean(
    essence.core_mechanism ||
    essence.commercial_concept ||
    essence.pivotal_insight ||
    essence.candidate_performance_summary ||
    essence.candidate_vs_optimal_gap
  );
  if (!hasContent) {
    el.essenceCard.classList.add("hidden");
    return;
  }

  el.essenceCard.classList.remove("hidden");
  el.essenceMechanism.textContent = essence.core_mechanism || "Not specified";
  el.essenceConcept.textContent = essence.commercial_concept || "Not specified";
  el.essenceInsight.textContent = essence.pivotal_insight || "Not specified";
  el.essencePerformance.textContent = essence.candidate_performance_summary || "Not assessed";
  el.essenceGap.textContent = essence.candidate_vs_optimal_gap || "Not assessed";
}
```

5. **Section 3: Dimension Card Renderer (/5 scale)**:
```javascript
function renderDimension(dimension) {
  const card = node("article", "card dimension-card");

  const header = node("header");
  header.append(node("p", "dimension-name", DIMENSION_LABELS[dimension.name] || titleCase(dimension.name)));
  const scoreLine = node("div", "dimension-score-line");
  const rounded = Math.round(Number(dimension.score || 0) * 10) / 10;
  scoreLine.append(
    node("span", "dimension-score", rounded.toFixed(1)),
    node("span", "dimension-out-of", "/5"),
  );
  header.append(scoreLine);
  card.append(header);

  const track = node("div", "score-track", "");
  const fill = node("span", "score-fill");
  const fillPct = Math.max(0, Math.min(5, Number(dimension.score || 0))) / 5 * 100;
  fill.style.width = `${fillPct}%`;
  track.setAttribute("role", "meter");
  track.setAttribute("aria-valuemin", "1");
  track.setAttribute("aria-valuemax", "5");
  track.setAttribute("aria-valuenow", String(rounded.toFixed(1)));
  track.setAttribute("aria-label", `${DIMENSION_LABELS[dimension.name] || dimension.name} score`);
  track.append(fill);
  card.append(track);

  const bands = node("div", "dimension-bands");
  const bandClass = String(dimension.band || "").toLowerCase().replace(/[\s%]+/g, "-");
  bands.append(node("span", `band band-${bandClass}`, dimension.band || "Not Assessed"));
  bands.append(node("span", `confidence-chip${dimension.confidence === "low" ? " is-low" : ""}`, `${dimension.confidence || "medium"} confidence`));
  card.append(bands);

  if (dimension.observations?.length) {
    const section = node("div", "dimension-section");
    section.append(node("p", "dimension-label", "What Leo saw"));
    const list = node("ul", "dimension-list");
    list.replaceChildren(...dimension.observations.map((t) => node("li", null, t)));
    section.append(list);
    card.append(section);
  }

  if (dimension.improvements?.length) {
    const section = node("div", "dimension-section");
    section.append(node("p", "dimension-label", "Do differently"));
    const list = node("ul", "dimension-list is-improvements");
    list.replaceChildren(...dimension.improvements.map((t) => node("li", null, t)));
    section.append(list);
    card.append(section);
  }

  for (const citation of dimension.evidence || []) card.append(evidenceBlock(citation));
  return card;
}
```

6. **Section 4: Golden MBB Rewrites Renderer**:
```javascript
function renderGoldenRewrites(rewrites) {
  if (!rewrites || !Array.isArray(rewrites) || rewrites.length === 0) {
    el.goldenRewritesSection.classList.add("hidden");
    return;
  }
  el.goldenRewritesSection.classList.remove("hidden");
  el.goldenRewritesList.replaceChildren(
    ...rewrites.map((item) => {
      const card = node("div", "rewrite-item-card");

      const head = node("div", "rewrite-item-head");
      const phase = item.phase || item.stage || "Turn comparison";
      head.append(node("span", "rewrite-phase-badge", titleCase(phase)));
      card.append(head);

      const comparison = node("div", "rewrite-comparison");

      // Candidate Turn
      const candCol = node("div", "rewrite-col candidate-turn");
      candCol.append(node("p", "rewrite-col-label", "What You Said"));
      const candText = item.candidate_turn || "(No spoken turn recorded)";
      candCol.append(node("blockquote", "rewrite-speech candidate-speech", `“${candText}”`));
      if (item.candidate_message_index !== null && item.candidate_message_index !== undefined) {
        candCol.append(node("p", "evidence-ref", `Message ${item.candidate_message_index + 1}`));
      }
      comparison.append(candCol);

      // MBB Partner Turn
      const partnerCol = node("div", "rewrite-col partner-turn");
      partnerCol.append(node("p", "rewrite-col-label", "How an MBB Partner Would Deliver It"));
      const partnerText = item.mbb_partner_turn || item.golden_mbb_turn || "Clear, hypothesis-driven synthesized communication.";
      partnerCol.append(node("blockquote", "rewrite-speech partner-speech", `“${partnerText}”`));
      comparison.append(partnerCol);

      card.append(comparison);

      // Diagnostic Notes / Craft Delta
      const notes = item.diagnostic_notes || item.consulting_craft_delta || [];
      if (notes.length) {
        const notesBlock = node("div", "diagnostic-notes");
        notesBlock.append(node("p", "dimension-label", "Consulting Craft Delta"));
        const list = node("ul", "diagnostic-list");
        list.replaceChildren(...notes.map((n) => node("li", null, n)));
        notesBlock.append(list);
        card.append(notesBlock);
      }

      return card;
    })
  );
}
```

7. **Section 5 & 6: Headline Strengths & Areas for Development Renderers**:
```javascript
function renderStrengths(strengths) {
  if (!strengths || !strengths.length) {
    el.strengths.replaceChildren(node("li", "empty-note", "No distinct strengths were recorded for this attempt."));
    return;
  }
  el.strengths.replaceChildren(
    ...strengths.map((item) => {
      const row = node("li", "takeaway-item strength-entry");
      if (typeof item === "string") {
        row.append(node("p", "takeaway-title", item));
      } else {
        const body = node("div", "takeaway-content");
        body.append(node("p", "takeaway-title", item.claim || "Strength"));
        if (item.verbatim_quote) {
          body.append(node("blockquote", "takeaway-quote", `“${item.verbatim_quote}”`));
        }
        if (item.impact) {
          body.append(node("p", "takeaway-impact", item.impact));
        }
        row.append(body);
      }
      return row;
    })
  );
}

function renderAreasForDevelopment(areas) {
  if (!areas || !areas.length) {
    el.priorities.replaceChildren(node("li", "empty-note", "Nothing pressing was flagged this time."));
    return;
  }
  el.priorities.replaceChildren(
    ...areas.map((item) => {
      const row = node("li", "takeaway-item priority-entry");
      if (typeof item === "string") {
        row.append(node("p", "takeaway-title", item));
      } else {
        const body = node("div", "takeaway-content");
        const titleRow = node("div", "takeaway-header-row");
        titleRow.append(node("span", "takeaway-title", item.gap || "Area for improvement"));
        if (item.priority) {
          const pClass = `priority-badge is-${String(item.priority).toLowerCase()}`;
          titleRow.append(node("span", pClass, `${titleCase(item.priority)} priority`));
        }
        body.append(titleRow);
        if (item.corrective_guidance) {
          body.append(node("p", "takeaway-guidance", item.corrective_guidance));
        }
        row.append(body);
      }
      return row;
    })
  );
}
```

8. **Section 7: Action Plan Renderer (Drill + Readings)**:
```javascript
function renderActionPlan(drillDetail, nextDrill, readings) {
  // 1. Drill
  if (drillDetail && typeof drillDetail === "object") {
    el.drillContainer.classList.remove("hidden");
    el.drillTitle.textContent = drillDetail.title || "Targeted Skill Drill";
    el.drillFocus.textContent = drillDetail.focus_area || "Case Craft";
    const duration = drillDetail.duration_seconds
      ? `${Math.round(drillDetail.duration_seconds / 60)} min drill`
      : "2 min drill";
    el.drillDuration.textContent = duration;
    el.drill.textContent = drillDetail.prompt || "Practise opening hypotheses on next case.";
  } else if (nextDrill && typeof nextDrill === "string") {
    el.drillContainer.classList.remove("hidden");
    el.drillTitle.textContent = "Next Recommended Drill";
    el.drillFocus.textContent = "Focus Area";
    el.drillDuration.textContent = "2 min drill";
    el.drill.textContent = nextDrill;
  } else {
    el.drillContainer.classList.add("hidden");
  }

  // 2. Suggested Readings
  if (readings && Array.isArray(readings) && readings.length) {
    el.readingsContainer.classList.remove("hidden");
    el.readingsList.replaceChildren(
      ...readings.map((reading) => {
        const li = node("li", "reading-item");
        if (typeof reading === "string") {
          const readableName = reading.split("/").pop().replace(/_/g, " ").replace(".md", "");
          li.append(node("span", "reading-title", titleCase(readableName)));
          li.append(node("span", "reading-path", reading));
        } else {
          li.append(node("span", "reading-title", reading.title || "Recommended Reading"));
          if (reading.path) {
            li.append(node("span", "reading-path", reading.path));
          }
          const why = reading.why_relevant || reading.relevance_reason;
          if (why) {
            li.append(node("p", "reading-why", why));
          }
        }
        return li;
      })
    );
  } else {
    el.readingsContainer.classList.add("hidden");
  }
}
```

---

### 5.3 CSS Specification (`app/static/debrief.css`)

```css
/* --- Executive Badges & Summary --- */
.mbb-rating-container {
  margin: 6px 0 4px;
}

.mbb-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: var(--r-pill);
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid transparent;
}

.mbb-badge.badge-distinction {
  background: var(--gold-light);
  color: var(--gold-deep);
  border-color: var(--gold-primary);
}

.mbb-badge.badge-strong-pass {
  background: var(--status-success-bg);
  color: var(--status-success);
  border-color: var(--status-success);
}

.mbb-badge.badge-meets-bar {
  background: var(--status-info-bg);
  color: var(--status-info);
  border-color: var(--status-info);
}

.mbb-badge.badge-developing {
  background: var(--status-warning-bg);
  color: var(--status-warning);
  border-color: var(--status-warning);
}

.mbb-badge.badge-needs-practice {
  background: var(--status-danger-bg);
  color: var(--status-danger);
  border-color: var(--status-danger);
}

.executive-summary-box {
  margin-top: 14px;
  padding: 12px 16px;
  border-left: 3.5px solid var(--brand-primary);
  background: var(--bg-sunken);
  border-radius: 0 var(--r-md) var(--r-md) 0;
}

.executive-summary {
  font-family: var(--font-serif);
  font-size: 15.5px;
  line-height: 1.5;
  color: var(--ink-primary);
  margin: 0;
}

/* --- Section 2: Case Essence Card --- */
.essence-card {
  margin-bottom: 22px;
  border: 1px solid var(--line-strong);
}

.section-title {
  font-family: var(--font-serif);
  font-weight: 500;
  font-size: clamp(20px, 2.5vw, 24px);
  margin: 4px 0 2px;
}

.essence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.essence-block {
  padding: 12px 14px;
  background: var(--bg-sunken);
  border: 1px solid var(--line-subtle);
  border-radius: var(--r-md);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.essence-block.is-highlight {
  background: var(--brand-light);
  border-color: var(--brand-tint-hover);
}

.essence-label {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-muted);
}

.essence-text {
  font-size: 13.5px;
  line-height: 1.45;
  color: var(--ink-primary);
  margin: 0;
}

/* --- Section 4: Golden Rewrites --- */
.rewrites-card {
  margin-bottom: 22px;
}

.rewrites-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 14px;
}

.rewrite-item-card {
  border: 1px solid var(--line-base);
  border-radius: var(--r-md);
  padding: 16px;
  background: var(--bg-surface);
}

.rewrite-phase-badge {
  display: inline-block;
  padding: 3px 9px;
  background: var(--gold-soft);
  color: var(--gold-deep);
  font-size: 11px;
  font-weight: 700;
  border-radius: var(--r-pill);
  letter-spacing: 0.03em;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.rewrite-comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

@media (max-width: 768px) {
  .rewrite-comparison {
    grid-template-columns: 1fr;
  }
}

.rewrite-col {
  padding: 12px 14px;
  border-radius: var(--r-md);
}

.rewrite-col.candidate-turn {
  background: var(--bg-sunken);
  border: 1px solid var(--line-base);
}

.rewrite-col.partner-turn {
  background: var(--brand-light);
  border: 1px solid var(--brand-tint-hover);
}

.rewrite-col-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-muted);
  margin: 0 0 6px 0;
}

.partner-turn .rewrite-col-label {
  color: var(--brand-primary);
}

.rewrite-speech {
  font-family: var(--font-serif);
  font-size: 14.5px;
  line-height: 1.5;
  margin: 0;
}

.partner-speech {
  color: var(--brand-deep);
  font-weight: 500;
}

:root[data-theme="dark"] .partner-speech {
  color: var(--ink-primary);
}

.diagnostic-notes {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--line-dashed);
}

.diagnostic-list {
  list-style: disc;
  padding-left: 18px;
  margin: 4px 0 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.diagnostic-list li {
  font-size: 13px;
  line-height: 1.4;
  color: var(--ink-secondary);
}

/* --- Section 5 & 6 Takeaway Enhancements --- */
.takeaway-entry {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.takeaway-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.takeaway-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--ink-primary);
  margin: 0;
}

.takeaway-quote {
  font-family: var(--font-serif);
  font-style: italic;
  font-size: 13.5px;
  color: var(--ink-secondary);
  margin: 4px 0 0;
  padding-left: 8px;
  border-left: 2px solid var(--brand-lift);
}

.takeaway-impact,
.takeaway-guidance {
  font-size: 13px;
  line-height: 1.4;
  color: var(--ink-muted);
  margin: 2px 0 0;
}

.priority-badge {
  font-size: 10.5px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--r-pill);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.priority-badge.is-high {
  background: var(--status-danger-bg);
  color: var(--status-danger);
}

.priority-badge.is-medium {
  background: var(--status-warning-bg);
  color: var(--status-warning);
}

.priority-badge.is-low {
  background: var(--bg-subtle);
  color: var(--ink-muted);
}

/* --- Section 7: Action Plan & Suggested Readings --- */
.action-plan-card {
  margin-bottom: 22px;
}

.action-plan-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 14px;
}

@media (max-width: 768px) {
  .action-plan-grid {
    grid-template-columns: 1fr;
  }
}

.drill-container {
  padding: 14px;
  border: 1px solid var(--line-base);
  border-radius: var(--r-md);
  background: var(--bg-sunken);
}

.drill-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.drill-meta {
  display: flex;
  gap: 6px;
}

.drill-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: var(--r-pill);
  background: var(--brand-light);
  color: var(--brand-primary);
}

.drill-duration {
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  padding: 2px 7px;
  border-radius: var(--r-pill);
  background: var(--gold-soft);
  color: var(--gold-deep);
}

.drill-title {
  font-size: 14.5px;
  font-weight: 700;
  margin: 4px 0 6px;
}

.drill-prompt {
  font-size: 13.5px;
  line-height: 1.45;
  color: var(--ink-secondary);
  margin: 0;
}

.readings-container {
  padding: 14px;
  border: 1px solid var(--line-base);
  border-radius: var(--r-md);
  background: var(--bg-surface);
}

.readings-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reading-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line-subtle);
}

.reading-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.reading-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ink-primary);
}

.reading-path {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--ink-muted);
}

.reading-why {
  font-size: 12.5px;
  color: var(--ink-secondary);
  margin: 2px 0 0;
}
```

---

## 6. Robustness & Partial Data Handling Matrix

| Scenario / Field | Evaluator Output | UI Behavior | Error Guarding |
|---|---|---|---|
| `what_the_case_wanted_to_test` | `null` or `{}` | `#essence-card` gets `.hidden` class | `if (!essence || !hasContent) el.essenceCard.classList.add("hidden");` |
| `golden_rewrites` | `null` or `[]` | `#golden-rewrites-section` gets `.hidden` class | `if (!rewrites || !rewrites.length) el.goldenRewritesSection.classList.add("hidden");` |
| `strengths` | `[]` or missing | Renders `.empty-note`: "No distinct strengths were recorded for this attempt." | `if (!strengths.length) ...` |
| `areas_for_development` | `[]` or missing | Renders `.empty-note`: "Nothing pressing was flagged this time." | `if (!areas.length) ...` |
| `targeted_drill` | `null` or `""` | Hides drill container or shows default prompt | `if (!drillDetail && !nextDrill) ...` |
| `suggested_readings` | `null` or `[]` | Hides readings container | `if (!readings || !readings.length) ...` |
| `dimension.score` | `0` or `null` | Renders `0.0 / 5`, 0% meter fill width | `Math.max(0, Math.min(5, Number(score || 0))) / 5 * 100` |
| `overall.overall` | `null` / `undefined` | Displays `– / 5` with explanation note | `el.overallScore.textContent = "–"` |
| Malicious strings in quotes | Contains `<script>alert(1)</script>` | Safe text rendering via `textContent` | Zero dynamic `innerHTML` on user/model strings |

---

## 7. Verification Method & Test Plan

### Test Strategy:
1. **Existing Test Suite**:
   Run `uv run pytest` to ensure all 175 baseline tests continue to pass.
2. **Updated debrief UI Test Suite (`tests/test_debrief_ui.py`)**:
   - `test_t1_all_debrief_static_assets_exist`: Verifies asset files exist.
   - `test_t1_debrief_html_executive_header_card`: Verifies `#case-title`, `#overall-score`, `#mbb-rating-badge`, `#executive-summary`.
   - `test_t1_debrief_html_masterclass_essence_card`: Verifies `#essence-card`, `#essence-mechanism`, `#essence-insight`.
   - `test_t1_debrief_html_dimension_grid_and_synthesis`: Verifies `#dimension-grid` and 5 dimensions in `DIMENSION_LABELS`.
   - `test_t1_debrief_html_golden_rewrites_section`: Verifies `#golden-rewrites-section`, `#golden-rewrites-list`.
   - `test_t1_debrief_html_takeaways_and_strengths_cards`: Verifies `#strengths-card`, `#priorities-card`.
   - `test_t1_debrief_html_action_plan_and_readings`: Verifies `#action-plan-card`, `#drill-text`, `#readings-list`.
   - `test_t2_scale_is_out_of_five`: Verifies `/5` in HTML and JS (no `/10` in score displays).
   - `test_t2_debrief_js_xss_protection_uses_textcontent`: Ensures all text insertions use `textContent`.
   - `test_t3_debrief_page_route_serves_html`: Confirms authenticated endpoint serves HTML with all 7 section containers.

---

## 8. Summary of Action Items for Implementation Agent

1. **`app/static/debrief.html`**:
   - Update overall score out of from `/10` to `/5`.
   - Add `#executive-summary-box` & `#mbb-rating-badge` to header.
   - Insert Section 2 `#essence-card`.
   - Insert Section 4 `#golden-rewrites-section`.
   - Wrap Takeaways with Section 5 `#strengths-card` and Section 6 `#priorities-card`.
   - Insert Section 7 `#action-plan-card` with `#drill-container` and `#readings-list`.
2. **`app/static/debrief.js`**:
   - Add `synthesis: "Synthesis & recommendation"` to `DIMENSION_LABELS`.
   - Update `el` queries for all new section containers and sub-elements.
   - Update `renderDimension` to use `/5` scale, `aria-valuemax="5"`, and fill formula `(score / 5) * 100%`.
   - Implement `renderExecutiveHeader`, `renderCaseEssence`, `renderGoldenRewrites`, `renderStrengths`, `renderAreasForDevelopment`, and `renderActionPlan`.
   - Wire all renderers into `renderReport` with full null/empty safety.
3. **`app/static/debrief.css`**:
   - Add styling rules for MBB badges, Executive summary callout, Masterclass essence grid, Golden rewrites dual columns, Takeaway rich items with priority badges, and Action Plan drill/reading cards.
   - Ensure complete light/dark theme compliance and mobile responsiveness.
4. **`tests/test_debrief_ui.py`**:
   - Extend test suite to validate all 7 section containers, the 5 dimension keys, and the `/5` scale.
