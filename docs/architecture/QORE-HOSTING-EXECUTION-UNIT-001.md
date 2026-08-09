# QORE-HOSTING-EXECUTION-UNIT-001 — Account Execution Unit Foundation

## Status

**IMPLEMENTED — NON-PRODUCTION HOSTING IDENTITY/PLACEMENT CONTRACTS; EXECUTION AUTHORITY NOT YET IMPLEMENTED**

MISSION-08 Delivery 2 defines the immutable account-scoped execution-unit descriptor used by later Runtime Registry, lease/fencing and orchestration deliveries.

## Fundamental rule

```text
HOSTING PLACEMENT != EXECUTION AUTHORITY
```

A `HostingExecutionUnit` can be `READY` or `RUNNING` and still has no authority to submit an order. Lease/fencing has not yet been implemented by this delivery.

## Account scope

Each execution unit binds exactly:

- `ClientId`;
- `TradingAccountId`;
- existing `ExecutionRuntimeReference`;
- hosting mode;
- execution-agent software version;
- QORE deployment/region references when managed;
- opaque secret references;
- lifecycle classification;
- explicit recorded timestamp.

The unit never contains strategic Core logic.

## Hosting modes

Closed vocabulary:

```text
SELF_HOSTED
QORE_MANAGED
```

`QORE_MANAGED` requires explicit QORE deployment and region references.

`SELF_HOSTED` is descriptive only and is forbidden from claiming QORE deployment/region placement.

## Runtime / software identity

The delivery reuses the existing account-scoped `ExecutionRuntimeReference` rather than creating a second client runtime identity.

`HostingSoftwareVersion` uses explicit semantic-version syntax. There is no mutable `latest` alias in the contract.

## Secret boundary

`secret_refs` may contain only existing canonical `SecretRef` values.

Raw password/token/API-key/credential fields are absent.

Secret references must be unique inside one execution unit.

This preserves the existing QORE Secret Boundary rather than creating a Hosting-specific secret store.

## Lifecycle classification

The execution-unit lifecycle vocabulary is:

```text
PLANNED
READY
RUNNING
DRAINING
STOPPED
UNKNOWN
```

These values describe placement/runtime lifecycle only.

They do not imply:

- a valid execution lease;
- fencing ownership;
- broker connectivity;
- permission to trade;
- Core Decision authorization.

## Region boundary

Managed units carry an opaque canonical region reference. This is deployment metadata only.

MISSION-08 does not yet implement regional execution-routing optimization or the Regional Futures Fabric.

## Determinism

All identities/timestamps are caller-supplied and immutable. No hidden clock, UUID generation, scheduler, cloud SDK or mutable process-global registry is introduced.

## Tests

`tests/infrastructure/test_hosting_execution_unit.py` verifies:

- QORE-managed account/runtime/deployment/region binding;
- SELF_HOSTED isolation from QORE placement;
- managed placement requires deployment + region;
- only opaque unique SecretRef values are accepted;
- raw credential fields are absent;
- lifecycle/orchestration classification grants no execution authority;
- software/region references use canonical syntax.

## Non-goals

No Runtime Registry, execution lease, fencing, heartbeat, orchestrator, failover, provider adapter, broker IO, commercial hosting suspension or Production activation is introduced here.

## Next delivery

After exact-head Quality Gate GREEN and merge:

```text
QORE-HOSTING-RUNTIME-REGISTRY-001
```