# QORE CORE — CIBO MARKET ATLAS 20Y V1

**Status:** RESEARCH FREEZE — NO TRADER AUTHORITY  
**Identity:** `CIBO_MARKET_ATLAS_20Y_V1`  
**Tracker:** Issue #602  
**Repository:** `mezas3238-hue/qore-core`  
**Execution surface:** GitHub / GitHub Actions only. VPS is out of scope.

## 0. Mission

Build a long-horizon, cross-asset market-intelligence laboratory so CIBO can study how markets actually behave from the deepest verified M5 history exposed by the provider through the current boundary. The nominal twenty-year horizon is not a cap: if verified M5 extends farther back, the laboratory consumes the farther history; if it is shorter, the laboratory records the exact shorter boundary.

This program studies markets first and traders second. It is descriptive/diagnostic research. It does not certify a trader, select a setup, mutate strategy code, size risk, or authorize execution.

The laboratory must preserve the full evidence chain. It must not collapse the research output into a small summary that discards the underlying observations.

## 1. Canonical historical horizon

For every symbol, the primary target interval is:

`EARLIEST_CONTIGUOUS_VERIFIED_M5 -> CURRENT_FROZEN_CLOSE`

Twenty years is a planning target, not an assumption and not a maximum.

Rules:
- Probe provider history until the earliest genuinely available M5 boundary is established.
- Never synthesize missing OHLC.
- Never interpolate unavailable bars.
- Never silently replace a missing interval with another.
- Never infer one broker/provider's history from another without a new evidence identity.
- Never declare the requested twenty years present merely because a query succeeded.
- A shorter verified interval remains valid and must be labeled with exact first/last bars and completeness.
- If history extends beyond twenty years, retain it; do not truncate merely to fit the program name.

## 2. M5 as canonical primary evidence

M5 is the canonical market-history source for this laboratory wherever provider history exists.

For the verified M5 interval, all higher analytical timeframes are derived deterministically from the same M5 evidence:
- M15
- H1
- H4
- D1
- W1
- MN

No alternate native H1/H4/D1 feed may be silently mixed with the canonical M5-derived series inside the same evidence identity.

Derived candles must fail closed when their required M5 components are incomplete. A missing M5 segment may not be hidden by creating an apparently complete higher-timeframe candle.

If a future phase explicitly studies provider-native higher-timeframe history outside the M5 boundary, that requires a separate evidence identity and must never be presented as the same canonical M5 atlas.

## 3. Initial market universe

### Forex
`AUDJPY`, `AUDUSD`, `EURUSD`, `GBPJPY`, `GBPUSD`, `USDCAD`, `USDJPY`

### Indices
`NAS100`, `SP500`, `US30`

### Metals
`XAUUSD`, `XAGUSD`

Any new market requires a versioned scope change.

## 4. Phase A — Data Availability Map

Before any market-state inference, GitHub Actions must probe and record for every symbol:
- exact provider symbol identity;
- digits/tick size / market specification where available;
- earliest successful M5 observation;
- earliest contiguous verified M5 observation;
- latest verified M5 observation;
- total expected vs observed M5 bars by year/month/day;
- missing-bar runs and their duration;
- duplicate bars;
- contradictory bars;
- market closures vs unexplained holes where deterministically identifiable;
- DST/time-zone conventions;
- per-year completeness percentage;
- artifact digest and exact git SHA.

Output: `market-availability-manifest.json` plus one symbol-level manifest per market.

No regime or behavioral inference is authorized until this phase is complete.

## 5. Exhaustive evidence-retention law

The phrase “the laboratory must return all data” is defined operationally as follows.

For every computed observation, the laboratory must retain the machine-readable row or partition that produced the summary. No analysis may exist only as a sentence in a Markdown report.

The atlas must retain, partitioned by market and year where volume requires it:

