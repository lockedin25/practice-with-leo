# Frontend Debrief UI & Integration — Comprehensive Survey Report

**Date**: 2026-08-24  
**Author**: Explorer 3 (Frontend Debrief UI & Integration)  
**Target Repository**: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2`  
**Working Directory**: `.agents/explorer_survey_frontend/`  

---

## 1. Executive Summary

This report documents the architectural survey, frontend asset inspection, design token system analysis, and gap analysis for upgrading the post-attempt debrief interface into the **10x Interactive MBB Debrief Engine**.

### Current State:
- The current debrief interface (`app/static/debrief.html`, `app/static/debrief.css`, `app/static/debrief.js`) is an early prototype built around a 0–10 scoring scale and 4 generic consulting dimensions (`structuring`, `problem_solving`, `communication`, `quantitative`).
- It renders a simple overall score, basic bullet-list takeaways (headline strengths, priority improvements, next drill), a 4-dimension grid with progress bars, and a static behavior checklist.
- The UI fetches data concurrently from `/api/attempts/{attempt_id}` and `/api/attempts/{attempt_id}/evaluation`.

### Critical Gaps:
- **0 out of the 3 new marquee cards** ("What This Case Really Wanted to Test" Masterclass Card, Golden MBB Rewrites Comparison, Clickable Knowledge Base Suggested Readings) are implemented.
- The scoring system is calibrated on a legacy 0–10 scale instead of the required **BCG 1.0–5.0 scale**.
- The 5th core consulting dimension (**`synthesis`**) is entirely missing from the frontend dictionary and layout.
- The Executive Header lacks the required **MBB Rating Badge** (e.g. *Strong Pass*, *Meets Bar*, *Distinction*) and **2-Sentence Executive Summary**.
- The Behaviors Checklist is static and lacks interactive filter tabs/counters and MBB behavioral flags/severity tags.

---

## 2. File Inventory & Frontend Asset Structure

| File Path | Size (Bytes) | Role & Status | Key Observations |
|---|---|---|---|
| `app/static/debrief.html` | 6,940 | Debrief HTML Template / View | Contains topbar, state overlays (loading/error/retry), header, takeaways section, dimension grid, and checklist. Missing masterclass card, golden rewrites, and readings. |
| `app/static/debrief.css` | 7,973 | Debrief Page Styles | Uses legacy CSS variable aliases (`--paper`, `--surface`, `--brand`, `--clay`) alongside `tokens.css`. Needs modernization to token system and new component classes. |
| `app/static/debrief.js` | 11,285 | Debrief Logic & DOM Renderer | Fetches attempt and evaluation in parallel via `Promise.all`. Hardcodes 4 dimensions, 10-point scale, and basic string rendering. |
| `app/static/tokens.css` | 9,234 | Global Design Tokens | Standardized Warm Luxury Editorial palette (Light) and Crisp Bioluminescent Emerald / Topaz (Dark). Font definitions, radii, elevations, transition curves. |
| `app/static/styles.css` | 38,642 | Core Application Styles | Shared base elements, topbar, buttons, user menus, cards, chat room, and utility classes. |
| `app/static/theme.js` | 1,096 | Shared Theme Toggle Script | Persists `casecall:theme` in `localStorage`, syncs `data-theme` attribute on `<html>`, binds `#theme-toggle` and `.theme-toggle-btn`. |
| `app/static/profile.html` / `profile.js` | 8,121 / 11,469 | User Progress & Practice History | Already implements 1–5 scoring visualization (`row.average_score / 5`), displays historical attempts and debrief links. |
| `app/static/admin.html` / `admin.js` | 7,856 / 17,942 | Admin Console & Attempt Drawer | Displays debrief summary in administrative drawer (currently hardcodes `/10`). |

---

## 3. Backend Integration & Data Flow

### 3.1. Route & Invocation Flow
1. User navigates to `/attempts/{attempt_id}/debrief`.
2. `app/main.py` (`debrief_page` at line 158) checks user authentication (`current_user(request)`). If authenticated, serves `app/static/debrief.html`; otherwise redirects to `/login?next=/attempts/{attempt_id}/debrief`.
3. `debrief.js` reads `state.attemptId = window.location.pathname.split("/")[2]` and issues two parallel HTTP GET requests:
   ```javascript
   const [attempt, evaluation] = await Promise.all([
     request(`/api/attempts/${state.attemptId}`),
     request(`/api/attempts/${state.attemptId}/evaluation`),
   ]);
   ```
