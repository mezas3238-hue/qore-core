# VT-08 INDEX V5 — PHASE B IDEAL FORMATION PREREGISTRATION 001

Status: PRE-ECONOMIC / CONSUMED-EVIDENCE ONLY

## Purpose

Falsify a source-bound repair of the V5 Phase-A failure without opening the sealed 2020–2022 holdout and without selecting predicates from outcomes.

## Frozen evidence and mechanics

- Consumed sample: the frozen 183-trade V4 feature census only.
- Fresh 2020–2022 holdout remains sealed during Phase B.
- V3 entry, stop, target, expiry, fill and management mechanics remain frozen.
- Primary stress friction: 0.05R/trade.
- Predictors must be available at `signal_at`; outcome columns are prohibited from predicates.

## Source-bound hypotheses

TTrades Ideal Formation states that the higher-timeframe C2/C3 closure is stronger when that closure simultaneously confirms the protected swing. The Fractal Model additionally requires higher-timeframe directional context and lower-timeframe continuation confirmation. For H4, M15 is the execution/confirmation timeframe.

### H1 — Ideal-formation simultaneity

Retain only rows where the selected protected swing is confirmed within the same H4 closure candle that establishes the C2/C3 closure. This is a structural timing requirement, not an outcome filter.

Operational definition on the frozen census: `0 <= cisd_latency_m15 <= 15`, because the census latency is measured in M15 bars from the H4 closure candle open. The selected protected swing must belong to the reconstructed closure-window swing set.

### H2 — C2 ideal formation

H1 plus `closure_family == c2`.

### H3 — C3 ideal formation

H1 plus `closure_family == c3`.

### H4 — Ideal formation with source-day directional agreement

H1 plus a causally resolved source-day continuation/reversal context whose direction agrees with trade side, using the already-preregistered V5 Phase-A context classifier. This hypothesis is secondary because Phase A falsified daily context as a standalone resolver.

## Explicitly forbidden

- No selection by `outcome_r`, MAE, MFE, exit reason, target replay, win/loss, market profitability or window profitability.
- No numerical wick-depth threshold invented from consumed outcomes.
- No target optimization.
- No market, side or anchor deletion because of observed economics.
- No opening of the 2020–2022 holdout before a candidate identity and fingerprint are frozen.

## Phase-B acceptance gate

A candidate may be frozen only if a preregistered source-bound hypothesis has positive stressed mean at 0.05R/trade in every consumed window (2022–23, 2023–24, 2024–26), remains directionally defensible across NAS100/SP500/US30 and LONG/SHORT with adequate support, and does not rely on post-hoc exclusions. Multiplicity and sparse strata must be reported explicitly.

If no preregistered hypothesis clears this gate, Phase B is falsified and the holdout remains sealed.

## Holdout protocol

Only after a Phase-B candidate passes the consumed-evidence gate:

1. freeze exact predicate, code SHA, methodology fingerprint and input digests;
2. make no economic/model changes;
3. open the sealed 2020–2022 tranche once;
4. run the identical frozen candidate;
5. adjudicate economic, stability and risk gates.

A failed holdout rejects the candidate. It must not be repaired using holdout outcomes.

No DEMO, LIVE, real-capital, prop-firm or production authority is granted by this document.