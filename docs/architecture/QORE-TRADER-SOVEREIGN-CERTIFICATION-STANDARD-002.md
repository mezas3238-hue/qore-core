# QORE — Sovereign Trader Certification Standard 002

**Owner / CEO:** Sergio Meza  
**Status:** CANONICAL / UNIVERSAL / NON-NEGOTIABLE  
**Scope:** VT-01 through VT-31  
**Effective:** 2026-10-06

This standard propagates the current Owner certification law to every Trader. It supersedes any older Trader-wall wording that conflicts with it. Instrument- or methodology-specific certification contracts may strengthen these gates, but may not weaken them without a later explicit Owner directive.

## 1. Certification identity

A Trader certifies from its own market edge:

`ENTRY EDGE + EXIT EDGE + WINNER PRESERVATION`

The certification harness uses neutral/equal trade weighting. Capital engineering may not obtain, improve, rescue, or manufacture certification.

> **R IS NOT FORBIDDEN. SIZING TO OBTAIN CERTIFICATION IS FORBIDDEN.**

## 2. Hard drawdown gate

`OBSERVED_MAX_DRAWDOWN_R <= 6R`

- observed DD <= 6R: drawdown gate PASS;
- observed DD > 6R: certification DD gate FAIL;
- 15R remains only a hard research/safety rejection ceiling and is not a certification pass threshold.

The former 10R certification target is superseded.

## 3. Forbidden certification aids

A Trader may not use any of the following to reach a certification gate:

- position sizing or dynamic sizing;
- volume reduction to hide a wide/expensive stop;
- volume increase to recover losses;
- leverage;
- compounding;
- portfolio allocation;
- risk budgeting;
- capital weighting;
- route-dependent capital scaling;
- CIBO capital rescue;
- any other capital rule that changes exposure to improve PF, DD, expectancy, payoff, survival, Monte Carlo, Sharpe, Sortino, or the scorecard.

Provider minimums, maximums, lot steps and rounding belong to the provider adapter and may not change the Trader's market thesis.

## 4. R is permitted Trader logic

R may be used when it is part of causally validated Trader logic, including:

- entry/invalidation geometry;
- stop movement;
- breakeven;
- trailing;
- partial exits;
- fixed/adaptive targets;
- target extension;
- MFE/MAE logic;
- profit protection;
- cognition deciding whether an R rule applies.

The Trader must repair the trade, not hide a bad trade with smaller size.

## 5. Maximum-intelligence gate

A Trader may not certify with a reduced, sliced, partial, or convenience version of its intelligence.

Every causally available and applicable intelligence domain must be consulted before EXECUTE, WAIT, ABSTAIN, HOLD, TRAIL, EXTEND, EXIT, or REARM, including where applicable:

- strategy identity;
- higher/multi-timeframe context;
- structure;
- liquidity;
- regime, volatility and range;
- timing, freshness and aging;
- entry intelligence;
- journey/position intelligence;
- target/exit intelligence;
- persistent governed memory;
- cross-market context;
- post-entry full reassessment.

Each candidate must emit an intelligence-completeness manifest with only these states:

- `CONSULTED`
- `NOT_APPLICABLE`
- `UNAVAILABLE`
- `UNWIRED`

For freeze/certification, all applicable domains must be `CONSULTED`. `UNWIRED`, silent omission, or intentional bypass of an available applicable domain is a hard blocker.

## 6. Current Owner target gates

The frozen candidate must satisfy:

- OOS PF each era >= 1.50;
- combined PF >= 1.70, preferred >= 2.00;
- expectancy > 0R/trade, target >= +0.15R/trade;
- observed max DD <= 6R;
- Sharpe >= 1.50, preferred >= 2.00;
- Sortino >= 2.00;
- payoff >= 1.20, preferred >= 1.50;
- Monte Carlo positive-terminal >= 90%, preferred >= 95%;
- Monte Carlo p95 max DD <= 15R, preferred <= 10–12R;
- severe-cost PF > 1.0;
- winner-count preservation >= 80%, preferred >= 90%;
- winner-R preservation >= 90%, preferred >= 95%;
- stable positive years / eras / folds.

No sizing or other capital engineering may be used to reach any of these gates.

## 7. Freeze and fresh holdout law

Before opening the fresh holdout, freeze:

- exact candidate ID;
- source SHA;
- configuration;
- methodology/version fingerprints;
- memory fingerprints;
- reasoning fingerprint;
- position-management contract;
- target contract;
- no-sizing manifest;
- maximum-intelligence manifest;
- evidence exclusions;
- holdout boundary.

Then:

1. open the fresh holdout once;
2. do not retune;
3. run edge-only certification;
4. if a gate fails, the candidate is not certified;
5. the consumed holdout may not be reused as fresh evidence.

A green workflow is not a certification.

## 8. Certification is not execution authority

`TRADER_CERTIFIED != LIVE_AUTHORIZED`

Certification alone grants no LIVE, real-capital, production, merge, or order-submission authority.

## 9. Universal wall law

Every Trader wall for VT-01..VT-31 must display this standard. Any older wall text that says 10R is a certification target, permits sizing/capital rescue, or permits partial intelligence is superseded by this document.