4. `/api/attempts/{attempt_id}` returns the candidate view of the session:
   - `attempt.id`: UUID string
   - `attempt.case`: Catalogue item (`title`, `category`, `industry`, `difficulty`, `supported_durations`, `skills_tested`)
   - `attempt.mode`: `"coached" | "realistic" | "pressure"`
   - `attempt.stage`: Active phase ID
   - `attempt.messages`: Full transcript array `[{role, content}]`
   - `attempt.facts`: Disclosed facts array `[{id, content}]`
   - `attempt.ended`: Boolean
5. `/api/attempts/{attempt_id}/evaluation` returns the evaluation report payload:
   - `evaluator_version`: String (e.g. `"evaluator-v2"`)
   - `created_at`: ISO timestamp string
   - `overall`: Overall score calculation object (`overall`, `rating_badge`, `band`, `assessed_dimensions`, `excluded_dimensions`)
   - `report`: The full structured `EvaluationReport`

### 3.2. Error & Lifecycle States
`debrief.js` gracefully handles HTTP status codes:
- **HTTP 401**: Redirects to `/login?next=...`
- **HTTP 409**: Shows state overlay: *"This practice has not ended yet. Finish the case with Leo first."*
- **HTTP 404**: Shows state overlay: *"Debrief not found. This attempt does not exist under your account."*
- **HTTP 503**: Shows retry overlay: *"Leo is still marking this case. The evaluator could not finish just now."* with a "Check again" button.

---

## 4. Comprehensive Gap Analysis: 7 Required 10x Debrief Sections

### Section 1: Executive Header
| Requirement | Current State | Gap & Action Required |
|---|---|---|
| **BCG 1.0–5.0 Score Scale** | Hardcoded `/10` in HTML (`debrief.html:74`) and JS (`overallScore` displays raw value out of 10). | Change display to `X.X / 5.0`. Update score range parsing and ARIA meter bounds. |
| **MBB Rating Badge** | Non-existent. Only displays a text description of assessed dimensions in `#overall-note`. | Add prominent visual badge with calibrated tiers: **Distinction / Partner-Ready (4.5–5.0)**, **Strong Pass (3.8–4.4)**, **Meets Bar (3.0–3.7)**, **Developing (<3.0)**. |
| **Executive Summary** | Non-existent. Subtitle only shows turn count, mode, and difficulty. | Add lead editorial paragraph (`report.executive_summary`) delivering a 2-sentence partner evaluation read. |
| **Metadata Badges** | Minimal string concatenation in `#report-subtitle`. | Format structured metadata pills: Case Title, Industry, Difficulty, Mode, Duration/Turns, Evaluator Version. |

### Section 2: "What This Case Really Wanted to Test" Masterclass Card
| Requirement | Current State | Gap & Action Required |
|---|---|---|
| **Core Economic Mechanism** | Completely absent. | Create editorial Masterclass Card displaying `case_essence.core_mechanism` (e.g., product mix shift, unhedged contract lag, route density collapse). |
| **Pivotal Insight** | Completely absent. | Render highlighted breakthrough "Aha!" callout box (`case_essence.pivotal_insight`). |
| **Candidate Comparison** | Completely absent. | Display comparative breakdown: Top 1% Benchmark Path vs Candidate's Actual Path & Performance. |
| **Common Traps** | Completely absent. | Render 2–3 red herring callouts / framework dumping traps with tags indicating whether candidate avoided or fell into them. |
| **Takeaway Lesson** | Completely absent. | Add durable consulting mental model footer/banner. |

### Section 3: 5 Core Dimension Cards
| Requirement | Current State | Gap & Action Required |
|---|---|---|
| **5 BCG Dimensions** | Only 4 dimensions mapped (`structuring`, `problem_solving`, `communication`, `quantitative`). Missing **`synthesis`**. | Expand `DIMENSION_LABELS` and layout to all 5 BCG dimensions: `structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`. |
| **1.0–5.0 Score Calibration** | Displays `X.X/10` and fills progress bar using `(score) * 10%`. | Calibrate progress fill to `(score / 5.0) * 100%`, score text to `X.X / 5.0`, and ARIA attributes `aria-valuemin="1"` `aria-valuemax="5"`. |
| **Band & Confidence Chips** | Basic bands (`Developing`, `Solid`, `Strong`, `Exceptional`) and confidence indicator exist. | Refine badge styling to match design tokens, with specific color tokens per band. |
| **Verbatim Evidence Blockquotes** | Template exists (`#evidence-template`), but lacks turn speaker context, styled quotation marks, and deep linking. | Polish quote typography (`Newsreader` italic, subtle emerald border-left, message index badge). |
| **Observations & Improvements** | Lists "What Leo saw" and "Do differently". | Retain structured observation lists, ensuring clean iconography and spacing. |

