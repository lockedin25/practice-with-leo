## 2026-08-24T07:51:14Z
You are the specialized Worker subagent for Milestone 3A: Industry Dossiers Batch 1 (Industries 01 to 05).
Your assigned working directory for metadata is: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/worker_ind_batch1_1`
Your write ownership for project deliverables is exclusively:
- `knowledge_base/industries/01_logistics_and_cold_chain.md`
- `knowledge_base/industries/02_ecommerce_and_marketplaces.md`
- `knowledge_base/industries/03_pharma_and_healthcare.md`
- `knowledge_base/industries/04_banking_and_financial_services.md`
- `knowledge_base/industries/05_fmcg_and_cpg.md`

MANDATORY FIRST STEP: Read `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/ORIGINAL_REQUEST.md` and `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/PROJECT.md`. Also check materials in `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/corpus/` (IIMA casebook industry overviews, playbooks).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Required structure for EACH industry dossier:
1. Industry Overview & Macro Dynamics (Global and India context where relevant)
2. Complete End-to-End Value Chain (with key actors, margin capture at each step)
3. Revenue Models & Monetization Mechanics
4. Detailed Unit Economics & Contribution Margin breakdown (sample P&L / unit economics table)
5. Comprehensive Cost Structure (Fixed vs Variable cost breakdown, key cost drivers)
6. Essential KPI Formulas (with clear definitions, mathematical formulations, and normal benchmark ranges)
7. Typical Case Scenarios & Diagnostic Issue Trees
8. Common Pitfalls & Candidate "Landmines" in this industry

Specific Focus for Batch 1:
- `01_logistics_and_cold_chain.md`: Fleet utilization, ton-km, route density, temperature zones, empty miles / deadhead %, hub-and-spoke vs point-to-point, spoilage rates.
- `02_ecommerce_and_marketplaces.md`: GMV vs Net Revenue, take rates, CAC/LTV, cohort retention, return rates (RTO), fulfillment cost per order (FPO), marketplace vs 1P inventory.
- `03_pharma_and_healthcare.md`: Drug discovery & clinical trial phases (I-IV), patent cliff & generic erosion, API vs formulation, hospital economics (ARPOB, ALOS, bed occupancy, doctor payout models).
- `04_banking_and_financial_services.md`: Net Interest Margin (NIM), CASA ratio, Cost of Funds, Yield on Advances, Credit Risk / GNPA / NNPA, Provision Coverage Ratio (PCR), Cost-to-Income ratio, Capital Adequacy (CAR).
- `05_fmcg_and_cpg.md`: Trade promotions, distributor margins, modern trade vs general trade (kiranas) vs quick commerce, primary vs secondary sales, SKU rationalization, working capital cycle.

Quality Requirements:
- Every file MUST begin with clean YAML frontmatter (`title`, `category`, `topics_covered`, `target_use_case`).
- Zero placeholders, zero TODOs, deeply thorough and authoritative MBB-level content.
- Write each file completely using `write_to_file`.

When complete, write your handoff report to `.agents/worker_ind_batch1_1/handoff.md` and send a completion message back to parent.
