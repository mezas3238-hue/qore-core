# ICT Turtle Soup R2 — All-Session Multi-Asset Freeze

Status: PRE-ECONOMIC / NO P&L OPENED
Identity: `ICT_TURTLE_SOUP_R2_ALL_SESSION_MULTI_ASSET`
Parent methodology family: ICT Turtle Soup multi-asset
Issue: #574

## Research question

Can the ICT-style Turtle Soup causal sequence retain positive, robust expectancy when eligibility is event-driven rather than restricted to a fixed kill-zone clock, across indices, Forex majors, Forex crosses/minors, and metals?

This is a QORE research hypothesis. Public secondary material often teaches Turtle Soup primarily in high-liquidity sessions (especially New York AM), so R2 does **not** claim that ICT guarantees equal edge at every hour.

## Immutable causal core

A trade can be considered only when all of the following occur in causal order:

1. A qualified liquidity pool exists before the event.
2. Price sweeps/purges that pool.
3. Price reclaims/rejects the swept level.
4. A CISD/change-in-delivery confirmation completes after the sweep.
5. Entry occurs only after completed confirmation; no same-bar look-ahead.
6. Structural invalidation is placed beyond the adverse sweep extreme.
7. The target is a qualified opposing liquidity pool that was already known before entry.

`NO_POOL | NO_SWEEP | NO_RECLAIM | NO_CISD | NO_CAUSAL_ENTRY | NO_OPPOSING_TARGET => ABSTAIN`.

Time-of-day alone is neither an inclusion nor exclusion condition in R2.

## Initial objective liquidity-pool families

To avoid discretionary hindsight, R2 starts only with deterministic external/time-based pools:

- previous New-York trading-day high/low;
- previous completed week high/low;
- completed Asia session high/low;
- completed London session high/low;
- completed New-York AM high/low for later same-day events;
- completed New-York PM high/low for subsequent events.

Equal-high/equal-low clustering, discretionary swing labeling, FVG, breaker, order block, NWOG and other PD-array families are excluded from the initial R2 economic run. Adding any of them requires a new preregistered identity or additive pre-result subcandidate before economics.

## Asset universe

### Indices
- NAS100
- SP500
- US30

### Forex majors
- EURUSD
- GBPUSD
- USDJPY
- USDCHF
- USDCAD
- AUDUSD
- NZDUSD

### Forex crosses/minors
- EURGBP
- EURJPY
- EURCHF
- EURCAD
- EURAUD
- EURNZD
- GBPJPY
- GBPCHF
- GBPCAD
- GBPAUD
- GBPNZD
- AUDJPY
- AUDCAD
- AUDCHF
- AUDNZD
- CADJPY
- CADCHF
- CHFJPY
- NZDJPY
- NZDCAD
- NZDCHF

### Metals
- XAUUSD
- XAGUSD

Provider-unavailable symbols are recorded as `DATA_UNAVAILABLE`; they are not silently removed after economic results are known.

## Timeframe and evidence

- decision/replay timeframe: native M5 where provider-native evidence exists;
- timestamps: timezone-aware and normalized to UTC, with session construction performed by explicit timezone rules;
- no fabricated bars across market closures;
- no future-defined liquidity pool;
- same-M5 unresolved stop/target ordering fails conservatively to STOP unless finer causal evidence is explicitly available and frozen before economics.

## CISD formalization

R2 inherits the R1 deterministic CISD family: after the sweep/reclaim, identify the frozen opposing candle series causally visible at the event and require a body close through the series threshold. Entry occurs at the next causal M5 open, not at the confirming close.

## Structural risk and target

- stop: one native minimum-price increment beyond the adverse sweep extreme;
- target: nearest valid opposing qualified liquidity pool known before entry that produces positive reward;
- minimum projected geometry: 1.5R;
- no trailing, break-even, partials, pyramiding or re-entry in R2 initial run.

## Clock governance

R2 has **no fixed kill-zone filter**. A signal at any clock time is admissible only if its liquidity reference was already completed and all causal states above are satisfied.

For diagnostics, results must still be reported by session/hour bucket. Those buckets are diagnostics only and cannot become filters after results without a new preregistered identity.

## Robustness requirements before any promotion

Each cohort (indices, FX majors, FX minors/crosses, metals) must separately report and pass preregistered gates for:

- forward closed-trade sample sufficiency;
- positive mean R and PF > 1 after primary friction;
- stress robustness;
- temporal fold stability;
- LONG/SHORT stability;
- symbol-level and leave-one-symbol-out robustness;
- right-tail concentration;
- hour/session diagnostics without retrospective filtering;
- data-integrity and causality invariants.

A combined multi-asset claim is forbidden if one failing cohort is hidden by another profitable cohort.

## Governance

R1 `ICT_TURTLE_SOUP_R1_CISD_SESSION` remains an immutable session-bound research slice. R2 is a new identity, not a rewrite.

No Monte Carlo, Risk, CIBO, prop-firm qualification, canonical trader assignment, DEMO eligibility, LIVE authority, Production authority or real-capital authority is granted by this freeze.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
