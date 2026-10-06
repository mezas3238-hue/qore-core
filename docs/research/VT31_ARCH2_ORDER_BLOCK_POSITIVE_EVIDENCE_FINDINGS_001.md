# VT31 NAS100 — Order Block Positive Evidence Findings 001

**Owner:** Sergio Meza  
**Status:** STRONGEST A+B CONSUMED-EVIDENCE DEVELOPMENT SURVIVOR / NOT FROZEN  
**Branch:** `agent/vt31-edge-position-cert-b-001`  
**Workflow:** `37451328063` — SUCCESS  
**Head tested:** `3025c989d99f76b9b2ba982b8865e761141c4672`

## Result

The positive-evidence Order Block frontier produced four cross-fold development
survivors. The strongest two variants are economically identical on all four
consumed folds:

- `A_EXPANDED_OB_REQUIRE_SHORT_AGE_11M`;
- `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`.

Both:

- PF non-degrading: 4/4;
- mean-R non-degrading: 4/4;
- DD non-degrading: 4/4;
- density >= 75%: 4/4;
- winner preservation: PASS 4/4;
- half-year temporal non-degradation: PASS;
- recent consumed PF >= 1.50: PASS;
- observed DD <= 6R: FAIL;
- MC positive terminal >= 90% recent: FAIL;
- MC p95 DD <= 15R recent: FAIL.

## Economics

### R5

- trades: 42
- density: 77.78%
- PF: 3.14737
- mean: +1.52531R
- DD: 9.45R
- MC positive terminal: 94.80%
- MC p95 DD: 22.53R
- winner preservation: 100% / 100%

### R6

- trades: 28
- density: 75.68%
- PF: 3.66964
- mean: +2.00700R
- DD: 7.49444R
- MC positive terminal: 96.24%
- MC p95 DD: 13.89444R
- winner preservation: 100% / 100%

### R8

- trades: 28
- density: 84.85%
- PF: 3.64462
- mean: +1.98347R
- DD: 8.40R
- MC positive terminal: 97.30%
- MC p95 DD: 13.94615R
- winner preservation: 100% / 100%

### Recent consumed

- trades: 39
- density: 81.25%
- PF: 1.55369
- mean: +0.44921R
- total: +17.51936R
- DD: 10.57140R
- max losing streak: 7
- MC positive terminal: 81.54%
- MC p95 DD: 19.69830R
- winner preservation: 100% / 100%

## Tie-break

The two leading variants produce the same current population. For continued
research, the preferred residual witness is:

`A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`

The tie-break is causal semantics, not outcome maximization:

- SHORT is an explicit directional requirement;
- reclaim age >=15m represents a matured liquidity sequence;
- it is more market-native than selecting a threshold solely from the age of
  the entry evidence object.

This remains development-only. The threshold was discovered on consumed
evidence and cannot be promoted from this result.

## Certification state

The recent PF gate is now crossed, but VT31 is not certification-ready.

The sovereign observed-DD gate is now <=6R. Current recent DD remains 10.57R.

Monte Carlo also remains below certification:

- positive terminal 81.54% < 90%;
- p95 DD 19.70R > 15R.

Therefore the next work is residual sequence / regime attribution on this
cleaner population, not additional capital engineering and not fresh holdout.

No sizing, leverage, compounding, capital weighting, LIVE, real capital,
candidate freeze or fresh holdout is authorized.
