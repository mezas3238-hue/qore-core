# VT08 EURJPY Cognitive Core Stack — 5Y Extended Validation V1 Freeze

Status: **PRE-ECONOMIC EXTENDED VALIDATION FREEZE / NO RETUNING**

EURJPY is the only market from the five-market program that passed both:

- the backward fresh temporal screen; and
- the frozen Core Stack robustness suite.

This document freezes the next validation stage before any five-year EURJPY
economic outcome is observed.

## Candidate identity

The candidate remains exactly `VT08_COGNITIVE_CORE_STACK_DEV_V1`:

1. VT08 signal admission unchanged.
2. VT08 entry unchanged.
3. VT08 structural initial stop unchanged.
4. Original fixed 2R target unchanged.
5. Original next-H4 lifecycle unchanged.
6. 50% bank at the VT08 reference-H4 midpoint when reached.
7. Bank remaining exposure at the opposite reference-H4 extreme when reached.
8. Pre-existing VT08 CIBO `aggressive` ratchets while exposure remains:
   - +0.50R observed -> stop 0.00R from next M15;
   - +1.00R observed -> stop +0.50R from next M15;
   - +1.50R observed -> stop +1.00R from next M15.
9. Active stop first on ambiguous M15.
10. Runner OFF.
11. No anchor/side deletion.
12. No parameter scan.

## Five-year evidence contract

Reuse the existing cTrader DEMO long-horizon acquisition machinery, but the
five-year wrapper MUST additionally fail closed unless actual M5, M15 and H4
history satisfies all of:

- requested horizon: 1825 calendar days;
- first retained bar no later than requested start + 5 days;
- recent retained close no earlier than checked time - 5 days;
- actual first-to-last span >= 1815 days;
- DEMO only;
- read_only=true;
- account_is_live=false.

The shared 730-1095 day collector CLI is not modified. Five-year acquisition is
research-local so existing Trader Lab contracts remain unchanged.

## Frozen 5Y gates

EURJPY advances beyond extended validation only if all are true:

- sample >= 100 terminal trades;
- full PF >= 1.50;
- full total R > 0;
- observed DD <= 6R;
- each of five consecutive 365-day blocks has total R > 0 and mean R > 0;
- each of four rolling 730-day windows has:
  - sample >= 30;
  - PF >= 1.20;
  - total R > 0;
  - DD <= 8R;
- Monte Carlo:
  - 10,000 deterministic paths;
  - moving block length 5;
  - positive terminal >= 0.90;
  - p95 DD <= 15R;
- +0.02R execution stress:
  - total R > 0;
  - PF >= 1.20;
  - DD <= 7R;
- +0.05R stress remains total-positive with PF > 1.00;
- removing the largest winner remains total-positive with PF > 1.20.

Removing the largest five winners remains diagnostic only.

## Evidence semantics

This stage is extended validation. It does not retroactively make the already
consumed 2023-2026 evidence fresh. It asks whether the exact frozen mechanism is
stable over a materially longer history.

## Authority

- research_only=true
- parameter_scan=false
- retuning_after_result=false
- demo_eligible=false
- live_authorized=false
- production_authorized=false
- real_capital_authorized=false
