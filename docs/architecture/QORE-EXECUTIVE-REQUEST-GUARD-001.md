# QORE-EXECUTIVE-REQUEST-GUARD-001 — Unified Executive Request Guard

Status: **MISSION-04 DELIVERY 4 — FAIL-CLOSED AUTHORIZATION COMPOSITION**

## Purpose

Compose the already-established authentication assertion, current authority source and canonical executive authorization functions into one protected entry point for executive commands and reads.

This delivery adds no new executive capability and no transport server.

## Mandatory chain

```text
AuthenticatedExecutivePrincipal
  → assertion currency evaluation
  → principal/correlation binding
  → ExecutiveAuthorityStateRequest
  → ExecutiveAuthorityStateSource.read_current()
  → exact response/request binding
  → ACTIVE current authority
  → existing authorize_executive_* function
  → AuthorizedExecutiveControlIntent / AuthorizedExecutiveReadRequest
```

Any missing, stale, contradictory or failed link produces no authorized request.

## No duplicated permission rules

`ExecutiveRequestGuard` does not reimplement action or read-scope allowlists.

After confirming authentication and current authority, it passes the exact active historical grant to:

- `authorize_executive_control_intent()`; or
- `authorize_executive_read_request()`.

Those existing functions remain the authority for action/scope permission, request chronology and grant expiry rules.

## Authentication checks

Before querying authority state, the guard requires:

- a valid current `AuthenticatedExecutivePrincipal` at caller-supplied `evaluated_at`;
- assertion principal equal to request principal;
- assertion correlation ID equal to request correlation ID;
- protected request timestamp not earlier than assertion issue.

Authentication failure, principal mismatch or correlation mismatch blocks before the authority source is called.

## Authority request checks

The explicit `ExecutiveAuthorityStateRequest` must:

- refer to the same principal;
- preserve the same correlation ID;
- not predate the protected command/read request;
- not postdate `evaluated_at`.

No authority-state request ID or timestamp is generated inside the guard.

## Authority response checks

The source response must:

- be an `ExecutiveAuthorityStateSnapshot`;
- preserve the exact authority-state request ID;
- preserve principal identity;
- be observed no earlier than the authority-state request;
- be observed no later than `evaluated_at`;
- be `ACTIVE`;
- expose an exact active grant.

`REVOKED`, `SUPERSEDED`, `EXPIRED` and `UNKNOWN` all fail closed.

Source failure also fails closed.

## Sanitized failures

The guard deliberately does not propagate arbitrary upstream error text to its public failure result.

Failures are represented by a closed stage and reason code:

Stages:

- `authentication`;
- `authority`;
- `authorization`.

Reasons:

- `authentication-invalid`;
- `principal-mismatch`;
- `correlation-mismatch`;
- `authority-request-invalid`;
- `authority-source-failed`;
- `authority-response-mismatch`;
- `authority-not-active`;
- `authorization-denied`.

This prevents a secret-bearing message from an external source from leaking through Control Plane error output.

## No dispatch

The guard produces only canonical authorized values.

It does not call `ExecutiveControlCommandPort`, `ExecutiveReadQueryPort`, provider clients, execution gateways or any trading surface.

Command and query dispatch remain Deliveries 5 and 6.

## Provider independence

This composition contains no OANDA/broker/provider dependency.

MISSION-03 remains operationally blocked at Gate #5 until an OANDA Practice account and token exist.

## Safety

The delivery introduces no:

- buy/sell/order command;
- Risk bypass;
- provider credential;
- Production authority;
- real capital;
- automatic retry;
- scheduler/thread;
- implicit clock;
- network/API server.

## Tests

The delivery proves:

- valid control reaches the existing control authorizer and returns its canonical authorized value;
- valid read reaches the existing read authorizer;
- expired authentication blocks before authority lookup;
- principal/correlation mismatch blocks before authority lookup;
- revoked current authority blocks;
- authority source failure is sanitized and blocks;
- mismatched authority response/request identity blocks;
- an action denied by the existing grant remains denied rather than being reimplemented by the guard.

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
QORE-EXECUTIVE-COMMAND-DISPATCH-001
```
