# VT08 CRT PURE — AUDUSD SOURCE SUITABILITY FAILURE 001

**Checkpoint:** 2026-09-23  
**PR:** #626  
**Run:** `35871986040 — SUCCESS`  
**Status:** SOURCE-STATE WALK-FORWARD FALSIFIED

## High-density core

- ROLLING_H4
- FIXED_1_5R
- no EFF gate
- one selected Model #1 hypothesis max per parent
- structural source stop
- C3 expiry
- STOP_FIRST

## R2-AW causal source-state walk-forward

Training:
- immediately preceding 3 years

Source-state family:
- source_generation
- source_reference_count
- confirmation_delay
- source_body_fraction
- source_range_to_c1
- source_penetration

Selection:
- one source state only
- negative in all 3 training years
- >=12 removed trades in each training year
- residual training retention >=70%
- most negative aggregate qualifying state
- frozen before next 1Y OOS fold

## Combined OOS baseline

- 1,693 trades
- PF 0.98438976
- Total-R -11.42511140R
- DD 46.51937809R

## Combined OOS suitability

- 1,319 trades
- 188.43 trades/year
- retention 77.91%
- PF 0.97990680
- Total-R -11.52781032R
- DD 33.01212162R
- positive OOS years 28.57%

## Advancement gate

- density >=170/year: PASS
- DD <= baseline: PASS
- PF >=1.05: FAIL
- Total-R >0: FAIL
- >=60% OOS years positive: FAIL
- global: FAIL

## Adjudication

Source quality is economically informative in retrospective attribution, but a
single adaptive source-state exclusion does not generalize strongly enough OOS.

Do not promote:
- confirmation_delay=D2 exclusion
- source-body exclusion
- generation exclusion
- source-range exclusion
- source-penetration exclusion

from R2-AW.

The next research layer is the already-frozen confirmation-candle geometry:
- R2-AX: 10Y confirmation geometry attribution atlas
- R2-AY: 3Y -> 1Y causal confirmation-geometry walk-forward

No merge / VPS / DEMO / LIVE / production / real capital.
