# QORE-HOSTING-EXECUTION-LEASE-001 — Execution Lease & Fencing

## Status

**IMPLEMENTED — NON-PRODUCTION SINGLE-WRITER AUTHORITY CONTRACTS**

MISSION-08 Delivery 4 defines the account-scoped execution-writer lease and monotonic fencing generation required before a QORE-managed runtime can possess infrastructure execution authority.

## Maximum invariant

```text
AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT
```

Runtime Registry state does not grant this authority. Only a current valid execution lease may produce a writer attestation.

This is infrastructure writer authority only:

```text
VALID HOSTING LEASE != CORE TRADE DECISION
```

All MISSION-07 Core Decision/security/risk/entitlement gates remain mandatory for new trading actions.

## Lease identity

`HostingExecutionLease` binds:

- lease ID;
- TradingAccountId;
- ExecutionRuntimeReference;
- HostingExecutionUnitId;
- monotonic `HostingFencingGeneration`;
- explicit status;
- acquired-at / expires-at;
- optional revoked-at;
- evidence reference.

## Lease status

Closed vocabulary:

```text
ACTIVE
REVOKED
EXPIRED
UNKNOWN
```

Only ACTIVE within its explicit time interval may be authoritative.

REVOKED, expired-by-time and UNKNOWN leases fail closed.

## Fencing

Fencing generation is positive and monotonic per account.

Historical generations must be unique and increase with acquisition order.

After a newer generation exists, an older generation cannot be returned as current authority.

A new lease acquisition must use a generation strictly greater than all previous generations for that account.

## Single writer

`HostingExecutionLeaseSnapshot` rejects a state with two simultaneously authoritative leases for one account at snapshot capture time.

Different accounts retain independent authority.

## Registry binding

Lease acquisition requires the runtime candidate to exist in the merged Runtime Registry and to bind the exact requested account.

A missing runtime or account/runtime mismatch fails closed.

## Acquisition semantics

The reference `acquire_hosting_execution_lease(...)` deterministically validates:

- registered candidate;
- exact account/runtime binding;
- no current authority in the known snapshot;
- monotonic fencing generation;
- valid lease chronology.

A productive durable implementation must make acquisition atomic. This delivery does not pretend an in-memory immutable snapshot is a distributed lock.

## Revocation

`revoke_hosting_execution_lease(...)` explicitly revokes one ACTIVE lease.

Revocation:

- removes current writer authority;
- records explicit timestamp/evidence;
- does not acquire a backup;
- does not retry/redispatch an order.

The next writer must independently satisfy later failover/reconciliation gates and acquire a higher fencing generation.

## Authority attestation

`HostingExecutionAuthorityAttestation` exposes only:

- account;
- runtime;
- lease;
- fencing generation;
- evaluation time;
- evidence.

It has no Core Decision, broker, order or retry method.

## Tests

The suite verifies:

- exactly one writer for one account;
- different accounts remain independent;
- simultaneous active writers are rejected;
- revocation removes authority and does not auto-activate backup;
- new writer requires higher fencing generation;
- expired lease is non-authoritative;
- runtime must be registered for exact account;
- authority attestation is infrastructure writer gating only.

## Non-goals

No heartbeat, orchestrator, failover eligibility, account reconciliation, broker IO, provider SDK, distributed database/consensus implementation or Production activation is introduced.

## Next delivery

After exact-head Quality Gate GREEN and merge:

```text
QORE-HOSTING-HEALTH-HEARTBEAT-001
```