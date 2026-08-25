# Original User Request

## 2026-08-24T09:26:35Z

Upgrade the interactive debrief web interface (`app/static/debrief.html`, `debrief.js`, `debrief.css`) to render the full 10x Masterclass Debrief Report that the backend evaluator already generates and returns via `GET /api/attempts/{id}/evaluation`. The backend evaluator engine, database persistence, API endpoints, and all case corpus content are complete and tested (175 tests passing). The frontend is the remaining gap: it still renders the old v1 layout with a /10 scale and is missing 4 of the 7 masterclass sections.

Working directory: /Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2
Integrity mode: development

## Context: What Already Works (Do Not Break)

The backend API at `GET /api/attempts/{id}/evaluation` returns a JSON payload with this structure (see `app/evaluator.py` for the full Pydantic schema):

```
{
  "report": {
    "attempt_id": "...",
    "executive_summary": "2-sentence partner read...",
    "overall_score": 3.9,          // BCG 1.0-5.0 scale
    "mbb_rating_badge": "Strong Pass",
    "what_the_case_wanted_to_test": {
      "core_mechanism": "...",
      "commercial_concept": "...",
      "pivotal_insight": "...",
      "candidate_performance_summary": "...",
      "candidate_vs_optimal_gap": "..."
    },
    "dimensions": [
      {
        "name": "structuring",     // also: problem_solving, quantitative, synthesis, communication
        "score": 3.4,              // 1.0-5.0
        "band": "Meets Bar",       // Below Bar | Meets Bar | Top 1% MBB
        "evidence": [{"message_index": 2, "quote": "..."}],
        "observations": ["..."],
        "improvements": ["..."],
        "confidence": "high",
        "notes": "..."
      }
    ],
    "golden_rewrites": [
      {
        "phase": "opening",        // or "closing" or "synthesis"
        "candidate_turn": "...",
        "mbb_partner_turn": "...",
        "diagnostic_notes": ["..."]
      }
    ],
    "strengths": [
      {"claim": "...", "verbatim_quote": "...", "impact": "..."}
    ],
    "areas_for_development": [
      {"gap": "...", "priority": "high", "corrective_guidance": "..."}
    ],
    "targeted_drill": {
      "title": "...",
      "duration_seconds": 120,
      "prompt": "...",
      "focus_area": "..."
    },
    "suggested_readings": ["knowledge_base/methodology/02_issue_tree_structuring.md", ...],
    "checklist": [
      {"title": "...", "status": "demonstrated", "note": "...", "evidence": [...]}
    ],
    "evaluator_version": "evaluator-v2|rubric=rubric-v2|..."
  },
  "overall": {
    "overall": 3.9,
    "assessed_dimensions": ["structuring", "problem_solving", ...],
    "excluded_dimensions": []
  }
}
```

Also: `GET /api/attempts/{id}` returns the attempt metadata (case title, difficulty, messages, mode, etc.). Both endpoints are auth-guarded and working.

The existing `debrief.html`, `debrief.js`, and `debrief.css` are the starting point — they have the topbar, loading states, error states, auth flow, theme toggle, and toast system already working. The upgrade must preserve all of that and extend it.

## Requirements

### R1. Fix the scoring scale from /10 to /5 across the entire debrief UI
The overall score display currently shows `/10`. It must show `/5`. The dimension score bars must use a 1.0-5.0 range (aria-valuemax="5", fill width = score/5 * 100%). The `DIMENSION_LABELS` map in `debrief.js` must include all 5 dimensions: `structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`.

### R2. Render all 7 masterclass sections in the debrief report
The debrief page must render these 7 sections in order, each as a visually distinct card or section. The data for all sections comes from the API payload described above:

1. **Executive Header**: Overall score badge (out of 5.0), MBB rating badge (Distinction / Strong Pass / Meets Bar / Developing / Needs Substantial Practice), executive summary text.
2. **"What This Case Really Wanted to Test"**: Core mechanism, pivotal insight, candidate performance summary, candidate-vs-optimal gap. This is the new masterclass reveal card.
3. **5 Core Dimension Cards**: Each with score bar (1-5), band badge, verbatim evidence blockquotes, observations, and improvements.
4. **Golden MBB Rewrites**: For each rewrite (opening and closing), show a side-by-side or stacked comparison of "What You Said" (candidate_turn) vs "How an MBB Partner Would Deliver It" (mbb_partner_turn), plus diagnostic notes.
5. **Headline Strengths**: Each strength with the claim, a verbatim transcript quote, and impact note.
6. **Areas for Development**: Each with the gap description, priority badge (high/medium/low), and corrective guidance.
7. **Action Plan**: Targeted drill (title, duration, prompt, focus area) and suggested readings list.

The observed behaviours checklist that already renders should remain at the bottom.

### R3. The debrief page must remain fully functional with partial or missing report fields
The backend may return reports where some fields are empty arrays, null, or missing (e.g. no golden_rewrites, no suggested_readings, quantitative dimension with score 0). The UI must gracefully hide or show "Not assessed" placeholders for missing sections. No JavaScript errors on partial data.

### R4. Visual design must be consistent with existing design system
The existing `tokens.css` design system (CSS custom properties for colors, spacing, typography) and the light/dark theme toggle in `theme.js` must be respected. New cards should use the existing `.card` class patterns and color tokens. The layout should be responsive and readable on both desktop and mobile.

## Acceptance Criteria

### Scale Correctness
- [ ] The overall score displays as `X.X / 5` (not /10) in the header
- [ ] Each dimension score bar uses `aria-valuemax="5"` and fills proportionally to score/5
- [ ] All 5 dimension names appear in `DIMENSION_LABELS`: structuring, problem_solving, quantitative, synthesis, communication

### Section Completeness
- [ ] "What This Case Really Wanted to Test" card renders when `what_the_case_wanted_to_test` is present in the API response
- [ ] Golden Rewrites section renders candidate_turn vs mbb_partner_turn for each phase, with diagnostic_notes
- [ ] Strengths section renders claim + verbatim_quote + impact for each StrengthItem
- [ ] Areas for Development section renders gap + priority badge + corrective_guidance for each DevelopmentAreaItem
- [ ] Targeted Drill section renders title, duration, prompt, and focus_area from the TargetedDrillPayload
- [ ] Suggested Readings renders as a list of readable file paths or names

### Robustness
- [ ] No JavaScript console errors when any section's data is null, undefined, empty array, or missing from the API response
- [ ] Sections with no data either hide completely or show a graceful placeholder

### Design & Accessibility
- [ ] All new sections respect `tokens.css` custom properties and work in both light and dark themes
- [ ] Score bars have proper ARIA meter attributes
- [ ] All text content is inserted via `textContent` (no innerHTML with user/model data) — XSS safety preserved

### Testing
- [ ] All existing tests continue to pass (`uv run pytest` — currently 175 passing)
- [ ] New/updated tests verify the HTML structure includes containers for all 7 sections
- [ ] New/updated tests verify the JS DIMENSION_LABELS includes all 5 dimension keys
