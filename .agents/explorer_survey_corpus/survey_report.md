# Comprehensive Survey Report: Case Corpus & Reservoir Architecture

**Author**: Explorer 1 (Case Corpus & Reservoir)  
**Date**: 2026-08-24  
**Project**: MBB Case Prep V2 (10x Debrief Report Engine & Multi-School Case Enrichment)  
**Target Paths**: `reservoir/`, `corpus/`, `knowledge_base/`, `app/`  

---

## 1. Executive Summary

An exhaustive investigation of the MBB Case Prep V2 repository reveals a solid dual-tier architecture consisting of:
1. **Active Reservoir (`reservoir/`)**: 12 curated, playable case packages covering major consulting case archetypes across diverse industries.
2. **Source Corpus (`corpus/`)**: 108 extracted source transcripts from the **IIM Ahmedabad (IIMA) Consult Prep Book 2025-26**, along with 1 fully specified case package (`meridian-cold-chain.case.md`), authoring templates, and interviewer pattern playbooks.
3. **Ground-Truth Knowledge Base (`knowledge_base/`)**: 31 comprehensive, production-grade reference files (5 methodology playbooks, 6 case-type deep dives, 17 industry dossiers, and 3 evaluation engine specifications).

### Key Architectural Findings & Gaps
- **Absence of `case_essence` (0/12 in reservoir, 0/108 in corpus)**: No case currently contains the structured `case_essence` schema (`core_mechanism`, `what_the_case_wanted_to_test`, `pivotal_insight`, `common_traps`, `takeaway_lesson`, `suggested_readings`) mandated by Requirement R1.
- **Asymmetric Issue Tree & Policy Coverage (1/12 in reservoir)**: Only `meridian-cold-chain` has a dedicated `issue-tree.yaml` (10 nodes, 3 routes, recovery policy), `conversation-policy.yaml`, and `validation.md`. The remaining 11 reservoir cases have only compact `case.yaml` (20 lines) and `facts.yaml` (12 facts), falling back to `_shared-policy.yaml` with zero `issue-tree.yaml` files.
- **Missing Hidden Diagnosis Facts (1/12 in reservoir)**: Only `meridian-cold-chain` defines an explicit `interviewer_only` fact (`diagnosis.hidden`) for evaluator answer-key comparisons and leakage scanning. The other 11 cases contain only candidate-releasable facts.
- **Multi-School Corpus Opportunity**: While `knowledge_base/` modules synthesize principles from IIM-A, IIM-B, IIM-C, and ISB, the raw source transcript corpus is currently 100% sourced from IIMA (108 cases). A curated subset of ~50-60 top exemplar cases across the four premier Indian B-schools and global casebooks can be systematically enriched with `case_essence` and issue trees.

---

## 2. Complete Inventory of Active Reservoir Cases (`reservoir/`)

The runtime catalogue (`app/case_runtime.py:CaseCatalogue`) loads 12 distinct, playable cases from `reservoir/`. All 12 cases pass current basic unit tests (`tests/test_case_library.py`).

