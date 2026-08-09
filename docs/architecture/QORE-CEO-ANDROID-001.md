# QORE-CEO-ANDROID-001 — CEO Android Reference Client

Status: **MISSION-05 DELIVERY 13 — NON-PRODUCTION REFERENCE COMPOSITION**

## Verified baseline

```text
main @ eb681be167c48a7aee93b0a31ac75b473bd2ac83
```

MISSION-05 Deliveries 1–12 are merged on this baseline. Production remains closed.

## Purpose

Provide the Android reference-client composition over the same approved MISSION-05 boundaries used
by Desktop and iOS, without putting platform reference code inside QORE Core and without creating a
second authority or transport path.

This delivery is framework-free reference client code. It does not implement Jetpack Compose or
Android Views.

## Repository boundary

The Android reference client lives under `src/qore_clients/`, outside `src/qore`.
QORE Core does not import `qore_clients`.

## Consumed contracts

The Android reference composes existing:

- `ExecutiveClientSurface`;
- `ExecutiveClientSessionBinding`;
- `ExecutiveCommandCenterViewModel`;
- optional `ExecutiveGovernanceUxState`;
- `ExecutiveClientGatewayEnvironment`;
- `ExecutiveClientGatewayProtocol`;
- canonical `build_executive_client_gateway_ingress()`.

State synchronization and CIBO Widget semantics remain in the existing Command Center composition.

## Android binding

A valid `ExecutiveAndroidReferenceClient` requires:

- exact `ExecutiveClientPlatform.ANDROID`;
- exact session/surface binding;
- exact Command Center surface identity;
- explicit non-production environment and protocol;
- explicit timezone-aware composition time;
- composition no earlier than session/view-model observation;
- composition no later than bound session expiry;
- optional Governance UX bound to the exact same surface and chronology.

Any mismatch fails closed.

## Transport semantics

The canonical client-surface contract binds Android to:

```text
ExecutiveTransportSurface.MOBILE
```

Request normalization delegates to the existing MISSION-05 client gateway. Android does not create
a second envelope, authentication path, authorization path or direct Control Plane call.

## Authority parity

Android receives the same logical authorized state and authority semantics as Desktop and iOS.
Platform selection cannot change authorization, governance permissions, replay protection,
freshness rules, evidence, audit or trading restrictions.

The reference client reports:

```text
automatic_redispatch_allowed = false
```

## Explicitly not implemented

This delivery does not implement:

- Jetpack Compose;
- Android Views/Activity lifecycle;
- Android Keystore integration;
- biometric prompt handling;
- push provider integration;
- network socket implementation;
- broker/provider connectivity;
- order entry;
- Production deployment.

## Safety

The Android reference client exposes no buy/sell/order entry, forced execution, Risk/Portfolio/
Capital Protection bypass, direct Core object, productive credential or automatic retry/redispatch.

MISSION-03 Gate #5 remains operationally blocked pending authorized OANDA Practice provisioning.
Nothing in this delivery changes that gate.

## Determinism

The implementation preserves immutable dataclasses, explicit UUID identities, timezone-aware
timestamps, deterministic `logical_values()`, explicit environment/protocol and no implicit clock
or identity generation.

## Tests

Contract tests prove:

- Android reference code remains outside the Core package;
- only Android client surfaces are accepted;
- Android uses the canonical MOBILE transport surface;
- exact session/surface/view-model binding;
- session-expiry containment;
- request normalization delegates to the canonical gateway;
- no native Android, direct Core, broker, execution or retry surface is exposed.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is permitted.

## Next delivery

After merge and repository re-verification, continue with:

```text
QORE-MOBILE-SECURITY-RESILIENCE-001
```
