# VT31 NAS100 — Bullish H1 Mid-Confirmation Breaker Conflict Gate 001

**Status:** PREDECLARED DEVELOPMENT GATE  
**Base comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

## Observation-only refinement

The broader predicate:

`Breaker + SHORT + prior-day bullish + cash-open bullish + H1 bullish`

was correctly rejected as a development policy because it mixed valid high-R
historical winners with losses.

Across all Comparator-007 trades matching that rejected broad class, the
already-existing confirmation-latency buckets separate as follows:

- `FAST_LE5M`: 6 trades = 3 winners / 3 losses;
- `MID_6_10M`: 3 trades = 0 winners / 3 losses;
- `SLOW_GE11M`: 1 raw-flat trade.

The three `MID_6_10M` observations are:

- R5: `2021-04-01T14:27:00+00:00`, raw `-1R`;
- recent: `2023-12-18T15:16:00+00:00`, raw `-1R`;
- recent: `2024-02-08T15:07:00+00:00`, raw `-1R`.

The large winners that invalidated the broad rule are all outside the
`MID_6_10M` bucket.

No new numerical threshold is introduced. `MID_6_10M` already exists in the
causal VT31 research vocabulary and is computed from entry-time confirmation
latency.

## Predeclared hypothesis

`BULLISH_H1_BREAKER_SHORT_MID_CONFIRMATION_CONFLICT`

Abstain only when **all** are true:

1. `entry_family == breaker`;
2. `side == short`;
3. `prior_day_state == bullish`;
4. `cash_open_state == bullish`;
5. `h1_state == bullish`;
6. confirmation latency bucket == `MID_6_10M`.

No H4 requirement is added.

No M15 requirement is added.

No volatility requirement is added.

No reclaim-age threshold is added.

No date, fold identity, future outcome, sizing, leverage, capital state or CIBO
capital authority may influence the action.

## Cross-fold adjudication

The exact same predicate must run unchanged on R5, R6, R8 and recent consumed.

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

Consumed-evidence development only.

This gate does not freeze a candidate and does not authorize opening Fresh
Holdout.

Sizing, dynamic sizing, leverage, compounding, portfolio weighting, capital
allocation rescue and CIBO rescue remain forbidden.
