# QORE CORE — CIBO MARKET ATLAS 20Y V1

**Status:** RESEARCH FREEZE — NO TRADER AUTHORITY  
**Identity:** `CIBO_MARKET_ATLAS_20Y_V1`  
**Tracker:** Issue #602  
**Repository:** `mezas3238-hue/qore-core`  
**Execution surface:** GitHub / GitHub Actions only. VPS is out of scope.

## 0. Mission

Build a long-horizon, cross-asset market-intelligence atlas so CIBO can study how markets actually behave across approximately twenty years of verified evidence. This program studies markets first and traders second.

The atlas is descriptive/diagnostic research. It does not certify a trader, select a setup, mutate strategy code, size risk, or authorize execution.

## 1. Target horizon

Target interval: approximately `2006-09-16` through `2026-09-16`.

Twenty years is a target, not an assumption. Exact availability must be discovered and recorded independently for every symbol and timeframe.

Rules:
- Never synthesize missing OHLC.
- Never interpolate unavailable bars.
- Never silently replace a missing interval with another.
- Never infer one broker/provider's history from another without a new evidence identity.
- A shorter verified interval remains useful but must be labeled exactly as such.

## 2. Initial market universe

### Forex
`AUDJPY`, `AUDUSD`, `EURUSD`, `GBPJPY`, `GBPUSD`, `USDCAD`, `USDJPY`

### Indices
`NAS100`, `SP500`, `US30`

### Metals
`XAUUSD`, `XAGUSD`

Any new market requires a versioned scope change.

## 3. Timeframes

Acquire/derive, where supported by exact provider evidence:
- M5
- M15
- H1
- H4
- D1
- W1
- MN

High-resolution and long-horizon availability are separate questions. It is valid for M5 to cover fewer years than D1/H1, but the manifest must make that explicit.

## 4. Phase A — Data Availability Map

Before any market-state inference, GitHub Actions must probe and record:
- earliest verified bar;
- latest verified bar;
- missing-bar counts;
- duplicate/contradictory bars;
- exact provider symbol identity;
- digits/tick-size/market specification where available;
- DST/time-zone conventions;
- per-year completeness;
- per-timeframe completeness;
- artifact digest and git SHA.

Output: `market-availability-manifest.json`.

No analysis beyond data-quality diagnostics is authorized until this phase is complete.

## 5. Phase B — Canonical market feature ledger

For every causal observation point, calculate only information available at that timestamp.

### Price-path geometry
- open/high/low/close;
- range and true range;
- body/wick fractions;
- close location;
- directional return;
- gap/open displacement;
- excursion from recent extrema;
- normalized distance to relevant liquidity levels.

### Volatility
- realized range/return volatility;
- rolling ATR-style range measures;
- expansion/contraction ratios;
- volatility percentiles using trailing/expanding history only;
- volatility clustering persistence;
- jump/shock flags;
- time since last shock.

### Trend / range / stagnation
- directional efficiency ratio;
- rolling slope normalized by volatility;
- higher-high/lower-low persistence;
- displacement vs overlap;
- range compression;
- stagnation duration;
- breakout/reversal frequency;
- time spent above/below rolling equilibrium.

### Liquidity behavior
- prior high/low raids;
- swing raids;
- equal-high/equal-low clustering where deterministically defined;
- reclaim vs acceptance;
- CISD/protected-swing observations where source-bound definitions exist;
- opposing-liquidity reach;
- time-to-reclaim;
- time-to-opposing-liquidity;
- MFE/MAE normalized by source range and causal volatility.

### Temporal dimensions
- minute/hour in New York time, DST-aware;
- session bucket as diagnostic metadata only;
- weekday;
- week-of-month;
- month;
- quarter;
- year;
- holiday/weekend-gap metadata only when source evidence supports it.

## 6. Phase C — Market-state ontology

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

Multiple simultaneous labels may be retained if the market genuinely exhibits overlapping dimensions (for example `TREND_UP + HIGH_VOL_EXPANSION`). CIBO must not force a single state where evidence is mixed.

## 7. Phase D — Temporal atlas

For each market/timeframe/state, compute descriptive distributions by:
- hour;
- session;
- weekday;
- month;
- quarter;
- year;
- rolling 24/36/60-month blocks.

Questions include:
- when expansion most often begins;
- how long trends/ranges/stagnation persist;
- typical transition times;
- whether volatility changes by hour/day/month;
- whether certain temporal patterns remain stable across decades.

Temporal effects are observations, not automatic filters.

## 8. Phase E — Regime transition atlas

Measure:
- state duration distributions;
- transition matrices;
- conditional next-state frequencies;
- transition latency;
- persistence by asset class;
- shock-to-normal recovery;
- compression-to-expansion transitions;
- trend-to-range and range-to-trend transitions.

All transition probabilities must include sample size and uncertainty.

## 9. Phase F — Cross-market atlas

Compute rolling and state-conditional:
- correlations;
- co-movement;
- dispersion;
- beta-like normalized response;
- lead/lag associations;
- simultaneous shocks;
- cross-index agreement/divergence;
- FX risk-on/risk-off clusters where evidence supports them;
- metals vs USD/indices relationships where symbols are available.

Lead/lag is association only unless independently replicated. No causal wording from correlation alone.

## 10. Phase G — Extreme-event atlas

Catalog large historical moves and transitions using causal, market-relative thresholds:
- extreme range days/hours;
- gap events;
- volatility shocks;
- prolonged stagnation;
- sustained trend runs;
- rapid reversals;
- liquidity cascades;
- correlation breakdowns.

Do not use retrospective named-event knowledge to construct state labels unless an external event calendar is added under a new evidence identity.

## 11. Statistical discipline

Required:
- block-bootstrap confidence intervals where dependence matters;
- rolling-period stability;
- yearly/quarterly stability;
- leave-one-market-out summaries;
- leave-one-period-out summaries;
- sample-size reporting;
- exploratory multiple-comparison warning;
- normalized metrics for cross-asset comparison;
- no P&L-based filter selection.

Exploration does not equal edge.

## 12. Evidence ladder

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

## 13. CIBO query layer

The final atlas must support questions such as:
- “Find historical states similar to the current NAS100 H4/D1 regime.”
- “How did EURUSD behave after comparable volatility compression?”
- “What normally followed a liquidity raid with reclaim but no CISD?”
- “How persistent was this type of trend over 20 years?”
- “Which market states preceded the hard-stop cluster seen in Turtle Soup R5?”

Answers must include provenance, sample size, interval, markets, uncertainty and evidence tier.

## 14. Storage / artifact policy

Large raw data do not belong in git history.

Git stores:
- code;
- schemas;
- tests;
- manifests;
- freeze documents;
- summarized results.

GitHub Actions artifacts store:
- immutable raw/processed evidence chunks;
- feature ledgers;
- state ledgers;
- yearly/market partitions;
- final atlas packages.

Every artifact requires SHA-256 and exact git SHA binding.

## 15. Anti-hindsight / anti-curve-fit

Prohibited:
- tuning regime thresholds to trader P&L;
- deleting markets because a trader lost there;
- converting an hour/day/session pattern directly into a trader filter;
- changing state definitions after seeing a desired economic result;
- calling consumed diagnostic evidence fresh OOS;
- allowing CIBO to self-promote a hypothesis into operating policy.

## 16. Authority

`CIBO MARKET ATLAS 20Y V1` has research/observation authority only.

```text
DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false
```

CIBO may observe, compare, explain, request research and recommend a research direction. Risk/execution/trader certification remain external authorities.