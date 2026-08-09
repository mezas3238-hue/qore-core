# QORE-HOSTING-RUNTIME-REGISTRY-001 — Runtime Registry

## Status

**IMPLEMENTED — NON-PRODUCTION RUNTIME CANDIDATE REGISTRY; WRITER AUTHORITY ABSENT**

MISSION-08 Delivery 3 defines the immutable Runtime Registry for QORE-managed execution candidates.

## Core invariant

```text
RUNTIME REGISTRATION != EXECUTION AUTHORITY
```

A runtime may be registered, desired RUNNING and observed RUNNING without holding any execution lease.

## Scope

`HostingRuntimeRecord` composes the merged `HostingExecutionUnit` with:

- desired runtime state;
- observed runtime state;
- registration timestamp;
- observation timestamp.

Only `QORE_MANAGED` execution units may enter this Registry. SELF_HOSTED runtimes remain outside QORE orchestration.

## Desired state

Closed desired-state vocabulary:

```text
RUNNING
DRAINING
STOPPED
```

This expresses deployment/control intent only.

## Observed state

Closed observed-state vocabulary:

```text
STARTING
RUNNING
DRAINING
STOPPED
UNREACHABLE
UNKNOWN
```

Observed RUNNING is not execution authority.

Observed UNREACHABLE is not proof that a previous writer is fenced or safe to replace.

## Multiple candidates per account

The Registry deliberately permits multiple runtime candidates for one `TradingAccountId`.

This is necessary for staged deployment, backup capacity and failover preparation.

It must never choose a writer itself.

There is intentionally no:

```text
active_runtime
writer
elect()
can_execute
```

inside the Registry contract.

## Uniqueness

Within one Registry snapshot:

- `HostingExecutionUnitId` is unique;
- `ExecutionRuntimeReference` is unique;
- one runtime reference cannot belong to multiple account records;
- multiple distinct runtime refs may belong to the same account.

## Generation

`HostingRuntimeRegistryGeneration` is a positive monotonic snapshot identity supplied by the caller.

It is Registry-versioning evidence only and is distinct from the fencing generation introduced by the next delivery.

## Chronology

All times are explicit and timezone-aware.

Runtime observation cannot predate registration and no record may be newer than its Registry snapshot.

## Determinism

Records are sorted deterministically by account/runtime identity. Exact runtime lookup fails closed when missing.

No hidden clock, scheduler, database, cloud API or process-global mutable registry is introduced.

## Tests

`tests/infrastructure/test_hosting_runtime_registry.py` verifies:

- N runtime candidates per one account;
- deterministic candidate binding;
- duplicate runtime identity rejection;
- SELF_HOSTED exclusion;
- exact fail-closed runtime resolution;
- chronology invariants;
- desired/observed RUNNING states still provide no lease/fencing/trading authority.

## Non-goals

No execution lease, fencing, heartbeat policy, orchestrator, failover, broker IO, provider SDK or Production authority is introduced.

## Next delivery

After exact-head Quality Gate GREEN and merge:

```text
QORE-HOSTING-EXECUTION-LEASE-001
```