| # | Case ID | Title | Category | Industry | Difficulty | Facts Count | Issue Tree Present? | Policy Present? | `case_essence` Present? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `meridian-cold-chain-v1` | Meridian Cold Chain | `profitability` | `temperature_controlled_logistics` | foundation | 24 | **Yes** (136 lines) | **Yes** (custom) | **No** (Missing) |
| 2 | `aster-diagnostics-v1` | Aster Diagnostics | `market_entry` | `healthcare_services` | intermediate | 12 | **No** | Fallback shared | **No** (Missing) |
| 3 | `bluecurrent-water-v1` | BlueCurrent Water | `public_sector_strategy` | `water_utility` | intermediate | 12 | **No** | Fallback shared | **No** (Missing) |
| 4 | `clearcart-v1` | ClearCart | `growth_strategy` | `ecommerce_marketplace` | intermediate | 12 | **No** | Fallback shared | **No** (Missing) |
| 5 | `forge-components-v1` | Forge Components | `mergers_and_acquisitions` | `industrial_manufacturing` | advanced | 12 | **No** | Fallback shared | **No** (Missing) |
| 6 | `harvest-table-v1` | Harvest Table | `profitability` | `quick_service_restaurants` | foundation | 12 | **No** | Fallback shared | **No** (Missing) |
| 7 | `loom-and-leaf-v1` | Loom & Leaf | `turnaround` | `apparel_retail` | intermediate | 12 | **No** | Fallback shared | **No** (Missing) |
| 8 | `metrolink-mobility-v1` | MetroLink Mobility | `operations` | `urban_transit` | intermediate | 12 | **No** | Fallback shared | **No** (Missing) |
| 9 | `northstar-bank-v1` | Northstar Bank | `growth_strategy` | `retail_banking` | intermediate | 12 | **No** | Fallback shared | **No** (Missing) |
| 10 | `orbit-learning-v1` | Orbit Learning | `digital_transformation` | `education` | intermediate | 12 | **No** | Fallback shared | **No** (Missing) |
| 11 | `sunpeak-solar-v1` | SunPeak Solar | `pricing` | `distributed_energy` | intermediate | 12 | **No** | Fallback shared | **No** (Missing) |
| 12 | `terrabuild-materials-v1` | TerraBuild Materials | `sustainability_strategy` | `construction_materials` | advanced | 12 | **No** | Fallback shared | **No** (Missing) |

---

## 3. Deep-Dive Analysis of the 12 Playable Reservoir Cases

### 3.1. Meridian Cold Chain (`meridian-cold-chain-v1`)
- **Objective Function**: EBITDA margin declined from 18% to 11% over 2 years despite 20% revenue growth; determine root cause and recommend a 12-month recovery plan.
- **Core Mechanism**: Adverse product/customer mix shift into pharmaceutical cold chain (from 5% to 30% volume) which has lower vehicle load factor (55% vs 88% for packaged food) due to strict 2–8°C non-consolidation rules, yet contracts were priced using the legacy food cost base plus a generic markup, producing ₹0 contribution margin per kg.
- **Pivotal Insight**: Revenue and overall volume are healthy, but pharma routes consume capacity without generating unit contribution because quotes failed to reflect pharma-specific low route density.
- **Current Files**: `case.yaml`, `conversation-policy.yaml`, `facts.yaml` (24 facts with dependencies and question examples), `issue-tree.yaml`, `validation.md`.
- **Gaps**: Lacks `case_essence` block in `case.yaml`.

