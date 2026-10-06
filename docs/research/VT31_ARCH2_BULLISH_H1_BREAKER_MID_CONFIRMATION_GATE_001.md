# VT31 NAS100 — Bullish H1 Breaker Mid-Confirmation Gate 001

**Status:** PREDECLARED DEVELOPMENT GATE  
**Base comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

## Observation-only refinement source

The previously predeclared broad class:

- Breaker;
- SHORT;
- prior-day bullish;
- cash-open bullish;
- H1 bullish;

was replayed unchanged across R5, R6, R8 and recent consumed and was rejected
as a development policy because it removed valid high-R historical winners.

Source workflow:

`37512015411`

The rejected broad class nevertheless provides a useful observation-only
control for refinement.

Within that class, the already-existing confirmation-latency bucket
`MID_6_10M` separates the residual-DD losses from the large historical winners
seen in that replay:

- recent consumed: 2 losses / 0 winners in `MID_6_10M`;
- R5: 1 loss / 0 winners in `MID_6_10M`;
- R6: 0 matching trades in `MID_6_10M`;
- R8: 0 matching trades in `MID_6_10M`.

The two recent matches are both inside the exact Comparator-007 maximum
drawdown episode:

- `2023-12-18T15:16:00+00:00`;
- `2024-02-08T15:07:00+00:00`.

The large historical winners removed by the rejected broad rule use the
pre-existing `FAST_LE5M` confirmation bucket, not `MID_6_10M`.

This observation is discovery evidence only. Outcome is not runtime authority.

## Predeclared hypothesis

`BULLISH_H1_BREAKER_SHORT_MID_CONFIRMATION_CONFLICT`

Abstain only when **all** are true at entry time:

1. `entry_family == breaker`;
2. `side == short`;
3. `prior_day_state == bullish`;
4. `cash_open_state == bullish`;
5. `h1_state == bullish`;
6. pre-existing confirmation-latency state == `MID_6_10M`.

No H4 requirement is added.

No M15 requirement is added.

No premarket requirement is added.

No volatility requirement is added.

No reclaim-age requirement is added.

No new numeric threshold is introduced. `MID_6_10M` is an already-existing
causal bucket used by prior VT31 research before this hypothesis.

No date, fold identity, terminal outcome, future bar, sizing, leverage,
compounding, portfolio weighting, capital state or CIBO capital authority may
influence the action.

## Cross-fold adjudication

The exact predicate above must run unchanged on R5, R6, R8 and recent consumed.

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

A no-op equality in R6/R8 is allowed as a control, but the mechanism may only
survive if it actuates in at least two consumed partitions and the aggregate
gate passes.

## Governance

This is consumed-evidence development research only.

It is not Comparator 008, candidate freeze, certification, LIVE authorization,
or permission to open the fresh holdout.

Fresh holdout remains sealed.

Sizing, dynamic sizing, leverage, compounding, portfolio weighting, capital
allocation rescue and CIBO rescue remain forbidden.
