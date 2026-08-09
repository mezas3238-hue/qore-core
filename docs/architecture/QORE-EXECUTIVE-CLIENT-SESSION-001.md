# QORE-EXECUTIVE-CLIENT-SESSION-001 — Executive Client Session Boundary

## Status

**IMPLEMENTED — SECRET-FREE NON-PRODUCTION SESSION BOUNDARY**

Opening baseline:

```text
main @ dfd77d9ed2387cc808f7fe07db1bfecebcfb711a
```

This is MISSION-05 Delivery 3.

## Purpose

Bind safe external device/session provenance to the already-existing MISSION-04 `AuthenticatedExecutivePrincipal` without storing or transporting raw credentials inside QORE contracts.

The session boundary exists above authentication and below future client-gateway composition:

```text
External device / platform authentication
              │
              ▼
AuthenticatedExecutivePrincipal
              +
ExecutiveClientSession
              │
              ▼
ExecutiveClientSessionBinding
              │
              ▼
future MISSION-05 client gateway
```

The session contract does not authenticate a user by itself.

## Contracts

`src/qore/governance/executive_client_session.py` defines:

- `ExecutiveClientSessionId`;
- `ExecutiveClientDeviceRef`;
- `ExecutiveClientSessionStatus`;
- `ExecutiveClientSession`;
- `ExecutiveClientSessionBinding`;
- `build_executive_client_session(...)`;
- `bind_executive_client_session(...)`.

All contracts are immutable, deterministic and secret-free.

## Session state

The explicit external session states are:

```text
ACTIVE
REVOKED
UNKNOWN
```

Expiry is not guessed from a status string. It is evaluated from explicit timezone-aware `established_at` and `expires_at` values supplied by the caller.

Only `ACTIVE` may bind.

`REVOKED` and `UNKNOWN` fail closed.

## Exact binding

A successful `ExecutiveClientSessionBinding` requires exact agreement between:

- client `surface_id`;
- executive `principal_id`;
- authentication `assertion_id`;
- correlation identity;
- explicit time windows.

The session:

- may not predate the authentication assertion;
- may not outlive the authentication assertion;
- must be active at the explicit evaluation timestamp;
- must bind to the exact client surface supplied by Delivery 2.

The existing `evaluate_authenticated_executive_principal(...)` contract remains authoritative for authentication currency. Delivery 3 does not create a second authentication evaluator.

## Device reference

`ExecutiveClientDeviceRef` is an opaque, sanitized public reference such as:

```text
device:ios-primary
```

It is not:

- a hardware serial number requirement;
- a biometric value;
- a secure-storage record;
- an access token;
- a device secret;
- proof of authentication by itself.

Secret-bearing and non-canonical values are rejected.

## Security invariant

The following material is forbidden from session values, `repr`, logical values, logs, audit evidence and telemetry:

- bearer/access/refresh tokens;
- passwords;
- private keys;
- API keys;
- authorization headers;
- biometric material;
- provider/broker credentials;
- secure-storage contents.

The session stores only safe typed identity/provenance references and explicit timestamps.

## Authority invariant

A valid client session grants no trading authority and does not bypass MISSION-04.

The full protected path remains:

```text
safe session binding
   → authenticated principal
   → current authority
   → request guard
   → replay/idempotency
   → governed dispatch
   → receipt
   → audit/evidence
```

Possession of a device reference or session id is never sufficient to authorize a command.

## Failure semantics

Binding fails closed when any mandatory relation is missing or contradictory, including:

- session revoked;
- session state unknown;
- session not yet active;
- session expired;
- authenticated principal not yet valid or expired;
- surface mismatch;
- principal mismatch;
- assertion mismatch;
- correlation mismatch;
- session predates authentication;
- session outlives authentication;
- malformed identity/timestamp/reference.

No retry, refresh, clock read or session renewal is performed implicitly.

## Determinism

The implementation preserves QORE doctrine:

- `dataclass(frozen=True, slots=True)`;
- caller-supplied UUIDs;
- caller-supplied timezone-aware timestamps;
- no `datetime.now()`;
- no `uuid4()`;
- deterministic `logical_values()`;
- typed `Result / Success / Failure`;
- typed errors;
- fail-closed validation;
- no hidden retries/sleeps/schedulers/threads.

## Validation evidence

`tests/governance/test_executive_client_session.py` proves:

- exact active session binding succeeds;
- binding is immutable/deterministic and secret-free;
- revoked/unknown session fails closed;
- early/expired session fails closed;
- session cannot predate or outlive authentication;
- surface/principal/assertion/correlation mismatch fails closed;
- expired authenticated principal fails closed;
- secret-bearing device references are rejected;
- invalid chronology and type coercion are rejected.

## Explicitly not implemented

This delivery does not implement:

- OAuth/OIDC/passkey provider integration;
- biometric capture;
- Keychain/Keystore/TPM access;
- token refresh;
- network cookies;
- public login endpoints;
- Production sessions;
- broker/provider sessions;
- real trading activation.

## Acceptance result

The delivery is complete only after unchanged QORE CI passes and the expected module, tests and architecture document merge.

The next authorized MISSION-05 delivery is:

```text
QORE-EXECUTIVE-CLIENT-GATEWAY-001
```

That delivery may map non-production external transport into the existing MISSION-04 envelopes and this safe session binding. It may not duplicate authorization or expose Production.