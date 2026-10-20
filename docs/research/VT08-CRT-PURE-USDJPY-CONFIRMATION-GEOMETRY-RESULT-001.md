# VT08 CRT PURE — USDJPY CONFIRMATION GEOMETRY RESULT 001

**Checkpoint:** 2026-09-23  
**PR:** #626  
**R2-BC run:** `35901301940 — SUCCESS`  
**R2-BD run:** `35901667508 — SUCCESS`  
**Status:** CONFIRMATION GEOMETRY DOES NOT REPAIR USDJPY

## R2-BC — 12Y baseline

2014-09-21 -> 2026-09-21

- 3,056 trades
- 254.67 trades/year
- PF 0.94379848
- -74.58491619R
- DD 111.95028145R

The market has ample density. The problem is economic quality.

## R2-BD — 3Y -> 1Y confirmation-geometry walk-forward

Combined OOS baseline:
- 2,257 trades
- PF 0.90304101
- -97.08302715R
- DD 109.18304891R

OOS retained:
- 1,893 trades
- 210.33 trades/year
- retention 83.87%
- PF 0.88497770
- -96.35339733R
- positive OOS years 11.11%

Gate:
- density: PASS
- DD: PASS
- PF: FAIL
- Total-R: FAIL
- temporal breadth: FAIL
- global: FAIL

## Adjudication

USDJPY is not an AUDUSD copy.

Confirmation geometry contains retrospective toxic states, but adaptive exclusion
does not repair the market.

Next step:
- USDJPY-specific PF loss attribution;
- pre-stop path analysis;
- determine selection failure vs position-retention failure before any new rule.

No merge / VPS / DEMO / LIVE / production / real capital.
