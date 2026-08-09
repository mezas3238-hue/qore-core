# QORE-MANAGED-HOSTING-ARCH-001 — Managed Hosting & Single-Writer Execution Architecture

## Status

**ARCHITECTURE DEFINED — IMPLEMENTATION NOT YET AUTHORIZED BY A MISSION**

This architecture is the first post-MISSION-07 boundary for managed account execution hosting.

It does not reopen MISSION-07, MISSION-06 or Production and does not create a broker/provider execution implementation.

## Why this boundary exists

MISSION-07 completed the non-production Client Execution & Commercial Platform through the account-scoped Client Agent, protected Core Decisions, causal position lifecycle, commercial entitlement and client presentation boundaries.

It explicitly left Managed Hosting outside its scope.

The next architectural problem is therefore not strategy or broker connectivity. It is how QORE can host one execution-agent runtime per account while preserving:

- one active execution authority per account;
- deterministic failover;
- fencing of stale runtimes;
- reconciliation before authority transfer;
- safe commercial suspension;
- secret isolation;
- provider-neutral execution boundaries.

## Maximum authority invariant

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

Managed Hosting cannot originate strategy, signals, risk intent or direction.

Hosting may only provide runtime placement and lifecycle infrastructure for an execution agent that remains subject to all previously closed Core Decision, decision-security, account-policy, risk, entitlement and execution boundaries.

## Hosting modes

A trading account may be classified for hosting as:

```text
SELF_HOSTED
QORE_MANAGED
```

The hosting mode does not alter strategic authority.

`SELF_HOSTED` means QORE does not own the execution runtime placement/orchestration for that account.

`QORE_MANAGED` means QORE may operate the account's execution-agent runtime inside the Managed Hosting fabric, subject to the single-writer and commercial gates defined here.

## Account Execution Unit

The fundamental hosting unit is one account-scoped logical execution unit:

```text
Client
  -> TradingAccountId
  -> Account Execution Unit
  -> one or more runtime candidates
  -> at most one active execution authority
```

An execution unit binds only opaque platform identities and policy references such as:

- client/account identity;
- hosting mode;
- execution-agent software/version identity;
- runtime identity;
- execution lease identity;
- fencing generation/token;
- deployment version;
- health/heartbeat evidence;
- secret references;
- provider-adapter references.

It must never carry raw broker passwords, API tokens, private keys or strategic model intelligence.

## Runtime Registry

Managed Hosting requires an immutable/versioned Runtime Registry capable of representing:

- known runtime candidates;
- account/runtime binding;
- hosting region/placement reference;
- software/deployment version;
- desired lifecycle state;
- observed lifecycle state;
- health classification;
- last heartbeat evidence;
- current lease/fencing evidence;
- reconciliation status;
- entitlement/commercial hosting status.

The Registry is descriptive state. Mere presence in the Registry does not grant execution authority.

## Single-writer execution

The core hosting invariant is:

```text
AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT
```

No two runtimes may simultaneously possess valid authority to submit account execution actions.

This applies across:

- primary/backup runtimes;
- redeployments;
- host replacement;
- regional migration;
- crash recovery;
- network partitions;
- stale process recovery.

## Execution Lease

Authority is represented by an explicit account-scoped execution lease.

A valid lease must bind at least:

- TradingAccountId;
- runtime identity;
- lease identity;
- fencing generation/token;
- acquired-at time;
- expiry/revocation state;
- authority scope;
- evidence.

The lease must be acquired atomically through a future boundary.

A runtime without a currently valid lease has **no new execution authority**.

A stale runtime cannot regain authority merely because it reconnects.

## Fencing

Every execution authority generation must carry monotonic fencing evidence.

Conceptually:

```text
generation N runtime -> valid
new authority transfer -> generation N+1
any action carrying generation N -> rejected
```

Fencing exists to contain split-brain and delayed/stale writers.

Fencing is not a retry mechanism and does not prove external account state by itself.

## Health and heartbeat

Managed Hosting must distinguish runtime liveness from execution authority.

A heartbeat may establish observations such as:

```text
HEALTHY
DEGRADED
UNREACHABLE
UNKNOWN
```

and freshness such as current/stale.

But:

```text
HEALTHY != AUTHORIZED TO EXECUTE
UNREACHABLE != SAFE TO START BACKUP
```

An unreachable primary may still be alive and capable of external writes. Therefore failover cannot activate a replacement solely from heartbeat absence.

## Deployment Controller / Orchestrator

The future Hosting Orchestrator may coordinate:

- desired deployment version;
- runtime creation;
- runtime drain;
- deployment replacement;
- lease requests/revocation;
- fencing;
- health observations;
- reconciliation requests;
- final activation/deactivation state.

The Orchestrator is infrastructure authority only.

It does not:

- create Core Decisions;
- bypass risk/entitlement;
- calculate strategic trades;
- connect internal Core logic directly to broker APIs.

## Failover sequence

Failover must be fail-closed and ordered.

