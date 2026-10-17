# VT08 CRT PURE — AUDUSD PROTECTION FAMILY RESULT 001

**Checkpoint:** 2026-09-23  
**PR:** #626  
**Run:** `35895053705 — SUCCESS`  
**Status:** PROTECTION IMPROVES ECONOMICS / GATE NARROW FAIL

## Source population

Exact R2-AY OOS retained entries:
- 1,463 trades
- 209 trades/year
- no entry removal

Replay integrity:
- CONTROL mismatch count: 0

## Control

- PF 1.02534351
- +15.69457153R
- DD 31.19534403R
- 5/7 OOS years positive

## Frozen protection family

### BE_CLOSE_050
- PF 1.02268914
- +12.60951366R
- DD 30.45139857R

### BE_CLOSE_075
- PF **1.03542604**
- **+20.59800997R**
- DD **27.76728438R**
- 209 trades/year
- 5/7 OOS years positive
- 599 C3-close exits

### BE_CLOSE_100
- PF 1.03227209
- +19.57092801R
- DD 28.98340160R

### LOCK025_CLOSE_100
- PF 1.02861620
- +17.35386733R
- DD 30.65006827R

### LOCK050_CLOSE_100
- PF 1.02703321
- +16.39388722R
- DD 30.33756827R

## Adjudication

BE_CLOSE_075 is the strongest frozen protection arm.

It improves:
- PF
- Total-R
- DD
- losing streak

without changing entry density.

However PF remains below the frozen 1.05 advancement gate.

No threshold is relaxed.

The next isolated causal lever is lifecycle/expiry because 599/1,463 trades under
BE_CLOSE_075 still terminate at C3 close.

No merge / VPS / DEMO / LIVE / production / real capital.
