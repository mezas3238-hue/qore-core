# QORE-MOBILE-SECURITY-RESILIENCE-001 — Mobile Security & Resilience Containment

Status: **MISSION-05 DELIVERY 14 — MOBILE SECURITY / RESILIENCE**

## Verified baseline

```text
main @ 8ab5478c01e439660509705ea01a27dd47e44f01
```

MISSION-05 Deliveries 1–13 are merged on this baseline. Production remains closed.

## Purpose

Compose the already-approved MISSION-05 mobile session/state boundaries with the MISSION-04
fail-closed resilience doctrine, without adding secrets, a native secure-storage implementation,
hidden retry, or a second authorization system to QORE Core.

The contract answers one narrow question:

> Is this iOS/Android presentation context currently safe to issue a read or governance request?

It does **not** authorize the request itself. Existing authentication, authority and Control Plane
contracts remain authoritative.

## Inputs

A mobile assessment consumes only explicit, secret-free facts:

- exact `ExecutiveClientSessionBinding`;
- opaque external secure-boundary assertion;
- explicit connectivity observation;
- canonical `ExecutiveClientStateView` for `GOVERNANCE`;
- optional canonical `ExecutiveGovernanceUxState`;
- caller-supplied assessment identity and time.

No implicit wall clock or generated identity is used.

## Secret boundary

`ExecutiveMobileSecretBoundaryAssertion` describes whether the external device security boundary is
available. Its `boundary_ref` is an opaque sanitized reference only.

The contract never accepts or stores:

- passwords;
- bearer tokens;
- private keys;
- broker credentials;
- raw Keychain/Keystore values;
- biometric material.

Native iOS Keychain / Android Keystore adapters remain outside QORE Core.

## Session revalidation

The assessment reuses `bind_executive_client_session(...)` at the explicit assessment timestamp.
A session that was valid when the screen was composed can therefore become invalid before a new
request is issued.

Invalid/expired session -> `BLOCKED`.

The assessment never revokes or mutates the original session object.

## State freshness

Governance command readiness requires the canonical `GOVERNANCE` state view.

If a snapshot exists, it is re-evaluated at the assessment timestamp using the existing state-sync
freshness function. Local UI state is never silently assumed current.

Canonical containment is:

```text
CURRENT      -> may remain READY
STALE        -> READ_ONLY
UNAVAILABLE  -> READ_ONLY
UNKNOWN      -> READ_ONLY
```

`READ_ONLY` means locally renderable/recoverable state. It does not mean network requests are always
possible; `read_request_eligible` additionally requires a current session, available secure boundary
and online connectivity.

## Connectivity

Connectivity is an explicit transport-neutral observation:

```text
ONLINE
OFFLINE
UNKNOWN
```

Offline or unknown connectivity prevents new network requests. Existing locally held presentation
state may remain visible as read-only evidence.

No socket, reachability framework, scheduler, reconnect loop or network library enters the contract.

## Governance activity containment

If a canonical Governance UX state is supplied:

```text
PENDING         -> BLOCKED for another control request
OUTCOME_UNKNOWN -> RECOVERY_REQUIRED
```

`OUTCOME_UNKNOWN` maps to the existing MISSION-04 recovery requirement:

```text
VERIFY_CONTROL_RECEIPT
```

The mobile layer does not invent a new recovery policy.

A terminal governance UX result can still require a fresh Governance read before another command if
the current state snapshot predates that result. In that case the assessment is `READ_ONLY` with
`GOVERNANCE_REFRESH_REQUIRED`.

## Dispositions

The closed mobile disposition set is:

```text
READY
READ_ONLY
BLOCKED
RECOVERY_REQUIRED
```

`READY` is presentation/request eligibility only. It is **not** executive authorization and never
implies trading authority.

## Retry doctrine

Every assessment reports:

```text
automatic_retry_allowed = false
automatic_redispatch_allowed = false
```

There is no hidden retry, redispatch, sleep, timer, worker, scheduler or thread.

A command with ambiguous outcome must be reconciled through the existing Control Plane recovery
contract before any new control action.

## Platform boundary

The assessment accepts only:

- `ExecutiveClientPlatform.IOS`;
- `ExecutiveClientPlatform.ANDROID`.

Desktop remains governed by its own reference-client boundary and common Control Plane contracts.

## Authority and trading safety

This delivery introduces no:

- new authentication engine;
- new executive authority engine;
- buy/sell/order API;
- forced execution;
- Risk bypass;
- Portfolio bypass;
- Capital Protection bypass;
- direct Core access;
- broker/provider connectivity;
- productive credential;
- Production activation.

MISSION-03 Gate #5 remains operationally blocked pending authorized OANDA Practice provisioning.

## Determinism

The implementation preserves:

- immutable `dataclass(frozen=True, slots=True)` values;
- closed enums;
- explicit UUID identity;
- timezone-aware timestamps;
- deterministic `logical_values()`;
- canonical state-sync re-evaluation;
- canonical session revalidation;
- canonical MISSION-04 recovery requirement reuse;
- no implicit clock;
- no implicit identity generation.

## Tests

Contract tests prove:

- valid mobile context becomes request-ready;
- unavailable/unknown governance state becomes read-only;
- offline state cannot issue network requests;
- unavailable secure boundary blocks requests;
- expired session fails closed without mutation;
- a previously-current snapshot becomes stale at assessment time;
- ambiguous governance outcome requires control-receipt verification;
- pending governance activity blocks another control request;
- secret-looking material is rejected from boundary references;
- Desktop surfaces are rejected;
- no native secret, retry or execution surface is exposed.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or quality-gate weakening is permitted.

## Next delivery

After merge and repository re-verification, continue with the exact Delivery 15 identifier defined by
the MISSION-05 mission document. No later mission or Production work is authorized by this delivery.
