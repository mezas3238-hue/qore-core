# VT08 CRT PURE — R2-H PROJECTED RR ACCEPTANCE 001

**Identity:** `VT08_CRT_PURE_R2H_PROJECTED_RR_ACCEPTANCE_001`  
**Workflow run:** `35811786720`  
**Evidence HEAD:** `c1720388be933e2877db525ee8873c13185699af`  
**Status:** COMPLETE / NO UNIVERSAL RR GATE  
**Base competition:** `NEWEST_SUPERSEDES_CONFIRMATION_FIRST`

## 1. Objective

R2-H kept the CRT methodology and R2-G competition policy fixed and changed one
engineering dimension only:

`MINIMUM_PROJECTED_RR_TO_C1_MIDPOINT`

The family was frozen before outcomes:

`0.00 / 0.50 / 0.75 / 1.00 / 1.25 / 1.50 / 2.00 R`

Projected RR is known at the causal entry slot from:

- entry open;
- source-candle structural stop;
- already-known C1 midpoint.

No stop, target, confirmation, timing or parent-CRT rule changed.

## 2. Validation

Run `35811786720` completed SUCCESS.

- Quality: SUCCESS
- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- AUDUSD: SUCCESS
- USDJPY: SUCCESS
- BTCUSD: SUCCESS

Cognitive Gate:
`35811786700 — SUCCESS`.

## 3. AUDUSD

| Min RR | Trades | PF | Total R | DD R | Year 1 R | Year 2 R |
|---|---:|---:|---:|---:|---:|---:|
| 0.00 | 114 | 0.9764 | -1.000 | 9.687 | -4.620 | +3.620 |
| 0.50 | 93 | 0.9615 | -1.510 | 10.360 | -5.108 | +3.598 |
| 0.75 | 82 | 1.0004 | +0.013 | 10.120 | -5.639 | +5.652 |
| 1.00 | 71 | 1.0932 | +2.850 | 9.184 | -5.197 | +8.047 |
| 1.25 | 65 | 1.0238 | +0.700 | 10.482 | -6.496 | +7.196 |
| 1.50 | 52 | 0.9373 | -1.555 | 9.341 | -5.449 | +3.894 |
| 2.00 | 34 | 0.7511 | -4.525 | 5.662 | -3.856 | -0.670 |

**Finding:** no RR threshold repairs AUDUSD temporal instability. Year 1 remains
negative at every tested threshold.

## 4. USDJPY

| Min RR | Trades | PF | Total R | DD R | Year 1 R | Year 2 R |
|---|---:|---:|---:|---:|---:|---:|
| 0.00 | 104 | 1.1139 | +4.160 | 12.321 | +4.752 | -0.591 |
| 0.50 | 86 | 1.1821 | +5.760 | 12.064 | +6.411 | -0.652 |
| 0.75 | 70 | 0.9385 | -1.936 | 15.212 | +3.720 | -5.657 |
| 1.00 | 61 | 1.0174 | +0.475 | 12.955 | +3.170 | -2.695 |
| 1.25 | 49 | 0.9983 | -0.040 | 12.719 | +3.836 | -3.875 |
| 1.50 | 44 | 1.1507 | +3.038 | 9.466 | +4.263 | -1.225 |
| 2.00 | 36 | 1.1957 | +3.174 | 8.024 | +3.351 | -0.178 |

**Finding:** every tested threshold remains positive in Year 1 and negative in
Year 2. This is regime/context inversion, not a simple RR problem.

## 5. BTCUSD

| Min RR | Trades | PF | Total R | DD R | Year 1 R | Year 2 R |
|---|---:|---:|---:|---:|---:|---:|
| 0.00 | 230 | 1.0567 | +4.626 | 14.646 | -1.915 | +6.541 |
| 0.50 | 177 | 1.0615 | +4.463 | 12.767 | +1.273 | +3.190 |
| 0.75 | 154 | 1.0512 | +3.338 | 10.366 | +3.664 | -0.326 |
| 1.00 | 129 | 1.0588 | +3.334 | 9.414 | +2.830 | +0.503 |
| 1.25 | 111 | 1.1428 | +7.022 | 7.146 | +6.432 | +0.590 |
| 1.50 | 86 | 1.0929 | +3.657 | 10.611 | +7.327 | -3.671 |
| 2.00 | 61 | 0.8867 | -3.602 | 8.769 | +2.699 | -6.301 |

**Finding:** BTCUSD does contain an intermediate projected-RR region that improves
the current sample. In particular 1.25R is positive in both halves with lower
drawdown.

This is **not promoted**. The 1.25R observation was discovered on consumed data and
must survive fresh/OOS evidence before becoming a candidate rule.

## 6. Adjudication

A universal projected-RR threshold is rejected.

R2-H proves:

- projected geometry carries information;
- it can materially improve BTCUSD;
- it does not explain AUDUSD's Year-1 failure;
- it does not explain USDJPY's Year-1/Year-2 inversion.

Therefore the next root-cause layer is contextual and market-specific.

R2-I is assigned to causal pre-entry forensics across:

- source generation;
- reference multiplicity;
- confirmation delay;
- projected RR;
- source body/range;
- source range relative to C1;
- penetration depth;
- direction;
- timing triplet;
- selected cross-dimensions.

No R2-I slice is automatically promoted to a filter.

## 7. Governance

- PR DRAFT / UNMERGED.
- No VPS mutation.
- No DEMO activation.
- No LIVE activation.
- No production authority.
- No real-capital authority.
