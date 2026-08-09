# QORE-FUTURES-TASTYTRADE-ADAPTER-001 — tastytrade Futures Certification Adapter

## Status

**NON-PRODUCTION SANDBOX CERTIFICATION ADAPTER — PRODUCTION CLOSED**

This delivery implements Delivery 11 of the Futures & Hosting Reliability Certification Program.

It reuses `QORE-FUTURES-ADAPTER-CONTRACTS-001` and adds deterministic tastytrade sandbox translation. It introduces no HTTP client, DXLink client, session-token resolver, Production endpoint, provider account number or secret value.

## Official capability revalidation

Official tastytrade documentation was revalidated on 2026-08-09 before implementation.

Current official documentation confirms:

- Open API exposes Futures instruments and order surfaces;
- a separate sandbox environment is available for testing;
- sandbox trades, transactions, positions and balances reset every 24 hours;
- sandbox quotes are always 15 minutes delayed;
- Production and sandbox environments use different hosts/credentials;
- market data uses the quote-token / DXLink flow outside this deterministic adapter.

Official references:

```text
https://tastytrade.com/api/
https://developer.tastytrade.com/
https://developer.tastytrade.com/sandbox/
https://developer.tastytrade.com/open-api-spec/orders/
https://developer.tastytrade.com/open-api-spec/instruments/
https://developer.tastytrade.com/faq/
```

These provider facts are mutable and must be revalidated before any authenticated operational certification.

## Sandbox only

Execution translation accepts only:

```text
FuturesExecutionEnvironment.SIMULATION
```

A canonical `PAPER` request is not silently routed to the tastytrade sandbox.

There is no Production environment selector in this adapter.

## Profile / secrets

`validate_tastytrade_profile(...)` requires:

- canonical provider name `tastytrade`;
- Market Data capability;
- Execution capability;
- at least one opaque canonical `SecretRef`.

No login, password, account number, access token, Authorization header or DXLink quote token is stored.

`TastytradeSandboxAccountReference` is an opaque QORE UUID, not a tastytrade account number.

## Futures symbol mapping

Provider slash-prefixed Futures symbols remain behind `FuturesContractMapping`.

```text
tastytrade /ES...
 -> provider contract mapping
 -> canonical QORE Instrument
```

Each payload symbol must match the exact provider contract ID before normalization.

## Sandbox market-data truth

The adapter encodes the currently documented sandbox market-data boundary explicitly:

```text
DELAYED_15_MINUTES
UNKNOWN
```

and records the dated provider constant:

```text
TASTYTRADE_SANDBOX_QUOTE_DELAY_MINUTES = 15
```

No sandbox observation is allowed to claim realtime certification:

```text
SANDBOX DATA != REALTIME MARKET DATA CERTIFIED
```

This is deliberate. The future cross-provider certification must distinguish provider behavior rather than pretending all three provider test environments have identical latency/data rights.

## Market Data translation

The adapter provides deterministic sandbox payloads for:

- quote;
- trade;
- closed bar.

Normalization produces Delivery 8 provider-neutral observations while retaining the tastytrade sandbox data-mode wrapper.

The canonical source, provider timestamp/interval and receive timestamp remain visible to later integrity and cross-provider certification.

## Sandbox lifecycle / daily reset

Because the sandbox documentation states that trading state resets periodically, Delivery 11 models sandbox lifecycle independently:

```text
CURRENT
RESET_DETECTED
UNKNOWN
```

with dispositions:

```text
CURRENT        -> CONTINUE
RESET_DETECTED -> RECONCILE_SANDBOX_STATE
UNKNOWN        -> BLOCK
```

A reset never means:

```text
RETRY ORDER
REDISPATCH
RESEND
```

The sandbox state must be reconciled before relying on order/position history.

## Sandbox execution translation

`translate_tastytrade_sandbox_order(...)` accepts only a valid canonical `FuturesExecutionRequest`.

The request already binds:

- Core `DecisionId`;
- account/runtime;
- current Hosting writer attestation;
- upstream-selected side;
- upstream-selected quantity;
- order type/prices;
- idempotency key;
- SIMULATION environment.

The adapter maps:

```text
BUY  -> Buy
SELL -> Sell

MARKET -> Market
LIMIT  -> Limit
STOP   -> Stop

DAY -> Day
GTC -> GTC
```

The canonical idempotency UUID is preserved as deterministic client-order identity.

No API call occurs in this translation.

## Execution evidence

Sandbox execution evidence normalizes as:

```text
ACCEPTED     -> ACKNOWLEDGED
REJECTED     -> REJECTED
PARTIAL_FILL -> PARTIALLY_FILLED
FILL         -> FILLED
UNKNOWN      -> AMBIGUOUS
```

The Delivery 8 validator enforces request identity, chronology and fill bounds.

## Ambiguity / reconciliation

Reconciliation maps:

```text
MATCHED  -> MATCHED
DIVERGED -> DIVERGED
UNKNOWN  -> AMBIGUOUS
```

The program rule remains:

```text
AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE
```

Never:

```text
AMBIGUITY -> RETRY ORDER
```

## Operational evidence boundary

This delivery is deterministic/offline.

It does not claim:

- an authenticated sandbox session;
- a real sandbox account number;
- a DXLink market-data connection;
- a Futures sandbox order submission;
- realtime tastytrade sandbox market data.

No operational evidence is fabricated.

## Authority exclusions

The adapter exposes no API for:

- Production requests;
- HTTP/DXLink mutation;
- session-token acquisition;
- automatic order retry/redispatch;
- Core Decision creation;
- risk/size/SL/TP/trailing mutation;
- strategic close;
- server failover;
- lease/fencing mutation.

## Files

```text
src/qore/infrastructure/futures_tastytrade_adapter.py
tests/infrastructure/test_futures_tastytrade_adapter.py
docs/architecture/QORE-FUTURES-TASTYTRADE-ADAPTER-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
