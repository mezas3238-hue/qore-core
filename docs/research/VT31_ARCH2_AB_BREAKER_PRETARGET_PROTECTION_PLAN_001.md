# VT31 NAS100 — A+B Breaker Pretarget Protection Plan 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Fixed candidate stack

Admission is frozen for this experiment as:

`A_EXPANDED_OB_REQUIRE_SHORT_AGE_11M`

Position logic remains:

`H3 + W5 FULL_COGNITION DOL2 + PS2`

## Defect being attacked

The best current admission survivor reaches recent consumed PF about 1.55 but
observed DD remains about 10.57R. The sovereign certification gate is now 6R,
so admission improvement alone is insufficient.

Residual losing streaks are dominated by Breaker trades. This experiment asks
whether Breaker losses can be compressed causally after fill without deleting
the historical Breaker winners.

## Pure-edge variants

- `CONTROL_AB`: current fixed A+B stack.
- `BREAKER_PS1`: Breaker may improve its stop after one confirmed M1
  protective swing.
- `BREAKER_PS2`: Breaker requires two confirmed M1 protective swings.

A swing is known only after its right M1 bar closes. Any stop change becomes
effective on the next M1. The stop may improve only once and can never widen.

## Frozen adjudication

Across R5, R6, R8 and recent consumed require:

- PF non-degrading;
- mean-R non-degrading;
- DD non-degrading;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- half-year mean/DD non-degrading.

Recent owner direction is reported against:

- PF >=1.50;
- mean >=+0.15R;
- observed DD <=6R;
- MC positive >=90%;
- MC p95 DD <=15R.

No sizing, leverage, compounding, portfolio/capital weighting, outcome oracle,
fold identity or fresh holdout is allowed. No survivor is promotion evidence
because the experiment uses consumed development evidence.
