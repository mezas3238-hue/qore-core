# VT31 NAS100 — Integrated Research Comparator 007

**Owner / CEO:** Sergio Meza  
**Status:** FIXED DEVELOPMENT RESEARCH COMPARATOR / NOT CANDIDATE FREEZE  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Comparator ID

`VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

## Provenance

This comparator freezes the strongest development survivor from:

- workflow: `37508820071`;
- workflow name: `QORE VT31 Rapid Breaker Conflict Admission Frontier V1`;
- evaluated research head: `e4dda550814d21894a6a79e995e480530cc59912`;
- source variant: `COMP006_PLUS_RAPID_BREAKER_UNION`;
- source comparator: `VT31_AB_COMP006_CLEAN_BREAKER_CONFLICT_SURVIVOR`.

This document freezes a **research comparator only**. It does not freeze a certification candidate and does not open fresh holdout evidence.

## Fixed position stack

B-side position logic remains:

`VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT`

including:

- H3 full-cognition post-1R management;
- W5 soft-DOL1;
- cognition-selected DOL2;
- post-acceptance PS2;
- causal `current_open_r`;
- validated maximum-cognition pre-DOL1 exits.

## Fixed admission stack

Comparator 006 admission remains intact:

1. `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
2. abstain Breaker + SHORT + prior-day rotation + compressed reference, except bullish recovery;
3. abstain FVG + SHORT + compressed reference + `FRESH_LT8M` reclaim + `FAST_LE5M` confirmation;
4. abstain Breaker + SHORT + prior-day bearish + compressed reference + H1 bullish.

Comparator 007 adds the predeclared rapid Breaker conflict union:

### Conflict A

Abstain only when all are true at entry time:

- Breaker;
- SHORT;
- prior-day bullish;
- reference volatility normal;
- H4 bullish;
- H1 mixed;
- M15 mixed;
- premarket bearish;
- cash open bullish.

### Conflict B

Abstain only when all are true at entry time:

- Breaker;
- SHORT;
- reference volatility normal;
- reclaim state `FRESH_LT8M`;
- confirmation latency `MID_6_10M`.

The union abstains when Conflict A **or** Conflict B is present.

No new numeric threshold was introduced by this union; the reclaim and confirmation buckets already existed before this frontier.

## Cross-fold development result

The union is a development survivor:

- PF non-degrade: 4/4;
- mean-R non-degrade: 4/4;
- observed DD non-degrade: 4/4;
- density >=75%: 4/4;
- winner preservation: PASS 4/4;
- half-year mean/DD non-degrade: PASS.

### R5

- sample: 35;
- PF: 4.643581503553654;
- mean: +2.105023061660241R;
- observed DD: 5.25R;
- MC positive: 98.34%;
- MC p95 DD: 14.794513919586287R;
- winner count preservation: 100%;
- winner-R preservation: 100%.

### R6

- sample: 23;
- PF: 5.140588914624902;
- mean: +2.705184757554936R;
- observed DD: 5.394444444444444R;
- MC positive: 98.97%;
- MC p95 DD: 7.494444444444444R;
- winner count preservation: 100%;
- winner-R preservation: 100%.

### R8

- sample: 21;
- PF: 6.951578883233517;
- mean: +3.120336625473599R;
- observed DD: 5.066126126126126R;
- MC positive: 98.60%;
- MC p95 DD: 7.949459459459459R;
- winner count preservation: 100%;
- winner-R preservation: 100%.

### Recent consumed

- sample: 33;
- wins: 8;
- losses: 25;
- PF: 2.207302162656619;
- mean: +0.814806603895185R;
- total: +26.888617928541105R;
- observed DD: 6.593383112613882R;
- max losing streak: 5;
- MC positive: 93.70%;
- MC p95 DD: 12.146999053159512R;
- winner count preservation: 100%;
- winner-R preservation: 100%.

## Sovereign 6R status

- R5: PASS;
- R6: PASS;
- R8: PASS;
- recent consumed: **FAIL** at 6.593383112613882R.

Residual excess over the sovereign hard gate:

`0.593383112613882R`.

Therefore:

`six_r_all_fold_survivor = false`.

## Governance

Comparator 007 is consumed-evidence development research only.

It is not:

- candidate freeze;
- certification;
- fresh-holdout opening;
- LIVE authorization;
- real-capital authorization;
- production policy.

Forbidden for certification:

- position sizing;
- dynamic sizing;
- leverage;
- compounding;
- portfolio weighting;
- capital allocation rescue;
- CIBO rescue;
- outcome-aware filtering;
- fold/date-specific filtering.

The next degree of freedom is **not** an immediate new filter. The next step is an observation-only reconstruction of the exact recent peak-to-trough drawdown path and matched winners before any new hypothesis is allowed.
