# VT31 NAS100 — Integrated Research Comparator 006

**Owner / CEO:** Sergio Meza  
**Status:** FIXED INTEGRATED RESEARCH COMPARATOR / NOT CANDIDATE FREEZE  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Comparator ID

`VT31_AB_COMP006_CLEAN_BREAKER_CONFLICT_SURVIVOR`

## Fixed position stack

B-side position logic:

`VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT`

including:

- H3 full-cognition post-1R management;
- W5 soft-DOL1;
- full-cognition DOL2;
- post-acceptance PS2;
- causal current_open_r;
- maximum-cognition pre-DOL1 exits already validated in Comparator 003.

## Fixed admission stack

1. `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
2. abstain Breaker + SHORT + prior-day rotation + compressed reference,
   except the bullish recovery sequence;
3. abstain FVG + SHORT + compressed reference + FRESH_LT8M reclaim +
   FAST_LE5M confirmation;
4. abstain Breaker + SHORT + prior-day bearish + compressed reference +
   H1 bullish.

## Cross-fold development result

Relative to Comparator 005, the final Breaker conflict exclusion:

- PF non-degrade: 4/4;
- mean-R non-degrade: 4/4;
- observed DD non-degrade: 4/4;
- density >=75%: 4/4;
- winner count preservation: PASS;
- winner-R preservation: PASS;
- half-year mean/DD non-degrade: PASS 4/4.

### R5

- PF: 4.64358;
- mean: +2.10502R;
- observed DD: 5.25R;
- MC positive: 98.34%;
- MC p95 DD: 14.79R.

### R6

- PF: 4.80485;
- mean: +2.54872R;
- observed DD: 5.39444R;
- MC positive: 98.43%;
- MC p95 DD: 8.54R.

### R8

- PF: 5.53228;
- mean: +2.61260R;
- observed DD: 6.00502R;
- MC positive: 99.13%;
- MC p95 DD: 9.42R.

### Recent consumed

- PF: 2.01711;
- mean: +0.70825R;
- observed DD: 7.23975R;
- MC positive: 90.76%;
- MC p95 DD: 14.70R;
- winner count preservation: 100%;
- winner-R preservation: 100%.

## Interpretation

Comparator 006 is the cleanest current integrated development base.

It passes current recent PF, expectancy and Monte Carlo direction, but is still
NOT CERTIFIED because:

- R8 observed DD is 6.005R, slightly above the sovereign 6R gate;
- recent observed DD is 7.240R, above the sovereign 6R gate.

No historical or recent gate may be relaxed to promote it.

## Governance

Comparator 006 is consumed-evidence research only.

It is not:

- candidate freeze;
- fresh-holdout opening;
- certification;
- LIVE authorization;
- real-capital authorization;
- production policy.

No sizing, dynamic sizing, leverage, compounding, portfolio allocation, capital
weighting or absolute-volume authority is used.