### 3.2. Aster Diagnostics (`aster-diagnostics-v1`)
- **Objective Function**: Decide whether and how a metro diagnostic chain should enter tier-2 Indian cities (₹1,200 Cr market, 12% growth, 25% organised penetration) to maximize risk-adjusted ROIC.
- **Core Mechanism**: Fixed cost leverage vs capacity utilization trap. High-capex imaging/radiology hubs cannot reach breakeven utilization in tier-2 cities alone during the first 2 years; a hub-and-spoke collection network with twice-daily 4-hour sample logistics to a regional processing hub achieves positive contribution at much lower volume.
- **Pivotal Insight**: Decouple routine pathology sample collection (asset-light spoke network) from high-capex specialized radiology (demand-gated regional hub).
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.3. BlueCurrent Water (`bluecurrent-water-v1`)
- **Objective Function**: Water utility with 42% Non-Revenue Water (NRW) facing rising complaints and political tariff freeze; identify high-leverage interventions to improve service and financial sustainability over 18 months.
- **Core Mechanism**: NRW decomposition into physical leakage vs commercial/apparent losses. Physical losses are concentrated in a few aged high-pressure zones; commercial losses stem from uncalibrated bulk commercial meters and unregularised informal connections. Citywide household replacement would exhaust capital; district metering and commercial regularisation yield immediate cash flow.
- **Pivotal Insight**: DMA (District Metered Area) zoning with night-flow analysis isolates 80% of physical leaks in 20% of pipes; calibrating large commercial meters yields instant cash flow without tariff hikes.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.4. ClearCart (`clearcart-v1`)
- **Objective Function**: E-commerce marketplace for home/lifestyle experiencing falling repeat rates (90-day repeat fell from 26% to 17%) and deteriorating CAC/LTV efficiency; prioritize highest-value retention intervention over 12 months.
- **Core Mechanism**: Fulfilment model quality breakdown across high-value categories. Low repeat is concentrated in bulky furniture/decor (not consumables) due to delivery delays, transit damage, and lack of installation support under unmanaged 3P seller logistics.
- **Pivotal Insight**: Subsidizing repeat marketing/discounts burns cash without addressing root dissatisfaction; enforcing SLA/white-glove delivery standards on high-value furniture sellers fixes the churn driver.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.5. Forge Components (`forge-components-v1`)
- **Objective Function**: Precision machining supplier evaluating acquisition of casting supplier AlloyWorks; determine conditions under which acquisition creates value vs standalone over 3 years.
- **Core Mechanism**: Synergy valuation vs integration friction. Upfront seller valuation captures expected procurement synergies (4% metal purchasing savings); cross-sell revenue synergies require 12–18 month engineering qualification cycles; the target plant requires automation capex and relies heavily on its founder.
- **Pivotal Insight**: The deal destroys value at the seller's asking multiple unless priced strictly on risk-adjusted, phased procurement synergies with milestone-gated founder earnouts and automation capex factored in.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.6. Harvest Table (`harvest-table-v1`)
- **Objective Function**: 180-store fast-casual chain with EBITDA margin down from 14% to 7% despite 5% same-store sales growth; diagnose margin compression and recommend a 12-month recovery plan.
- **Core Mechanism**: Channel mix shift toward food delivery aggregators (delivery grew from 20% to 46% of sales). Delivery orders contribute ₹35 on a ₹500 basket vs ₹110 for dine-in due to aggregator commissions, packaging costs, and brand-funded discounts, while kitchen staffing remained fixed to dine-in peak patterns.
- **Pivotal Insight**: Sales growth is cannibalistic; delivery orders carry 68% lower unit contribution margin while diluting direct customer relationships and straining off-peak labor efficiency.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.7. Loom & Leaf (`loom-and-leaf-v1`)
- **Objective Function**: Mid-market apparel retailer (95 stores + online) suffering a 6 percentage point gross margin collapse and tightening cash flow; diagnose causes and build a turnaround plan.
- **Core Mechanism**: Assortment complexity and inventory aging trap. Buying team expanded SKU count by 35% in fast-trend capsules with locked long-lead buys; low sell-through led to aged stock (>180 days rose from 12% to 29%), massive clearance markdowns, and working capital lockup, while core basics remained highly profitable.
- **Pivotal Insight**: The margin drop is not fabric cost inflation but inventory markdown erosion caused by unvalidated trend over-buying; core basics subsidize unprofitable trend sprawl.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.8. MetroLink Mobility (`metrolink-mobility-v1`)
- **Objective Function**: City bus operator with 1,100 buses experiencing a 12% ridership decline and rising subsidy requirements under a fixed fleet budget; restore ridership and reliability over 18 months.
- **Core Mechanism**: Schedule instability and route schedule elasticity. Construction on 2 main commuter corridors degraded on-time arrival from 81% to 58%; commuters defected to 2-wheelers/shared cabs due to arrival variance, while off-peak buses on those same corridors ran at <30% load factor.
- **Pivotal Insight**: Demand loss is driven by waiting-time variance, not fare levels; dynamic terminal dispatch and reallocating off-peak buses to peak corridor frequencies restores reliability within the existing fleet budget.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.9. Northstar Bank (`northstar-bank-v1`)
- **Objective Function**: Profitable urban private bank seeking a growth roadmap to increase retail income by 25% over 3 years without reckless credit expansion.
- **Core Mechanism**: Customer lifetime value across geographical tiers vs distribution unit economics. Urban affluent market is saturated; tier-2 emerging affluent (12M households) have high savings/digital activity but limited branch density. Traditional full branches are 4x too expensive to serve tier-2 unit economics; a digital-onboarding + relationship-manager hub model captures salary accounts and enables low-risk cross-sell.
- **Pivotal Insight**: Anchor emerging affluent households through corporate salary accounts and digital payments first; extend unsecured credit only after observing 6–12 months of domestic cash-flow patterns.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.10. Orbit Learning (`orbit-learning-v1`)
- **Objective Function**: Vocational college network whose digital learning platform pilot has only 38% completion and poor faculty adoption; redesign and scale the program over 12 months.
- **Core Mechanism**: Pedagogy-workflow mismatch and perverse incentives. The digital platform simply mirrored long passive lectures online, creating friction for mobile-first students and adding uncompensated prep work for faculty whose KPIs were tied to classroom contact hours.
- **Pivotal Insight**: Digital content efficacy is sound when completed; redesigning into bite-sized 10-minute micro-drills linked to lab sessions and aligning faculty incentive structures drives adoption.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.11. SunPeak Solar (`sunpeak-solar-v1`)
- **Objective Function**: Rooftop solar installer for commercial/industrial clients with lead conversion stuck at 9% (target 18%); diagnose conversion bottleneck and redesign pricing/offer structure over 12 months.
- **Core Mechanism**: Upfront capex hurdle vs operational cash-flow economics. SME factory owners understand long-term energy savings but reject large upfront lump-sum cash quotes to protect working capital; a financed 5-year monthly payment model makes monthly loan payments strictly lower than grid electricity savings from month one.
- **Pivotal Insight**: Customers are not price-elastic to total lifecycle cost—they are cash-flow constrained; offering an OPEX-equivalent financed monthly instalment unlocks immediate positive ROI for prospects.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

