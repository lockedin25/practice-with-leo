# Execution Plan: MBB Case Prep V2 Knowledge Base

## Objective
Build a world-class, production-grade MBB case interview knowledge repository across 4 core modules (29 files total) with deep domain authority, structured MECE frameworks, Mermaid diagrams, formula blocks, real-world case examples, and evaluation rubrics.

## Milestones & Work Breakdown

### Milestone 1: Methodology Playbooks (`knowledge_base/methodology/`) - 5 Files
1. `01_preliminary_questions.md`: 4-pillar groking framework, clarification vs data fishing, opening templates.
2. `02_issue_tree_structuring.md`: First-principles MECE issue trees (formula, segment, process, value chain), escaping framework traps.
3. `03_hypothesis_driven_drilling.md`: Hypothesis formulation, 80/20 prioritization, handling hints/pivots.
4. `04_data_gathering_and_notes.md`: High-speed consulting note-taking, tabular tracking, sanity-checking.
5. `05_synthesis_and_recommendations.md`: Pyramid Principle, answer-first synthesis, 4-part closing, partner-ready rewrites.

### Milestone 2: Case-Type Deep Dives (`knowledge_base/case_types/`) - 6 Files
1. `profitability.md`: Margin compression, price/volume, product mix, Mermaid trees, diagnostic steps.
2. `market_entry.md`: Attractiveness, modes of entry, economic feasibility, risks, Mermaid trees.
3. `growth_strategy.md`: Organic vs inorganic, Ansoff matrix applied, new channels, Mermaid trees.
4. `pricing_strategy.md`: Cost-plus, competitor, value-based, dynamic pricing, Mermaid trees.
5. `mergers_and_acquisitions.md`: Strategic fit, deal economics, synergy breakdown, post-merger integration.
6. `unconventional_and_abstract.md`: Guesstimates, public policy, sports/tech, operations optimization.

### Milestone 3: Industry & Business Model Dossiers (`knowledge_base/industries/`) - 15 Files
- **Batch 3A (Files 01-05)**:
  - `01_logistics_and_cold_chain.md`
  - `02_ecommerce_and_marketplaces.md`
  - `03_pharma_and_healthcare.md`
  - `04_banking_and_financial_services.md`
  - `05_fmcg_and_cpg.md`
- **Batch 3B (Files 06-10)**:
  - `06_aviation_and_airlines.md`
  - `07_telecom_and_media.md`
  - `08_saas_and_b2b_tech.md`
  - `09_retail_and_fashion.md`
  - `10_automotive_and_ev.md`
- **Batch 3C (Files 11-15)**:
  - `11_energy_and_renewables.md`
  - `12_hospitality_and_tourism.md`
  - `13_food_and_beverage_restaurants.md`
  - `14_heavy_manufacturing_and_steel.md`
  - `15_fintech_and_payments.md`
- **Batch 3D (Files 16-17)**:
  - `16_insurance.md`
  - `17_defense_and_aerospace.md`

### Milestone 4: Evaluator Prompts & Rubrics (`knowledge_base/evaluation_engine/`) - 3 Files
1. `detection_rubrics.yaml`: Behavioral markers, counter-markers, scoring weights across casing stages.
2. `golden_rewrites_catalogue.md`: Candidate response vs Top 1% MBB rewrites per case type.
3. `system_prompt_knowledge_pack.md`: Dense, token-optimized system prompt injection pack.

### Milestone 5: Quality Assurance, Review & Audit
- Lint all 29 files for YAML frontmatter completeness (`title`, `category`, `topics_covered`, `target_use_case`).
- Verify valid Mermaid diagrams, formula blocks, zero placeholders/TODOs.
- Cross-check against corpus references (IIMA, IIMB, IIMC, ISB, CIC, Crafting Cases, Cheng).
- Forensic audit verification.

## Execution Strategy
- Parallel worker subagents for high concurrency and deep focus.
- Dedicated reviewer and auditor subagents.
- Constant progress updates in `progress.md`.