1. **RAW_M5_LEDGER** — every verified canonical M5 OHLC bar plus provider identity and provenance.
2. **DERIVED_OHLC_LEDGER** — deterministic M15/H1/H4/D1/W1/MN bars with completeness flags.
3. **FEATURE_LEDGER** — every causal feature calculated at each supported observation point.
4. **EVENT_LEDGER** — every detected liquidity raid, gap, breakout, reclaim, CISD, protected swing, shock, compression/expansion event and other versioned event type.
5. **STATE_LEDGER** — every causal market-state label and the exact feature values supporting it.
6. **TRANSITION_LEDGER** — every state-to-state transition with start/end timestamps and duration.
7. **FORWARD_PATH_LEDGER** — standardized future path measurements used for descriptive research, kept explicitly separate from causal features so they cannot leak into state classification.
8. **TEMPORAL_CUBE** — counts/distributions by minute/hour/session/weekday/week/month/quarter/year.
9. **VOLATILITY_CUBE** — rolling and expanding volatility/range distributions and percentiles.
10. **LIQUIDITY_CUBE** — liquidity-reference type, age, sweep depth, reclaim/acceptance, time-to-reclaim, CISD/PS and opposing-liquidity outcomes.
11. **REGIME_CUBE** — state frequencies, durations and transition matrices by market/timeframe/period.
12. **CROSS_MARKET_CUBE** — aligned rolling correlations, dispersion, co-movement, lead/lag associations and simultaneous shock flags.
13. **EXTREME_EVENT_CATALOG** — market-relative shocks, gaps, prolonged trends/ranges/stagnation, rapid reversals and correlation breakdowns.
14. **DATA_QUALITY_LEDGER** — every missing/duplicate/contradictory/invalid partition decision.
15. **SUMMARY_REPORTS** — compact human-readable summaries generated only from the retained machine data.

If a metric is calculated during an official atlas run and used in a conclusion, its per-observation or per-partition source values must be retained in the artifact lineage.

## 6. Canonical feature ledger

For every causal observation point, calculate only information available at that timestamp.

### Price-path geometry
- open/high/low/close;
- range and true range;
- body/wick fractions;
- close location;
- directional return;
- gap/open displacement;
- distance from recent extrema;
- normalized distance to deterministic liquidity references;
- overlap/displacement ratios;
- path efficiency;
- time spent inside/outside prior ranges.

### Volatility
- realized range volatility;
- realized return volatility;
- rolling ATR-style range measures;
- expansion/contraction ratios;
- trailing/expanding volatility percentile;
- volatility-of-volatility;
- volatility clustering persistence;
- jump/shock flags;
- time since last shock;
- time required for volatility normalization after shocks.

### Trend / range / stagnation
- directional efficiency ratio;
- rolling slope normalized by causal volatility;
- higher-high/lower-low persistence;
- displacement vs overlap;
- range compression;
- range expansion;
- stagnation duration;
- breakout frequency;
- failed-breakout frequency;
- reversal frequency;
- distance/time above and below causal equilibrium proxies;
- trend-run duration and cumulative normalized move.

### Liquidity behavior
- prior high/low raids;
- swing raids;
- equal-high/equal-low clustering where deterministically defined;
- stacked-liquidity references;
- reclaim vs acceptance;
- reclaim latency;
- sweep depth in native ticks, percentage and source-range units;
- CISD/protected-swing observations where source-bound definitions exist;
- opposing-liquidity reach;
- time-to-opposing-liquidity;
- MFE/MAE normalized by source range and causal volatility;
- continuation beyond first liquidity objective;
- post-raid state transitions.

### Temporal dimensions
- exact UTC timestamp;
- minute/hour in New York time, DST-aware;
- session bucket as diagnostic metadata only;
- weekday;
- week-of-month;
- month;
- quarter;
- year;
- elapsed time since market reopen where identifiable;
- holiday/weekend-gap metadata only when source evidence supports it.

## 7. Forward-path research measurements

To study behavior, the laboratory may calculate future outcomes, but these fields are forbidden from causal state classification and must live in `FORWARD_PATH_LEDGER` or equivalent outcome columns.

Standard horizons should include where data permits:
- 5m
- 15m
- 30m
- 1h
- 2h
- 4h
- 8h
- 12h
- 24h
- 48h
- 5 trading days

Measure:
- favorable/adverse excursion;
- net displacement;
- realized range;
- time to new high/low;
- time to reclaim source level;
- time to opposing liquidity;
- maximum drawdown from event anchor;
- time to recovery;
- next causal state and transition latency.

Every forward metric must be clearly marked `OUTCOME_ONLY=true` or equivalent to prevent lookahead leakage.

## 8. Market-state ontology

Research labels:
- `TREND_UP`
- `TREND_DOWN`
- `RANGE`
- `COMPRESSION`
- `EXPANSION`
- `REVERSAL`
- `SHOCK`
- `STAGNATION`
- `TRANSITION`

No label may use future candles.

Thresholds must be causal/time-local: rolling or expanding distributions only. Whole-sample percentile thresholds are prohibited for causal state labeling.

Multiple simultaneous labels may be retained if evidence genuinely supports overlapping dimensions (for example `TREND_UP + HIGH_VOL_EXPANSION`). CIBO must not force a single state where evidence is mixed.

## 9. Temporal atlas

For each market/timeframe/state, compute distributions by:
- minute where sample size permits;
- hour;
- session;
- weekday;
- week-of-month;
- month;
- quarter;
- year;
- rolling 24/36/60-month blocks.

