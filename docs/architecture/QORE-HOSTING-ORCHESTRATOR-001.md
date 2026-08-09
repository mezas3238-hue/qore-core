# QORE-HOSTING-ORCHESTRATOR-001 — Hosting Orchestrator & Deployment Control

## Status

**MISSION-08 DELIVERY 6 — NON-PRODUCTION CONTRACTS**

This delivery composes the already-merged Account Execution Unit, Runtime Registry, Execution Lease/Fencing and Health/Heartbeat contracts into a deterministic hosting deployment-control decision boundary.

It does not implement a cloud/VPS/Kubernetes adapter, broker/provider connection or productive failover.

## Authority boundary

The maximum authority invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

The Hosting Orchestrator has infrastructure placement/control authority only. It cannot create a Core Decision, submit an order, calculate a trade, bypass account policy/risk/entitlement, acquire or revoke a lease, mint a fencing generation, activate a backup runtime or reconcile external broker state.

Execution authority remains represented only by the separate account-scoped lease/fencing contracts.

## Inputs

`evaluate_hosting_orchestration(...)` consumes explicit immutable facts:

- one exact `HostingRuntimeRecord`;
- one exact `HostingRuntimeHealthAssessment`;
- one `HostingExecutionLeaseSnapshot`;
- caller-supplied orchestration decision/evidence identities;
- an explicit timezone-aware evaluation time.

The health assessment must bind the same account/runtime and the exact evaluation time. The lease snapshot must be captured at or after that evaluation time. A future runtime observation is rejected.

These chronology checks prevent a stale lease snapshot from being used to infer that a runtime is or is not the current writer.

## Actions

The closed deployment-control vocabulary is:

```text
PREPARE_RUNTIME
REQUEST_DRAIN
CONTAIN_NEW_WORK
STOP_RUNTIME
NO_ACTION
```

No action named or equivalent to `ACTIVATE_EXECUTION`, `ACTIVATE_BACKUP`, `ACQUIRE_LEASE`, `REVOKE_LEASE`, `FENCE`, `RETRY` or `REDISPATCH` exists.

`PREPARE_RUNTIME` means placement/lifecycle preparation only. A prepared or RUNNING runtime still has no new execution authority without a separately valid lease/fencing attestation and all downstream Client Agent/Core gates.

## Decision order

The deterministic evaluation order is fail-closed:

1. any health containment requirement -> `CONTAIN_NEW_WORK`;
2. desired DRAINING -> `REQUEST_DRAIN`;
3. desired STOPPED while the runtime is the current writer -> `REQUEST_DRAIN`;
4. desired STOPPED for a non-writer -> `STOP_RUNTIME` unless already stopped;
5. desired RUNNING with STOPPED/UNKNOWN observation -> `PREPARE_RUNTIME`;
6. otherwise -> `NO_ACTION`.

Health containment takes precedence over deployment alignment.

## Current writer handling

The Orchestrator may read the separate lease snapshot only to avoid directly stopping a runtime that currently owns valid account-scoped writer authority.

For a desired STOP on the current writer, it emits `REQUEST_DRAIN` rather than `STOP_RUNTIME`.

It does not mutate the lease. Delivery 7 owns failover/reconciliation composition and must preserve the canonical sequence:

```text
contain new work
 -> revoke/expire previous authority
 -> fence previous generation
 -> reconcile external state
 -> resolve ambiguity
 -> acquire new fenced authority
```

## Health containment

`DEGRADED`, `UNREACHABLE`, stale or unknown heartbeat state can cause containment, but never backup activation.

```text
UNREACHABLE != SAFE TO START BACKUP
HEALTHY != EXECUTION AUTHORITY
```

The Orchestrator therefore emits deployment-control intent only and leaves all authority transfer to later contracts.

## Types and evidence

Decisions use canonical `TradingAccountId` and `ExecutionRuntimeReference` directly. They are not untyped objects or duplicated hosting identities.

Each decision carries an opaque UUID-based decision identity, an opaque evidence reference and the explicit evaluation timestamp. No raw secret, provider credential or strategic payload is stored.

## No provider runtime

This delivery introduces no:

- VPS/cloud/Kubernetes SDK;
- process manager;
- network listener;
- broker/FCM/FIX client;
- provider credentials;
- secret-value resolution;
- scheduler/background retry loop;
- productive deployment action;
- automatic failover.

Future adapters may consume an approved deployment-control decision, but they cannot reinterpret it as trading authority.

## MISSION-08 relationship

This is Delivery 6 of 11.

Deliveries 1–5 remain the prerequisite authority/state contracts. The next ordered delivery is `QORE-HOSTING-FAILOVER-RECONCILIATION-001`.

This delivery does not close MISSION-08.

MISSION-03 issue #146 remains an independent external OANDA Practice evidence blocker. MISSION-06 and Production remain CLOSED. Native Broker and Regional Futures remain outside MISSION-08.

## Quality gate

The exact delivery head must pass the unchanged repository gate:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No `type: ignore`, cast workaround, suppression, test removal or gate weakening is authorized.
