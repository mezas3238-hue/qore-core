# VT08 INDEX — REACTION STRUCTURE ATLAS 001

## Purpose

This research layer answers the missing CIBO question: **where does price arrive before it departs, what structure is present there, at what day/time does the reaction occur, what does price do around the level, and how long until expansion?**

It consumes only already-consumed VT08 Index evidence and the validated Market Journey Atlas. It does not change V7 or authorize any specialist trader.

## Source-bound diagnostic structures

### Fair Value Gap

TTrades defines the FVG as a three-candle imbalance created during displacement. The atlas detects the mechanical non-overlap between candle 1 and candle 3 and records later retests before the frozen V7 signal.

### Liquidity sweep

The atlas records short-term highs/lows run and closed back through as mechanical liquidity-take observations. These are descriptive and are not standalone entries.

### Order Block

TTrades defines an order block as the last series of opposing candles before a reversal/displacement, and its CISD/protected-swing material confirms the swing by closure through the opposing candle series. The atlas therefore labels a diagnostic Order Block only when a contiguous opposing series is subsequently closed through. It records the zone and later retest before the V7 signal.

### Breaker Block

TTrades defines:

- bullish breaker: `Low -> High -> Lower Low -> Higher High`;
- bearish breaker: `High -> Low -> Higher High -> Lower Low`.

The atlas detects that sequence from local pivots, builds the source candle zone described by the lesson, and requires a later retest before the V7 signal to label a reaction.

### Mitigation Block

TTrades has a separate mitigation-block definition, but this atlas leaves it unresolved until a dedicated formalization/test freeze is added. It must not be silently conflated with a breaker.

## Per-episode CIBO explanation

For every frozen V7 episode, CIBO retains:

- NAS100 / SP500 / US30;
- weekday and H4 anchor;
- side and original V7 POI;
- latest reaction timestamp and New York hour;
- all structures observed at that same reaction timestamp (confluence is preserved);
- descriptive behavior from reaction to signal: accumulation-like / expansion-like / transition-mixed / liquidity-take;
- minutes reaction -> signal;
- minutes reaction -> +1R and +2R when reached;
- whether +1R / +2R / +3R was later reached;
- whether V7 was stopped;
- post-stop afterlife;
- known H4/source-day directional boundaries;
- contemporaneous peer-index snapshot;
- prior-H4 range regime.

## Behavior labels

`accumulation-like`, `expansion-like` and `transition-mixed` are fixed descriptive heuristics based on directional efficiency and body flipping. They are **not TTrades entry rules**, are not tuned to PnL, and cannot promote a trade by themselves. `liquidity-take` is used when the latest reaction includes a mechanical sweep event.

## Required aggregation

CIBO must report structure behavior by:

1. market;
2. market x weekday;
3. market x New York reaction hour;
4. market x structure;
5. structure x subsequent 1R/2R/3R reach;
6. stop rate and post-stop continuation;
7. temporal window, so a pattern cannot be accepted solely because it appears in one period.

## Governance

- V7 remains frozen.
- All source periods are consumed evidence.
- Observed structure is not proof of causation.
- Positive retrospective structure behavior is not a specialist rule.
- Any NAS100/SP500/US30 specialist rule must be frozen under a new identity before a genuinely unseen one-year holdout is opened.
- `LIVE_AUTHORIZED=FALSE`.
- `REAL_CAPITAL_AUTHORIZED=FALSE`.
- `PRODUCTION_AUTHORIZED=FALSE`.
