# VT08 CRT PURE — R2-N USDJPY C1-BODY HISTORICAL VALIDATION 001

**Identity:** `VT08_CRT_PURE_R2N_USDJPY_C1_BODY_VALIDATION_001`  
**Workflow run:** `35843878633`  
**Evidence HEAD:** `3d9600e24105b47a14ef46e6468315d96365e34e`  
**Validation:** `2020-09-21 -> 2022-09-21`  
**Status:** COMPLETE / PRIMARY FALSIFIED / NO SURVIVORS

## 1. Frozen family

Before validation results:

- CONTROL
- C1 body 0.25-0.50 — PRIMARY
- C1 body 0.20-0.50
- C1 body 0.25-0.55
- C1 body 0.20-0.55

Research gate:

- min 20 trades;
- PF >= 1.05;
- total R > 0;
- DD <= 12R;
- both annual halves > 0R.

Neighbor survival was explicitly forbidden from replacing a failed primary candidate.

## 2. Validation integrity

Run `35843878633`: SUCCESS.

- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- 2020-2022 validation: SUCCESS
- Cognitive Gate: SUCCESS

The earlier run failed before replay because of Mypy narrowing on optional candidate bounds.
The candidate family and thresholds were not changed.

## 3. Primary candidate

`C1_BODY_025_050_PRIMARY`

- 24 trades
- PF 0.80160158
- -1.57346517R
- DD 5.87155575R

Year 1:
- 14 trades
- PF 0.77673056
- -1.02627764R

Year 2:
- 10 trades
- PF 0.83588874
- -0.54718753R

**FAILED.**

This directly falsifies the 2022-2026 C1-body clue as a universal USDJPY regime rule.

## 4. Neighborhoods

`C1_BODY_020_050`:
- 27 trades
- PF 1.35298692
- +2.79948116R
- Year 1 -1.02627764R
- Year 2 +3.82575880R
- FAIL: Year 1

`C1_BODY_025_055`:
- 33 trades
- PF 0.66934289
- -3.80127567R
- negative in both halves

`C1_BODY_020_055`:
- 36 trades
- PF 1.04972725
- +0.57167066R
- Year 1 -1.55550941R
- FAIL

No neighbor survived.

## 5. Control

- 112 trades
- PF 0.99936900
- -0.02414470R
- DD 11.91901470R

Year 1:
- +1.35003057R

Year 2:
- -1.37417527R

USDJPY therefore presents three materially different regimes:

- 2020-2022: approximately break-even control;
- 2022-2024: strongly negative control;
- 2024-2026: mildly positive control.

## 6. Adjudication

Do not tune the C1-body bounds.

The correct next layer is a multi-regime atlas that spans all three 2Y blocks and uses
pre-parent state over longer horizons. The target is not a profitable slice in one period;
it is a causal state definition that remains coherent across:

- 2020-2022;
- 2022-2024;
- 2024-2026.

## 7. Governance

- no survivor;
- no candidate promotion;
- PR DRAFT / UNMERGED;
- no VPS / DEMO / LIVE / production / real capital.
