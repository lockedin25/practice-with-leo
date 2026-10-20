# Loom & Leaf Reservoir Validation Contract

## Core Mechanism & Diagnosis Preservation

The following fundamental commercial retail proposition must remain true across all simulated sessions:

> The 6 percentage point gross margin collapse is not caused by raw material/fabric cost inflation, but by an aggressive 35% SKU proliferation into unvetted trend capsules with rigid long-lead buys; low sell-through doubled aged stock (>180 days to 29%), triggering severe clearance markdowns while core basics remained highly profitable. Turnaround requires cutting trend SKU count, adopting test-and-react buying, and establishing dynamic in-season replenishment triggers.

## Fact Dependency & Quality Verification
1. `inventory.age` depends on `financials.scope`.
2. `assortment` depends on `inventory.age`.
3. `planning` depends on `assortment`.
4. `economics` depends on `assortment`.
5. `diagnosis.hidden` is strictly `interviewer_only` and never disclosed during candidate turns.

## Simulated Route Verification
- **Route 1 (Merchandising First)**: COGS vs Markdowns -> Assortment Sprawl -> Economics (Basics vs Trend) -> Diagnosis -> 3-Pillar Synthesis.
- **Route 2 (Inventory Aging First)**: Inventory Age Profile -> Merchandising Economics -> Digital Returns -> Diagnosis -> 3-Pillar Synthesis.
