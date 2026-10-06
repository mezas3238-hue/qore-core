# VT31 NAS100 — FVG Fresh/Fast Admission Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Fixed base

The fixed research base is the current 4/4 development survivor:

`ABSTAIN_BREAKER_SHORT_ROTATION_COMPRESSED_EXCEPT_BULLISH_RECOVERY_SEQUENCE`

on top of:

`VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT`.

No position-management logic changes in this experiment.

## Discovery evidence

Observation-only multivariate attribution on the fixed survivor found the causal
pre-entry class:

`FVG + SHORT + compressed reference volatility + fresh reclaim (<8m) + fast confirmation (<=5m)`.

Across consumed development folds:

- R5: 5 trades / 5 losses / 0 winners;
- R6: 2 trades / 2 losses / 0 winners;
- R8: 2 trades / 2 losses / 0 winners;
- recent: 1 trade / 1 loss / 0 winners.

Total:

**10 trades / 10 losses / 0 winners.**

The result labels are consumed discovery evidence only and have zero runtime
authority.

## Why the state is causal

Every input exists before entry:

- selected entry family;
- side;
- frozen 09:00 reference-volatility state;
- reference-reclaim age;
- confirmation latency.

The reclaim bucket <8m and fast-confirmation bucket <=5m already existed in
VT31 forensic/state vocabulary before this hypothesis. No new numeric threshold
is introduced here.

The rule does not use:

- fold;
- date identity;
- future outcome;
- M15 as an isolated directional veto;
- money, volume, sizing, leverage or capital state.

## Predeclared variants

1. `RECOVERY_BASE_CONTROL`
   - keep the current 4/4 Breaker-recovery survivor unchanged.

2. `ABSTAIN_FVG_SHORT_COMPRESSED_FRESH_FAST`
   - same fixed stack;
   - additionally abstain only when all are true:
     - entry family = fair-value-gap;
     - side = SHORT;
     - reference volatility = compressed;
     - reference reclaim age <8 minutes;
     - confirmation latency <=5 minutes.

## Frozen development gates

Across R5/R6/R8/recent:

- PF non-degrading;
- mean-R non-degrading;
- observed DD non-degrading;
- density >=75%;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- every half-year mean/DD non-degrading.

Owner direction:

- era PF >=1.50;
- recent/combined PF >=1.70;
- expectancy >=+0.15R;
- observed DD <=6R hard gate;
- MC positive terminal >=90%;
- MC p95 DD <=15R.

Fresh holdout remains sealed. A development survivor cannot promote itself.

No sizing, dynamic sizing, leverage, compounding, portfolio allocation,
capital weighting, absolute volume, LIVE, real capital or production authority
is introduced.
