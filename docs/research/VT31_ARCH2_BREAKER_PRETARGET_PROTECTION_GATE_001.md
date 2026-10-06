# VT31 NAS100 — Breaker Pretarget Structural Protection Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED CONSUMED-EVIDENCE FRONTIER  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Purpose

The strongest current A+B development survivor has crossed recent PF 1.50 but
still violates the sovereign observed-DD gate:

- recent PF: approximately 1.5537;
- recent observed DD: approximately 10.57R;
- required observed DD: <=6R.

The next experiment may not use sizing. It therefore tests whether repeated
full-stop Breaker failures can be reduced by causal market-native protection.

## Fixed components

- admission: `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
- H3 full-cognition management;
- W5 soft-DOL1;
- full-cognition DOL2;
- post-acceptance PS2;
- same entry;
- same initial stop;
- same target logic;
- same terminal trade identity.

## Only degree of freedom

For Breaker entries before DOL1 acceptance:

- CONTROL: no additional protection;
- BREAKER_PS1: first confirmed improving M1 protective swing;
- BREAKER_PS2: two confirmed improving M1 protective swings.

Any stop change:

- uses only closed causal M1;
- can only improve the stop;
- becomes effective on the next M1;
- may never widen risk.

## Adjudication

A useful survivor must preserve or improve PF / mean / observed DD across all
four consumed folds and preserve at least 80% winner count / 90% winner-R.

The sovereign certification target remains observed DD <=6R.

MC p95 <=15R is tracked separately as Monte Carlo robustness. It is not the
observed-DD certification threshold.

No fresh holdout, candidate freeze, sizing, leverage, compounding, capital
weighting, LIVE, real capital or production authority is granted.
