# QORE-MISSION08-E2E-OFFLINE-001 — Managed Hosting Deterministic Offline E2E

## Status

**EVIDENCE DELIVERY — NON-PRODUCTION ONLY; PRODUCTION REMAINS CLOSED**

Opening baseline:

```text
main @ b3700aa02465306b08444bee5ee6c2b0e8827de1
```

MISSION-08 Delivery 10 composes the Managed Hosting contracts already merged in Deliveries 2–9. It adds deterministic offline evidence only and introduces no new production `src/qore` runtime surface.

## Objective

Prove that two QORE-managed runtime candidates for one `TradingAccountId` cannot become two writers, and that failover is gated by containment, removal of previous authority, reconciliation, healthy/current candidate evidence and a new fenced lease.

The exercised authority chain is:

```text
Runtime Registry candidates A + B
  -> canonical lease acquisition gives A generation N
  -> telemetry observes A as CURRENT_WRITER
  -> A becomes UNREACHABLE
  -> Hosting Orchestrator returns CONTAIN_NEW_WORK only
  -> failover remains BLOCKED while A authority is active
  -> canonical lease revocation removes A authority
  -> ambiguous reconciliation remains BLOCKED
  -> matched account + execution reconciliation
  -> healthy/current B
  -> READY_FOR_LEASE_ACQUISITION with generation N+1
  -> canonical lease acquisition gives B generation N+1
  -> telemetry observes B as CURRENT_WRITER
  -> A carries no current lease/fencing identity
```

`READY_FOR_LEASE_ACQUISITION` is evidence that the lease boundary may be invoked. It is not itself authority.

## Registry is not authority

The test registers two runtime candidates for the same account.

```text
N CANDIDATE RUNTIMES != N WRITERS
```

Both candidates may be `RUNNING` and healthy while the account still has at most one current execution authority. Runtime Registry membership never elects a writer.

## Unreachable does not activate backup

When Runtime A becomes `UNREACHABLE`, health derives new-work containment and the Hosting Orchestrator emits:

```text
CONTAIN_NEW_WORK
```

It does not acquire/revoke leases, fence a generation, activate Runtime B, submit an order or perform provider I/O.

While A's lease remains authoritative, failover readiness is:

```text
BLOCKED
PREVIOUS_AUTHORITY_STILL_ACTIVE
```

This proves there is no heartbeat-to-backup shortcut.

## Ambiguity blocks

After the previous lease is explicitly revoked through the canonical lease boundary, the E2E independently proves both ambiguity gates:

```text
external account state AMBIGUOUS
 -> BLOCKED / EXTERNAL_ACCOUNT_AMBIGUOUS

execution reconciliation DIVERGED
 -> BLOCKED / EXECUTION_RECONCILIATION_AMBIGUOUS
```

No new lease is acquired in either blocked state and no duplicate redispatch/retry path exists.

## Fenced N+1 handoff

Only after:

- previous runtime containment;
- previous authority removal;
- external account reconciliation `MATCHED`;
- execution reconciliation `MATCHED`;
- candidate health `HEALTHY`;
- candidate heartbeat freshness `CURRENT`;

may the failover contract return:

```text
READY_FOR_LEASE_ACQUISITION
generation = N+1
```

Runtime B still is not a writer until `acquire_hosting_execution_lease(...)` succeeds.

After acquisition the E2E verifies exactly one authoritative account lease at the handoff timestamp and confirms that the stale/revoked A generation cannot regain authority.

## Telemetry after handoff

The repository's canonical telemetry vocabulary is:

```text
CURRENT_WRITER
OTHER_RUNTIME_IS_WRITER
NO_CURRENT_WRITER
```

Therefore after handoff:

```text
Runtime A = OTHER_RUNTIME_IS_WRITER
Runtime B = CURRENT_WRITER
```

Only B telemetry carries current lease identity and fencing generation. Telemetry remains observational and cannot create authority.

## Commercial suspension composition

The same evidence delivery composes Hosting commercial failure:

```text
PAYMENT_FAILED + open position
 -> SUSPEND_PENDING_FLAT
 -> allows_new_trades = false
 -> preserve_authorized_position_lifecycle = true
```

There is no Billing close/liquidation authority and no automatic runtime stop.

After the account is flat:

```text
SUSPENDED
MAY_STOP_WHEN_FLAT
```

`MAY_STOP_WHEN_FLAT` remains a disposition, not a provider mutation. A separate non-writer runtime with explicit desired `STOPPED` state may then receive the infrastructure decision `STOP_RUNTIME` from the Hosting Orchestrator.

## Negative authority evidence

The E2E asserts that the Hosting surfaces expose no strategic or execution-provider methods for:

- BUY/SELL strategy;
- Core Decision creation;
- risk mutation;
- order submission;
- retry order;
- redispatch;
- forced close/liquidation;
- provider SDK mutation.

The Account Execution Unit carries only `secret_refs`; the test verifies that secret-value/password/token/Authorization fields are absent.

The governing invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

Hosting controls placement, containment and readiness. It never invents a trading action.

## Deterministic offline test architecture

`tests/infrastructure/test_mission08_e2e_offline.py` uses only:

- canonical merged Hosting contracts;
- explicit UUID fixtures;
- explicit timezone-aware timestamps;
- immutable snapshots;
- canonical `Result / Success / Failure` semantics;
- no network;
- no broker;
- no provider SDK;
- no secret values;
- no productive credentials;
- no wall-clock dependency;
- no automatic retry;
- no duplicate redispatch;
- no background scheduler.

## Explicitly not implemented

This delivery does not authorize or implement:

- Production broker execution;
- real capital;
- productive VPS/cloud/Kubernetes control;
- productive failover;
- Native Broker Production;
- Futures Production;
- provider-specific SDKs inside Core;
- productive credentials;
- MISSION-03 Gate #5 closure.

Production remains CLOSED.

## Acceptance

Delivery 10 is complete only when its exact PR head passes the unchanged repository Quality Gate:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

After merge the only remaining MISSION-08 delivery is:

```text
QORE-MISSION08-CLOSURE-001
```