Questions include:
- when expansion most often begins;
- how long trends/ranges/stagnation persist;
- typical transition times;
- volatility changes by hour/day/month;
- stability of temporal behavior across years and decades.

Temporal effects are observations, not automatic trader filters.

## 10. Regime transition atlas

Measure:
- state duration distributions;
- transition matrices;
- conditional next-state frequencies;
- transition latency;
- persistence by asset class;
- shock-to-normal recovery;
- compression-to-expansion transitions;
- trend-to-range and range-to-trend transitions;
- reversal-to-continuation and false-breakout transitions.

All transition estimates must include sample size and uncertainty.

## 11. Cross-market atlas

Compute rolling and state-conditional:
- correlations;
- co-movement;
- dispersion;
- beta-like normalized response;
- lead/lag associations;
- simultaneous shocks;
- cross-index agreement/divergence;
- FX clusters where evidence supports them;
- metals vs USD/indices relationships where symbols are available.

Lead/lag is association only unless independently replicated. No causal wording from correlation alone.

## 12. Extreme-event atlas

Catalog large historical moves and transitions using causal market-relative thresholds:
- extreme range bars/days;
- gap events;
- volatility shocks;
- prolonged stagnation;
- sustained trend runs;
- rapid reversals;
- liquidity cascades;
- correlation breakdowns;
- unusually fast state transitions.

Do not use retrospective named-event knowledge to construct state labels unless an external event calendar is added under a new evidence identity.

## 13. Statistical discipline

Required:
- block-bootstrap confidence intervals where dependence matters;
- rolling-period stability;
- yearly/quarterly stability;
- leave-one-market-out summaries;
- leave-one-period-out summaries;
- sample-size reporting;
- exploratory multiple-comparison warning;
- normalized metrics for cross-asset comparison;
- no P&L-based filter selection;
- no winner/loser labeling for the general market atlas unless explicitly joining a frozen trader outcome dataset under a separate diagnostic identity.

Exploration does not equal edge.

## 14. Evidence ladder

Every CIBO statement must be labeled:
- `E0_OBSERVATION`
- `E1_ASSOCIATION`
- `E2_CAUSAL_HYPOTHESIS`
- `E3_REPLICATED_MECHANISM`
- `E4_CANDIDATE_RULE`

No E0/E1 finding may directly alter a trader.

E2 requires a falsifiable mechanism and preregistration.
E3 requires replication on independent evidence not used to originate the hypothesis.
E4 requires a new candidate identity and separate trader-validation workflow.

## 15. CIBO query layer

The final atlas must allow CIBO to retrieve the underlying rows as well as summaries. Example queries:
- “Find all historical states similar to the current NAS100 H4/D1 regime and return the exact matched episodes.”
- “How did EURUSD behave after comparable volatility compression, broken down by year and hour?”
- “Return every liquidity raid with reclaim but no CISD and its subsequent path.”
- “How persistent was this type of trend across every available rolling five-year block?”
- “Which market states preceded the hard-stop cluster seen in Turtle Soup R5?”
- “Show raw counts, distributions, confidence intervals and exact episode IDs behind this conclusion.”

Answers must include provenance, sample size, exact interval, markets, uncertainty, evidence tier and retrievable episode/partition identifiers.

## 16. Storage / artifact policy

Large raw data do not belong in git history.

Git stores:
- code;
- schemas;
- tests;
- manifests;
- freeze documents;
- summarized results;
- artifact indexes.

GitHub Actions artifacts store:
- immutable raw M5 partitions;
- derived OHLC partitions;
- feature/event/state/transition ledgers;
- forward-path ledgers;
- statistical cubes;
- yearly/market partitions;
- final atlas packages.

Every artifact requires:
- SHA-256;
- exact git SHA binding;
- symbol;
- exact first/last timestamp;
- row count;
- schema version;
- parent evidence refs.

No official output may exist only in runner-local temporary storage.

## 17. Anti-hindsight / anti-curve-fit

Prohibited:
- tuning regime thresholds to trader P&L;
- deleting markets because a trader lost there;
- converting an hour/day/session pattern directly into a trader filter;
- changing state definitions after seeing a desired economic result;
- calling consumed diagnostic evidence fresh OOS;
- allowing CIBO to self-promote a hypothesis into operating policy;
- deleting inconvenient observations from the atlas without an explicit data-quality reason and ledger entry.

## 18. Authority

`CIBO MARKET ATLAS 20Y V1` has research/observation authority only.

```text
DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false
```

CIBO may observe, compare, explain, request research and recommend a research direction. Risk/execution/trader certification remain external authorities.