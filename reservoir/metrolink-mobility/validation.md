# MetroLink Mobility Reservoir Validation Contract

## Core Mechanism & Diagnosis Preservation

The following fundamental operational transit proposition must remain true across all simulated sessions:

> The 12% ridership decline is concentrated on 2 main commuter corridors where construction-induced congestion degraded on-time arrival from 81% to 58%, driving time-sensitive commuters to motorcycles and shared cabs due to arrival variance rather than fare levels; with a fixed fleet budget, MetroLink must dynamically reallocate off-peak fleet (<30% load) to peak frequencies, institute terminal headway dispatch, and partner with the city on dedicated bus-priority lanes.

## Fact Dependency & Quality Verification
1. `reliability` depends on `ridership.pattern`.
2. `cause.congestion` depends on `reliability`.
3. `customer.behaviour` depends on `reliability`.
4. `diagnosis.hidden` is strictly `interviewer_only` and never disclosed during candidate turns.

## Simulated Route Verification
- **Route 1 (Reliability First)**: Corridor Pattern -> Reliability & Congestion -> Fleet Allocation -> Diagnosis -> 3-Pillar Synthesis.
- **Route 2 (Capacity First)**: Corridor Pattern -> Peak/Off-Peak Capacity -> Reliability & Congestion -> Policy Safeguards -> Diagnosis -> 3-Pillar Synthesis.
