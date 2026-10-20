# E2E Test Infra: MBB Case Prep V2

## Test Philosophy
- Opaque-box, requirement-driven. Derives test assertions directly from `ORIGINAL_REQUEST.md`.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial + Real-World Workload Testing.

## Feature Inventory & Test Mapping
| # | Feature | Requirement Source | Tier 1 (Coverage) | Tier 2 (Boundary/Edge) | Tier 3 (Cross-Feature) | Tier 4 (Real-World) |
|---|---------|-------------------|:-----------------:|:----------------------:|:----------------------:|:-------------------:|
| 1 | Case Essence Schema & Loader | ORIGINAL_REQUEST §R1.1 | 5 tests | 5 tests | Pairwise | Real-world |
| 2 | Reservoir 12-Case 5-File Packages | ORIGINAL_REQUEST §R1.1, R1.2 | 5 tests | 5 tests | Pairwise | Real-world |
| 3 | Multi-School Case Corpus Expansion | ORIGINAL_REQUEST §R1.1, R1.2 | 5 tests | 5 tests | Pairwise | Real-world |
| 4 | Knowledge Base Linkages | ORIGINAL_REQUEST §R1.1 | 5 tests | 5 tests | Pairwise | Real-world |
| 5 | BCG 1–5 Scoring & 5 Dimensions | ORIGINAL_REQUEST §R2.1 | 5 tests | 5 tests | Pairwise | Real-world |
| 6 | Rich EvaluationReport Payload | ORIGINAL_REQUEST §R2.2 | 5 tests | 5 tests | Pairwise | Real-world |
| 7 | Evaluator Engine & Fallback | ORIGINAL_REQUEST §R2.1, R2.2 | 5 tests | 5 tests | Pairwise | Real-world |
| 8 | DB Persistence of Evaluations | ORIGINAL_REQUEST §R3.1 | 5 tests | 5 tests | Pairwise | Real-world |
| 9 | Attempt Lifecycle Auto-Evaluation | ORIGINAL_REQUEST §R3.2 | 5 tests | 5 tests | Pairwise | Real-world |
| 10 | Profile & Attempt APIs | ORIGINAL_REQUEST §R3.3, R3.4 | 5 tests | 5 tests | Pairwise | Real-world |
| 11 | Debrief UI 7 Cards & Theme | ORIGINAL_REQUEST §R4.1-R4.7 | 5 tests | 5 tests | Pairwise | Real-world |

## Test Architecture
- **Runner**: `pytest tests/` (all tests must run and pass with exit code 0)
- **Structure**:
  - `tests/test_case_essence.py`: Validation of case packages, essence schemas, multi-school catalog, issue trees, and knowledge base links.
  - `tests/test_evaluator_v2.py`: BCG 1.0–5.0 scoring scale, 5 dimensions, rich report models, golden rewrites, what case wanted to test payload, and fallback evaluator.
  - `tests/test_store_persistence.py`: SQLite evaluation storage, retrieval, attempt lifecycle auto-evaluation, profile metrics, and API endpoints.
  - `tests/test_debrief_ui.py`: HTML/JS/CSS structural verification of all 7 cards, design tokens, and API payload compatibility.
  - `tests/test_e2e_workflow.py`: End-to-end simulation from case selection through conversation turns, attempt completion, evaluation storage, profile update, and debrief rendering.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised |
|---|----------|--------------------|
| 1 | Full Case Lifecycle on Reservoir Case with Rich Evaluation | F1, F2, F5, F6, F7, F8, F9, F10, F11 |
| 2 | Multi-School Case Selection & Essence Validation | F1, F3, F4, F6, F10 |
| 3 | Debrief Page Delivery & Verification with 5 Dimensions & Golden Rewrites | F5, F6, F10, F11, F12, F13, F14, F15, F16, F17 |
| 4 | Profile Trend Tracking Across Multiple 1-5 Evaluated Attempts | F5, F8, F10 |
| 5 | Deterministic Fallback Evaluation under Missing/Degraded LLM Conditions | F5, F6, F7, F8, F9 |

## Minimum Thresholds
- Tier 1: ≥5 per feature
- Tier 2: ≥5 boundary & negative tests
- Tier 3: Cross-feature integration tests
- Tier 4: ≥5 end-to-end real-world scenarios
