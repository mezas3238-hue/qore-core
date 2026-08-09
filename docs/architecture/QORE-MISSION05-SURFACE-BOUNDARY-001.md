# QORE-MISSION05-SURFACE-BOUNDARY-001 — Executive Client Surface Boundary

## Status

**IMPLEMENTED — NON-PRODUCTION PLATFORM-NEUTRAL BOUNDARY**

Opening baseline:

```text
main @ a4f3ac974aa93edff75a7c05f78b9a5b2a13e23c
```

This delivery is MISSION-05 Delivery 2. It establishes the first executable boundary between future Desktop/iOS/Android presentation code and the already-completed MISSION-04 Executive Control Plane.

It does not implement a Desktop application, iOS application, Android application, network server, authentication provider or Production deployment.

## Purpose

The presentation layer needs a stable answer to two questions before platform code exists:

1. Which presentation platform is making the request?
2. Through which already-approved MISSION-04 transport category may that platform enter?

The answer is encoded without importing Core runtime, provider, broker, credential or UI-framework types.

## Contracts

`src/qore/governance/executive_client_surface.py` defines:

- `ExecutiveClientPlatform`
  - `DESKTOP`
  - `IOS`
  - `ANDROID`
- `ExecutiveClientSurfaceId`
- `ExecutiveClientVersion`
- `ExecutiveClientSurface`
- `build_executive_client_surface(...)`
- `expected_transport_surface(...)`
- `validate_executive_client_envelope_binding(...)`

All value contracts remain immutable, deterministic and secret-free.

## Dependency direction

The allowed dependency direction is:

```text
Desktop / iOS / Android presentation
              │
              ▼
ExecutiveClientSurface
              │
              ▼
ExecutiveTransportEnvelope
              │
              ▼
MISSION-04 Executive Control Plane
```

The reverse direction is prohibited:

```text
Core / Control Plane ─X─► Desktop UI framework
Core / Control Plane ─X─► iOS framework
Core / Control Plane ─X─► Android framework
Core / Control Plane ─X─► platform secure storage
```

This delivery introduces no UI-framework import into `src/qore`.

## Transport reuse

MISSION-05 does not invent a second ingress envelope.

The platform mapping intentionally reuses the existing MISSION-04 `ExecutiveTransportSurface`:

```text
Desktop  -> CEO_COMMAND_CENTER
iOS      -> MOBILE
Android  -> MOBILE
```

A caller cannot construct an iOS/Android client descriptor bound to `CEO_COMMAND_CENTER`, and cannot construct a Desktop descriptor bound to `MOBILE` through the approved builder.

Direct manual construction with a contradictory platform/transport binding also fails closed.

## Message capability boundary

Each client surface declares an explicit non-empty tuple of existing MISSION-04 `ExecutiveTransportMessageKind` values.

The tuple:

- rejects unknown/non-enum values;
- rejects duplicates;
- is deterministically ordered;
- does not create new authorization semantics.

Current MISSION-04 message kinds remain:

```text
CONTROL
READ
```

Future MISSION-05 subscription, evidence and notification deliveries must compose around the established Control Plane rather than silently expanding command authority here.

## Envelope binding

`validate_executive_client_envelope_binding(...)` performs a narrow presentation-boundary check only:

- input must be an `ExecutiveClientSurface`;
- input envelope must be the existing `ExecutiveTransportEnvelope`;
- envelope transport surface must match the client descriptor;
- message kind must be explicitly allowed by the descriptor.

If any condition is false, the result is a typed `Failure`.

A successful client-surface check does **not** mean a command or query is authorized. Authentication, current authority, request guard, replay/idempotency, dispatch and audit remain MISSION-04 responsibilities.

## Security boundary

`ExecutiveClientSurface` intentionally contains no fields for:

- bearer/access/refresh tokens;
- passwords;
- provider or broker clients;
- API keys;
- authorization headers;
- biometric material;
- platform secure-storage contents;
- Core application/runtime objects.

The surface descriptor contains only typed presentation identity/version/platform, approved transport mapping and allowed existing message kinds.

## Core protection

This delivery does not import or redefine:

- `EventBus`;
- `RuntimePlan`;
- `RuntimeSnapshot`;
- `RuntimeHealth`.

It creates no route from presentation code to Core internals.

The only executable dependency introduced by this delivery is from the new presentation-boundary contract toward the existing transport-neutral governance envelope.

## Determinism

The implementation preserves QORE doctrine:

- `dataclass(frozen=True, slots=True)`;
- caller-supplied identity values;
- no implicit clock;
- no implicit UUID generation;
- deterministic `logical_values()`;
- deterministic capability ordering;
- typed `Result / Success / Failure`;
- typed errors;
- strict type validation;
- no retries, sleeps, threads, schedulers or polling;
- no secret metadata.

## Validation evidence

`tests/governance/test_executive_client_surface.py` proves:

- Desktop maps only to `CEO_COMMAND_CENTER`;
- iOS and Android map only to `MOBILE`;
- client descriptors are immutable and deterministic;
- capability order is normalized;
- empty or duplicate capability sets fail closed;
- type coercion is not accepted;
- matching existing MISSION-04 envelopes are accepted by the narrow surface check;
- transport mismatch fails closed;
- disallowed message kind fails closed;
- contradictory manual platform/transport construction fails closed;
- non-contract inputs fail closed.

## What this delivery does not authorize

This delivery does not authorize:

- public Internet exposure;
- real device authentication;
- mobile secure storage;
- Desktop/iOS/Android executable product release;
- OANDA credentials or MISSION-03 Gate #5 closure;
- broker/provider access;
- real trading execution;
- Production;
- Client EA;
- Client Widget;
- MISSION-06.

## Acceptance result

The surface boundary is complete when the unchanged QORE CI passes and the delivery merges with only the expected module, tests and architecture documentation.

After merge, the next authorized MISSION-05 delivery is:

```text
QORE-EXECUTIVE-CLIENT-SESSION-001
```

That next delivery may bind safe external device/session provenance to the existing authenticated executive principal assertion. It may not introduce raw secret material into QORE contracts.