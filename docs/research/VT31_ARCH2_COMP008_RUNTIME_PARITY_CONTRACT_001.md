# VT31 NAS100 — Comparator 008 Runtime Parity Contract 001

**Status:** PRE-HOLDOUT RUNTIME INTEGRATION CONTRACT  
**Comparator:** `VT31_AB_COMP008_BULLISH_H1_MID_CONFIRMATION_SURVIVOR`

## Purpose

Promote the exact consumed-evidence survivor semantics from research-only
frontiers into importable VT31 runtime policy before candidate freeze.

This work may not change economics. It must reproduce the already-frozen
Comparator-008 behavior.

## Admission policy to promote

The runtime policy must apply the complete Comparator-008 admission stack:

1. expanded-reference abstention plus Order-Block positive-evidence requirement
   (SHORT and reclaim age >=15m);
2. Breaker SHORT + prior-day rotation + compressed reference abstention except
   the already-defined bullish recovery sequence;
3. FVG SHORT + compressed reference + FRESH_LT8M reclaim + FAST_LE5M
   confirmation abstention;
4. Breaker SHORT + prior-day bearish + compressed reference + H1 bullish
   abstention;
5. Rapid Breaker Conflict A;
6. Rapid Breaker Conflict B;
7. Bullish-H1 Breaker SHORT + MID_6_10M confirmation conflict.

All state comparisons must be explicit exact comparisons. Substring matching is
forbidden.

## Post-entry policy to promote

The current Comparator-003 pre-DOL1 cognitive-exit authorizer must become a
runtime primitive.

It may authorize an exit only after maximum cognition is verified and the live
trade is materially adverse (`current_open_r <= -0.50R`), then uses the
already-frozen conjunction:

- CAUTIOUS; or
- MIXED with reclaim age 8-14m; or
- FVG whose destination is not SHALLOW; or
- non-Order-Block in normal reference volatility.

The decision is made from a fully closed M1. Execution remains at next M1 open.

## Parity requirement

Before candidate freeze:

- R5, R6, R8 and recent consumed must be replayed with the promoted runtime
  policy;
- runtime terminal trade identity and R outcomes must equal the frozen
  Comparator-008 research survivor;
- PF, expectancy and observed DD must reproduce Comparator 008;
- no fresh holdout may be touched.

Any mismatch blocks candidate freeze.

## Governance

No sizing, leverage, compounding, portfolio weighting, capital allocation or
CIBO rescue may enter this policy.

This contract is integration work only and grants no LIVE, real-capital or
production authority.
