# QORE-MARKET-DATA-INTEGRITY-CERTIFICATION-001 — Market Data Integrity & Candle Certification

## Status

**NON-PRODUCTION PROVIDER-NEUTRAL CERTIFICATION — PRODUCTION CLOSED**

Opening baseline:

```text
main @ 438d18c260486599fbcb2dbd64c012ce1e0615fd
```

This delivery implements Delivery 5 of the Futures & Hosting Reliability Certification Program.

It certifies the integrity of canonical closed OHLC data and introduces no provider SDK, market-data network client or trading action.

## Canonical types are reused

The repository already defines the provider-neutral market-data boundary in:

```text
src/qore/infrastructure/market_data.py
src/qore/infrastructure/ingestion.py
```

Delivery 5 therefore reuses:

- `Instrument`;
- `Timeframe`;
- `MarketDataSnapshotId`;
- `OhlcSnapshot`;
- `ExternalSourceDescriptor`.

It does not introduce a second Futures candle type.

`OhlcSnapshot` already enforces:

- explicit source identity;
- timezone-aware open/close timestamps;
- exact timeframe interval;
- positive finite OHLC values;
- `low <= high`;
- open within low/high;
- close within low/high.

Integrity certification composes around those existing invariants instead of duplicating them.

## Ingress evidence

`MarketDataIngressRecord` binds one canonical `OhlcSnapshot` to:

- Hosting receive timestamp;
- Core-ingress representation timestamp;
- normalization evidence reference.

The record preserves the source descriptor already embedded in the canonical snapshot.

A closed candle cannot claim arrival before its own close timestamp, and Core ingress observation cannot predate Hosting receipt.

Delivery delay is derived deterministically in integer microseconds.

## Integrity states

The canonical Delivery 5 vocabulary is:

```text
VALID
DELAYED
GAP_DETECTED
DUPLICATE
OUT_OF_ORDER
CORRUPTED
QUARANTINED
```

`QUARANTINED` is the evidence state of an explicit quarantine record; initial classification never skips directly to that state.

## Classification priority

Evaluation occurs against previously accepted contiguous history for one exact:

```text
SOURCE + INSTRUMENT + TIMEFRAME
```

The candidate is classified in this order:

1. same interval as latest accepted bar + same OHLC values -> `DUPLICATE`;
2. same interval + conflicting OHLC values -> `CORRUPTED`;
3. candidate opens before the expected next interval -> `OUT_OF_ORDER`;
4. candidate opens after the expected next interval -> `GAP_DETECTED`;
5. candidate is contiguous but exceeds certified delivery-delay policy -> `DELAYED`;
6. otherwise -> `VALID`.

For the first bar of a sequence, only freshness can be evaluated; continuity requires prior accepted evidence.

## Dispositions

States map to evidence handling:

```text
VALID
 -> ACCEPT

DELAYED
GAP_DETECTED
 -> DEGRADE

DUPLICATE
OUT_OF_ORDER
CORRUPTED
 -> QUARANTINE
```

Only `ACCEPT` is eligible for certified Core use.

A degraded bar remains preserved as evidence but does not receive a valid integrity certificate.

## Duplicate versus corruption

Two bars with the same source/instrument/timeframe and interval are treated differently:

```text
same OHLC values
 -> DUPLICATE

different OHLC values
 -> CORRUPTED / conflicting interval
```

This prevents a provider from silently revising a previously accepted candle without producing integrity evidence.

## Gap detection

For a canonical timeframe sequence:

```text
expected next open = previous closed_at
```

If the candidate opens later, the state is `GAP_DETECTED` and the assessment retains the exact expected timestamp.

The Lab does not fabricate the missing candle.

## Out-of-order detection

A candidate that overlaps or predates the latest accepted interval is `OUT_OF_ORDER` unless it matches that latest interval exactly, in which case duplicate/corruption classification takes precedence.

The record is quarantinable rather than silently reordered into accepted history.

## Freshness

`MarketDataIntegrityPolicy` defines a provider-neutral maximum delivery delay using the same deterministic `HostingLatencyDuration` used by Hosting reliability contracts.

The threshold is policy data, not a hard-coded universal number.

A contiguous but late bar becomes `DELAYED` and is not certified.

Provider-specific deliveries may calibrate freshness using actual feed evidence; they may not silently reinterpret a delayed bar as realtime.

## Integrity certificate

`MarketDataIntegrityCertificate` is:

```text
CERTIFIED
```

only when its exact assessment state is:

```text
VALID
```

All anomaly states produce:

```text
NOT_CERTIFIED
```

with the underlying state, timestamps, source identity, expected interval and evidence retained.

## Quarantine

`quarantine_market_data_assessment(...)` is valid only for assessments whose disposition is `QUARANTINE`.

The resulting `MarketDataQuarantineRecord` binds:

- quarantine identity;
- `QUARANTINED` state;
- original anomaly state;
- assessment identity;
- the exact original canonical snapshot;
- timestamp;
- evidence reference.

It intentionally exposes no replacement snapshot, repair function or synthetic candle.

```text
DETECT -> CLASSIFY -> PRESERVE -> QUARANTINE
```

never:

```text
DETECT -> SILENTLY REWRITE CANDLE
```

## Source identity / provider disagreement

Delivery 5 evaluates one provider/source sequence at a time. Accepted history and candidate must share exact source/instrument/timeframe scope.

This is deliberate: provider disagreement is a separate cross-provider question and is reserved for Delivery 12.

One provider's candle cannot overwrite another provider's evidence inside this integrity boundary.

## Trades and volume

The current canonical `OhlcSnapshot` does not contain trade-count or volume fields.

Delivery 5 therefore does not invent provider-neutral volume semantics that the repository has not yet authorized.

Provider-specific Futures Market Data Certification must validate trades and volume **when available** and must preserve them through a future canonical contract before those values can participate in cross-provider certification.

This is an explicit scope boundary, not a claim that volume is irrelevant.

## Reliability authority

Integrity classification is evidence, not infrastructure authority:

```text
MARKET DATA ANOMALY != SERVER FAILOVER AUTHORITY
```

A gap, delayed candle or conflicting bar may later feed Reliability Incident evidence. It does not directly:

- switch server;
- switch provider;
- acquire/revoke a lease;
- fence a runtime;
- submit/retry/redispatch an order.

The governing infrastructure rule remains:

```text
NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION
```

## Trading authority

No market-data certificate creates a trading decision.

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

The module exposes no BUY/SELL, risk, sizing, order submission, retry or strategic-close authority.

## Files

```text
src/qore/infrastructure/market_data_integrity.py
tests/infrastructure/test_market_data_integrity.py
docs/architecture/QORE-MARKET-DATA-INTEGRITY-CERTIFICATION-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
