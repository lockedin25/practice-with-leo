# Dispatch Record

## 2026-08-24T07:51:14Z
You are the specialized Worker subagent for Milestone 1: Methodology Playbooks.
Your assigned working directory for metadata is: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/worker_methodology_1`
Your write ownership for project deliverables is exclusively: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/knowledge_base/methodology/`

MANDATORY FIRST STEP: Read `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/ORIGINAL_REQUEST.md` and `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/PROJECT.md`. Also inspect materials in `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/corpus/` (such as IIMA casebook, playbooks, etc.).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Deliverables to write (5 files in `knowledge_base/methodology/`):
1. `01_preliminary_questions.md`:
   - 4-pillar groking framework (Business Model & Monetization, Scope & Context, Segmentation & Customers, Quantified Objective).
   - Distinguishing clarification vs premature data fishing.
   - Case-type opening templates for Profitability, Market Entry, Growth, Pricing, M&A, Abstract.
   - Pitfalls: Asking generic/irrelevant laundry list questions, failing to clarify objective metrics/timeframes, asking for data before building a structure.
2. `02_issue_tree_structuring.md`:
   - First-principles structuring; MECE by construction (mathematical formulas, customer segmentation, process steps/life-cycle, value chain).
   - Standard vs custom tailored trees; avoiding and escaping the "Framework Trap".
   - How to handle messy, ambiguous, or multi-faceted problem statements.
   - Branching depth guidelines (L1, L2, L3) and cross-checking MECE completeness.
3. `03_hypothesis_driven_drilling.md`:
   - Formulating initial hypotheses grounded in preliminary info.
   - Stating hypotheses explicitly before requesting data ("I hypothesize X because Y, to test this I would like to see Z").
   - 80/20 branch prioritization (high leverage vs low impact).
   - Detecting interviewer hints, nudges, and pivots; how to gracefully course-correct.
4. `04_data_gathering_and_notes.md`:
   - High-speed consulting note-taking layout (3-zone page split: Case Facts & Objective, Structure & Math, Key Insights & Recommendations).
   - Tabular data tracking, arithmetic sanity-checking (unit consistency, percentage math, order of magnitude checks).
   - Verbalizing math calculations cleanly without dead silence.
5. `05_synthesis_and_recommendations.md`:
   - Pyramid Principle execution: top-down, answer-first synthesis.
   - 4-part closing structure: (1) Core Recommendation, (2) 2-3 Supporting Strategic Pillars with quantitative justification, (3) Key Risks & Mitigation Trade-offs, (4) 100-Day Action Plan / Next Steps.
   - Partner-Ready rewrites vs amateur candidate summaries (before-and-after benchmarks).

Quality Requirements:
- Every file MUST begin with clean YAML frontmatter (`title`, `category`, `topics_covered`, `target_use_case`).
- Zero placeholders, zero TODOs, production-grade depth, authoritative consulting tone, clear markdown formatting with tables, callout blocks, and bullet points.
- Write each file completely using `write_to_file`.

When complete, write your handoff report to `.agents/worker_methodology_1/handoff.md` and send a completion message back to parent.
