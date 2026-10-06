# VT31 NAS100 — Adverse Journey Cognitive Exit Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / PURE-EDGE CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Problem

The strongest current A+B stack remains near:

- recent PF: 1.5537;
- recent mean: +0.449R/trade;
- recent observed DD: 10.57R;
- recent MC positive: 81.54%.

The sovereign observed-DD certification gate is <=6R.

Mechanical early exits and universal/selective Breaker trailing have been
rejected. They either fail to reduce DD enough or destroy expectancy/winner-R.

## New causal information

VT31 now observes `current_open_r` from:

- frozen entry;
- frozen initial structural risk;
- side;
- latest fully closed M1 price.

It uses no volume, money, equity, sizing, leverage, compounding or portfolio
state.

The already-predeclared material-adverse band is:

`current_open_r <= -0.50R`.

## Experiment

Fixed candidate stack:

- admission `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
- H3;
- W5 soft-DOL1;
- full-cognition DOL2;
- post-acceptance PS2.

Variants:

1. `COG_EXIT_CAUTION`
   - material adverse;
   - full cognition maximum-ready;
   - management context CAUTIOUS.

2. `COG_EXIT_CAUTION_WEAK_PATH`
   - all of the above;
   - plus existing weak-path definition
     (efficiency <=0.30 or overlap >=0.75).

3. `COG_EXIT_NONSUPPORTIVE`
   - material adverse;
   - full cognition maximum-ready;
   - context MIXED or CAUTIOUS.

## Execution causality

The decision is made only after a fully closed M1.

If EXIT is authorized, it executes at the **next M1 open**.

The same M1 close cannot be used as an executable exit price. This removes
same-bar hindsight.

DOL1 touch keeps ownership of target logic; this pretarget cognitive-exit
frontier cannot override a bar that already touched DOL1.

## Gates

A useful survivor must:

- PF non-degrade 4/4;
- mean-R non-degrade 4/4;
- observed DD non-degrade 4/4;
- preserve >=80% winner count;
- preserve >=90% winner-R;
- avoid half-year mean/DD degradation;
- improve Monte Carlo directionally.

Certification still requires observed DD <=6R. Passing only development gates
is not certification.

Fresh holdout remains sealed.

No sizing, dynamic sizing, leverage, compounding, capital weighting, LIVE, real
capital or production authority is introduced.
