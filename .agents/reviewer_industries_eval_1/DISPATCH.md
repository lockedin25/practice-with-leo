## 2026-08-24T07:57:14Z

You are Reviewer 2 for Milestone 5: Verification of Industry Dossiers & Evaluation Engine in MBB Case Prep V2.
Your assigned working directory for metadata is: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/reviewer_industries_eval_1`

MANDATORY FIRST STEP: Read `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/ORIGINAL_REQUEST.md` and `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/PROJECT.md`.

Review Scope:
1. `knowledge_base/industries/` (17 files):
   - `01_logistics_and_cold_chain.md` through `17_defense_and_aerospace.md`
2. `knowledge_base/evaluation_engine/` (3 files):
   - `detection_rubrics.yaml`
   - `golden_rewrites_catalogue.md`
   - `system_prompt_knowledge_pack.md`

Verification Checks:
- Verify that all 17 industry files strictly contain the 8 mandatory structural sections:
  1. Industry Overview & Macro Dynamics
  2. Complete End-to-End Value Chain
  3. Revenue Models & Monetization Mechanics
  4. Detailed Unit Economics & Contribution Margin breakdown (sample P&L table)
  5. Comprehensive Cost Structure (Fixed vs Variable)
  6. Essential KPI Formulas & Benchmark Tables
  7. Typical Case Scenarios & Diagnostic Issue Trees (with Mermaid diagrams)
  8. Common Pitfalls & Candidate Landmines
- Verify YAML validity of `detection_rubrics.yaml` and frontmatter across all markdown files.
- Verify zero placeholders/TODOs.
- Run any verification commands/scripts needed.

When done, write your report to `.agents/reviewer_industries_eval_1/handoff.md` with an explicit verdict: APPROVE or REQUEST_CHANGES, and send a message back to parent.
