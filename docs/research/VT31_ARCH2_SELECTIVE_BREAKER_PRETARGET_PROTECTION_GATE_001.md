# VT31 NAS100 — Selective Breaker Pretarget Protection Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Why this frontier exists

Global Breaker PS1/PS2 protection is rejected because it damages expectancy
and winner-R. The residual recent failure is not "all Breakers".

After the strongest admission survivor, a specific regime-flip class remains:

`Breaker + M15 mixed + confirmation latency 3-5m`

On recent consumed evidence it is 7/7 stressed losses, while the same class is
historically profitable in R5/R6/R8.

A hard veto would therefore destroy historical edge. The correct question is
whether market-native M1 protection can distinguish the failing paths from the
historical winners after entry.

## Fixed stack

- admission: `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
- H3;
- W5 soft-DOL1;
- full-cognition DOL2;
- post-acceptance PS2;
- same entry;
- same initial stop;
- same target logic.

## Predeclared variants

- control;
- Breaker + M15 mixed -> PS1;
- Breaker + M15 mixed -> PS2;
- Breaker + M15 mixed + confirmation 3-5m -> PS1;
- Breaker + M15 mixed + confirmation 3-5m -> PS2.

Protection uses closed M1 only, is effective from the next M1, and can only
improve the stop.

## Governance

This is consumed-evidence development. No survivor can open fresh holdout or
authorize candidate freeze by itself.

Certification remains pure-edge with observed DD <=6R. Sizing, leverage,
compounding, capital weighting and CIBO capital rescue are forbidden.
