# VT31 NAS100 — Breaker Rotation Admission Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Fixed comparator

All admission variants in this frontier are measured against:

`VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT`

with the already-fixed A admission:

`A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`.

## Discovery evidence

Observation-only Breaker entry-quality forensics compared all Breaker winners
and losses across R5/R6/R8/recent.

The multidimensional causal state:

`Breaker + SHORT + prior_day_state=rotation + reference_volatility_state=compressed`

contains:

- R5: 1 trade, 0 winners, 1 loss;
- R6: 3 trades, 0 winners, 3 losses;
- R8: 3 trades, 0 winners, 3 losses;
- recent: 2 trades, 0 winners, 2 losses.

Total:

`9 trades / 9 losses / 0 winners`.

Four of the nine are rapid structural invalidations, but the admission
hypothesis is **not** based on future invalidation. It uses only entry-time
causal state.

## Why this is admissible for a causal test

No new numeric threshold is introduced.

All dimensions already exist before entry:

- selected entry family;
- side;
- prior-day regime;
- reference-volatility state.

The conjunction is multidimensional, consistent with VT31 Trader Experience
which explicitly warns against promoting isolated context bins.

This evidence is consumed discovery only. It cannot promote itself.

## Predeclared variants

1. `COMP003_CONTROL`
   - fixed current admission and Comparator 003 position logic.

2. `ABSTAIN_BREAKER_SHORT_ROTATION_COMPRESSED`
   - same stack;
   - abstain only when:
     - entry family = Breaker;
     - side = SHORT;
     - prior-day state = rotation;
     - reference volatility = compressed.

No other entry family or context is changed.

## Frozen development gates

Across R5/R6/R8/recent require:

- PF non-degrading 4/4;
- mean-R non-degrading 4/4;
- observed DD non-degrading 4/4;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- half-year mean/DD non-degrading;
- density >=75% in every fold.

Owner direction:

- OOS/era PF >=1.50;
- combined/recent PF >=1.70;
- expectancy >=+0.15R;
- observed DD <=6R hard gate;
- MC positive >=90%;
- MC p95 DD <=15R.

## Governance

No sizing, dynamic sizing, leverage, compounding, portfolio allocation,
capital weighting, fold identity, date lookup or outcome oracle may influence
the admission decision.

Fresh holdout remains sealed. A development survivor is not promotion evidence
and does not authorize candidate freeze or certification.
