# VT31 NAS100 — Remaining Order Block Discrimination Gate 001

**Owner:** Sergio Meza  
**Status:** OBSERVATION-ONLY / CONSUMED EVIDENCE  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Purpose

The narrow Order Block age filter preserves density and winners, while the
full family veto improves recent arithmetic but removes useful historical
trades and fails the predeclared density floor in R6.

This diagnostic therefore records the Order Block trades that remain after:

`ORDER_BLOCK age 0-2m OR expanded reference volatility -> ABSTAIN`

under the fixed B-side comparator.

The purpose is to identify causal evidence that distinguishes historical Order
Block winners from recent Order Block losers before testing any stronger
admission rule.

## Recorded causal fields

- decision minute;
- prior day;
- H4 / H1 / M15;
- premarket / cash-open state;
- prior-day location;
- reference-volatility state;
- reference-width ratio;
- current-path ratio;
- confirmation latency;
- entry-evidence age;
- reclaim age;
- risk/reference geometry;
- destination distance;
- raid depth;
- recent path efficiency;
- recent overlap.

## Authority

Observation only. No outcome-aware rule is created here.

No sizing, leverage, compounding, capital weighting, fold identity, future
outcome, fresh holdout, candidate freeze, LIVE, real capital or production is
authorized.