### 3.12. TerraBuild Materials (`terrabuild-materials-v1`)
- **Objective Function**: Regional cement and concrete producer facing customer green procurement mandates and rising carbon costs; develop an EBITDA-resilient decarbonization sequence over 5 years.
- **Core Mechanism**: Marginal Abatement Cost Curve (MACC) sequencing. Deep kiln overhauls and CCUS (carbon capture) require immense capex and fail ROIC hurdles today; energy efficiency and Supplementary Cementitious Materials (SCM) blended cement (using slag/fly ash) yield immediate emissions reductions at net negative/low cost.
- **Pivotal Insight**: Avoid capital-intensive unproven tech first; prioritize high-blend SCM cement with co-developed certified specs for anchor infrastructure buyers, protecting EBITDA while reducing clinker factor.
- **Current Files**: `case.yaml` (20 lines), `facts.yaml` (12 facts).
- **Gaps**: Lacks `issue-tree.yaml`, `conversation-policy.yaml`, `diagnosis.hidden` fact, and `case_essence`.

---

## 4. Source Corpus Inventory & Multi-School Distribution (`corpus/`)

### 4.1. Structure of `corpus/`
```
corpus/
├── README.md (Rights guidelines and ingestion state rules)
├── case-examples/
│   └── meridian-cold-chain.md
├── cases/
│   └── meridian-cold-chain.case.md (Fully approved case specification, 553 lines)
├── playbooks/
│   └── iima-case-interviewer-pattern.md (Turn patterns and facilitation rules)
├── sources/
│   └── iima-consult-prep-book-2025-26.md (Rights assertions and metadata)
├── templates/
│   ├── case-world-package-template.md
│   └── runnable-case-template.md
└── iima-consult-prep-book-2025-26/
    ├── README.md & STRUCTURING-REPORT.md
    ├── case-index.md (115 lines, cataloguing all 108 cases)
    ├── sections/ (Panoramas, Guesstimates, Front-Matter Frameworks, Appendices)
    └── cases/ (108 structured source case markdown files)
```

