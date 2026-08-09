# QORE-HOSTING-HEALTH-HEARTBEAT-001 — Runtime Health & Heartbeat

## Status

**IMPLEMENTED — NON-PRODUCTION OBSERVABILITY/CONTAINMENT CONTRACTS; AUTHORITY ABSENT**

MISSION-08 Delivery 5 defines explicit runtime heartbeat freshness and health assessment for registered QORE-managed runtime candidates.

## Fundamental rule

```text
HEALTHY != AUTHORIZED TO EXECUTE
UNREACHABLE != SAFE TO ACTIVATE BACKUP
```

Health is observational only. Execution authority remains exclusively in the merged lease/fencing boundary.

## Heartbeat sample

`HostingHeartbeatSample` binds:

- heartbeat identity;
- exact TradingAccountId;
- exact ExecutionRuntimeReference;
- health classification;
- observed time;
- explicit freshness deadline;
- evidence reference.

No hidden wall clock or implicit timeout exists.

## Health vocabulary

```text
HEALTHY
DEGRADED
UNREACHABLE
UNKNOWN
```

## Freshness vocabulary

```text
CURRENT
STALE
UNKNOWN
```

Freshness is evaluated at an explicit caller-supplied timestamp.

## Containment vocabulary

```text
NONE
STOP_ASSIGNING_NEW_WORK
FAIL_CLOSED
```

Containment is deterministic from health + freshness:

- CURRENT + HEALTHY -> NONE;
- DEGRADED/UNREACHABLE/UNKNOWN -> STOP_ASSIGNING_NEW_WORK;
- STALE -> STOP_ASSIGNING_NEW_WORK;
- no heartbeat evidence -> FAIL_CLOSED.

`NONE` means only that health does not require containment. It does **not** grant a lease, Core Decision or broker authority.

## Registry binding

Assessment requires the runtime to exist in the merged Runtime Registry and bind the exact account.

Foreign/missing runtime or heartbeat binding fails closed.

## Missing evidence

If no heartbeat exists, assessment becomes:

```text
health = UNKNOWN
freshness = UNKNOWN
containment = FAIL_CLOSED
```

and does not fabricate heartbeat identity/evidence.

## Failover boundary

This delivery exposes no:

- lease revocation;
- fencing mutation;
- backup activation;
- runtime election;
- order retry/redispatch.

The later failover delivery must compose health evidence with explicit lease revocation/expiry, fencing and reconciliation.

## Tests

The suite verifies:

- CURRENT HEALTHY is observation only;
- stale heartbeat stops new work but does not activate backup;
- UNREACHABLE stops new work only;
- missing heartbeat fails closed without fabricated evidence;
- exact registered account/runtime binding;
- future/invalid heartbeat chronology fails closed;
- no execution/lease/backup authority appears in health assessment.

## Non-goals

No network probe, scheduler, process monitor, cloud SDK, lease mutation, orchestrator, failover, provider/broker IO or Production activation is introduced.

## Next delivery

After exact-head Quality Gate GREEN and merge:

```text
QORE-HOSTING-ORCHESTRATOR-001
```