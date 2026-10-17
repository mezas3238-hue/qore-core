# VT08 CRT PURE — AUDUSD CONFIRMATION GEOMETRY RESULT 001

**Checkpoint:** 2026-09-23  
**PR:** #626  
**R2-AX run:** `35893069904 — SUCCESS`  
**R2-AY run:** `35893170251 — SUCCESS`  
**Status:** CAUSAL IMPROVEMENT / ADVANCEMENT GATE NARROW FAIL

## R2-AX — 10Y confirmation geometry atlas

High-density core:
- ROLLING_H4
- FIXED_1_5R
- EFF OFF
- one selected Model #1 hypothesis per parent

Full 10Y:
- 2,468 trades
- 246.8 trades/year
- PF 1.00974499
- +10.22574427R
- DD 67.37729085R

Strong retrospective toxic confirmation states included:

1. `CONFOVERLAP_0.50_TO_0.75`
   - 724 trades
   - PF 0.88089225
   - -38.38341189R
   - negative 8/10 years
   - residual retention 70.66%

2. `CONFDISP_LT_0.50 × CONFOVERLAP_0.50_TO_0.75`
   - 518 trades
   - PF 0.85762963
   - -34.65730187R
   - negative 7/10 years
   - retention 79.01%

3. `CONFRANGE_SRC_0.50_TO_1.00 × THROUGH_SOURCE_EXTREME`
   - 499 trades
   - PF 0.87186497
   - -25.80165402R
   - retention 79.78%

4. `CONFBODY_0.50_TO_0.75 × CONFLOC_GE_0.75`
   - 608 trades
   - PF 0.91056700
   - -23.84971250R
   - negative 7/10 years
   - retention 75.36%

R2-AX did not promote any state.

## R2-AY — 3Y -> 1Y causal confirmation walk-forward

Combined OOS baseline:
- 1,693 trades
- PF 0.98438976
- -11.42511140R
- DD 46.51937809R

Combined OOS confirmation-suitability:
- 1,463 trades
- 209.0 trades/year
- retention 86.41%
- PF 1.02534351
- +15.69457153R
- DD 31.19534403R
- positive OOS years: 5/7 = 71.43%

## Frozen advancement gate

- density >=170/year: PASS
- Total-R >0: PASS
- >=60% OOS years positive: PASS
- DD <= baseline: PASS
- PF >=1.05: **FAIL**
- global: FAIL

## Interpretation

Confirmation geometry is the first tested suitability layer that improves the
high-density AUDUSD core simultaneously on:

- Total-R
- drawdown
- temporal breadth
- retained density

while remaining causal walk-forward.

It is therefore economically informative, but not yet sufficient for advancement
because PF remains below the frozen 1.05 gate.

No threshold is relaxed after the result.

## Active next layer

R2-AZ is frozen as a post-entry protection family over the exact R2-AY retained
OOS entries.

No entries are removed by R2-AZ.

Protection:
- only after completed M15 closes
- effective on next M15 bar
- stop never widens
- fixed 1.5R target unchanged
- STOP_FIRST preserved

No merge / VPS / DEMO / LIVE / production / real capital.