### 4.2. Breakdown of 108 IIMA Cases by Category
1. **Profitability (25 cases, 001–025)**:
   - *Exemplars*: 001 Beer Manufacturer (Capacity/Import restrictions), 002 Diagnostic Center (Doctor referral incentives), 004 Urban Company (Service partner churn), 006 Port Operator (Berth turnaround time), 011 Zoomcar (Damage & maintenance costs), 014 Auto Insurance (Telematics & claim fraud), 019 Fast Food Chain (Regional store cannibalization), 025 Air India vs Indigo (Turnaround times & aircraft utilization).
2. **Market Entry (12 cases, 026–037)**:
   - *Exemplars*: 026 Healthcare Test Kit (Regulatory barriers & hospital tender cycles), 027 EV Manufacturer (Battery swapping vs fast charging network), 031 iPhone Manufacturer (Local sourcing norms & supply chain ecosystem), 033 Fintech in UAE (Cross-border remittances & Islamic banking compliance).
3. **Pricing (7 cases, 038–044)**:
   - *Exemplars*: 040 5G Plan Pricing (Tiered data vs speed tiering), 041 Quick-Commerce Membership Pricing (Delivery fee waiver vs average order value increase), 043 Drug Pricing (Value of statistical life vs generic reference pricing).
4. **Growth Strategy (15 cases, 045–059)**:
   - *Exemplars*: 048 B2B SaaS Logistics (Enterprise tier expansion), 050 E-Grocery Player (Dark store density & slot delivery economics), 054 OTTCo India (Vernacular content vs subscription tiering), 056 Midstream Oil & Gas (Potable water pipeline diversification).
5. **M&A and Due Diligence (14 cases, 060–073)**:
   - *Exemplars*: 060 AI Startup Acquisition (Tech talent acquisition vs IP integration), 065 Co-working Space (Long lease liabilities vs flexible tenant churn), 069 Q-Commerce Fulfillment (In-house dark stores vs 3P hub buyout), 072 Pharma Giants Acquisition (Patent expiry pipeline replacement).
6. **Unconventional & Abstract (35 cases, 074–108)**:
   - *Exemplars*: 075 GenAI in International Bank (Front-office automated compliance), 079 Food Delivery Service (Rider fleet idle time optimization), 089 Commercial Vehicle Loan (Underwriting telemetry), 095 ISRO Lunar Manned Mission (Public procurement & mission-critical redundancy), 108 Digitizing Gold Loans (Appraisal turnaround vs collateral risk).

### 4.3. Multi-School Exemplar Strategy (IIM-A, IIM-B, IIM-C, ISB)
To fulfill the multi-school curation target (~50-60 cases) while maintaining simulator compatibility:
- **IIM Ahmedabad (IIMA)**: 25 top exemplar cases selected from the active 108 corpus (e.g. Beer Manufacturer, Diagnostic Center, Urban Company, Zoomcar, Auto Insurance, EV Manufacturer, Quick-Commerce Pricing, B2B SaaS Logistics, Q-Commerce M&A, GenAI Bank).
- **IIM Bangalore (IIMB)**: 10 flagship casing archetypes (e.g. Microfinance Credit Delivery, Hospital Bed Occupancy Optimization, Renewable IPP Bidding, D2C Personal Care Omnichannel Expansion, Toll Road Infrastructure Yield).
- **IIM Calcutta (IIMC)**: 10 quantitative/analytical exemplar archetypes (e.g. Steel Mill Fixed Cost Absorption, Airline Fleet Optimization, Telecom Tower Sharing Economics, Port Dredging Concession Valuation).
- **Indian School of Business (ISB)**: 10 strategy & tech-transformation exemplar archetypes (e.g. Fintech Buy-Now-Pay-Later Default Containment, SaaS Multi-Product Cross-Sell, Cloud Migration Cost Runaway, Quick-Commerce Dark Store Unit Economics).

---

