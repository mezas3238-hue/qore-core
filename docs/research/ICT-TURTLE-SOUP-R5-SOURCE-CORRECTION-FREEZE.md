# ICT Turtle Soup R5 — authentic Ideal Formation source correction freeze

Date: 2026-09-16

## Governance

R4 is consumed and rejected. R5 is a new candidate identity derived from a post-R4 source re-audit, not a parameter fit to the R4 P&L.

No R4 winner/loser threshold, pair, side, session, projected-R bucket, reclaim depth, stop width, or DOL age is used as an R5 eligibility rule.

## Why R5 exists

R4 implemented the standard TTrades Fractal Model correctly:

higher-timeframe Candle 2 reversal closure -> lower-timeframe CISD -> protected swing -> continuation.

However, R4's identity used the term `IDEAL_C2`. TTrades separately defines **Ideal Formation** as a stricter same-timeframe structure in which Candle 2 or Candle 3 simultaneously creates the closure and the protected swing by closing through the opposing candle series responsible for the swing.

The R5 research family tests that source-defined stricter formation as its own identity.

Primary TTrades sources:

- https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/
- https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/
- https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/
- https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/
- https://ttrades.com/positional-entries-enter-before-the-expansion/
- https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/

## Frozen identity

`ICT_TURTLE_SOUP_R5_D1_AUTHENTIC_IDEAL_C2__H4_AUTHENTIC_IDEAL_C2__POSITIONAL_DAILY_DOL`

## Frozen methodology

### 1. Turtle Soup / liquidity event

No session gate. A reversal family begins from a sweep of a prior high/low and a reversal closure. Asia, London, and New York remain eligible.

### 2. Forex source candles

- timezone: `America/New_York`, DST-aware;
- source day opens 17:00 New York;
- H4 opens 17:00 / 21:00 / 01:00 / 05:00 / 09:00 / 13:00 New York.

### 3. Daily authentic Ideal Candle 2

For LONG:

1. Daily C2 sweeps below Daily C1 low.
2. Daily C2 closes back above Daily C1 low.
3. Daily C2 is an up-close candle (`close > open`).
4. Immediately before C2, identify the contiguous same-Daily-timeframe down-close candle series that led into the C2 low. A doji belongs to neither series and terminates contiguity.
5. Daily C2 closes above the opening price of the first candle in that opposing series.
6. This same Daily C2 therefore creates the Daily protected low under the authentic Ideal Formation definition.
7. Daily C3 is the expected expansion candle.

SHORT is the exact mirror using an up-close series and a down-close Daily C2.

If the opposing series cannot be determined unambiguously, abstain.

### 4. Daily point of interest

The Daily Ideal Formation must occur at a source-valid point of interest. The first deterministic R5 POI family is a previous completed Daily high/low that is still relevant/untouched at the time of the sweep. No arbitrary ATR, bar-age, or wick-ratio threshold is introduced.

This is deliberately narrower than treating every Daily reversal closure as eligible.

### 5. H4 authentic Ideal Candle 2 inside Daily C3

Within the aligned Daily C3:

For LONG:

1. H4 C2 sweeps below H4 C1 low and closes back above H4 C1 low.
2. H4 C2 closes bullish (`close > open`).
3. Immediately before H4 C2, identify the contiguous same-H4-timeframe down-close series responsible for delivery into the H4 C2 low.
4. H4 C2 closes above the opening price of the first candle in that series.
5. The H4 C2 low becomes the H4 protected swing immediately.
6. H4 C3 is the expected expansion candle.

SHORT mirrors these rules.

R5 does **not** call a standard H4 C2 + M15 CISD an Ideal Formation. M15 may be retained as diagnostic metadata but it is not what defines the authentic H4 Ideal C2 in this identity.

### 6. Entry

Use a positional entry at the H4 C3 open only after the H4 authentic Ideal C2 is complete before that open.

No entry before the formation is complete.

### 7. Invalidation

- LONG: one native tick below H4 protected low.
- SHORT: one native tick above H4 protected high.

The native tick is QORE execution discretization only; no arbitrary pip/ATR buffer is allowed.

### 8. Target / DOL

Target is pre-entry higher-timeframe untouched liquidity in the direction of the Daily bias.

For this first deterministic R5 identity:

- use the nearest eligible untouched completed Daily swing high for LONG;
- use the nearest eligible untouched completed Daily swing low for SHORT.

A level already taken before entry is not eligible.

No minimum projected-R gate exists.

No runner, partial, BE, trailing, or re-entry is included in R5. TTrades allows multi-target management, but that is a separate management identity and will not be mixed into this structural test.

### 9. Lifecycle

Target or protected-swing invalidation first; otherwise close at the end of the containing Daily C3.

If the same M5 touches stop and target and no lower-resolution ordering is pre-frozen, use STOP_FIRST.

Data gaps fail closed. Real favorable gap through target is capped at target; gap through stop exits at the observed market-open price.

### 10. Sessions

Asia / London / New York are diagnostic metadata only. No clock inclusion/exclusion rule.

## Explicitly excluded

- no R4 reclaim-depth threshold;
- no CISD latency threshold;
- no minimum R;
- no symbol selection;
- no side selection;
- no session/hour filter;
- no stop widening;
- no SMT requirement;
- no fixed wick ratio;
- no Ideal C3 / Candle 4 family;
- no management runner variant.

## Fresh-evidence requirement

R5 must not use as fresh evidence:

- 2018-2020 R4 holdout;
- 2020-2022 Turtle Soup R2/R3 holdout;
- 2022-2024 VT-08 fresh holdout;
- any later consumed VT-08/Index development windows.

Repository audit found no documented trading-research exposure to 2016/2017. The intended next one-shot window is immediately prior to R4 acquisition and must not overlap it:

- warm-up/acquisition start: `2016-03-01T22:00:00Z` (17:00 New York while EST is in force);
- evaluation: `[2016-05-01T21:00:00Z, 2018-05-01T21:00:00Z)`;
- span: 730 days;
- symbols: AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, USDCAD, USDJPY.

Status language must be `FRESH_RELATIVE_TO_DOCUMENTED_REPO_EVIDENCE`.

If the provider cannot supply the frozen window, fail. No replacement interval is authorized after mechanics are frozen.

## Authority

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
