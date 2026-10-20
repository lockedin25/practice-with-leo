# SunPeak Solar Reservoir Validation Contract

## Core Mechanism & Diagnosis Preservation

The following fundamental commercial pricing proposition must remain true across all simulated sessions:

> The conversion bottleneck (9% vs 18% target) is not caused by uncompetitive hardware pricing or low lead interest, but by presenting solar as a large upfront capital expenditure to cash-constrained SME owners who prioritize working capital over 10-year NPV; because monthly electricity savings exceed 5-year loan installments for high-usage commercial clients, SunPeak must package installations as a financed monthly OPEX offer with partnered non-recourse lenders.

## Fact Dependency & Quality Verification
1. `customer.cashflow` depends on `funnel`.
2. `economics.loan` depends on `price.position`.
3. `economics.segment` depends on `economics.loan`.
4. `diagnosis.hidden` is strictly `interviewer_only` and never disclosed during candidate turns.

## Simulated Route Verification
- **Route 1 (Funnel First)**: Funnel Drop-off -> Customer Cash Flow -> Financed Economics -> Segment Prioritization -> Diagnosis -> 3-Pillar Synthesis.
- **Route 2 (Competitive Benchmark First)**: Competitor Pricing -> Customer Hurdle Rates -> Loan Economics -> Process Integration -> Diagnosis -> 3-Pillar Synthesis.
