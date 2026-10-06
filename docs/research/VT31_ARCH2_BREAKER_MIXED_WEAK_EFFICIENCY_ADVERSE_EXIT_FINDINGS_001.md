# VT31 NAS100 — Breaker Mixed Weak-Efficiency Adverse Exit Findings 001

**Status:** DEVELOPMENT SURVIVOR / SIX-R ALL-FOLD SURVIVOR  
**Workflow:** `37512877757` — SUCCESS  
**Evaluated head:** `0cc727cf992abc7581af41ceee6d1d9043266275`  
**Base comparator:** `VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

## Tested policy

Preserve all Comparator-007 logic and additionally authorize a causal
next-M1-open exit for a still-pre-DOL1 Breaker only when:

- maximum cognition verified;
- current_open_r <= -0.50R;
- management_context == MIXED;
- recent_path_efficiency is available and <=0.30.

Both numeric thresholds were pre-existing before this frontier.

## Aggregate adjudication

- actuated folds: 2;
- PF non-degrade: 4/4;
- mean-R non-degrade: 4/4;
- DD non-degrade: 4/4;
- density floor: 4/4;
- winner preservation all folds: PASS;
- half-year temporal non-degrade: PASS;
- era PF >=1.50: PASS;
- all consumed folds observed DD <=6R: **PASS**;
- development survivor: **YES**;
- six-R all-fold survivor: **YES**.

## Fold results

### R5

Unchanged economically:

- sample 35;
- PF 4.6435815036;
- mean +2.1050230617R;
- DD 5.25R;
- winner preservation 100% / 100%.

### R6

Improved:

- sample 23;
- PF 5.2509388174 vs 5.1405889146 baseline;
- mean +2.7189147347R vs +2.7051847576R;
- DD 5.3944444444R unchanged;
- winner preservation 100% / 100%.

One losing trade changed:

- `2018-09-21T14:05:00Z`;
- baseline -1.0R;
- candidate -0.6842105263R;
- delta +0.3157894737R.

### R8

Unchanged economically:

- sample 21;
- PF 6.9515788832;
- mean +3.1203366255R;
- DD 5.0661261261R;
- winner preservation 100% / 100%.

### Recent consumed

Improved:

- sample 33;
- PF 2.2879394805 vs 2.2073021627;
- mean +0.8385930798R vs +0.8148066039R;
- total +27.6735716322R vs +26.8886179285R;
- observed DD **5.8084294089R** vs 6.5933831126R;
- winner count preservation 100%;
- winner-R preservation 100%;
- MC positive 94.61%;
- MC p95 DD 11.2568861036R.

Two losses changed:

1. `2024-01-29T15:26:00Z`
   - baseline -1R;
   - candidate -0.4962962963R;
   - delta +0.5037037037R.

2. `2024-02-08T15:07:00Z`
   - baseline -1R;
   - candidate -0.71875R;
   - delta +0.28125R.

Combined saved raw R in the exact recent DD episode:

`+0.7849537037R`.

That is enough to move the recent observed DD below the sovereign hard gate.

## Why the previous broad admission idea remains rejected

This survivor does not revive the rejected
`Breaker SHORT + prior-day bullish + cash-open bullish + H1 bullish`
admission veto.

That broad rule removed historical +21.50R, +6.808R and +4.646R winners.

The new survivor acts post-entry only when actual causal journey deterioration
is observed and preserves those winners.

## Current sovereign DD state

- R5: 5.25R PASS;
- R6: 5.394444R PASS;
- R8: 5.066126R PASS;
- recent: **5.808429R PASS**.

This is the first current-stack all-fold survivor below 6R.

## Governance

This is still development evidence.

It is not:

- final candidate freeze;
- fresh-holdout PASS;
- certification;
- LIVE authorization;
- real-capital authorization.

The next required phase is final pre-holdout robustness plus exact
research/runtime parity.
