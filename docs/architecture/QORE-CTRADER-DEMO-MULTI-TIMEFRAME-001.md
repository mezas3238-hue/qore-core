# QORE-CTRADER-DEMO-MULTI-TIMEFRAME-001 — Native six-period closed-OHLC boundary

## Status

**ENGINEERING — IMPLEMENTATION SLICE — cTrader DEMO native closed-OHLC generalized from M5 to six periods.**

This document records the bounded causal-family closure for the cTrader DEMO
market-data boundary. It is engineering evidence, not a validation or
Production-authorization marker.

## Purpose

At the prior slice, `src/qore/infrastructure/ctrader_demo_market_data.py`
admitted only `M5` (`CTraderTrendbarPeriod.M5`, `_M5_SECONDS = 300`) and
hard-coded M5 in four places: the timeframe support gate, the response period
identity check, the interval derivation, and the payload `timeframe_seconds`.

This slice generalizes the boundary to exactly six provider-native cTrader
trendbar periods — `M1`, `M5`, `M15`, `M30`, `H1`, and Daily — without leaking
provider-specific period rules into Core/Domain.

## Provider-native period contract (verified)

Primary source: cTrader Open API `spotware/openapi-proto-messages` →
`OpenApiModelMessages.proto` ([blob](https://github.com/spotware/openapi-proto-messages/blob/main/OpenApiModelMessages.proto#L536-L562)).

```
enum ProtoOATrendbarPeriod {
    M1 = 1; M2 = 2; M3 = 3; M4 = 4; M5 = 5; M10 = 6;
    M15 = 7; M30 = 8; H1 = 9; H4 = 10; H12 = 11;
    D1 = 12; W1 = 13; MN1 = 14;
}
message ProtoOATrendbar {
    required int64 volume = 3;
    optional ProtoOATrendbarPeriod period = 4 [default = M1];
    optional int64 low = 5;
    optional uint64 deltaOpen = 6;   // open  = low + deltaOpen
    optional uint64 deltaClose = 7;  // close = low + deltaClose
    optional uint64 deltaHigh = 8;   // high  = low + deltaHigh
    optional uint32 utcTimestampInMinutes = 9; // open-tick time in minutes
}
```

The six admitted periods and their native identifiers:

| Native name | Wire code | Fixed seconds | Calendar vs fixed |
|---|---|---|---|
| M1 | 1 | 60 | fixed |
| M5 | 5 | 300 | fixed |
| M15 | 7 | 900 | fixed |
| M30 | 8 | 1800 | fixed |
| H1 | 9 | 3600 | fixed |
| **D1** | **12** | **86400 (UTC day)** | **calendar** |

## Daily (`D`) mapping — explicit and immutable

- The cTrader native Daily identifier is **`D1`** (wire code 12), not `"D"`.
- Canonical Core-facing daily is `MarketTimeframeCode.D1` in
  `market_observation.py`, whose `MarketTimeframe.fixed_seconds` returns `None`
  (a calendar period; no fabricated fixed duration).
- The legacy fixed-duration contract (`market_data.Timeframe`, `OhlcSnapshot`,
  `MarketDataIngestionFlow`) represents Daily as `Timeframe(86400)`.
- The boundary keeps provider-native identity separate from the canonical code:
  `CTraderTrendbarPeriod.D1.canonical_timeframe_code is MarketTimeframeCode.D1`
  (an immutable `MappingProxyType` bridge, pinned by tests). The read path
  emits the legacy `Timeframe(86400)` for downstream ingestion.

The Daily open/close law is explicit and UTC-pinned: `opened_at` must be the
UTC-midnight instant (verified via `astimezone(UTC)`), and `closed_at` is the
next UTC midnight (`opened_at + 86400s` in UTC). No `datetime.now()`,
`date.today()`, or host-local timezone participates in the law. A non-midnight
Daily open (e.g. a 17:00 UTC forex anchor) fails closed before the provider
call.

## Architecture (no Core/Domain change)

All period→seconds/calendar knowledge lives inside
`ctrader_demo_market_data.py`:

- `CTraderTrendbarPeriod` — six members with `.seconds`, `.is_daily`,
  `.canonical_timeframe_code`.
- `_SECONDS_BY_PERIOD`, `_CANONICAL_TIMEFRAME_CODE_BY_PERIOD`,
  `_PERIOD_BY_SECONDS` — immutable `MappingProxyType` bijections with a
  construction-time bijection assertion.
- `_period_for_timeframe(Timeframe) -> CTraderTrendbarPeriod | None` — the
  single exact typed admission map; `None` → `CTraderDemoMarketDataUnsupportedError`.
- `_is_utc_midnight(datetime)` — the Daily calendar-day guard.

`market_data.py`, `ingestion.py`, and `market_observation.py` are unchanged.
Provider→canonical import direction is one-way; no import cycle exists.

## Temporal / evidence laws enforced by the boundary

- Fully-closed single bar: exactly one trendbar, `has_more=False`.
- Exact interval identity: `closed_at == opened_at + period.seconds`, and both
  must equal the request's `opened_at`/`closed_at`.
- Period grid alignment: `utc_timestamp_in_minutes % (period.seconds // 60) == 0`
  (Daily ⇒ UTC midnight; M1 ⇒ any whole minute).
- Response period binding: `response.period is period` (exact enum identity).
- No resampling/aggregation: one trendbar in, one bar out.
- #290 `deltaHigh` law preserved: `0 <= delta_open <= delta_high` and
  `0 <= delta_close <= delta_high`, with exact runtime type
  (`type(...) is int`, `type(trendbars) is tuple`, `type(item) is CTraderTrendbar`)
  so subclasses cannot bypass validation.
- Overflow fail-closed: a provider timestamp whose derived `closed_at` would
  exceed the `datetime` range returns a `ValidationError` Failure, never an
  uncaught `OverflowError`.
- Secret hygiene: no credential/account material in any payload, snapshot,
  trendbar, error, `repr`, or `logical_values` (the injected client owns auth).

## Residual (non-claims)

- The boundary reads one period per call; closed-bar-vs-`now` and
  backfill/revision ownership remain in the integrity/quarantine layer
  (`market_data_integrity.py`) and versioned persistence.
- The canonical `OhlcRequest`/`OhlcSnapshot` interval check uses same-`tzinfo`
  wall-clock `total_seconds()`; this is DST-inexact for non-UTC windows in
  `market_data.py` (a pre-existing shared-contract limitation). The cTrader
  Daily path is not affected because it is UTC-pinned. Fixing the shared
  contract is out of scope for this slice.
- The raw `ProtoOATrendbar` `volume` and per-bar `period` fields are collapsed
  at the sanitization boundary into the wrapper `CTraderTrendbarReadResult.period`;
  `symbol_id` is validated but not cross-checked to a request identity (the
  `OhlcRequest` contract carries no account/symbol id).
