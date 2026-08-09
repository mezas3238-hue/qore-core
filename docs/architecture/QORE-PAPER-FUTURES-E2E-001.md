# QORE-PAPER-FUTURES-E2E-001 — Paper Futures Execution E2E

## Status

**DETERMINISTIC NON-PRODUCTION E2E — PRODUCTION CLOSED**

This delivery implements Delivery 16 of the canonical Futures & Hosting Reliability Certification Program.

It composes already-merged contracts rather than introducing a new provider client or execution authority.

## Purpose

The E2E proves the repository-level execution genealogy:

```text
CORE DECISION
 -> CANONICAL FUTURES EXECUTION REQUEST
 -> CURRENT HOSTING WRITER AUTHORITY
 -> CERTIFIED PROVIDER ADAPTER TRANSLATION
 -> PAPER ORDER INTENT
 -> ACK / PARTIAL FILL / FILL / REJECT / AMBIGUOUS EVIDENCE
 -> RECONCILIATION
```

The test is deterministic and offline. It does not claim an authenticated IBKR session, a real broker ACK, a real paper fill or operational provider certification beyond the provider-specific evidence already represented by the repository contracts.

## Representative PAPER path

The executable E2E uses the merged IBKR certification adapter because its canonical delivery maps:

```text
FuturesExecutionEnvironment.PAPER
 -> IBKRPaperOrderIntent
```

The provider-specific account reference is an opaque QORE UUID reference, not an IBKR account code, login or credential.

No network request is emitted by this delivery.

## Decision and authority genealogy

Every `FuturesExecutionRequest` is required by the canonical Delivery 8 contract to carry:

- `DecisionId`;
- `TradingAccountId`;
- `ExecutionRuntimeReference`;
- `HostingExecutionAuthorityAttestation`;
- provider-neutral contract mapping;
- exact side, quantity, order type and time-in-force;
- idempotency key;
- explicit `PAPER` environment.

The E2E binds the request to a resolved approved `FunctionalDecision` and to an exact current-writer attestation.

Therefore the adapter receives already-authorized intent; it does not invent BUY/SELL, quantity, risk, SL/TP, trailing or strategic close.

The governing invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

## Happy-path lifecycle

The deterministic paper path validates:

```text
PAPER REQUEST
 -> PROVIDER PAPER INTENT
 -> ACKNOWLEDGED
 -> PARTIALLY_FILLED
 -> FILLED
 -> MATCHED RECONCILIATION
```

The provider order intent preserves the canonical request ID and maps the canonical idempotency key to the provider order reference field used by the IBKR certification adapter.

Partial and full fills remain bounded by the original requested quantity.

## Ambiguous / lost-ACK path

The E2E separately injects an `UNKNOWN` provider execution event.

It must normalize to:

```text
AMBIGUOUS
```

and an unknown provider reconciliation state must normalize to:

```text
FuturesExecutionReconciliationStatus.AMBIGUOUS
```

The same request is then classified as already known by the canonical replay classifier.

No second order is generated.

The delivery explicitly checks that the relevant evidence/order-intent surfaces expose no retry or redispatch API.

The required rule remains:

```text
AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE
```

never:

```text
AMBIGUITY -> RETRY ORDER
```

## Rejection path

A provider rejection normalizes to canonical `REJECTED` evidence with zero fill.

A reject does not create a retry command, replacement request or strategic decision.

## Environment boundary

The canonical execution environment remains closed to:

```text
PAPER
SIMULATION
```

The E2E asserts that neither `LIVE` nor `PRODUCTION` exists in the execution enum.

This delivery does not enable real capital, productive credentials, productive account identifiers or a broker SDK/client.

## Secrets

No secret value is introduced.

Provider authentication remains behind previously defined `SecretRef` boundaries and external operational gates.

This E2E contains no:

- token;
- password;
- Authorization header;
- bearer value;
- productive account code;
- API client session.

## Scope exclusions

This delivery does not:

- add a provider SDK;
- perform network I/O;
- acquire/revoke Hosting leases;
- switch runtime/server/provider;
- create a Core Decision inside an adapter;
- retry or redispatch an order;
- authorize Production.

## Files

```text
tests/infrastructure/test_paper_futures_e2e.py
docs/architecture/QORE-PAPER-FUTURES-E2E-001.md
```

No new production source file is required because the E2E composes the already canonical Delivery 8/10 boundaries.

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.