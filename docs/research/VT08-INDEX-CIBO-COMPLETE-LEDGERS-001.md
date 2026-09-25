# VT08 INDEX — CIBO COMPLETE MARKET-INTELLIGENCE LEDGERS 001

## Scope

This research-only package materializes the eight ledgers required to explain the
full behavior of NAS100, SP500 and US30 around frozen VT08 Index V7 signals.

The ledgers are:

1. `MARKET_JOURNEY_LEDGER` — full per-episode journey and frozen trader context.
2. `STRUCTURE_TOUCH_LEDGER` — every direction-aligned FVG / Order Block /
   Breaker Block / liquidity-sweep observation found in the fixed pre-signal
   lookback, including touch count, dwell time and penetration.
3. `PRE_DEPARTURE_SEQUENCE_LEDGER` — ordered structures and events preceding the
   mechanically defined departure.
4. `DEPARTURE_TIMING_LEDGER` — weekday, reaction hour, signal hour and latency to
   the first +0.5R favorable departure, plus 1R/2R timing.
5. `TARGET_DESTINATION_LEDGER` — 0.5R–5R destinations, known H4/source-day
   boundaries, 24h maximum favorable excursion and extension beyond 2R.
6. `CROSS_INDEX_JOURNEY_LEDGER` — NAS100/SP500/US30 side agreement, signal leader,
   departure leader and lead/lag minutes inside the same NY-date/anchor cohort.
7. `DAILY_PATH_LEDGER` — source-day path, high/low timing, first extreme,
   directional efficiency, body flips, inside-bar rate and range state.
8. `TRADER_MARKET_SYNC_LEDGER` — formal comparison of frozen trader outcome with
   what the market subsequently did, including stop-then-expansion cases.

## Mechanical definitions

### Departure

The diagnostic departure is the first favorable `+0.5R` touch after the frozen V7
signal. This threshold is not a new entry rule. It is a fixed ruler for comparing
latency across markets, structures, weekdays and anchors.

### Structure touch

Structure observations are direction-aligned with the frozen V7 side and are
searched in a fixed 72-hour pre-signal window. Zone penetration is measured as the
fraction of zone depth reached from the expected retest side. Dwell is the number
of M15 bars overlapping the zone multiplied by 15 minutes.

### Daily path

The day follows VT08 source-day convention (`18:00 -> 17:00 America/New_York`).
Labels such as lateral/accumulation-like or directional/expansion-like are fixed
descriptive heuristics and are not economic admission rules.

### Cross-index lead/lag

Cohorts are grouped by New York calendar date and frozen anchor. Signal leader is
the first frozen V7 signal. Departure leader is the first market in the cohort to
reach the fixed +0.5R diagnostic departure threshold.

## Governance

- V7 identity and economic fingerprint remain frozen.
- Only already-consumed evidence from 2018-09-15 through the retained 2026 endpoint
  is used.
- No fresh holdout is accessed by this package.
- Structure association does not establish causation.
- Post-arrival information is outcome evidence and cannot be used as an admission
  feature without a new candidate identity.
- No ledger may automatically rewrite entry, stop, target, day, anchor or market
  policy.
- Any specialist derived from these findings requires a new frozen identity and a
  genuinely unseen holdout.
- `LIVE_AUTHORIZED=FALSE`
- `REAL_CAPITAL_AUTHORIZED=FALSE`
- `PRODUCTION_AUTHORIZED=FALSE`
