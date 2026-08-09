# QORE-FUTURES-TRADOVATE-CANDIDATE-001 — Tradovate/NinjaTrader Candidate Evaluation

## Status

**OPTIONAL CANDIDATE — DETERMINISTIC/OFFLINE ONLY — OPERATIONAL EVIDENCE REQUIRED**

This delivery implements the optional position 13 already defined by the canonical Futures & Hosting Reliability roadmap.

It does **not** reopen or weaken the completed mandatory Futures/Hosting Reliability certification path. TradeStation, IBKR and tastytrade remain the mandatory three-provider minimum.

It does **not** authorize Production, real capital, LIVE Tradovate execution, productive credentials, productive failover or any direct broker API inside Core.

## Purpose

Evaluate whether the Tradovate/NinjaTrader Partner API shape can remain behind the existing provider-neutral Futures contracts without changing QORE strategic authority.

Canonical invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

The candidate adapter may only translate an already-authorized `FuturesExecutionRequest`. It cannot create direction, size, risk, SL, TP, trailing, strategic close or a Core Decision.

## Official provider verification — 2026-08-09

Official Tradovate/NinjaTrader Partner API documentation was re-checked when this candidate delivery began.

The official documentation currently describes:

- separate DEMO and LIVE domains;
- DEMO as simulated trading;
- a dedicated market-data WebSocket service;
- market-data requests for quotes, DOM, charts and histograms;
- authenticated access-token/WebSocket flows;
- an order endpoint on the DEMO domain;
- order actions including `Buy` / `Sell`;
- order types including `Market`, `Limit` and `Stop`;
- time-in-force values including `Day` and `GTC`;
- a `clOrdId` field suitable for preserving an upstream client/idempotency identity;
- an `isAutomated` field which official guidance requires for automated orders.

Official references checked:

```text
https://partner.tradovate.com/overview/welcome/introduction-to-tradovate-partner-api
https://partner.tradovate.com/resources/reference/environments
https://partner.tradovate.com/overview/core-concepts/web-sockets/market-data/market-data
https://partner.tradovate.com/overview/core-concepts/web-sockets/market-data/market-data-request-reference
https://partner.tradovate.com/api/rest-api-endpoints/orders/place-order
https://partner.tradovate.com/overview/quick-setup/auth-overview
https://partner.tradovate.com/resources/reference/best-practices
```

Provider documentation, account prerequisites, entitlements, API policies and endpoint behavior are mutable external facts. They must be revalidated before any authenticated operational certification.

## Implemented repository boundary

Source:

```text
src/qore/infrastructure/futures_tradovate_candidate.py
```

Tests:

```text
tests/infrastructure/test_futures_tradovate_candidate.py
```

The candidate boundary provides:

- canonical provider identity `tradovate`;
- profile validation requiring market-data + execution capabilities;
- opaque `SecretRef` only;
- deterministic quote/trade/bar payload normalization;
- exact provider-symbol mapping checks;
- deterministic DEMO/SIMULATION order-intent translation;
- canonical idempotency preservation through `client_order_id`;
- mandatory `is_automated=True` on translated automated intent;
- explicit candidate assessment state that still requires operational evidence.

## Candidate assessment

The deterministic repository verdict is intentionally limited to:

```text
provider                       = tradovate
DEMO simulation shape          = supported by official docs
market-data WebSocket shape    = supported by official docs
authenticated operational run  = false
network IO performed           = false
Production authorized          = false
status                         = OPERATIONAL_EVIDENCE_REQUIRED
```

This is not a claim that QORE has authenticated to Tradovate, subscribed to a live feed, submitted a DEMO order, received an exchange/simulator ACK or reconciled an actual Tradovate order.

## Execution authority preservation

Input remains the canonical already-authorized request:

```text
FuturesExecutionRequest
  -> DecisionId
  -> HostingExecutionAuthorityAttestation
  -> provider mapping
  -> side
  -> quantity
  -> order type
  -> time in force
  -> idempotency key
```

The candidate translation produces only an in-memory `TradovateDemoOrderIntent`.

No network send occurs.

The mapping is mechanical:

```text
BUY  -> Buy
SELL -> Sell

MARKET -> Market
LIMIT  -> Limit
STOP   -> Stop

DAY -> Day
GTC -> GTC

QORE idempotency UUID -> candidate client_order_id
is_automated          -> true
```

`PAPER` is rejected instead of being silently rerouted to Tradovate DEMO. The candidate accepts only canonical `SIMULATION` requests.

## Market-data boundary

Quote, trade and bar evidence is converted only after exact provider-contract mapping validation.

The candidate preserves:

- canonical provider mapping;
- source identity;
- provider timestamp;
- receipt timestamp;
- bid/ask invariants;
- trade price/quantity invariants;
- OHLC invariants;
- exact bar timeframe validation through existing provider-neutral contracts.

No provider payload object enters Core.

## Secrets

Only opaque canonical `SecretRef` values may appear in repository configuration.

The candidate module and tests contain no:

- access token;
- password;
- API key value;
- bearer value;
- real account identifier;
- Authorization header.

A `TradovateDemoAccountReference` is an opaque QORE UUID and is explicitly not a real Tradovate account ID.

## Network / LIVE boundary

The candidate implementation contains no network transport and no LIVE/Production selector.

It does not expose:

```text
submit_order
send_order
retry_order
redispatch
http_client
websocket_client
```

The existing provider-neutral `FuturesExecutionEnvironment` remains limited to:

```text
PAPER
SIMULATION
```

## Operational evidence gate

If this optional candidate is later promoted from offline evaluation to operational certification, a separate explicit repository delivery must first define its operational evidence contract.

At minimum that future gate would need to independently verify, without committing secret values:

- approved Tradovate/NinjaTrader API access;
- exact account/API prerequisites applicable at that time;
- required market-data entitlements;
- authentication and token handling behind secret resolution;
- DEMO-only market-data connectivity;
- provider timestamp/source preservation;
- sanitized market-data evidence;
- DEMO-only order submission derived from a valid canonical Core Decision;
- ACK/reject/partial/fill normalization;
- lost/unknown ACK containment;
- reconciliation before any subsequent action;
- no duplicate redispatch;
- no credential leakage.

Until that future delivery exists and passes, this candidate remains:

```text
OPERATIONAL EVIDENCE REQUIRED
```

## Relationship to issue #146

MISSION-03 issue #146 — OANDA Practice operational evidence — remains independent and OPEN/BLOCKED until its own authenticated evidence criteria pass.

This optional Tradovate candidate neither substitutes for OANDA evidence nor consumes it.

## Production boundary

After this delivery:

```text
Mandatory three-provider Futures program = COMPLETED
Tradovate optional candidate              = OFFLINE EVALUATED
Tradovate operational certification       = NOT COMPLETED
Tradovate LIVE execution                  = CLOSED
Production                                = CLOSED
Real capital                              = CLOSED
```

## Quality Gate

The unchanged repository gate remains mandatory:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No test, typing guarantee, safety invariant or coverage expectation may be weakened to make this optional candidate pass.
