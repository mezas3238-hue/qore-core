# VT08 CRT PURE — AUDUSD OVERLAP FRESH RESULT 001

**Checkpoint:** 2026-09-23  
**PR:** #626  
**Run:** `35900989541 — SUCCESS`  
**Status:** FROZEN CANDIDATE PASSED UNTOUCHED HISTORICAL HOLDOUT

## Candidate

Frozen before opening the holdout:

- AUDUSD
- ROLLING_H4
- Model #1 unchanged
- NEWEST_SUPERSEDES_CONFIRMATION_FIRST
- one selected hypothesis max per parent
- fixed 1.5R
- structural source stop
- exclude confirmation overlap 0.50 <= overlap < 0.75
- BE_CLOSE_075 protection
- C3-close expiry

## Untouched holdout

2011-09-21 -> 2016-09-21

No holdout data was used to select the overlap state.

## Same-window unfiltered BE0.75 control

- 1,259 trades
- 251.8 trades/year
- PF 1.07430819
- +36.07069330R
- DD 26.08722503R

## Frozen candidate

- **901 trades**
- **180.2 trades/year**
- **PF 1.06367608**
- **+21.97026437R**
- **DD 23.72791200R**
- retention vs control: 71.56%
- positive annual windows: 3/5 = 60%

Annual:
- 2011-12: 195 trades, PF 0.80115019, -16.37645604R
- 2012-13: 181 trades, PF 1.19742357, +11.72622982R
- 2013-14: 171 trades, PF 1.45273277, +26.97715175R
- 2014-15: 170 trades, PF 1.00969731, +0.58697988R
- 2015-16: 184 trades, PF 0.98865297, -0.94364104R

## Frozen advancement gate

- density >=170/year: PASS
- PF >=1.05: PASS
- Total-R >0: PASS
- >=60% years positive: PASS
- DD <= same-window control: PASS
- **GLOBAL: PASS**

## Interpretation

This is the first AUDUSD high-density candidate in the current research chain to
pass every frozen gate on an untouched multi-year historical window.

It is not yet certified for runtime or capital.

Required next layer:
- full candidate continuity build across all consumed+holdout years
- deterministic cost stress
- block/bootstrap path robustness
- temporal/start-subwindow robustness
- overlap/concurrency review if lifecycle is later extended
- final research seal only if robustness survives

No merge / VPS / DEMO / LIVE / production / real capital.
