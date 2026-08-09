# MISSION-08 — Managed Hosting & Single-Writer Execution Control

## Status

**OPEN — NON-PRODUCTION IMPLEMENTATION MISSION**

MISSION-08 is authorized by the merged architecture:

```text
QORE-MANAGED-HOSTING-ARCH-001
```

It follows completed MISSION-07 and does not reopen MISSION-06 or Production.

## Mission objective

Implement and verify the provider-neutral, non-production contracts required for QORE Managed Hosting to operate account-scoped Client Execution Agent runtimes while preserving:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT
```

The mission owns runtime placement/control infrastructure only. It does not create strategic trading authority.

## In scope

MISSION-08 authorizes non-production contracts/reference composition for:

- Account Execution Unit identity/binding;
- SELF_HOSTED / QORE_MANAGED hosting classification;
- Runtime Registry;
- execution lease;
- fencing generation/token;
- runtime health and heartbeat freshness;
- Hosting Orchestrator / deployment-control contracts;
- failover sequencing;
- reconciliation before authority transfer;
- hosting telemetry/readiness;
- hosting commercial safe suspension;
- existing SecretRef composition;
- deterministic offline E2E evidence;
- mission closure/readiness review.

## Explicitly out of scope

MISSION-08 does **not** authorize:

- productive VPS/cloud/Kubernetes integration;
- native broker/FCM/FIX execution;
- provider SDK placement inside Core;
- Regional Futures Execution Fabric;
- Market Data Edge;
- Core Decision Edge/fanout network;
- productive credentials;
- real-capital execution;
- productive failover;
- confirmed Hosting price;
- confirmed Futures price;
- Production activation;
- MISSION-03 Gate #5 closure.

Native Broker Execution and Regional Futures remain future independent boundaries.

## Authority invariants

1. Core remains the only strategic authority for new trading actions.
2. Hosting mode/placement never creates trading authority.
3. A runtime requires a valid account-scoped execution lease before it may possess new execution authority.
4. At most one runtime may hold current execution authority for one TradingAccountId.
5. Every authority generation carries fencing evidence.
6. A stale/revoked/expired generation fails closed.
7. Heartbeat health is observational and never equals authority.
8. Loss of heartbeat cannot immediately activate a backup runtime.
9. Failover requires previous authority revocation/expiry + fencing + reconciliation + new lease acquisition.
10. Ambiguous external account state blocks new authority.
11. Recovery never authorizes automatic duplicate order redispatch.
12. Existing open-position lifecycle protection must not be intentionally abandoned.
13. Hosting commercial failure blocks new trades but does not grant Billing authority to close trades.
14. Runtime/lease/telemetry contracts store only opaque secret references, never secret values.
15. Provider-specific behavior remains behind adapters/boundaries.
16. Mobile remains outside the execution path.
17. Production remains CLOSED until separately authorized.

## Hosting modes

Closed hosting-mode vocabulary:

```text
SELF_HOSTED
QORE_MANAGED
```

`SELF_HOSTED` remains a classification/reference boundary; MISSION-08 does not orchestrate the client's own infrastructure.

`QORE_MANAGED` is eligible for the Managed Hosting control-plane contracts defined by this mission.

## Single-writer failover sequence

The mission must preserve the canonical sequence:

```text
failure/unreachable observation
 -> stop assigning new work to suspect runtime
 -> lease expiry or explicit revocation
 -> fence previous generation
 -> reconcile account/orders/positions/execution evidence
 -> resolve ambiguity
 -> new runtime atomically acquires new fenced lease
 -> resume only authorized lifecycle/new Core Decisions
```

No shortcut from `UNREACHABLE` directly to backup activation is permitted.

## Secret boundary

MISSION-08 reuses the existing canonical QORE secret-reference boundary.

A separate secret-value store is not implemented in Core. Runtime contracts may carry only opaque references required by future deployment/provider adapters.

## Commercial hosting suspension

Hosting is independent from EA and Widget products.

The required safe state flow is:

```text
HOSTING PAYMENT FAILED
 -> NO NEW HOSTED TRADES
 -> SUSPEND_PENDING_FLAT
 -> preserve already-authorized lifecycle protection
 -> account FLAT
 -> runtime may be stopped/decommissioned
 -> HOSTING SUSPENDED
```

Billing never receives position-close authority.

## Official delivery sequence

MISSION-08 consists of eleven ordered deliveries:

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

No later delivery may bypass an earlier authority contract.

## Acceptance criteria

MISSION-08 may close only when:

- all eleven deliveries merge in order;
- every exact PR head passes the unchanged QORE Quality Gate;
- account/runtime identities are deterministic and secret-free;
- Runtime Registry does not imply execution authority;
- lease/fencing proves single-writer semantics;
- stale/expired/revoked authority fails closed;
- health/heartbeat cannot grant authority;
- orchestrator/deployment control cannot bypass leases;
- failover composes fencing + reconciliation before new authority;
- telemetry is observational only;
- Hosting payment failure preserves open-position lifecycle and blocks new entries;
- deterministic offline E2E demonstrates split-brain containment;
- closure re-verifies no provider/Production authority was introduced.

## External state

MISSION-03 issue #146 remains an independent external OANDA Practice operational-evidence blocker and must remain fail-closed unless real evidence satisfies its repository-defined acceptance criteria.

MISSION-07 is completed.

MISSION-06 remains CLOSED.

Production remains CLOSED.

## Quality Gate

Every delivery must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No valid safety test may be deleted to pass CI. No `type: ignore`, cast or suppression shortcut is authorized without exceptional architectural justification.