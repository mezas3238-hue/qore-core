# VT08 INDEX — DEEP BEHAVIOR LAB 001

## Purpose

This lab studies the frozen `VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001` identity in depth across already-consumed NAS100, SP500 and US30 evidence. It is diagnostic infrastructure, not a candidate-selection engine.

It must not:

- alter V7 admission, daily bias, POI, C2/C3, CISD, continuation, stop or target rules;
- remove a market, side, anchor, model or POI because its retrospective PnL is poor;
- describe consumed evidence as fresh;
- authorize LIVE, production or real capital;
- promote a post-result filter into V7.

Any future rule change derived from this lab creates a new candidate identity and requires a new unseen validation partition.

## Frozen identity under observation

- Candidate: `VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001`
- Rule fingerprint: `a7f3b7afa3a98bfcb4daad1595762ce3925000fb256e2cbd2db84b8ec80b1308`
- Executable H4 anchors: 22 / 02 / 06 / 10 New York
- 18:00 New York: daily-open/context only
- 14:00 New York: execution disabled
- SAME_C2 requires body-side transition through the H4 open
- Stop: Protected Swing extreme
- Target: fixed 2R
- Primary diagnostic friction: -0.05R/trade
- Secondary diagnostic friction: -0.10R/trade

## Consumed evidence universe

The lab is permitted to use all of the following because each partition has already been consumed by earlier research or holdout execution:

1. 2018-09-15 .. 2020-09-15
2. 2020-09-15 .. 2022-09-15
3. 2022-09-15 .. 2023-09-15
4. 2023-09-15 .. 2024-08-13
5. 2024-08-13 .. 2026-09-12

No output from this lab changes the fresh/consumed status of another period.

## Diagnostic architecture

### 1. Opportunity funnel

Every complete executable H4 opportunity is classified at the first stage where it fails:

- no daily bias;
- no POI;
- POI not touched;
- no CISD;
- no continuation or Protected Swing invalidated;
- SAME_C2 still inside wick side of H4 open;
- non-positive risk;
- valid signal.

Funnel conversion is reported overall, by market, by anchor and market×anchor.

### 2. Per-trade feature ledger

Every executed V7 trade records, without future leakage in the pre-entry features:

- market, side, anchor, H4 model and POI family;
- year and quarter;
- entry, stop and structural risk fraction;
- entry latency within H4;
- CISD latency and CISD→continuation latency;
- trade duration;
- prior completed H4 body alignment;
- rolling prior-H4 range state based on the latest 20 completed H4 bars;
- previous/current completed source-day body alignment;
- completed source-day range ratio;
- contemporaneous cross-index H4 returns observable by signal time;
- peer alignment count;
- side-adjusted relative-strength rank.

### 3. Stop-loss anatomy

The lab computes conservative pre-exit MFE/MAE and classifies stopped trades by how far they progressed before invalidation:

- <0.5R;
- 0.5–1R;
- 1–1.5R;
- 1.5–2R;
- ≥2R in an ambiguous/gap bar.

It also reports stop duration buckets and market-specific stop behavior.

### 4. Target surface

For research only, the exact same frozen entry and stop are replayed with targets:

- 0.5R;
- 1R;
- 1.5R;
- 2R;
- 2.5R;
- 3R.

The same M15 gap semantics and STOP-first same-bar ordering are preserved. The target surface is descriptive; its best retrospective point must not be selected as a new operating target without a new candidate identity and new holdout.

### 5. Cohort cube

Primary-stress metrics are produced for:

- market;
- side;
- anchor;
- H4 model;
- POI family;
- year;
- quarter;
- entry timing quartile of the H4;
- prior-H4 range regime;
- cross-index peer alignment;
- side-adjusted relative-strength rank;
- current and previous source-day body alignment;
- market×anchor;
- market×model;
- market×side;
- anchor×model;
- market×range regime.

### 6. Path-dependence and portfolio behavior

The lab identifies:

- deepest drawdown episodes and their market/anchor/model/side composition;
- long losing streaks;
- multi-index loss clusters whose signals occur within four hours;
- aggregate and per-window regime degradation.

### 7. Session reconstruction health

The accepted/rejected source-day reconstruction statistics are retained per market, including broker-maintenance-gap handling. No synthetic OHLC is created.

## Interpretation discipline

A negative cohort is a hypothesis source, not a deletion instruction. A positive cohort is not a promotion instruction. Before changing V7, the research team must show a causal explanation that is source-compatible and temporally stable. Any such change creates a new identity (for example V8) and must be frozen before a genuinely unseen holdout is opened.
