# QORE-CEO-IOS-001 — CEO iOS Reference Client

Status: **MISSION-05 DELIVERY 12 — NON-PRODUCTION REFERENCE COMPOSITION**

## Verified baseline

```text
main @ 8b47ecded37533af8a7174a98d9cfad2a8d5bcea
```

MISSION-05 Deliveries 1–11 are merged on this baseline. Production remains closed.

## Purpose

Provide the iOS reference-client composition over the same approved MISSION-05 boundaries used by
Desktop, without putting native/platform reference code inside the QORE Core package and without
creating a second authority or transport path.

This delivery is framework-free reference client code. It does not implement SwiftUI or UIKit.

## Repository boundary

The iOS reference client lives under:

```text
src/qore_clients/
```

It does not live under `src/qore`. QORE Core does not import `qore_clients`.

## Consumed contracts

The iOS reference composes existing:

- `ExecutiveClientSurface`;
- `ExecutiveClientSessionBinding`;
- `ExecutiveCommandCenterViewModel`;
- optional `ExecutiveGovernanceUxState`;
- `ExecutiveClientGatewayEnvironment`;
- `ExecutiveClientGatewayProtocol`;
- canonical `build_executive_client_gateway_ingress()`.

State synchronization and CIBO Widget semantics remain inside the existing Command Center view model.
This delivery does not duplicate them.

## iOS binding

A valid `ExecutiveIosReferenceClient` requires:

- exact `ExecutiveClientPlatform.IOS`;
- the exact same client surface in the session binding;
- the exact same surface identity in the Command Center view model;
- explicit non-production gateway environment;
- explicit gateway protocol;
- explicit timezone-aware composition time;
- composition no earlier than session/view-model observation;
- composition no later than the bound session expiry;
- optional Governance UX bound to the same surface and chronology.

Any mismatch fails closed.

## Transport semantics

The canonical surface mapping already binds iOS to:

```text
ExecutiveTransportSurface.MOBILE
```

The reference client delegates request normalization to the existing client gateway. It does not
build a second transport envelope or call Control Plane internals directly.

## Authority parity

iOS receives the same logical state and executive authority semantics as Desktop. Platform choice
cannot change:

- authorization;
- allowed governance commands;
- replay protection;
- stale-state behavior;
- evidence requirements;
- audit requirements;
- trading restrictions.

The reference state exposes `automatic_redispatch_allowed = false`.

## Explicitly not implemented

This delivery does not implement:

- SwiftUI;
- UIKit;
- UIApplication lifecycle;
- Keychain integration;
- Face ID / Touch ID handling;
- push notification providers;
- network socket implementation;
- broker/provider connectivity;
- order entry;
- Production deployment.

Those mechanisms, when authorized later, remain external adapters around the safe contracts.

## Safety

The reference client exposes no buy/sell/order entry, forced execution, Risk/Portfolio/Capital
Protection bypass, productive credential, direct Core object or automatic redispatch.

MISSION-03 Gate #5 remains operationally blocked pending authorized OANDA Practice provisioning.
Nothing in this delivery changes that gate.

## Determinism

The implementation preserves immutable dataclasses, explicit UUID identities, timezone-aware
timestamps, deterministic `logical_values()`, explicit environment/protocol, and no implicit wall
clock or identity generation.

## Tests

Contract tests prove:

- the iOS reference module remains outside the Core package;
- only iOS client surfaces are accepted;
- iOS uses the canonical MOBILE transport surface;
- exact session/surface/view-model binding;
- session-expiry containment;
- request normalization delegates to the canonical client gateway;
- no native UI, direct Core, broker, execution or retry surface is exposed.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or quality-gate weakening is permitted.

## Next delivery

After merge and repository re-verification, continue with:

```text
QORE-CEO-ANDROID-001
```
