# ICT TURTLE SOUP BEHAVIOR LAB V1 — RESEARCH FREEZE

Identity: `ICT_TS_BEHAVIOR_LAB_V1`
Issue: #590
Implementation: #591

## Mission
Study Turtle Soup as a market behavior, not as a finished entry system.
The lab records liquidity raids first and only then measures rejection,
confirmation and subsequent price delivery.

It must not optimize a trader, rank markets for promotion, or authorize capital.

## Source-confirmed conceptual core
- Official ICT Rejection Block material: violations/rejections of old highs/lows
  are Turtle Soup / false-breakout liquidity events.
- Official ICT examples include NQ outside a London/NY-AM-only restriction.
- TTrades Relevant Swings: not every high/low is equally meaningful; relevance
  is contextual and separation matters.
- TTrades Ideal Formation: a C2/C3 closure and creation of a protected swing are
  distinct information layers.
- TTrades targets: untouched HTF highs/lows are logical liquidity objectives.

## V1 observational ontology
Every event is decomposed into independent layers:
1. reference liquidity;
2. first mechanical violation (raid);
3. reclaim / acceptance behavior;
4. CISD and protected-swing confirmation;
5. post-raid imbalance/FVG observation;
6. opposing-reference travel;
7. fixed-horizon MFE/MAE.

V1 observes D1, H4 and H1 source candles.
Reference families are `prior-candle` and `swing-3`.
`swing-3` is a QORE observational formalization, not a claim that ICT/TTrades
canonically require a three-candle pivot for every relevant swing.

Numeric source ambiguities are deliberately continuous variables:
- sweep depth;
- peer/equal-liquidity distance;
- wick/body geometry;
- range-normalized depth;
- reclaim latency;
- CISD latency;
- protected-swing distance.
No data-derived cutoff is embedded in V1.

## Time/session governance
Asia, London and New York are eligible observations.
Session bucket and NY minute-of-day are diagnostic coordinates only.
The lab contains no session/hour validity gate.

## Statistical contract
- group by asset class, symbol, timeframe, reference, side, session, year, quarter;
- block-bootstrap reclaim confidence intervals by source day;
- quintile response tables for continuous sweep depth;
- reclaim time-to-event table;
- leave-one-symbol-out and leave-one-quarter-out stability;
- no P&L-based winner selection.

## Evidence governance
Initial pilot: already-consumed R5 FX 2016-2018 evidence only.
Later cross-market runs may use consumed/diagnostic evidence for FX, indices and metals.
Any newly acquired research interval is consumed immediately and cannot later be fresh OOS.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
