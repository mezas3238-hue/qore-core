# VT31 NAS100 — Bullish H1 Breaker Conflict Findings 001

**Status:** REJECTED AS DEVELOPMENT POLICY  
**Workflow:** `37511118620` — SUCCESS  
**Evaluated head:** `19862f14a53ac394425115eff78573126c01ec51`  
**Base comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

## Tested predicate

Abstain only when all are true at entry time:

- Breaker;
- SHORT;
- prior-day bullish;
- cash-open bullish;
- H1 bullish.

No new numeric threshold was used.

## Aggregate adjudication

- actuated folds: 4/4;
- PF non-degrade: 2/4;
- mean-R non-degrade: 2/4;
- DD non-degrade: 4/4;
- density floor: 4/4;
- winner preservation all folds: FAIL;
- half-year non-degrade: FAIL;
- all four observed DD values <=6R: YES;
- development survivor: **NO**;
- six-R all-fold survivor: **NO**.

The rule is rejected even though it closes the observed DD gate, because it
destroys valid historical edge.

## Recent consumed

Baseline Comparator 007:

- PF: 2.207302;
- mean: +0.814807R;
- DD: 6.593383R;
- sample: 33.

Tested rule:

- PF: 2.570921;
- mean: +1.001287R;
- DD: 4.493383R;
- sample: 30;
- excluded: 3 losses / 0 winners;
- winner count preservation: 100%;
- winner-R preservation: 100%;
- MC positive: 97.28%;
- MC p95 DD: 9.4995R.

Therefore the recent-only picture is excellent but insufficient for promotion.

## Historical damage

### R5

The rule excludes:

- one -1R loss;
- one +6.808219R winner.

Result:

- PF falls from 4.643582 to 4.545387;
- mean falls from +2.105023R to +2.059624R;
- half-year non-degrade fails in 2021-H1.

### R6 — decisive rejection

The rule excludes:

- one -1R loss;
- one +21.50R winner;
- one flat raw-R trade.

Result:

- PF falls from 5.140589 to 4.006409;
- mean falls from +2.705185R to +2.093462R;
- winner count preservation: 85.71%;
- winner-R preservation: **72.29%**;
- 2020-H1 mean degrades materially.

This alone disqualifies the hypothesis.

### R8

The rule excludes:

- one +4.645833R winner;
- one -1R loss.

Result:

- PF and mean improve because of sample geometry;
- winner count preservation: 87.5%;
- winner-R preservation: 93.96%;
- 2016-H1 temporal mean still degrades.

## Interpretation

The broad causal statement

`SHORT Breaker + prior-day bullish + cash-open bullish + H1 bullish`

is **not sufficient** to identify bad trades.

It mixes:

- genuine structural-invalidations;
- valid high-R continuation/extension winners.

Therefore it must not be promoted to Comparator 008 or runtime.

## Next research step

Remain on Comparator 007.

Perform observation-only refinement forensics on every trade matching the
rejected broad class, comparing pre-entry dimensions such as:

- H4;
- M15;
- premarket;
- reference volatility;
- position in prior-day range;
- reclaim bucket;
- confirmation bucket.

The objective is to determine whether a narrower **semantic** state separates
the historical large winners from the losses without introducing date/fold or
outcome authority.

No fresh holdout may be opened.
