# Handoff Report: Case Corpus & Reservoir Survey

**Agent**: Explorer 1 (Case Corpus & Reservoir)  
**Recipient**: Orchestrator (`parent`, ID: `52543645-e2ea-4420-b0e0-9105575079aa`)  
**Timestamp**: 2026-08-24T14:17:00+05:30  
**Status**: Survey Complete (Hard Handoff)  
**Deliverable**: `.agents/explorer_survey_corpus/survey_report.md`  

---

## 1. Observation

1. **Active Reservoir Count & Structure (`reservoir/`)**:
   - Inspected `reservoir/` directory containing 12 subdirectories: `aster-diagnostics`, `bluecurrent-water`, `clearcart`, `forge-components`, `harvest-table`, `loom-and-leaf`, `meridian-cold-chain`, `metrolink-mobility`, `northstar-bank`, `orbit-learning`, `sunpeak-solar`, `terrabuild-materials`.
   - `meridian-cold-chain/` contains 5 files: `case.yaml` (62 lines), `conversation-policy.yaml` (56 lines), `facts.yaml` (282 lines, 24 facts), `issue-tree.yaml` (136 lines, 10 nodes, 3 acceptable routes), `validation.md` (66 lines).
   - The other 11 directories contain only 2 files each: `case.yaml` (20 lines) and `facts.yaml` (15 lines, 12 facts each).
   - None of the other 11 directories contain `issue-tree.yaml`, `conversation-policy.yaml`, or `validation.md`.

2. **Presence/Absence of `case_essence`**:
   - Grep search for `case_essence` across the codebase revealed 0 instances in `reservoir/` or `corpus/`.
   - All 12 active reservoir cases currently lack the `case_essence` block (`core_mechanism`, `what_the_case_wanted_to_test`, `pivotal_insight`, `common_traps`, `takeaway_lesson`, `suggested_readings`).

3. **Interviewer-Only Hidden Diagnosis Facts**:
   - In `reservoir/meridian-cold-chain/facts.yaml:246-255`:
     ```yaml
     - id: diagnosis.hidden
       domain: diagnosis
       release_level: interviewer_only
       provenance: source_derived
       content: >-
         Margin fell because growth shifted into a pharma book that was priced off
         the food cost base despite lower load factors, producing no contribution
         per kilogram.
     ```
   - In the other 11 `facts.yaml` files, all 12 facts per case are candidate-releasable (`broad_context`, `sharp_question`, `hypothesis_backed`, `synthesis_support`), with no `interviewer_only` hidden diagnosis fact.

4. **Corpus Inventory (`corpus/`)**:
   - `corpus/iima-consult-prep-book-2025-26/cases/` contains exactly 108 structured source cases (from `001-beer-manufacturer.md` to `108-digitizing-gold-loans.md`).
   - Distribution across categories in IIMA book: Profitability (25 cases), Market Entry (12 cases), Pricing (7 cases), Growth Strategy (15 cases), M&A and Due Diligence (14 cases), Unconventional & Abstract (35 cases).
   - `corpus/cases/meridian-cold-chain.case.md` exists as an approved 553-line reference case package.
   - No direct raw transcripts for IIM Bangalore, IIM Calcutta, or ISB currently exist in `corpus/`; however, knowledge base modules in `knowledge_base/` cite and integrate cross-school principles and case exemplars.

5. **Knowledge Base Coverage (`knowledge_base/`)**:
   - 31 complete production files: 5 in `methodology/`, 6 in `case_types/`, 17 in `industries/`, 3 in `evaluation_engine/`.
   - All 31 files pass strict tests (`tests/test_knowledge_base.py`): valid frontmatter, no TODO/TBD placeholders, valid KaTeX formulas, and valid Mermaid.js diagrams.

6. **Test Suite Execution**:
   - Command: `.venv/bin/pytest`
   - Result: `101 passed in 0.97s` across all existing unit and integration tests.

---

