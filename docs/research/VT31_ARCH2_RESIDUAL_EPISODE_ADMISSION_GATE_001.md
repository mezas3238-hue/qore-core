# VT31 NAS100 — Residual Episode Admission Frontier 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED-EVIDENCE DEVELOPMENT  
**Base:** `VT31_AB_COMP005_BREAKER_RECOVERY_PLUS_FVG_FRESH_FAST`

## Purpose

Comparator 005 leaves recent observed DD at approximately 8.29R.

Residual attribution found no remaining zero-winner class with 4/4 fold
coverage. Therefore this frontier tests only classes that:

- are causal before entry;
- contain no observed winners in the post-COMP005 population;
- occur in at least two consumed folds; and
- either lie inside the recent max-DD episode or repair a remaining historical
  >6R fold.

## Predeclared classes

### A — recent-episode FVG normal bullish-rotation sequence

`FVG | SHORT | prior-day bullish | reference normal | H1 mixed | premarket rotation | cash-open bullish`

Observed discovery support:

- R5: 1 loss / 0 winners;
- recent: 2 losses / 0 winners.

### B — recent-episode Breaker bearish/compressed conflict

`Breaker | SHORT | prior-day bearish | reference compressed | H1 bullish`

Observed discovery support:

- R5: 1 loss / 0 winners;
- recent: 1 loss / 0 winners.

### C — R8/R5 mature-normal Breaker repair

`Breaker | SHORT | reference normal | reclaim MATURE_GE15M | confirmation FAST_LE5M`

Observed discovery support:

- R5: 5 losses / 0 winners;
- R8: 4 losses / 0 winners.

No new numeric thresholds are introduced. `MATURE_GE15M` and
`FAST_LE5M` are pre-existing VT31 causal buckets.

## Variants

1. A only.
2. B only.
3. A+B.
4. C only.
5. A+B+C.

## Frozen adjudication

Against Comparator 005 require:

- PF non-degrade 4/4;
- mean-R non-degrade 4/4;
- observed DD non-degrade 4/4;
- density >=75% 4/4;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- half-year mean/DD non-degrade.

Certification target remains observed DD <=6R.

No fresh holdout, sizing, leverage, compounding, capital weighting, LIVE, real
capital or production authority.
