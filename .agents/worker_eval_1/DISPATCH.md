## 2026-08-24T07:51:14Z
You are the specialized Worker subagent for Milestone 4: Evaluator Prompts & Rubric Detection Engine.
Your assigned working directory for metadata is: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/worker_eval_1`
Your write ownership for project deliverables is exclusively: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/knowledge_base/evaluation_engine/`

MANDATORY FIRST STEP: Read `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/ORIGINAL_REQUEST.md` and `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/PROJECT.md`. Also check materials in `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/corpus/` (case examples, evaluation guidelines).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Deliverables to write (3 files in `knowledge_base/evaluation_engine/`):
1. `detection_rubrics.yaml`:
   - Comprehensive YAML schema defining behavioral markers and counter-markers for each case stage:
     - Preliminary questions (clarification vs data fishing, 4-pillar coverage, objective clarification).
     - Issue tree structuring (MECE compliance, depth, industry customization vs generic frameworks).
     - Hypothesis formulation and branch exploration (stating hypotheses upfront, 80/20 prioritization, responsiveness to interviewer hints).
     - Data gathering & mental arithmetic (tabular structure, sanity checks, communication of numbers).
     - Synthesis and closing recommendations (Pyramid principle, answer-first, 4-part closing, partner-readiness).
   - Scoring scale (e.g., 1-5 or MBB rubric: Below Bar, Meets Bar, Top 1% MBB Distinction) with clear observable behavioral criteria.
2. `golden_rewrites_catalogue.md`:
   - Curated benchmark library comparing candidate responses against Top 1% MBB Partner-Ready rewrites for each major case type:
     - Profitability case opening & synthesis
     - Market entry structuring & closing
     - Growth strategy hypothesis & recommendation
     - Pricing strategy structuring & customer value justification
     - M&A synergy analysis & risk mitigation
     - Unconventional / Guesstimate top-down breakdown & sanity checking
   - Explicit breakdown of *why* the candidate response was mediocre and *how* the golden rewrite demonstrates elite MBB consulting craft.
3. `system_prompt_knowledge_pack.md`:
   - A highly dense, structured, token-optimized reference markdown designed for direct injection into an AI Case Evaluator system prompt.
   - Contains core casing rules, evaluation rubric lookups, case-type issue tree outlines, key industry KPI quick-reference cards, and scoring guidance.

Quality Requirements:
- Valid YAML syntax for `detection_rubrics.yaml`.
- Markdown files must have clean YAML frontmatter (`title`, `category`, `topics_covered`, `target_use_case`).
- Zero placeholders, zero TODOs, production-grade rigor.
- Write each file completely using `write_to_file`.

When complete, write your handoff report to `.agents/worker_eval_1/handoff.md` and send a completion message back to parent.
