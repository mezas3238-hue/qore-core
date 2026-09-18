# ICT Turtle Soup R3 — Consumed Development Replay Result

Date: 2026-09-15
Candidate: `ICT_TURTLE_SOUP_R3_H4_C2_M15_CISD`
Parent research identity: `ICT_TURTLE_SOUP_R3_SOURCE_BOUND`

## Authoritative execution

Workflow: `QORE ICT Turtle Soup R3 Source Bound`
Run: `35038587031` — SUCCESS
HEAD: `9ddb92dfa9090b39fa43d7b7dff298f1d20d736c`
Artifact: `10424038795`
Artifact digest: `sha256:22f81c49f59b62ff7f2effcdfab41a2af9e282196396cfce64da05cf1b36f65e`
Report SHA-256: `62bcd9b71623da31d8e63b707757723ad2f7fc6ea3229aa85eb4805bc7858a42`
Trades SHA-256: `0c1fa264a36375ebce5818fb9135a7aae9c0ca54135ae1d797023aa76f0bfb25`

Evidence status: `CONSUMED_DEVELOPMENT_ONLY`.
The raw `[2020-07-01, 2022-07-01)` Forex evidence was already opened under VT-08/R2. This replay cannot independently validate or approve R3.

## Frozen mechanics actually tested

- no time/session inclusion or exclusion filter;
- Asia, London and New York all eligible if methodology completes;
- relevant H4 C1 high/low from the pre-frozen three-H4 context;
- H4 Candle-2 sweep + close back inside C1 range;
- M15 CISD within the same C2 using the opening price of the first candle of the contiguous opposing series;
- protected swing formed from the causal M15 series through CISD;
- C3 H4-open entry;
- stop exactly at protected swing, no offset;
- target at the opposite C1 extreme;
- no minimum projected-R gate;
- C3 lifecycle; STOP-first same-M5 ambiguity;
- gross / 0.05R primary / 0.10R stress reporting.

## Aggregate result

- trades: **1,843**
- primary winners: **911**
- primary losers: **932**
- primary flats: **0**
- primary win rate: **49.43%**
- gross winners: **972**
- gross losers: **868**
- gross flats: **3**
- gross win rate: **52.74%**
- gross total: **-0.613819607R**
- gross mean: **-0.000333055R/trade**
- gross PF: **~0.9991**
- primary total: **-92.763819607R**
- primary mean: **-0.050333055R/trade**
- primary PF: **0.868552127**
- stress total: **-184.913819607R**
- stress mean: **-0.100333055R/trade**
- stress PF: **0.754878122**
- max drawdown: **111.241730474R**
- longest losing streak: **10**

## Funnel

- H4 C2 cycles evaluated: **18,885**
- source C2 reversals: **3,682**
- no source C2 reversal: **15,178**
- ambiguous both sides: **25**
- no M15 CISD: **1,400**
- no causal opposing C1 target: **439**
- executed trades: **1,843**

## Exit census

- target: **636**
- time exit: **649**
- normal stop: **556**
- gap stop: **1**
- stop-first: **1**

Stop-family exits therefore account for **558 / 1,843 = 30.28%** of R3 trades.

## R2 -> R3 structural comparison

The source-bound reconstruction materially changed the population before economics:

- trades: `5,162 -> 1,843` (**64.30% reduction**);
- gross mean: `-0.101624R -> -0.000333R/trade`;
- gross PF: `~0.8457 -> ~0.9991`;
- gross win rate: `~29.45% -> ~52.74%`;
- structural stop-family share: `63.48% -> 30.28%`;
- longest losing streak: `23 -> 10`.

This is strong consumed-development evidence that the source-bound C2/CISD/protected-swing reconstruction removed a large amount of the failure mode present in R2. It is not independent validation and cannot establish causal profitability.

## Breadth

Primary net by symbol:

- AUDJPY: 258 trades, **-13.4052R**, PF 0.8715
- AUDUSD: 258, **-8.5582R**, PF 0.9147
- EURUSD: 260, **-4.1749R**, PF 0.9563
- GBPJPY: 283, **+7.4062R**, PF 1.0843
- GBPUSD: 282, **-21.4318R**, PF 0.8004
- USDCAD: 260, **-33.0614R**, PF 0.7019
- USDJPY: 242, **-19.5385R**, PF 0.8033

All seven leave-one-symbol-out totals remain negative. The positive GBPJPY result is diagnostic only and cannot authorize pair selection.

By side:

- LONG: 863 trades, **-13.4271R**, PF 0.9556
- SHORT: 980 trades, **-79.3368R**, PF 0.8033

The side difference is diagnostic only; no side deletion is authorized.

## Sessions are diagnostics, never gates

- Asia: 438 trades, **-37.7508R**, PF 0.7865
- London: 776 trades, **+3.8351R**, PF 1.0130
- New York: 460 trades, **-19.5305R**, PF 0.8484
- Other: 169 trades, **-39.3177R**, PF 0.6248

The positive London aggregate does **not** authorize a London-only filter. The candidate was explicitly frozen without a session gate, and the owner requirement remains methodology-first rather than clock-first.

## Temporal stability

- 2020 retained portion: **-34.0325R**, PF 0.8285
- 2021: **-7.4602R**, PF 0.9768
- 2022 retained portion: **-51.2711R**, PF 0.7243

Only 2021-Q2 is materially positive among the reported quarters. No quarter/date selection is authorized.

## Adjudication

`ICT_TURTLE_SOUP_R3_H4_C2_M15_CISD = REJECTED_FOR_ADVANCEMENT`.

Reason:

The source-bound reconstruction nearly eliminates the gross negative expectancy seen in R2, but it does **not** establish a positive economic edge. Gross PF is approximately 1.0 and the normalized primary friction produces PF 0.869 / -92.76R. Breadth is also insufficient: six of seven symbols are negative, both sides are negative after primary friction, all leave-one-symbol-out totals are negative, and temporal stability is weak.

The candidate must not be repaired in place after this result. Any next economic mechanic requires a new identity and a new pre-economic freeze.

## Source-directed next research questions

The result does not justify hour/pair/session filters. The next work must stay tied to ICT/TTrades source semantics and determine whether this candidate still under-specifies:

1. the exact `higher-timeframe point of interest / narrative` required before a Candle-2 reversal closure;
2. the source meaning of a `relevant swing` beyond the deliberately simple three-H4 historical formalization;
3. whether C3-open historical entry is too late relative to TTrades' protected-swing/CISD entry model;
4. whether target selection should follow a pre-established Draw on Liquidity rather than mechanically using C1's opposite extreme;
5. whether the protected swing should be established using TTrades' full swing-confirmation semantics rather than the frozen causal-series extreme.

These questions must be resolved from ICT/TTrades first, not from profitable cells in this consumed replay.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
