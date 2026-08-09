# MISSION-08 — Managed Hosting & Single-Writer Execution Control — Closure

## Status

**COMPLETED — NON-PRODUCTION MISSION SCOPE ONLY**

This closure is valid only after `QORE-MISSION08-CLOSURE-001` passes the unchanged QORE Quality Gate and its exact PR head merges to `main`.

MISSION-08 completion does not open Production, productive Managed Hosting, native broker execution, real capital or Futures Production.

## Mission boundary closed

MISSION-08 closes the non-production implementation sequence authorized in `MISSION-08-MANAGED-HOSTING-SINGLE-WRITER.md`:

1. `QORE-MISSION08-DOCS-001`
2. `QORE-HOSTING-EXECUTION-UNIT-001`
3. `QORE-HOSTING-RUNTIME-REGISTRY-001`
4. `QORE-HOSTING-EXECUTION-LEASE-001`
5. `QORE-HOSTING-HEALTH-HEARTBEAT-001`
6. `QORE-HOSTING-ORCHESTRATOR-001`
7. `QORE-HOSTING-FAILOVER-RECONCILIATION-001`
8. `QORE-HOSTING-TELEMETRY-001`
9. `QORE-HOSTING-COMMERCIAL-SUSPENSION-001`
10. `QORE-MISSION08-E2E-OFFLINE-001`
11. `QORE-MISSION08-CLOSURE-001`

## Closed authority invariants

The completed non-production scope preserves:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT
```

and reasserts:

```text
REGISTRY != AUTHORITY
HEALTH != AUTHORITY
TELEMETRY != AUTHORITY
ORCHESTRATOR != LEASE AUTHORITY
```

Managed Hosting controls runtime placement, liveness observation, containment, failover readiness and commercial suspension only. It does not create strategic trading authority.

## Single-writer / fencing review

Runtime Registry may contain multiple QORE-managed runtime candidates for one `TradingAccountId`, but registry presence never grants writer status.

Current execution authority exists only through the canonical account-scoped execution lease boundary.

The closed lease contract preserves:

- at most one current writer per account;
- monotonic fencing generations;
- stale/revoked/expired generations fail closed;
- registry `RUNNING` is not authority;
- revocation does not automatically activate a replacement.

The deterministic Delivery 10 E2E proves a complete fenced handoff from Runtime A generation N to Runtime B generation N+1 without simultaneous writers.

## Health / orchestration review

Heartbeat and health are observations.

An `UNREACHABLE`, stale or unknown runtime may require new-work containment, but:

```text
UNREACHABLE != SAFE TO START BACKUP
```

The Hosting Orchestrator may decide only infrastructure actions such as:

- `PREPARE_RUNTIME`;
- `REQUEST_DRAIN`;
- `CONTAIN_NEW_WORK`;
- `STOP_RUNTIME`;
- `NO_ACTION`.

It cannot acquire/revoke leases, create fencing generations, create Core Decisions, submit orders or perform provider mutation.

## Failover / reconciliation review

The completed failover contract remains fail-closed:

```text
AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE
```

not:

```text
AMBIGUITY -> RETRY ORDER
```

A replacement runtime may become `READY_FOR_LEASE_ACQUISITION` only after:

1. the previous runtime is contained;
2. previous current authority no longer exists;
3. external account reconciliation is `MATCHED`;
4. execution reconciliation is `MATCHED`;
5. the candidate is `HEALTHY`;
6. candidate heartbeat freshness is `CURRENT`;
7. the candidate differs from the previous runtime;
8. the next fencing generation is N+1.

Readiness never creates authority. A new writer exists only after canonical lease acquisition succeeds.

No automatic duplicate redispatch or ACK-loss retry shortcut is authorized.

## Telemetry review

Hosting telemetry is strictly observational.

The canonical writer observation vocabulary is:

```text
CURRENT_WRITER
OTHER_RUNTIME_IS_WRITER
NO_CURRENT_WRITER
```

Only `CURRENT_WRITER` telemetry may carry current lease/fencing identity. Telemetry cannot elect, fence or mutate a writer.

## Commercial suspension review

Hosting commercial failure remains separate from trading authority and Billing close authority.

For payment failure with an open position:

```text
NO NEW TRADES
SUSPEND_PENDING_FLAT
PRESERVE_POSITION_LIFECYCLE
```

Billing does not close or liquidate the position and does not automatically stop the runtime.

After the account becomes flat:

```text
SUSPENDED
MAY_STOP_WHEN_FLAT
```

Any later `STOP_RUNTIME` remains an explicit infrastructure decision for a non-writer runtime, not a Billing trade action.

## Secret boundary

Managed Hosting stores only opaque secret references through the existing canonical `SecretRef` boundary.

No secret values, passwords, bearer tokens, Authorization headers or productive account credentials are added to Core by MISSION-08.

## Delivery evidence

MISSION-08 functional delivery PRs merged before closure are:

- #204 — Mission scope;
- #205 — Hosting Execution Unit;
- #206 — Runtime Registry;
- #207 — Execution Lease & Fencing;
- #208 — Health & Heartbeat;
- #210 — Hosting Orchestrator;
- #211 — Failover & Reconciliation;
- #212 — Hosting Telemetry;
- #213 — Hosting Commercial Suspension;
- #215 — Deterministic Offline E2E.

PR #209 is the independent MISSION-07 closure CI repair and is not a MISSION-08 delivery.

PR #214 is the post-MISSION-08 Futures & Reliability roadmap and does not retrospectively expand MISSION-08.

The closure PR itself becomes Delivery 11 only after its exact GREEN head merges.

## External blocker preserved

Issue **#146 — MISSION-03 Gate #5 — OANDA Practice operational evidence blocker** remains OPEN/BLOCKED unless independently satisfied by a real authenticated OANDA Practice read-only run and audited sanitized evidence.

MISSION-08 does not fabricate, simulate, substitute or close that external evidence gate.

## Production state

At MISSION-08 closure:

```text
MISSION-08 = COMPLETED
Production = CLOSED
Futures Production = CLOSED
Native Broker Production = CLOSED
Real capital = CLOSED
```

This mission does not authorize productive VPS/cloud/Kubernetes deployment, productive failover, productive broker credentials or any real-money execution path.

## Post-MISSION-08 roadmap

The already-merged canonical transition document is:

```text
docs/roadmap/QORE-POST-MISSION08-FUTURES-RELIABILITY-ROADMAP.md
```

It defines the future direction for Futures provider certification, minimum three broker adapters, Hosting Reliability Lab, market-data integrity, latency/I/O certification, Shadow Core and Paper/Simulation Futures.

This closure does not invent a mission number for that program and does not activate any future Production boundary. A subsequent program must be formally scoped from the repository-governed roadmap.

## Closure condition

MISSION-08 is `COMPLETED` only when the closure branch passes:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

with no gate weakening, typing suppression or removal of valid safety tests, and the exact GREEN head is merged into `main`.
