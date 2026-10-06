# VT31 NAS100 — Predeclared Non-Breaker Reloss Momentum Experiment 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED EVIDENCE ONLY / NO POLICY PROMOTION  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Sovereign rule

This experiment obeys:

`ENTRY EDGE + EXIT EDGE + WINNER PRESERVATION`

Runtime inputs may not use:

- R multiple;
- MFE/MAE thresholds;
- sizing;
- volume;
- leverage;
- compounding;
- capital weighting;
- portfolio allocation.

R is evaluation-only after each replayed trade.

## Why this experiment is being declared

The already-consumed `RELOSS_MOMENTUM_SWING_ONCE` study showed that every
observed harmful changed trade belonged to the **Breaker** entry family.

In the same burned evidence, changed Fair Value Gap and Order Block trades were
non-harmful in every observed fold. This is a post-hoc clue, not validation.

Therefore the next experiment is frozen **before execution** as:

`NONBREAKER_RELOSS_MOMENTUM_SWING_ONCE`

## Runtime rule

The original trade admission, entry price, initial structural invalidation and
primary structural target are unchanged.

Post-entry protection may arm exactly once only when all conditions are true:

1. entry family is **not Breaker**;
2. a confirmed M1 protective swing exists;
3. the candidate swing improves the current stop and never widens it;
4. recent closed-price momentum has stopped progressing in the trade direction;
5. current closed price has re-lost the source confirmation structure;
6. the observation is based only on closed M1 bars;
7. the improved stop becomes effective from the next M1 bar.

If the entry family is Breaker, this experiment uses the sovereign structural
baseline unchanged.

No fixed R threshold is present.

## Frozen variants

- V0: `BASELINE`
- V1: `NONBREAKER_RELOSS_MOMENTUM_SWING_ONCE`

## Required folds

- R5
- R6
- R8
- consumed recent 2Y

No fresh holdout.

## Gates versus baseline, independently in every fold

Required 4/4:

- PF non-degrading;
- mean R non-degrading;
- total R non-degrading;
- max DD non-degrading;
- winner count preservation >= 80%, preferred 90%;
- winner-R preservation >= 90%, preferred 95%;
- no baseline winner converted to a loser;
- no half-year total-R degradation;
- no half-year PF degradation where PF is defined;
- same terminal trade population;
- no admission change.

Additional mechanism requirement:

- every changed trade must have `entry_family != breaker`;
- no Breaker trade outcome may change.

## Adjudication

Possible results:

- `SUPPORTED_CONSUMED_RESEARCH_WITNESS`
- `BREAKER_EXCLUSION_INSUFFICIENT`
- `TEMPORAL_INSTABILITY`
- `WINNER_DESTRUCTION`
- `NO_EFFECT`
- `NOT_SUPPORTED`

Even `SUPPORTED_CONSUMED_RESEARCH_WITNESS` does not freeze a candidate and
does not open a holdout.

## Governance

- consumed evidence only;
- no sizing;
- no volume-dependent logic;
- no leverage;
- no compound;
- no capital weighting;
- no merge;
- no LIVE;
- no real capital;
- no production authorization.
