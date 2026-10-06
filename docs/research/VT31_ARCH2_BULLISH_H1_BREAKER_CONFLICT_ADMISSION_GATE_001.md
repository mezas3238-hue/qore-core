# VT31 NAS100 — Bullish H1 Breaker Conflict Admission Gate 001

**Status:** PREDECLARED DEVELOPMENT GATE  
**Base comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

## Causal observation

The exact Comparator-007 recent drawdown forensics reconstructed a peak-to-trough
episode from 2023-12-01 to 2024-03-01.

Within that episode, two full-loss SHORT Breakers share the same pre-entry
directional conflict:

- prior-day state = bullish;
- cash-open state = bullish;
- H1 state = bullish;
- side = SHORT;
- entry family = Breaker.

The proposed distinction is semantic: a SHORT Breaker is admitted into a market
where the prior day, the H1 context and the active cash-open state are all
bullish.

## Predeclared hypothesis

`BULLISH_H1_BREAKER_SHORT_CONFLICT`

Abstain only when **all** are true:

1. `entry_family == breaker`;
2. `side == short`;
3. `prior_day_state == bullish`;
4. `cash_open_state == bullish`;
5. `h1_state == bullish`.

No H4 requirement is added.

No M15 requirement is added.

No volatility requirement is added.

No reclaim-age or confirmation-latency threshold is added.

No date, fold identity, future outcome, sizing, leverage, capital state or CIBO
capital authority may influence the action.

## Cross-fold adjudication

The same exact predicate must run unchanged on R5, R6, R8 and recent consumed.

Required for a development survivor:

- PF non-degrade: 4/4;
- mean-R non-degrade: 4/4;
- observed DD non-degrade: 4/4;
- density >=75%: 4/4;
- winner-count preservation >=80%;
- winner-R preservation >=90%;
- half-year mean/DD non-degrade;
- economic actuation in at least two consumed partitions;
- R5 DD <=6R;
- R6 DD <=6R;
- R8 DD <=6R;
- recent DD <=6R.

Recent direction gates remain:

- PF >=1.70;
- mean >=+0.15R/trade;
- MC positive >=90%;
- MC p95 DD <=15R.

## Governance

This is consumed-evidence development research only.

It is not candidate freeze, certification, LIVE authorization or permission to
open the fresh holdout.

Sizing, dynamic sizing, leverage, compounding, portfolio weighting, capital
allocation rescue and CIBO rescue remain forbidden.
