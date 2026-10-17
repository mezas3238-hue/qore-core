# VT08 CRT PURE — R2-CK SIX FROZEN ROLLING-H4 STARTS — RESULTS 001

**Date:** 2026-10-13 · **PR:** #626 · **Status:** EXPLORATORY DESCRIPTIVE AUDIT / NO RULE PROMOTION

**Pre-result freeze:** `VT08-CRT-PURE-R2CK-SIX-START-TIMING-ATTRIBUTION-FREEZE-001.md`.  
**Final correct workflow:** [38453530235](https://github.com/mezas3238-hue/qore-core/actions/runs/38453530235), quality/AUDUSD/USDJPY SUCCESS; original R2-AQ older and R2-AO recent fixed-1.5R event sources and entire R2-CJ pooled cost economics reconciled. All six explicit runner labels output and artifact `report.json` retained.

**IMPORTANT correction to CI lineage:** earlier R2-CK runs `38453200166` and `38453391681` were structurally green but, due a copied workflow invocation, called R2-CJ instead of the R2-CK module. They are **NOT** accepted evidence for six-start attribution. This was repaired at commit `c9532147ae7dd2533a974efd067d1ff80bcda509`. Only run `38453530235` is authoritative for R2-CK H4 strata. Original per-market ledger sources are identical to R2-CJ: AO `35863768335`, AQ `35865028789`.

## Frozen categories

The original six H4 start labels were enumerated before any per-label results were read:

- `ROLLING_H4:1`: 01:00 NY
- `ROLLING_H4:2`: 05:00 NY
- `ROLLING_H4:3`: 09:00 NY
- `ROLLING_H4:4`: 13:00 NY
- `ROLLING_H4:5`: 17:00 NY
- `ROLLING_H4:6`: 21:00 NY

All entries retain R2-AQ/AO original Model #1, NEWEST same-parent competition with cap-one selected hypothesis, structural stop, fixed target 1.5R, C3 expiry, STOP_FIRST. Costs are **hypothetical 0.02R per trade**, not broker BID/ASK fills.

## AUDUSD — 10-year combined (2016–2026)

| NY H4 start | Trades | Gross PF | Gross R | 0.02R net R | Positive net years / 10 |
|---|---:|---:|---:|---:|---:|
| 01:00 | 470 | 0.93173031 | -12.54307107 | -21.94307107 | 4 |
| 05:00 | 421 | 0.91707938 | -13.53227641 | -21.95227641 | 2 |
| 09:00 | 353 | 0.94468696 | -9.68054370 | -16.74054370 | 5 |
| 13:00 | 295 | 1.01845062 | +2.10056092 | -3.79943908 | 5 |
| 17:00 | 450 | **1.24538481** | **+45.98913996** | **+36.98913996** | **8** |
| 21:00 | 479 | 0.99067771 | -2.10806543 | -11.68806543 | 5 |
| TOTAL | 2,468 | 1.00974499 | +10.22574427 | -39.13425573 | 5 across full pooled annual portfolios |

AUDUSD `ROLLING_H4:5` shows **positive 0.02R in both prespecified historical periods**, unlike many other labels:
- Older 2016–2020: 190 trades; gross +29.30332665R, 0.02R net +25.50332665R; positive net years 3/4.
- Recent 2020–2026: 260 trades; gross +16.68581331R, 0.02R net +11.48581331R; positive net years 5/6.

This is a **descriptive retrospective discovery from reused historical data**, NOT a confirmed causal timing edge. One label alone supplies only 450/10 = **45 trades/year**, far below the 170/year research density goal. Apparent PF selection from six reused comparisons is not a legitimate automatic filter.

## USDJPY — 12-year combined (2014–2026)

| NY H4 start | Trades | Gross PF | Gross R | 0.02R net R | Positive net years / 12 |
|---|---:|---:|---:|---:|---:|
| 01:00 | 540 | 0.93241944 | -14.44247395 | -25.24247395 | 2 |
| 05:00 | 472 | **1.10228236** | **+18.03419901** | **+8.59419901** | **7** |
| 09:00 | 519 | 0.95042427 | -12.55287683 | -22.93287683 | 5 |
| 13:00 | 329 | 1.04672206 | +5.36747901 | -1.21252099 | 4 |
| 17:00 | 632 | 0.87179890 | -37.54021636 | -50.18021636 | 3 |
| 21:00 | 561 | 0.87829458 | -33.42471128 | -44.64471128 | 4 |
| TOTAL | 3,053 | 0.94375362 | -74.55860040 | -135.61860040 | 3 across pooled annual portfolios |

USDJPY `ROLLING_H4:2` positive at 0.02R in both frozen historical periods:
- Older 2014–2020: 240 trades; +10.83559982R gross, +6.03559982R at 0.02R, net-positive years 4/6.
- Recent 2020–2026: 232 trades; +7.19859919R gross, +2.55859919R at 0.02R, net-positive years 3/6.

It averages **472/12 = 39.33 trades/year**, less than a quarter of the 170/year research density floor. Annual breadth is 7/12, not strong. More recent six-year net R +2.56R is extremely thin and is not robust to realistic execution cost changes without BID/ASK verification.

## Adjudication / next question

- Six H4 strata reconcile exactly with published R2-CJ AUDUSD net -39.13425573R and USDJPY -135.61860040R at 0.02R per trade.
- The gross and net economic damage is **not uniform across start labels**. Market-specific differences exist in this consumed historical dataset; they could reflect session structure, regime, or post-hoc random variation, not necessarily causality.
- Selecting AUDUSD 17:00 and USDJPY 05:00 *because they won* would be multiple-comparison selection bias. No statistical significance claimed; no timing gates frozen as profitable.
- High-density system's gross economics still need independently tested **causal pre-entry market suitability** across multiple H4 starts rather than selecting one favorable thin-frequency start.
- If proposing a new bounded market-suitability hypothesis, specify mechanism, frozen variables and holdout plan BEFORE looking at new outcomes. Minimum density 170/year requires multiple valid starts; narrow one-start strategy is insufficient without a separately approved density objective. Full development/validation boundaries and fresh unconsumed holdout required.
- Caution: older vs recent periods were already used in earlier QORE model exploration. Seeing similar sign in both does **not** make them untouched out-of-sample validation.

No automatic promotion; no sizing/volume/lot/leverage/capital authority, merge, VPS, DEMO, LIVE, production or real money. BTCUSD R3 market research freeze remains untouched. Global VT08 NOT CERTIFIED.
