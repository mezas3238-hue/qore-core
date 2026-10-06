# VT31 NAS100 — Breaker Rotation Recovery Exception Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Fixed base

Position logic remains frozen as:

`VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT`

Admission base remains:

`A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`.

The previously tested admission hypothesis:

`Breaker + SHORT + prior-day rotation + compressed reference volatility`

improved PF/DD/Monte Carlo and preserved 100% winners, but failed the frozen
half-year non-degradation gate in R8.

## Why the original filter failed temporal adjudication

Observation-only exclusion forensics found that two members of the 9-trade
class were already being partially rescued by maximum-cognition management:

- R8: about -0.46R rather than full structural invalidation;
- R6: about -0.63R rather than full structural invalidation.

Both share the same entry-time causal recovery sequence:

- H1 = bullish;
- M15 = mixed;
- premarket = bullish;
- cash-open = rotation;
- reference reclaim = fresh (<8m).

The <8m reclaim bucket predates this experiment and is already part of VT31's
causal sequence vocabulary. It is not introduced here from terminal outcome.

## New predeclared admission variant

`ABSTAIN_BREAKER_SHORT_ROTATION_COMPRESSED_EXCEPT_BULLISH_RECOVERY_SEQUENCE`

Abstain only when all are true:

- entry family = Breaker;
- side = SHORT;
- prior-day state = rotation;
- frozen reference volatility = compressed;

**unless** all recovery-sequence conditions are true:

- H1 = bullish;
- M15 = mixed;
- premarket = bullish;
- cash-open = rotation;
- reclaim age <8m.

The exception is evaluated entirely before entry.

## Scientific boundary

The excluded-trade terminal outcomes were consumed discovery evidence only.
They have zero runtime authority.

This new rule must be replayed across R5/R6/R8/recent against Comparator 003.
No pass on the same discovery evidence can constitute promotion evidence.

## Frozen development gates

Across all four folds:

- PF non-degrading;
- mean-R non-degrading;
- DD non-degrading;
- density >=75%;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- every half-year mean/DD non-degrading.

Owner direction remains:

- era PF >=1.50;
- recent/combined PF >=1.70;
- expectancy >=+0.15R;
- observed DD <=6R hard gate;
- MC positive >=90%;
- MC p95 DD <=15R.

No sizing, dynamic sizing, leverage, compounding, portfolio allocation, capital
weighting, fold/date identity, outcome oracle, fresh holdout, candidate freeze,
LIVE, real capital or production authority is allowed.
