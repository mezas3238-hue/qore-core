# QORE-FUTURES-ADAPTER-CONTRACTS-001 — Provider-Neutral Futures Adapter Contracts

## Status

**NON-PRODUCTION CONTRACT DELIVERY — PRODUCTION CLOSED**

This delivery implements Delivery 8 of the Futures & Hosting Reliability Certification Program.

It defines the shared translation/certification boundary that TradeStation, IBKR and tastytrade adapters must reuse. It introduces no provider SDK, network client, broker credential or real-capital path.

## Strategic authority

The governing invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

`FuturesExecutionRequest` therefore requires both:

- canonical `DecisionId`;
- canonical `HostingExecutionAuthorityAttestation` for the exact account/runtime writer.

The adapter does not create either one.

BUY/SELL exists only as an upstream-supplied order side inside an already-authorized execution request. The adapter may translate it; it may not decide it.

## Provider architecture

The allowed architecture remains:

```text
BROKER/API
 -> CERTIFIED PROVIDER ADAPTER
 -> PROVIDER-NEUTRAL FUTURES CONTRACTS
 -> HOSTING / CANONICAL QORE BOUNDARIES
 -> CORE
```

Never:

```text
CORE -> CONCRETE BROKER SDK
```

## Canonical identities reused

This delivery reuses existing repository types rather than creating provider-specific Core identities:

- `AdapterId`;
- `ExternalSourceDescriptor`;
- `TradingAccountId`;
- `ExecutionRuntimeReference`;
- `DecisionId`;
- `HostingExecutionAuthorityAttestation`;
- `Instrument`;
- `Timeframe`;
- `QuoteSnapshot`;
- `OhlcSnapshot`;
- `SecretRef`.

## Adapter profile and secrets

`FuturesAdapterProfile` binds:

- adapter identity;
- provider name;
- market-data source;
- execution source;
- declared capabilities;
- immutable `SecretRef` tuple.

No secret value, password, bearer token, Authorization header or provider account credential is stored.

## Instrument mapping

`FuturesContractMapping` maps one provider contract identifier to one canonical QORE `Instrument`.

Provider symbols remain outside Core semantics. Provider-specific deliveries may parse their own contract IDs, but the canonical QORE side sees only the mapped `Instrument`.

## Market Data Certification surface

Provider-specific adapters may emit provider-neutral observations for:

- quotes;
- trades;
- closed OHLC bars.

Every observation preserves:

- provider contract mapping;
- source identity;
- provider timestamp;
- QORE receipt timestamp where applicable.

Quote and bar observations can be normalized into the existing canonical `QuoteSnapshot` and `OhlcSnapshot` contracts.

Trade observations remain provider-neutral evidence because the repository does not yet expose a canonical trade-tape domain type. Provider-specific deliveries must not invent a broker-specific Core trade object.

## Execution environment

The only execution environments are:

```text
PAPER
SIMULATION
```

There is deliberately no Production execution enum/value.

Shadow/Read-only work remains non-executable and outside this request type.

## Execution request

`FuturesExecutionRequest` binds:

- explicit request ID;
- account/runtime;
- Core `DecisionId`;
- current infrastructure writer attestation;
- PAPER/SIMULATION environment;
- canonical instrument mapping;
- upstream-supplied side;
- positive contract quantity;
- market/limit/stop order type;
- time in force;
- exact order-price shape;
- idempotency key;
- request timestamp.

The writer attestation account/runtime must exactly match the request scope.

The request is a translation input. It is not authority to create a second strategy decision.

## Idempotency and duplicate protection

`classify_futures_request_replay(...)` is observational only.

States:

```text
NEW_REQUEST_UNSEEN
DUPLICATE_ALREADY_KNOWN
IDEMPOTENCY_CONFLICT
```

There is no:

```text
RETRY
RESEND
REDISPATCH
```

A duplicate or conflict is evidence for containment/reconciliation, never permission to transmit another order.

## Execution observations

Provider-specific adapters normalize broker events into:

```text
ACKNOWLEDGED
REJECTED
PARTIALLY_FILLED
FILLED
AMBIGUOUS
```

The observation validator checks exact request identity, chronology and cumulative fill bounds.

`AMBIGUOUS` is a valid evidence state. It never implies retry.

## Reconciliation

Provider execution reconciliation uses:

```text
MATCHED
DIVERGED
AMBIGUOUS
```

The repository rule remains:

```text
AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE
```

not:

```text
AMBIGUITY -> RETRY ORDER
```

## Provider-specific delivery requirements

TradeStation, IBKR and tastytrade adapters must reuse these exact contracts and prove independently:

### Market Data

- contract mapping;
- provider timestamp preservation;
- quote/trade/bar translation;
- source identity;
- delayed/stale classification;
- reconnect evidence;
- candle integrity;
- ingress timing.

### Execution

- PAPER/SIM only;
- Core Decision genealogy;
- exact writer attestation;
- deterministic translation;
- ACK/reject/fill/partial-fill handling;
- idempotency protection;
- ambiguous ACK containment;
- reconciliation;
- egress/round-trip timing.

## Authority exclusions

These contracts expose no API to:

- create a Core Decision;
- invent BUY/SELL;
- mutate risk/size/SL/TP/trailing;
- strategically close a position;
- switch server;
- acquire/revoke leases;
- call a provider SDK;
- automatically retry/redispatch an order.

## Files

```text
src/qore/infrastructure/futures_adapter_contracts.py
tests/infrastructure/test_futures_adapter_contracts.py
docs/architecture/QORE-FUTURES-ADAPTER-CONTRACTS-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
