# QORE-EXECUTIVE-COMMAND-DISPATCH-001 — Governed Command Dispatch

Status: **MISSION-04 DELIVERY 5 — AUTHORIZED GOVERNANCE DISPATCH**

## Purpose

Dispatch an already-authorized executive governance intent through the existing `ExecutiveControlCommandPort` exactly once and validate the returned canonical `ExecutiveControlReceipt` before exposing it upstream.

This delivery does not authorize requests. Authorization remains Delivery 4.

This delivery does not implement governance-state persistence/mutation. That remains Delivery 7.

## Input boundary

`ExecutiveCommandDispatcher.dispatch()` accepts only:

```text
AuthorizedExecutiveControlIntent
```

An unauthenticated/raw `ExecutiveControlIntent` cannot enter this dispatcher.

The caller must first pass through the MISSION-04 request guard.

## Downstream boundary

The dispatcher reuses the canonical existing port:

```text
ExecutiveControlCommandPort.apply(
    AuthorizedExecutiveControlIntent
) -> Result[ExecutiveControlReceipt, ExecutivePortError]
```

No second command-port abstraction is introduced.

## Exactly-once dispatch attempt

For each `dispatch()` invocation, the dispatcher invokes `apply()` at most once.

There is no:

- hidden retry;
- automatic resubmit;
- sleep/backoff;
- scheduler;
- worker thread;
- ambiguity recovery by repeating the command.

Replay/idempotency across multiple external requests is a separate MISSION-04 Delivery 9 concern.

## Receipt binding

A successful downstream call is accepted only when the receipt preserves the exact authorization identity:

- intent ID;
- executive principal;
- governance action;
- optional target;
- authority version;
- correlation ID;
- `received_at >= authorized_at`.

A contradictory receipt fails closed and is not returned as success.

## Receipt outcome semantics

The dispatcher does **not** reinterpret valid downstream governance outcomes.

The canonical receipt statuses remain:

- `APPLIED`;
- `NO_CHANGE`;
- `BLOCKED`;
- `FAILED`.

If a receipt is correctly bound and safe, any of these statuses is returned as a successful transport/domain receipt result. This preserves the downstream governance outcome for later audit/observability instead of confusing `BLOCKED` or `FAILED` business outcomes with a broken command transport.

## Sanitized failures

Arbitrary downstream exception text is never propagated.

Dispatch-level failures use the closed reason set:

- `downstream-failed`;
- `receipt-invalid`;
- `receipt-mismatch`;
- `receipt-unsafe`.

This protects the Control Plane from accidentally exposing database, service or credential details returned by a concrete downstream implementation.

## Receipt safety check

Although the canonical receipt contracts already constrain syntax, this dispatch boundary additionally rejects obvious secret-bearing fragments in:

- `reason_code`;
- evidence references.

This prevents an unsafe concrete command-port implementation from injecting credential-like data into a receipt that would otherwise be propagated to audit/transport layers.

## No trading semantics

`ExecutiveControlCommandPort` accepts only the closed `ExecutiveControlAction` governance allowlist established by the repository.

This dispatcher cannot construct:

- BUY/SELL;
- broker orders;
- position changes;
- quantity/price requests;
- provider calls.

It is a governance dispatcher, not a trading executor.

## Relationship to Delivery 7

A later `QORE-EXECUTIVE-GOVERNANCE-MUTATION-001` delivery will define the explicit materialized governance-state mutation port.

A concrete `ExecutiveControlCommandPort` implementation may eventually compose that mutation boundary, but Delivery 5 does not assume storage technology or mutation mechanics.

## Relationship to audit

The canonical `ExecutiveControlReceipt` already contains evidence references, but durable audit append/read boundaries remain Delivery 8.

Delivery 5 validates and returns the receipt; it does not silently write to a database or log sink.

## Provider independence

No OANDA/broker/provider dependency is introduced.

MISSION-03 remains operationally blocked at Gate #5 pending OANDA Practice account/token provisioning.

## Safety

This delivery introduces no:

- Production authority;
- real capital;
- direct trading command;
- Risk bypass;
- credentials;
- provider/broker client;
- automatic retry/resubmit;
- implicit clock;
- background scheduler/thread;
- persistence implementation.

## Tests

The delivery proves:

- one authorized request produces exactly one downstream `apply()` call;
- the exact canonical receipt is preserved;
- valid `BLOCKED`, `FAILED` and `NO_CHANGE` statuses remain explicit receipt outcomes;
- downstream failure is sanitized and not retried;
- principal/identity receipt mismatch fails closed;
- a receipt predating authorization fails closed;
- secret-like reason/evidence content fails closed.

## Quality Gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppressions or weakened checks are permitted.

## Next delivery

After merge, continue directly with:

```text
QORE-EXECUTIVE-QUERY-DISPATCH-001
```