## 5. Specification: The Standardized Case Package Architecture

To elevate all reservoir cases to full production readiness, every case directory in `reservoir/<case-id>/` must adhere to the following 5-file architecture:

```
reservoir/<case-id>/
├── case.yaml                # Metadata, Opening Brief, Objective Function, and `case_essence`
├── facts.yaml               # Atomic facts with domains, release levels, dependencies, and hidden diagnosis
├── issue-tree.yaml          # Private causal DAG, node types, acceptable candidate routes, recovery rules
├── conversation-policy.yaml # Interviewer goals per phase, challenge rules, redirection guidance
└── validation.md            # Reconciled mathematical checks, fact dependencies, and scoring sanity rules
```

### 5.1. `case.yaml` Specification with Mandatory `case_essence`
```yaml
schema_version: reservoir-v1
case_id: "<unique-slug>-v1"
title: "<Human-Readable Title>"
status: "approved"
rights_status: "original"
category: "<profitability|market_entry|growth_strategy|pricing|mergers_and_acquisitions|unconventional_and_abstract>"
industry: "<industry_slug>"
difficulty: "<foundation|intermediate|advanced>"
supported_durations: [30]
skills_tested: [clarification, tailored structure, unit economics, hypothesis drilling, synthesis]

candidate_opening:
  context: >-
    <Context statement describing client and baseline situation>
  objective: >-
    <Clear decision question and timeline>
  opening_requirements:
    - Name client and operating model.
    - State performance problem or mandate.
    - Confirm primary decision metric and time horizon.
    - Ask clarifying questions before structuring.

objective_function:
  primary_metric: "<Primary metric name>"
  decision_question: "<Decision question>"
  time_horizon: "<Timeframe>"
  expected_candidate_output:
    - Root cause diagnosis supported by data.
    - Prioritized 3-pillar recommendation.
    - Core implementation risks and mitigations.
    - 100-day execution milestone.
  design_principle: >-
    Reward first-principles problem structuring and hypothesis testing over memorized framework dumping.

case_essence:
  core_mechanism: "<Exact economic, commercial, or operational mechanism driving the problem>"
  what_the_case_wanted_to_test: "<Explicit business principle tested by the interviewer>"
  pivotal_insight: "<Breakthrough 'Aha!' moment unlocking the case>"
  common_traps:
    - "<Trap 1: Generic framework dumping / red herring exploration>"
    - "<Trap 2: Misinterpreting surface data without unit economics>"
    - "<Trap 3: Proposing unviable/generic solutions that violate operational constraints>"
  takeaway_lesson: "<Durable management consulting mental model>"
  suggested_readings:
    - "knowledge_base/industries/<relevant_industry>.md"
    - "knowledge_base/methodology/<relevant_methodology>.md"
    - "knowledge_base/case_types/<relevant_case_type>.md"

session_contract:
  mode: realistic
  live_fact_invention: disabled
  scratchpad: disabled
  quantitative_drills: disabled
  transcript_visibility: post_case_only
  reasoning_graph_visibility: post_case_only
  current_phases:
    - clarification
    - drill_down
    - synthesis

reservoir_files:
  - facts.yaml
  - issue-tree.yaml
  - conversation-policy.yaml
  - validation.md
```

### 5.2. `facts.yaml` Specification with Hidden Diagnosis
```yaml
schema_version: reservoir-facts-v1
facts:
  - id: company.model
    domain: company
    release_level: opening
    content: "..."
    candidate_purpose: "Establish business context."
  
  - id: financials.performance
    domain: financials
    release_level: sharp_question
    content: "..."
    question_examples: ["..."]
    candidate_purpose: "Disclose high-level financial split upon direct inquiry."

  - id: economics.unit_split
    domain: economics
    release_level: hypothesis_backed
    dependencies: [financials.performance]
    content: "..."
    candidate_purpose: "Reveal root unit economic divergence."

  - id: diagnosis.hidden
    domain: diagnosis
    release_level: interviewer_only
    provenance: source_derived
    content: "<Exact root cause diagnosis used by evaluator and interviewer recovery>"
    candidate_purpose: "Never disclose directly. Evaluator scoring and leakage baseline only."

  - id: recommendation.pillar1
    domain: recommendation
    release_level: synthesis_support
    content: "..."
```

