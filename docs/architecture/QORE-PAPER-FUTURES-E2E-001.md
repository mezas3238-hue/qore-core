# QORE-PAPER-FUTURES-E2E-001 — Paper Futures Execution E2E

## Status

**DETERMINISTIC NON-PRODUCTION E2E — PRODUCTION CLOSED**

This delivery implements Delivery 16 of the canonical Futures & Hosting Reliability Certification Program.

It composes already-merged contracts and adds only a deterministic aggregate certification boundary. It does not introduce a provider client or a new execution authority.

## Purpose

The E2E proves the repository-level execution genealogy:

```text
CORE DECISION
 -> CANONICAL FUTURES EXECUTION REQUEST
 -> CURRENT HOSTING WRITER AUTHORITY
 -> CERTIFIED PROVIDER ADAPTER TRANSLATION
 -> PAPER / SIMULATION ORDER INTENT
 -> ACK / PARTIAL FILL / FILL / REJECT / AMBIGUOUS EVIDENCE
 -> RECONCILIATION
```

The tests are deterministic and offline. They do not claim an authenticated broker session, a real broker ACK, a real paper fill or operational provider evidence that did not actually occur.

## Aggregate prerequisite certificate

`FuturesPaperE2EPrerequisiteSnapshot` requires previously established evidence before the aggregate Paper E2E may certify:

- Shadow Futures Core is certified;
- Hosting Reliability Drill is certified offline;
- Three-Provider Cross-Certification is either fully certified or explicitly delay-aware certified.

The aggregate boundary does not create those facts; it only requires their canonical certification states.

## Mandatory three-provider matrix

The aggregate certificate covers the three mandatory Futures providers and their certified non-production execution environments:

```text
TradeStation -> SIMULATION
IBKR         -> PAPER
tastytrade   -> SIMULATION
```

For every provider, exactly three deterministic cases are required:

```text
PARTIAL_FILL_THEN_FILL
REJECTED
LOST_ACK_RECONCILED
```

Therefore a complete report contains exactly nine provider/scenario cases.

Every case carries a unique `DecisionId` and `FuturesExecutionRequestId`, and final reconciliation must be `MATCHED` before the case can be considered complete.

## Representative IBKR PAPER path

The executable composition test uses the merged IBKR certification adapter because its canonical delivery maps:

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
- explicit non-production environment.

The representative E2E binds the request to a resolved approved `FunctionalDecision` and to an exact current-writer attestation.

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

The representative E2E injects an `UNKNOWN` provider execution event.

It must normalize to:

```text
AMBIGUOUS
```

and an unknown provider reconciliation state must normalize to:

```text
FuturesExecutionReconciliationStatus.AMBIGUOUS
```

The same request is classified as already known by the canonical replay classifier. No second order is generated.

At the aggregate-certificate level, the `LOST_ACK_RECONCILED` case requires the ambiguous observation to be followed by final `MATCHED` reconciliation. Until that reconciliation exists, certification is rejected.

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

## Negative authority assertions

Every aggregate `FuturesPaperE2ECaseResult` requires:

```text
network_io_performed = false
production_execution_performed = false
automatic_redispatch_triggered = false
```

Any attempt to claim one of those actions fails contract construction.

The aggregate report likewise exposes zero network orders, zero Production orders and zero automatic redispatches.

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

This E2E contains no token, password, Authorization header, bearer value, productive account code or API client session.

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
src/qore/infrastructure/futures_paper_e2e.py
tests/infrastructure/test_paper_futures_e2e.py
docs/architecture/QORE-PAPER-FUTURES-E2E-001.md
```

The source file is an aggregate evidence/certification contract only. It performs no provider mutation and grants no execution authority.

## Quality Gate

The exact PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Production remains CLOSED.