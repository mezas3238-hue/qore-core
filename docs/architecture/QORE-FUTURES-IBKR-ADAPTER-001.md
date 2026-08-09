# QORE-FUTURES-IBKR-ADAPTER-001 — IBKR Futures Certification Adapter

## Status

**NON-PRODUCTION PAPER CERTIFICATION ADAPTER — PRODUCTION CLOSED**

This delivery implements Delivery 10 of the Futures & Hosting Reliability Certification Program.

It reuses `QORE-FUTURES-ADAPTER-CONTRACTS-001` and adds a deterministic IBKR-specific translation layer. It introduces no TWS client, IB Gateway client, Web API client, network connection, productive account identifier or credential value.

## Official capability revalidation

IBKR official documentation was revalidated on 2026-08-09 before implementation.

Current official documentation confirms:

- Web API and TWS API expose market-data and trading interfaces;
- paper accounts can use IBKR APIs subject to simulator-specific differences/limitations;
- individual Web API paper use depends on an associated live account being fully open and funded;
- market-data access depends on relevant subscriptions, permissions and session state;
- live market-data entitlements may be shared from a live username to an associated paper user subject to IBKR rules;
- current Web API documentation/changelog describes bounded market-data websocket subscriptions that require market-data resubscription for continuity.

These are external operational gates, not assumptions or authority inside Core.

Official references:

```text
https://ibkrcampus.com/campus/ibkr-api-page/getting-started/
https://ibkrcampus.com/campus/ibkr-api-page/webapi-doc/
https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/
https://ibkrcampus.com/campus/ibkr-api-page/market-data-subscriptions/
```

Provider requirements are mutable and must be revalidated before any authenticated operational certification.

## Paper only

IBKR execution translation accepts only:

```text
FuturesExecutionEnvironment.PAPER
```

A canonical `SIMULATION` request is not silently routed to IBKR paper.

There is no IBKR Live/Production execution selector in this adapter.

## Profile / secrets

`validate_ibkr_profile(...)` requires:

- provider name `ibkr`;
- Market Data capability;
- Execution capability;
- at least one opaque canonical `SecretRef`.

No username, account code, password, token, Authorization header or session secret is stored.

`IBKRPaperAccountReference` is a QORE-side opaque UUID and is deliberately not a real IBKR account code.

## Contract identity

IBKR uses a provider-specific numeric contract identity (`conid`).

Delivery 10 keeps it outside canonical QORE instrument semantics through:

```text
IBKRContractId
 -> FuturesContractMapping.provider_contract_id
 -> canonical QORE Instrument
```

Every incoming payload contract ID must match the exact mapping provider contract ID.

## Market-data entitlement state is preserved

IBKR access can yield different market-data modes depending on external entitlements/session conditions.

The adapter therefore preserves:

```text
REALTIME
DELAYED
UNKNOWN
```

through `IBKRNormalizedQuote`, `IBKRNormalizedTrade` and `IBKRNormalizedBar`.

A normalized observation is realtime-certifiable only when the explicit mode is `REALTIME`.

```text
API REACHABLE != REALTIME MARKET DATA CERTIFIED
```

Delayed/unknown evidence is preserved rather than silently relabeled as realtime.

## Market-data continuity versus order retry

The adapter models market-data continuity independently from execution:

```text
ACTIVE
RESUBSCRIPTION_REQUIRED
BLOCKED
```

A provider-ended market-data stream may produce:

```text
RESUBSCRIPTION_REQUIRED
```

This is a feed-continuity classification only. It is not an order action and does not authorize order replay.

```text
MARKET DATA RESUBSCRIPTION != ORDER RETRY
```

Unauthorized or unknown session state fails closed as `BLOCKED`.

## Market Data translation

The adapter provides deterministic IBKR payload contracts for:

- quote;
- trade;
- closed bar.

Each preserves:

- provider contract identity;
- explicit realtime/delayed/unknown mode;
- provider timestamp/interval;
- QORE receive timestamp;
- prices/contract quantity.

Normalization produces the provider-neutral Delivery 8 observations while retaining the IBKR data-mode wrapper for certification.

## Paper execution translation

`translate_ibkr_paper_order(...)` accepts only a valid canonical `FuturesExecutionRequest`.

The request already binds:

- Core `DecisionId`;
- account/runtime;
- current Hosting writer attestation;
- upstream-selected side;
- upstream-selected quantity;
- order type/prices;
- idempotency key;
- PAPER environment.

The adapter maps:

```text
BUY  -> BUY
SELL -> SELL

MARKET -> MKT
LIMIT  -> LMT
STOP   -> STP

DAY -> DAY
GTC -> GTC
```

The canonical idempotency UUID becomes the provider-side paper order reference in the deterministic intent.

The adapter does not send the order.

## Execution events

Provider-side evidence normalizes into Delivery 8 states:

```text
ACKNOWLEDGED -> ACKNOWLEDGED
REJECTED     -> REJECTED
PARTIAL_FILL -> PARTIALLY_FILLED
FILL         -> FILLED
UNKNOWN      -> AMBIGUOUS
```

The canonical Delivery 8 validator enforces request identity, chronology and fill bounds.

## Reconciliation

IBKR reconciliation maps:

```text
MATCHED  -> MATCHED
DIVERGED -> DIVERGED
UNKNOWN  -> AMBIGUOUS
```

Unknown order state never authorizes retransmission.

```text
AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE
```

not:

```text
AMBIGUITY -> RETRY ORDER
```

## Paper simulator limitations

IBKR paper trading is a simulator and can differ from live behavior. This delivery therefore does not claim live execution equivalence merely because a paper translation passes deterministic tests.

Operational certification must record the actual paper environment, market-data permissions and provider limitations when real authenticated evidence becomes available.

## Operational evidence boundary

This delivery is deterministic/offline.

It does not claim:

- authenticated Web API/TWS/IB Gateway connectivity;
- a funded/approved account prerequisite has been satisfied;
- market-data subscriptions exist;
- realtime Futures data was received;
- an IBKR paper order was actually submitted.

No such evidence is fabricated.

## Authority exclusions

The adapter exposes no API for:

- TWS/Web API/IB Gateway network calls;
- Production execution;
- automatic order retry/redispatch;
- Core Decision creation;
- risk/size/SL/TP/trailing mutation;
- strategic close;
- server failover;
- lease/fencing mutation.

## Files

```text
src/qore/infrastructure/futures_ibkr_adapter.py
tests/infrastructure/test_futures_ibkr_adapter.py
docs/architecture/QORE-FUTURES-IBKR-ADAPTER-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