### Section 4: Golden MBB Rewrites Comparison
| Requirement | Current State | Gap & Action Required |
|---|---|---|
| **Side-by-Side Comparison Grid** | Completely absent. | Add `<section class="golden-rewrites-section">` featuring a 2-column comparative layout. |
| **"What You Said" Card** | Completely absent. | Display candidate's verbatim transcript turns from key case moments (Opening/Clarification and Closing Synthesis) with diagnostic critique tags. |
| **"How an MBB Partner Would Deliver It" Card** | Completely absent. | Display top 1% boardroom-grade benchmark rewrite with highlighted consulting techniques. |
| **Diagnostic Notes & Craft Breakdown** | Completely absent. | Include expandable/inline diagnostic callouts detailing value-chain decomposition, hypothesis formulation, Pyramidal structure, and quantitative clarity. |

### Section 5: Strengths & Areas for Development
| Requirement | Current State | Gap & Action Required |
|---|---|---|
| **Split-Card Layout** | Exists as `.debrief-takeaways` with 2 cards, but styling is plain. | Modernize split-card layout into side-by-side executive cards with distinct accent colors (Emerald for Strengths, Amber/Clay for Areas for Development). |
| **Verbatim Evidence for Strengths** | Only renders flat string arrays (`report.headline_strengths`). | Support rich strength items with embedded verbatim quote citations from the transcript. |
| **Prioritized Actionable Guidance** | Only renders flat string arrays (`report.priority_improvements`). | Render numbered priority items with explicit actionable corrective guidance callouts. |

### Section 6: Action Plan & Resources
| Requirement | Current State | Gap & Action Required |
|---|---|---|
| **Next 2-Minute Drill Card** | Rendered as a small text footnote inside the priority improvements card. | Elevate into a dedicated, prominent Action Plan Card featuring a structured 2-minute drill prompt. |
| **Clickable Knowledge Base Readings** | Completely absent. | Render interactive resource cards with category pills (`Industry Deep Dive`, `Methodology`, `Case Archetype`), title, excerpt, and direct links to knowledge base modules (`knowledge_base/industries/...`, `knowledge_base/methodology/...`). |

### Section 7: Observed Behaviors Checklist
| Requirement | Current State | Gap & Action Required |
|---|---|---|
| **Demonstrated / Missed Markers** | Renders static list of items with SVG check/cross/dash icons. | Upgrade with interactive status filter tabs: `All`, `Demonstrated`, `Missed`, `N/A`. |
| **Counters & Summary** | Static legend only. | Add live count badges (e.g. `8 Demonstrated`, `2 Missed`). |
| **Severity Tags & MBB Flags** | No flag rendering. | Support behavioral flags (e.g. `Flag Framework Dumping`, `Flag Data Fishing`, `Flag Missing Unit Sanity`). |
| **Verbatim Evidence per Behavior** | Renders evidence block if present. | Polish evidence layout within checklist rows. |

---

## 5. Design System, Typography & Responsive Styling

### 5.1. Design Tokens Integration
The UI must strictly consume CSS custom properties from `app/static/tokens.css`:

```css
/* Color Tokens */
--bg-base        /* #fbfaf7 (light) | #0b0f10 (dark) */
--bg-surface     /* #ffffff (light) | #121819 (dark) */
--bg-subtle      /* #f4f0e6 (light) | #192123 (dark) */
--bg-sunken      /* #ede8dc (light) | #070a0b (dark) */
--ink-primary    /* #111a18 (light) | #f2f6f4 (dark) */
--ink-secondary  /* #43514c (light) | #b3c0bc (dark) */
--ink-muted      /* #6b7a74 (light) | #80908b (dark) */
--brand-primary  /* #0e453a (light) | #45bf9f (dark) */
--brand-light    /* #e6f3ee (light) | rgba(69,191,159,0.15) */
--gold-primary   /* #c98838 (light) | #e6b162 (dark) */
--gold-soft      /* #f4e3cd (light) | rgba(230,177,98,0.25) */
--status-success /* #15803d (light) | #4ade80 (dark) */
--status-warning /* #b45309 (light) | #fbbf24 (dark) */
--status-danger  /* #b91c1c (light) | #f87171 (dark) */
--status-info    /* #0369a1 (light) | #38bdf8 (dark) */

/* Typography */
--font-sans      /* "Plus Jakarta Sans", sans-serif */
--font-serif     /* "Newsreader", Georgia, serif */
--font-mono      /* "JetBrains Mono", monospace */

/* Radii & Shadows */
--r-sm: 8px; --r-md: 12px; --r-lg: 16px; --r-xl: 24px; --r-pill: 9999px;
--shadow-sm; --shadow-md; --shadow-lg; --shadow-card;
```

### 5.2. Theme Switcher & Dark Mode Support
- `app/static/theme.js` is already loaded in `debrief.html`.
- Theme toggles seamlessly switch between Light and Dark mode by setting `document.documentElement.dataset.theme = 'dark' | 'light'`.
- All cards, borders, text, chips, gradients, and meter fills automatically adapt when using semantic tokens (`--bg-surface`, `--line-base`, `--brand-primary`, etc.).