Canonical sequence:

```text
runtime failure/unreachable observation
  -> stop granting new work to suspect runtime
  -> lease expiration or explicit revocation
  -> establish fencing against previous generation
  -> reconcile external account/orders/positions
  -> resolve ambiguity
  -> new runtime acquires a new fenced lease
  -> new runtime may resume authorized execution lifecycle
```

A backup must **not** become active immediately after one failed heartbeat.

If previous-writer state cannot be proven/fenced/reconciled:

```text
NO NEW EXECUTION AUTHORITY
```

## Reconciliation before authority transfer

The repository's existing execution reconciliation doctrine remains authoritative and must be composed rather than replaced.

A failover candidate must reconcile relevant external state before authority acquisition is considered operationally safe, including where applicable:

- open positions;
- pending orders;
- execution receipts;
- last known lifecycle actions;
- account state;
- provider acknowledgements.

Ambiguity remains fail-closed.

No automatic duplicate order submission is authorized by recovery.

## Existing position protection

A hosting failure or commercial hosting suspension must never intentionally abandon an already-authorized open position.

Where a valid execution lifecycle already exists, the hosting control plane must preserve the ability to complete only the protection/lifecycle actions already authorized by the position policy, subject to reconciliation and single-writer authority.

This is infrastructure continuity, not a new strategic decision.

## Hosting commercial suspension

Managed Hosting is a separate commercial product from the EA.

If hosting payment/entitlement fails:

```text
HOSTING PAYMENT FAILED
  -> block new trades for hosted runtime
  -> SUSPEND_PENDING_FLAT
  -> preserve authorized open-position protection
  -> when account is FLAT
  -> stop/decommission hosted runtime
  -> HOSTING SUSPENDED
```

Billing does not receive authority to close a trade.

Hosting suspension does not modify the client's Widget product and does not rewrite Core decisions.

## Secret Boundary

Existing QORE secret-reference contracts must be reused.

Managed Hosting stores only opaque secret references such as `SecretRef`/provider-secret requirements.

Raw broker/provider credentials must remain behind dedicated runtime/provider secret-resolution boundaries.

The Runtime Registry, lease records, health telemetry and deployment contracts must never serialize secret values.

## Provider boundary

Managed Hosting is provider-neutral infrastructure.

Broker/provider-specific behavior remains behind existing/future adapters:

```text
QORE CORE
 -> protected canonical decision
 -> Client Execution Agent
 -> provider-neutral execution boundary
 -> broker/provider adapter
 -> broker/FCM/venue
```

The Hosting Orchestrator must not import provider SDK behavior into strategic Core logic.

## Telemetry

Hosting telemetry must be account/runtime scoped and evidence-oriented. It may include:

- runtime health;
- heartbeat timing;
- deployment version;
- lease/fence generation;
- reconciliation result;
- execution latency observations;
- resource/availability diagnostics;
- last successful lifecycle evidence.

Telemetry is observational. It cannot grant execution authority or generate strategy.

## Region / placement

This architecture does not yet define the Regional Futures Execution Fabric.

Managed Hosting placement may carry opaque region references, but client residence is not itself an execution-routing rule.

Future Native Broker/Regional Futures missions remain separate and must use measured provider/venue routing when authorized.

## Mobile boundary

A managed client may operate commercially using only a mobile device, but the mobile device remains outside the execution path.

```text
Mobile Client -> presentation/control surfaces
Hosted Runtime -> execution path
```

Disconnecting the mobile phone cannot become an execution failure mode.

## Production boundary

This architecture authorizes **no production hosting deployment**.

Before productive operation, later missions must provide tested contracts/reference composition for leases, fencing, reconciliation, deployment, health, telemetry and safe suspension, followed by whatever production gates the repository requires.

MISSION-06 and Production remain CLOSED.

MISSION-03 issue #146 remains an independent external OANDA Practice evidence blocker and is not closed or bypassed here.

## Proposed implementation decomposition

A later mission may use this architecture to authorize non-production work in a sequence such as:

1. mission scope/docs;
2. Account Execution Unit foundation;
3. Runtime Registry;
4. execution lease + fencing;
5. health + heartbeat;
6. Hosting Orchestrator / deployment control;
7. failover + reconciliation composition;
8. telemetry/readiness;
9. commercial safe suspension;
10. deterministic offline E2E;
11. closure.

These are architectural work packages, not pre-assigned future Mission IDs.

## Explicit non-goals

This architecture does not implement:

- a VPS vendor integration;
- Kubernetes/cloud SDK;
- broker API/FIX integration;
- productive credentials;
- productive failover;
- real-money execution;
- Regional Futures Fabric;
- market-data edge;
- confirmed Hosting price;
- confirmed Futures price;
- Production activation.

## Acceptance

This architecture becomes the canonical Managed Hosting boundary only after its exact PR head passes the unchanged QORE Quality Gate and merges to `main`.

After that merge, the repository may formally open the next non-production mission if no conflicting canonical scope exists.