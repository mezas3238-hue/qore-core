# QORE-EXECUTIVE-QUERY-DISPATCH-001 — Governed Query Dispatch

Status: **MISSION-04 DELIVERY 6 — AUTHORIZED EXECUTIVE READ DISPATCH**

## Purpose

Dispatch an already-authorized executive read through the existing `ExecutiveReadQueryPort` exactly once and return only the canonical `ExecutiveReadDelivery` that is bound to that exact authorization.

This delivery does not authorize reads and does not define new read-model schemas.

## Input boundary

`ExecutiveQueryDispatcher.dispatch()` accepts only:

```text
AuthorizedExecutiveReadRequest
```

Raw `ExecutiveReadRequest` values must first pass through `ExecutiveRequestGuard`.

## Downstream boundary

The dispatcher reuses the existing repository contract:

```text
ExecutiveReadQueryPort.read(
    AuthorizedExecutiveReadRequest
) -> Result[ExecutiveReadDelivery, ExecutivePortError]
```

No second query port, projection wrapper or receipt type is introduced.

## Exactly-once query attempt

One dispatcher invocation performs at most one downstream `read()` call.

There is no hidden retry, sleep, scheduler, thread or automatic second query.

## Delivery binding

The existing `ExecutiveReadDelivery` already enforces the detailed relationships among:

- authorized request;
- projection scope and timestamp;
- served receipt;
- principal;
- authority version;
- correlation ID;
- receipt chronology.

The dispatcher additionally requires that `delivery.authorized_request` equals the exact authorized request supplied to `dispatch()`.

A correctly structured delivery for a different request is therefore rejected rather than accidentally crossing request boundaries.

## Sanitized failures

Arbitrary downstream exception text is never propagated.

Dispatch failures use the closed reason set:

- `downstream-failed`;
- `delivery-invalid`;
- `delivery-mismatch`;
- `receipt-unsafe`.

## Receipt safety

Before returning a delivery, the dispatcher checks the served receipt for obvious secret-bearing fragments in:

- `reason_code`;
- evidence references.

Unsafe receipt evidence fails closed even if the underlying object is structurally valid.

The dispatcher does not inspect or expose private internal model state; it returns only the already-established `ExecutiveReadProjection` boundary contained by `ExecutiveReadDelivery`.

## Read models remain canonical

MISSION-04 reuses the executive projection system already delivered for:

- System Health;
- CIBO State;
- Markets;
- Traders;
- Validation Lab;
- Trade Forensics;
- Audit;
- Portfolio;
- Risk;
- Capital State;
- CEO Accounts;
- Governance;
- Corporate Profit Vault.

No provider object, broker object or internal Core object is added to this query surface.

## No mutation

Query dispatch is read-only.

It cannot:

- mutate governance state;
- pause/resume/restrict anything;
- submit trades;
- call a broker/provider;
- access credentials.

## Relationship to Delivery 8

`ExecutiveReadDelivery` contains an audit-safe served receipt and evidence refs, but durable audit append/read persistence remains Delivery 8.

## Provider independence

No OANDA/broker/provider dependency or MISSION-03 operational evidence is introduced.

MISSION-03 remains operationally blocked at Gate #5 until OANDA Practice account/token provisioning exists.

## Safety

This delivery introduces no:

- Production authority;
- real capital;
- direct trading controls;
- Risk bypass;
- credentials;
- provider client;
- automatic retry;
- implicit runtime clock;
- background scheduler/thread;
- network/API server.

## Tests

The delivery proves:

- one authorized read produces exactly one query-port call;
- the exact canonical delivery is preserved;
- downstream failure is sanitized and not retried;
- a valid delivery for a different authorization is rejected;
- secret-like served-receipt reason/evidence data is rejected.

## Quality Gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or weakened gate is permitted.

## Next delivery

After merge, continue directly with:

```text
QORE-EXECUTIVE-GOVERNANCE-MUTATION-001
```