### 5.3. Responsive Layout Strategy
- **Desktop (>1024px)**:
  - Max container width: `1120px` centered.
  - Golden rewrites: 2-column side-by-side comparison grid (`grid-template-columns: 1fr 1fr`).
  - Takeaways: 2-column split-card (`grid-template-columns: 1fr 1fr`).
  - Dimension cards: 2-column grid (`repeat(auto-fit, minmax(480px, 1fr))`).
- **Tablet (768px – 1024px)**:
  - Golden rewrites: 2-column or stacked with compact padding.
  - Dimension cards: 1-column or 2-column.
- **Mobile (<768px)**:
  - All multi-column grids collapse to single-column (`grid-template-columns: 1fr`).
  - Topbar collapses cleanly; actions wrap or collapse.
  - Score cards, rating badges, and checklist filter buttons stack vertically or scroll horizontally without clipping.

---

## 6. Implementation Blueprint for Worker Agents

To implement the complete 10x Debrief UI cleanly and maintainably:

1. **`app/static/debrief.html` Upgrades**:
   - Modernize topbar to include case library link, profile link, theme toggle, and user menu.
   - Restructure report body into 7 semantic sections:
     1. `<header class="debrief-head">`: Title, metadata chips, overall score out of 5.0, MBB rating badge, and executive summary lead card.
     2. `<section class="masterclass-section">`: Masterclass card ("What This Case Really Wanted to Test") with core mechanism, pivotal insight, candidate comparison, and traps.
     3. `<section class="rewrites-section">`: Side-by-side Golden Rewrites component with Opening and Closing comparisons.
     4. `<section class="takeaways-section">`: Split-card layout for Headline Strengths and Priority Areas for Development.
     5. `<section class="dimensions-section">`: 5 BCG Dimension cards with 1.0–5.0 meter bars, bands, observations, and verbatim citations.
     6. `<section class="action-plan-section">`: 2-Minute Drill card + Suggested Readings resource grid with knowledge base links.
     7. `<section class="checklist-section">`: Interactive Observed Behaviors checklist with filter buttons and severity tags.

2. **`app/static/debrief.css` Upgrades**:
   - Remove deprecated CSS aliases; bind directly to `tokens.css`.
   - Add styles for:
     - `.rating-badge` (.badge-distinction, .badge-strong-pass, .badge-meets-bar, .badge-developing)
     - `.masterclass-card`, `.insight-box`, `.mechanism-pill`, `.trap-item`
     - `.rewrite-grid`, `.candidate-card`, `.partner-card`, `.diagnostic-callout`
     - `.split-takeaway-grid`, `.guidance-callout`
     - `.resource-grid`, `.resource-card`, `.resource-category`
     - `.checklist-filter-bar`, `.flag-tag`
   - Complete mobile/tablet responsive media queries (`@media (max-width: 900px)`, `@media (max-width: 640px)`).

3. **`app/static/debrief.js` Upgrades**:
   - Update `DIMENSION_LABELS` to include `synthesis: "Pyramid Synthesis & Close"`.
   - Map 1.0–5.0 score rendering and rating badge calculation.
   - Implement rendering functions:
     - `renderExecutiveHeader(attempt, payload)`
     - `renderMasterclassCard(whatTheCaseWantedToTest)`
     - `renderGoldenRewrites(goldenRewrites)`
     - `renderTakeaways(strengths, areasForDevelopment)`
     - `renderDimensions(dimensions)`
     - `renderActionPlan(targetedDrill, suggestedReadings)`
     - `renderChecklist(checklistItems)` with interactive filter listeners.

4. **Coordinate with Other Modules**:
   - `app/evaluator.py`: Ensure payload output matches the expected JSON schema.
   - `app/static/profile.js` & `app/static/admin.js`: Verify compatibility with the 1.0–5.0 scale and 5 dimensions.

---

## 7. Survey Verification Summary

All findings in this survey have been verified against the live codebase:
- Static HTML/CSS/JS files: `app/static/debrief.html`, `app/static/debrief.css`, `app/static/debrief.js`, `app/static/tokens.css`, `app/static/styles.css`, `app/static/theme.js`, `app/static/profile.js`, `app/static/admin.js`.
- Server routes: `app/main.py` (`/attempts/{id}/debrief`, `/api/attempts/{id}/evaluation`, `/api/me/profile`).
- Knowledge base assets: `knowledge_base/evaluation_engine/golden_rewrites_catalogue.md`, `knowledge_base/industries/*`, `knowledge_base/methodology/*`, `knowledge_base/case_types/*`.
