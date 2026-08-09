# QORE-FUTURES-TRADESTATION-ADAPTER-001 — TradeStation Futures Certification Adapter

## Status

**NON-PRODUCTION SIM CERTIFICATION ADAPTER — PRODUCTION CLOSED**

This delivery implements Delivery 9 of the Futures & Hosting Reliability Certification Program.

It reuses `QORE-FUTURES-ADAPTER-CONTRACTS-001` and adds a deterministic TradeStation-specific translation layer. It does not create an HTTP client, OAuth client, live-order sender, productive account binding or secret value.

## Official capability revalidation

TradeStation official API documentation was revalidated on 2026-08-09 before implementation.

Current official documentation confirms:

- API v3 supports Futures;
- market-data bars and brokerage/order surfaces exist;
- authenticated requests use bearer-token authorization;
- a separate SIM API exists for paper trading with simulated accounts/money;
- SIM uses a distinct base URL from Live.

External capability/access remains mutable and must be revalidated again before any authenticated operational certification.

Official references:

```text
https://api.tradestation.com/docs/
https://api.tradestation.com/docs/specification/
https://api.tradestation.com/docs/fundamentals/authentication/auth-overview/
https://api.tradestation.com/docs/fundamentals/sim-vs-live/
```

## No Live selector

This delivery intentionally exposes no TradeStation Live/Production environment type.

The only execution translation accepted is from the canonical:

```text
FuturesExecutionEnvironment.SIMULATION
```

A canonical `PAPER` request is not silently rerouted to TradeStation SIM. Environment translation must be explicit.

## Profile / secrets

`validate_tradestation_profile(...)` requires:

- canonical provider name `tradestation`;
- Market Data capability;
- Execution capability;
- at least one opaque canonical `SecretRef`.

The adapter never resolves that secret reference and stores no access token, refresh token, password, Authorization header or real provider account ID.

`TradeStationSimAccountReference` is a QORE-side opaque UUID reference, not a TradeStation account number.

## Instrument mapping

Provider symbols remain provider-side values.

Example conceptual mapping:

```text
TradeStation provider symbol
 -> FuturesContractMapping
 -> canonical QORE Instrument
```

Every payload symbol must match the exact provider contract ID in its mapping. A payload cannot be normalized under an unrelated contract mapping.

## Market Data translation

The adapter defines deterministic provider payloads for:

- quote;
- trade;
- closed bar.

Each preserves:

- provider symbol;
- provider timestamp/interval;
- QORE receive timestamp;
- raw price/size facts.

Normalization produces Delivery 8 provider-neutral observations. Those can then enter the canonical QORE quote/OHLC and integrity-certification boundaries.

No provider-specific candle type leaks into Core.

## SIM execution translation

`translate_tradestation_sim_order(...)` accepts only an already-valid `FuturesExecutionRequest`.

Therefore the input already contains:

- Core `DecisionId`;
- exact account/runtime;
- current Hosting writer attestation;
- side selected upstream;
- quantity selected upstream;
- order type/prices;
- idempotency key;
- SIMULATION environment.

The adapter translates those values into `TradeStationSimOrderIntent`.

It does not decide BUY/SELL, quantity, risk, SL/TP/trailing or strategic close.

Canonical mappings include:

```text
BUY  -> BUY
SELL -> SELL

MARKET -> Market
LIMIT  -> Limit
STOP   -> StopMarket

DAY -> DAY
GTC -> GTC
```

The canonical idempotency UUID becomes the SIM client-order identity. This is deterministic translation, not a retry mechanism.

## Execution event normalization

TradeStation-side evidence normalizes into the provider-neutral Delivery 8 states:

```text
ACKNOWLEDGED -> ACKNOWLEDGED
REJECTED     -> REJECTED
PARTIAL_FILL -> PARTIALLY_FILLED
FILL         -> FILLED
UNKNOWN      -> AMBIGUOUS
```

The canonical observation validator then verifies:

- exact request identity;
- chronology;
- cumulative fill does not exceed requested contracts;
- `FILLED` equals requested quantity;
- partial fill remains below requested quantity.

## Ambiguity / reconciliation

Unknown provider state becomes:

```text
AMBIGUOUS
```

never:

```text
RETRY ORDER
REDISPATCH
RESEND
```

TradeStation reconciliation maps:

```text
MATCHED  -> MATCHED
DIVERGED -> DIVERGED
UNKNOWN  -> AMBIGUOUS
```

The program-wide rule remains:

```text
AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE
```

## Operational evidence boundary

This delivery proves deterministic adapter behavior offline.

It does **not** claim that an authenticated TradeStation SIM session was executed from GitHub Actions, because no operational provider credential/evidence is fabricated here.

A future authenticated certification run, if authorized and credentials exist, must use external secret resolution and sanitized evidence only.

## Authority exclusions

The adapter exposes no API for:

- HTTP/WebSocket provider mutation;
- OAuth token acquisition;
- Live/Production order submission;
- automatic retry/redispatch;
- Core Decision creation;
- strategy/risk mutation;
- server failover;
- lease/fencing mutation.

## Files

```text
src/qore/infrastructure/futures_tradestation_adapter.py
tests/infrastructure/test_futures_tradestation_adapter.py
docs/architecture/QORE-FUTURES-TRADESTATION-ADAPTER-001.md
```

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.
