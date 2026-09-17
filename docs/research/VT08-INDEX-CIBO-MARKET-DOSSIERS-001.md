# VT08 Index — CIBO Market Dossiers + Temporal Stability

## Scope

This research layer consumes only two already-validated artifact families:

1. Complete Ledgers V1 over the five consumed windows.
2. Semantic V2 over the same five consumed windows.

It produces descriptive dossiers for NAS100, SP500 and US30 plus one cross-index
dossier. It does not freeze a specialist, select a trading rule, or open a holdout.

## Per-market dossier

Each market dossier includes:

- stressed primary-R economics already present in consumed evidence;
- stop rate and stop-to-later-2R rate;
- source-POI-arrival -> CISD -> continuation timing;
- A-I diagnostic candidate rates from Semantic V2;
- stability by consumed window, year, semester and quarter;
- slices by anchor, side, model, POI, weekday and prior-H4 range regime;
- POI/model/reaction-structure mixes;
- descriptive 24h destination bands;
- daily-path descriptor and range/efficiency summaries.

Temporal blocks are descriptive. No positive block, regime, weekday, anchor, side,
POI, or market is automatically admitted or excluded by this layer.

## Cross-index dossier

The cross-index dossier records:

- cohort count and three-market coverage;
- side-agreement frequency;
- leader counts for source-POI arrival, CISD confirmation and causal continuation;
- arrival -> CISD -> continuation leader-transition counts;
- cohorts with at least two simultaneous stopped markets;
- same-side share of those multi-market stop cohorts.

These measurements do not create a cross-index admission gate.

## Governance

- consumed evidence only;
- V7 unchanged;
- Semantic V2 unchanged;
- no automatic rule promotion;
- no specialist identity frozen by this layer;
- fresh 1Y holdout remains sealed;
- LIVE_AUTHORIZED = FALSE;
- REAL_CAPITAL_AUTHORIZED = FALSE;
- PRODUCTION_AUTHORIZED = FALSE.

A later specialist-freeze layer may use these dossiers only after explicit
stability/causality review and must create separate market identities before any
fresh holdout is opened.
