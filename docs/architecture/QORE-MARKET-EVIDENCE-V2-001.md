# QORE-MARKET-EVIDENCE-V2-001 — Exact Market Observation Contracts

## Status

**FOUNDATION SLICE 1 — ADDITIVE CONTRACTS — ADVERSARIAL PREFLIGHT CORRECTED**

This document records the first implementation slice authorized by the Trader
Midpoints Architecture Integration Gate. It does not implement the Trader
Midpoints evaluator, provider networking, replay ordering, or execution.

## Purpose

The legacy `OhlcSnapshot` and `QuoteSnapshot` contracts remain valid and
unchanged. Trader Midpoints requires evidence that the legacy fully-valid OHLC
contract cannot express:

- exact decimal price semantics for tick-sensitive predicates;
- explicit candle price side;
- native versus aggregated bar provenance;
- field-level OHLC validity;
- provider-qualified minimum price increment / precision provenance;
- timeframe identities that do not pretend calendar periods have fixed seconds.

The v2 contracts are additive so existing Phase 1A/1B fingerprints and legacy
market-data consumers are not silently reinterpreted.

## Contracts

`MarketPrice` retains an exact positive `Decimal` and exposes one canonical
decimal-string projection.

`MarketTimeframeCode` defines the current Core-facing catalog covering every
native cTrader Open API trendbar period:

`M1, M2, M3, M4, M5, M10, M15, M30, H1, H4, H12, D1, W1, MN1`.

This catalog is the complete current cTrader provider set for this delivery; it
does not claim that no future provider can expose additional periods. Extension
of the provider-neutral catalog must be additive and evidence-backed.

`MarketTimeframe` exposes fixed seconds for minute/hour periods. `D1`, `W1`,
and `MN1` retain explicit provider bar boundaries and do not fabricate constant
durations.

`MarketOhlcField` represents `VALID`, `MISSING`, or `INVALID` independently for
each OHLC field. Missing or invalid fields do not retain a normalized price
value.

`QualifiedOhlcBarObservation` binds instrument, market-data source, timeframe,
price side, native/aggregated origin, explicit interval boundaries, four
field-validity values, and an evidence reference.

`QualifiedQuoteTickObservation` retains exact Bid/Ask evidence and derives exact
spread from those retained decimal values. A zero spread is representable; the
contract must not fabricate a positive spread.

`InstrumentMarketSpecification` binds canonical instrument identity to provider
symbol identity, exact price precision, minimum price increment, effective time,
and evidence provenance.

All logical timestamp projections are normalized to UTC with microsecond
precision. Two timezone-aware `datetime` values representing the same instant
must therefore have the same logical projection. The retained Python datetime
still remains explicit and timezone-aware.

## Trader Midpoints boundary

Trader Midpoints will later accept structural candles only when the concrete
evaluator can prove:

`price_side == BID`

and:

`origin == NATIVE`

and:

`timeframe == M5`.

This slice deliberately does not encode Trader Midpoints session, entry, TP, SL,
or state-machine logic inside generic market-data contracts.

## Core-wide compatibility

The market-evidence layer is not limited to the seven Trader Midpoints
instruments. Provider-specific symbol discovery and capability mapping will be
implemented outside these provider-neutral contracts, allowing Core to retain
any canonical instrument exposed by an authorized provider.

Trader Midpoints remains native M5, while Core market observation covers every
currently supported cTrader trendbar period. A future provider may add
provider-qualified canonical periods through a later additive delivery; Trader
Midpoints itself remains non-configurable and M5-only.

Native versus QORE-aggregated bars remain separate provenance states. A later
aggregation service must never mark an aggregated bar as provider-native.

## Adversarial pre-review corrections

The initial exact head passed Ruff, Mypy, and Pytest/coverage, but pre-review
found two architectural defects that CI could not detect:

1. the timeframe catalog omitted valid current cTrader periods and used
   incomplete calendar aliases;
2. logical timestamp projections preserved arbitrary original UTC offsets,
   allowing equal instants to project differently.

Both are corrected before independent review. This is an explicit example of the
QORE rule:

`CI GREEN ALONE != ENGINEERING APPROVAL`.

## Gap disposition

This slice establishes the contract foundation for:

- `GAP-C` — typed BID/native OHLC provenance;
- `GAP-D` — field-level OHLC validity;
- `GAP-E` — exact minimum-price-increment provenance.

Those gaps are not closed until the provider, historical retention, replay, and
concrete evaluator paths actually consume and independently verify this
evidence.

`GAP-A`, `GAP-B`, `GAP-F`, `GAP-G`, `GAP-H`, `GAP-I`, `GAP-EXEC`, and
`GAP-LIN-001` remain implementation work for later authorized slices.

## Non-claims

This slice does not prove:

- live or historical cTrader Bid/Ask capture;
- native BID M5 provenance from any provider;
- complete tick chronology;
- true first-arrival ordering;
- wall-clock replay transitions;
- Trader Midpoints implementation;
- broker execution;
- calibration, OOS performance, profitability, or production readiness.