## 2. Logic Chain

1. **Premise**: Requirement R1 requires all active reservoir cases and multi-school exemplar cases to have structured `case_essence` metadata, verified facts, and private causal issue trees (`issue-tree.yaml`).
2. **Analysis of Current Reservoir**: 
   - While all 12 reservoir cases have solid business foundations and valid basic facts, 11/12 lack `issue-tree.yaml`, 11/12 lack `conversation-policy.yaml`, 11/12 lack `diagnosis.hidden` facts, and 12/12 lack `case_essence`.
   - `app/evaluator.py:load_issue_tree` specifically looks for `issue-tree.yaml` in the case directory. Because 11 cases lack this file, the evaluator agent falls back to evaluating claims without a formal causal DAG map for those cases.
3. **Analysis of Evaluator & Debrief Integration**:
   - Requirements R2 & R4 mandate that the debrief report display "What This Case Really Wanted to Test", "Pivotal Insight", "Takeaway Lessons", and clickable "Suggested Readings".
   - Having `case_essence` explicitly authored in `case.yaml` allows the backend evaluator and debrief API (`/api/attempts/{id}/evaluation`) to deterministically pull the exact commercial mechanisms and knowledge base links for any attempted case.
4. **Analysis of Multi-School Expansion**:
   - The 108 IIMA cases provide an immediate, rich pipeline of 25+ top-tier cases that can be promoted to full reservoir status.
   - For IIM-B, IIM-C, and ISB, authoring 10 high-yield exemplar case packages per school will achieve the ~50-60 curated multi-school target, providing comprehensive coverage across all 17 industry sectors and 6 case archetypes.

---

## 3. Caveats

1. **Live Interview Runtime Independence**: The runtime (`app/case_runtime.py`) currently relies on `case.yaml`, `facts.yaml`, and `conversation-policy.yaml` (or `_shared-policy.yaml`). Adding `case_essence` and `issue-tree.yaml` is backward-compatible and does not alter live interview conversation flow.
2. **School Attribution**: While the IIMA casebook is licensed and asserted in `corpus/sources/iima-consult-prep-book-2025-26.md`, case packages representing IIMB, IIMC, and ISB archetypes should be curated and packaged as original CaseCall reservoir packages with proper sector grounding.
3. **Scope Constraint**: As Explorer 1, this investigation was conducted strictly read-only. No source files or case packages were modified.

---

## 4. Conclusion

The repository has an exceptionally well-structured foundation, with 12 playable reservoir cases, 108 source-extracted IIMA cases, and a comprehensive 31-file knowledge base.

To achieve the full 10x Debrief and Multi-School enrichment milestone:
1. **Immediate Case Enrichment**: Upgrade all 12 reservoir cases with full `case_essence` blocks in `case.yaml`, complete `issue-tree.yaml` causal DAGs, `interviewer_only` hidden diagnosis facts, and custom `conversation-policy.yaml` files.
2. **Multi-School Curation Pipeline**: Promote the top 25 exemplar IIMA cases and author 30 curated exemplar cases across IIMB, IIMC, and ISB archetypes.
3. **Debrief Integration**: Connect `app/evaluator.py` and `app/attempt_service.py` to ingest `case_essence` from `case.yaml` and pass it to the debrief payload for the 10x interactive UI.

---

## 5. Verification Method

To independently verify all findings:
1. **Case Inventory & Missing Files**:
   ```bash
   ls -la reservoir/
   find reservoir/ -name "issue-tree.yaml"
   find reservoir/ -name "case.yaml" | wc -l
   ```
2. **`case_essence` Absence Verification**:
   ```bash
   grep -rn "case_essence" reservoir/ corpus/
   ```
3. **Corpus File Verification**:
   ```bash
   ls -1 corpus/iima-consult-prep-book-2025-26/cases/ | wc -l
   ```
4. **Current Test Suite Verification**:
   ```bash
   .venv/bin/pytest
   ```