### 5.3. `issue-tree.yaml` Specification
```yaml
schema_version: issue-tree-v1
visibility: post_case_only

root:
  id: objective.root
  label: "<High-level problem statement>"

nodes:
  - id: branch_1
    type: branch
    label: "<Branch label>"
    status: valid_branch
    evidence: [fact_id_1]
    conclusion: "<Branch conclusion>"

  - id: mechanism_test
    type: mechanism
    label: "<Mechanism label>"
    status: pivotal_test
    evidence: [fact_id_2, fact_id_3]
    conclusion: "<Mechanism insight>"

  - id: diagnosis
    type: diagnosis
    label: "<Diagnosis label>"
    status: hidden_target
    evidence: [branch_1, mechanism_test]
    conclusion: "<Synthesis of root cause>"

  - id: actions
    type: recommendation
    label: "<Actions label>"
    status: synthesis
    evidence: [recommendation_fact_1, recommendation_fact_2]
    conclusion: "<Actionable next steps>"

edges:
  - { from: objective.root, to: branch_1, relation: investigate }
  - { from: branch_1, to: mechanism_test, relation: motivates }
  - { from: mechanism_test, to: diagnosis, relation: supports }
  - { from: diagnosis, to: actions, relation: determines }

acceptable_routes:
  - id: route_primary
    sequence: [branch_1, mechanism_test, diagnosis, actions]
    interviewer_behaviour: "<Interviewer guidance>"

recovery_policy:
  maximum_unproductive_follow_ups: 2
  recovery_order:
    - "Ask candidate to state hypothesis behind current inquiry branch."
    - "Neutrally explain why current branch is insufficient to explain magnitude."
    - "Redirect candidate toward core unit economic divergence."
```

---

## 6. Knowledge Base Cross-Reference Matrix

The 31 files in `knowledge_base/` provide the definitive reference ground-truth for case authoring and evaluator debrief linking:

| Reservoir Case | Primary Industry Dossier | Primary Case-Type Module | Primary Methodology Playbook |
|---|---|---|---|
| `meridian-cold-chain` | `knowledge_base/industries/01_logistics_and_cold_chain.md` | `knowledge_base/case_types/profitability.md` | `knowledge_base/methodology/02_issue_tree_structuring.md` |
| `aster-diagnostics` | `knowledge_base/industries/03_pharma_and_healthcare.md` | `knowledge_base/case_types/market_entry.md` | `knowledge_base/methodology/01_preliminary_questions.md` |
| `bluecurrent-water` | `knowledge_base/industries/11_energy_and_renewables.md` | `knowledge_base/case_types/unconventional_and_abstract.md` | `knowledge_base/methodology/03_hypothesis_driven_drilling.md` |
| `clearcart` | `knowledge_base/industries/02_ecommerce_and_marketplaces.md` | `knowledge_base/case_types/growth_strategy.md` | `knowledge_base/methodology/03_hypothesis_driven_drilling.md` |
| `forge-components` | `knowledge_base/industries/14_heavy_manufacturing_and_steel.md` | `knowledge_base/case_types/mergers_and_acquisitions.md` | `knowledge_base/methodology/04_data_gathering_and_notes.md` |
| `harvest-table` | `knowledge_base/industries/13_food_and_beverage_restaurants.md` | `knowledge_base/case_types/profitability.md` | `knowledge_base/methodology/02_issue_tree_structuring.md` |
| `loom-and-leaf` | `knowledge_base/industries/09_retail_and_fashion.md` | `knowledge_base/case_types/profitability.md` | `knowledge_base/methodology/03_hypothesis_driven_drilling.md` |
| `metrolink-mobility` | `knowledge_base/industries/01_logistics_and_cold_chain.md` | `knowledge_base/case_types/unconventional_and_abstract.md` | `knowledge_base/methodology/02_issue_tree_structuring.md` |
| `northstar-bank` | `knowledge_base/industries/04_banking_and_financial_services.md` | `knowledge_base/case_types/growth_strategy.md` | `knowledge_base/methodology/01_preliminary_questions.md` |
| `orbit-learning` | `knowledge_base/industries/08_saas_and_b2b_tech.md` | `knowledge_base/case_types/unconventional_and_abstract.md` | `knowledge_base/methodology/03_hypothesis_driven_drilling.md` |
| `sunpeak-solar` | `knowledge_base/industries/11_energy_and_renewables.md` | `knowledge_base/case_types/pricing_strategy.md` | `knowledge_base/methodology/04_data_gathering_and_notes.md` |
| `terrabuild-materials` | `knowledge_base/industries/14_heavy_manufacturing_and_steel.md` | `knowledge_base/case_types/growth_strategy.md` | `knowledge_base/methodology/05_synthesis_and_recommendations.md` |

