# QORE-EXECUTIVE-AUTHORITY-STATE-001 — Current Authority State

Status: **MISSION-04 DELIVERY 3 — SOURCE-OF-TRUTH CONTRACT**

## Purpose

Define the canonical current-state boundary used by the Executive Control Plane to determine whether an executive authority grant is active, revoked, superseded, expired or unknown.

The Control Plane must not reconstruct current authority by replaying an incomplete audit log.

## Existing grant vs current state

`ExecutiveAuthorityGrant` remains the immutable historical grant contract.

A grant alone cannot prove that it is still current because it may later have been revoked or superseded.

MISSION-04 therefore separates:

```text
Historical issued grant
        │
        ▼
Current Authority State Source
        │
        ├── active
        ├── revoked
        ├── superseded
        ├── expired
        └── unknown
```

Only `ACTIVE` exposes `active_grant`.

`UNKNOWN` is explicitly non-authorizing.

## State lifecycle

### ACTIVE

Requires an exact `ExecutiveAuthorityGrant` whose principal matches the snapshot principal.

The observation must not predate grant issue or postdate grant expiry.

An active state carries no invalidation timestamp or superseding version.

### REVOKED

Requires the historical grant and an explicit `invalidated_at` timestamp no later than the state observation.

It carries no superseding version.

A revoked grant is never returned through `active_grant`.

### SUPERSEDED

Requires:

- the replaced historical grant;
- explicit `invalidated_at`;
- explicit successor `ExecutiveAuthorityVersion` different from the replaced grant's version.

This state does not imply that the successor is itself active for the same principal; the current source must answer that explicitly on the relevant current read.

### EXPIRED

Requires the historical grant and an observation strictly after grant expiry.

Expiry is derived from the immutable grant chronology, not from a hidden runtime clock.

### UNKNOWN

Represents an authoritative answer that no current authority can be established for the principal.

It must not carry a grant, invalidation timestamp or successor version.

`UNKNOWN` must never be treated as `ACTIVE`.

## Request contract

`ExecutiveAuthorityStateRequest` binds:

- explicit request UUID;
- canonical `ExecutivePrincipalId`;
- caller-supplied timezone-aware request timestamp;
- canonical `CorrelationId`.

No request identity or timestamp is generated implicitly.

## Snapshot provenance

Every snapshot carries a sanitized `ExecutiveAuthorityStateEvidenceRef` pointing to the authoritative materialized-state record or equivalent evidence boundary.

The reference rejects secret-like material and is safe for audit/logical values.

## Source boundary

`ExecutiveAuthorityStateSource` is a structural `Protocol`:

```text
read_current(request)
    → Result[ExecutiveAuthorityStateSnapshot, ExecutiveAuthorityStateError]
```

Persistence, database technology, remote transport and storage implementation are outside the governance contract.

An unavailable source returns a typed failure; source unavailability must never be converted to `ACTIVE`.

## Authentication separation

Delivery 2 established `AuthenticatedExecutivePrincipal`.

Delivery 3 does not consume authentication assertions yet and does not authorize commands or reads.

Delivery 4 will compose:

```text
AuthenticatedExecutivePrincipal
  + ExecutiveAuthorityStateSource
  + ExecutiveControlIntent / ExecutiveReadRequest
  → authorized request OR fail-closed result
```

This separation prevents authentication from silently becoming authority.

## Audit separation

Current authority state is not reconstructed from the audit log.

Audit may explain how a state was reached, but the current source is authoritative for whether the grant is presently active/revoked/superseded/expired/unknown.

## Provider independence

No OANDA/broker/provider dependency is introduced.

MISSION-03 remains operationally blocked at Gate #5 until OANDA Practice account/token provisioning exists.

## Safety

This delivery introduces no:

- trading execution;
- buy/sell/order controls;
- broker/provider client;
- credentials;
- Production authority;
- real capital;
- automatic retry;
- scheduler/thread;
- implicit clock;
- audit-history reducer.

## Determinism

All values use frozen slotted dataclasses, explicit timestamps, deterministic logical values and typed errors.

## Tests

The delivery verifies:

- active state exposes the exact active grant;
- unknown state is non-authorizing and cannot fabricate a grant;
- revoked state requires explicit invalidation;
- superseded state requires a distinct successor version;
- active/expired state respects grant chronology;
- principal mismatch fails closed;
- future invalidation fails closed;
- secret-bearing evidence refs fail closed;
- request timestamps are timezone-aware;
- `ExecutiveAuthorityStateSource` is structurally substitutable.

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
QORE-EXECUTIVE-REQUEST-GUARD-001
```