---

## 7. Runtime & Case Loading Validation Audit

1. **Loader Functionality (`app/case_runtime.py`)**:
   - `CaseCatalogue.from_reservoir(ROOT)` iterates through `reservoir/*` subdirectories where `case.yaml` exists.
   - It requires `case.yaml`, `facts.yaml`, and loads `conversation-policy.yaml` if present (or falls back to `_shared-policy.yaml`).
   - It ignores `release_level == "interviewer_only"` facts from the live interview session context, ensuring private diagnoses are never exposed to candidate turns.
2. **Evaluator Loading (`app/evaluator.py`)**:
   - `load_case_manifest(reservoir_root, case_id)` loads `case.yaml`.
   - `load_issue_tree(reservoir_root, case_id)` attempts to load `issue-tree.yaml` (returns `None` if absent).
   - `private_fact_contents(reservoir_root, session)` parses unreleased facts directly from `facts.yaml` for answer-key comparison and leakage guard.
3. **Current Integrity State**:
   - Running `.venv/bin/pytest` confirms 101/101 tests pass across admin, API, auth, case library, evaluator, knowledge base, store, and voice modules.
   - Adding `case_essence` blocks to `case.yaml` and adding `issue-tree.yaml` files will not break existing loaders, provided schemas follow standard YAML dictionary contracts.

---

## 8. Prioritized Implementation Recommendations for Downstream Agents

1. **Enrich All 12 Active Reservoir Cases**:
   - Author complete `case_essence` blocks in `case.yaml` for all 12 cases.
   - Author dedicated `issue-tree.yaml` files for the 11 missing reservoir cases (`aster-diagnostics`, `bluecurrent-water`, `clearcart`, `forge-components`, `harvest-table`, `loom-and-leaf`, `metrolink-mobility`, `northstar-bank`, `orbit-learning`, `sunpeak-solar`, `terrabuild-materials`).
   - Add explicit `diagnosis.hidden` (`release_level: interviewer_only`) facts and dependency linkages to all 11 `facts.yaml` files.
2. **Exemplar Ingestion Batch from Multi-School Corpus**:
   - Convert top 20-30 IIMA structured source cases into full reservoir packages with `case_essence`, `facts.yaml`, and `issue-tree.yaml`.
   - Source/compile representative IIM-B, IIM-C, and ISB case packages across under-represented sectors (e.g. FinTech, B2B SaaS, CleanTech, Aviation, Healthcare).
3. **Update Runtime & Evaluator Schemas**:
   - Update `CaseWorld` in `app/case_runtime.py` to optionally expose `case_essence` safely to post-attempt evaluator services.
   - Wire `evaluator.py` to populate debrief report fields (`what_the_case_wanted_to_test`, `suggested_readings`, `pivotal_insight`, `takeaway_lesson`) directly from the case package's `case_essence`.
