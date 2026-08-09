# QORE-CEO-DESKTOP-001 — CEO Desktop Reference Client

Status: **MISSION-05 DELIVERY 11 — NON-PRODUCTION REFERENCE COMPOSITION**

## Verified baseline

```text
main @ bb0f2c4ba2046b08b3f320816c5d4aaf7e48761e
```

MISSION-05 Deliveries 1–10 are merged on this baseline. Production remains closed.

## Purpose

Provide the first Desktop reference-client composition over the already-approved MISSION-05 client
boundaries without putting platform/reference-client code inside the QORE Core package and without
creating a second authority or transport path.

This delivery is framework-free reference client code. It does not implement a native desktop UI.

## Repository boundary

The reference client lives under:

```text
src/qore_clients/
```

It intentionally does **not** live under:

```text
src/qore/
```

This preserves the MISSION-05 repository rule that platform adapters/reference clients remain
outside the Core package and depend inward only through stable client-safe contracts.

QORE Core does not import `qore_clients`.

## Consumed contracts

The Desktop reference composes, rather than replaces:

- `ExecutiveClientSurface`;
- `ExecutiveClientSessionBinding`;
- `ExecutiveCommandCenterViewModel`;
- optional `ExecutiveGovernanceUxState`;
- `ExecutiveClientGatewayEnvironment`;
- `ExecutiveClientGatewayProtocol`;
- the canonical `build_executive_client_gateway_ingress()` boundary.

The Command Center view model already contains the approved state-sync composition and may carry the
CIBO Widget. This delivery does not duplicate those models.

## Desktop binding

A valid `ExecutiveDesktopReferenceClient` requires:

- exact `ExecutiveClientPlatform.DESKTOP`;
- the exact same client surface in the session binding;
- the exact same surface identity in the Command Center view model;
- explicit non-production gateway environment;
- explicit gateway protocol;
- explicit timezone-aware composition time;
- composition no earlier than session/view-model observation;
- composition no later than the bound session expiry;
- optional Governance UX bound to the exact same surface and chronology.

Any mismatch fails closed.

## Gateway usage

Desktop request normalization delegates directly to the existing MISSION-05 client gateway:

```text
Desktop reference client
        -> existing ExecutiveClientSessionBinding
        -> build_executive_client_gateway_ingress(...)
        -> existing MISSION-04 ExecutiveTransportEnvelope
        -> Control Plane
```

The reference client does not call `CoreApplication`, a broker, an execution gateway or a command
port directly.

The existing gateway revalidates the session at request receipt time and normalizes the request into
the existing MISSION-04 transport envelope.

## No automatic redispatch

The Desktop reference state exposes:

```text
automatic_redispatch_allowed = false
```

It contains no retry loop, resubmit operation, background worker, scheduler, thread or hidden sleep.
Ambiguous governance outcomes remain governed by the existing Governance UX/replay/resilience
contracts.

## Platform semantics

Desktop uses the same logical authorized state and authority semantics that future iOS and Android
reference clients must consume.

Desktop may later adapt layout, navigation density, keyboard/mouse interaction and native secure
storage outside QORE Core. It may not reinterpret:

- authorization;
- allowed governance commands;
- replay protection;
- stale-state behavior;
- evidence requirements;
- audit requirements;
- trading restrictions.

## Explicitly not implemented

This delivery does not implement:

- WinUI, WPF, AppKit, Qt, Electron or another desktop UI framework;
- a native window/event loop;
- network sockets or an HTTP server;
- secure-storage implementation;
- authentication provider implementation;
- broker/provider connectivity;
- order entry;
- forced trading;
- Production deployment.

## Safety

The reference client exposes no:

- `buy` / `sell`;
- `submit_order` / `cancel_order`;
- Risk bypass;
- Portfolio bypass;
- Capital Protection bypass;
- broker/provider credentials;
- direct Core object;
- Production activation.

MISSION-03 Gate #5 remains operationally blocked pending authorized OANDA Practice provisioning.
Nothing in this delivery changes that gate.

## Determinism

The implementation preserves:

- immutable `dataclass(frozen=True, slots=True)` values;
- explicit UUID identity;
- explicit timezone-aware timestamps;
- deterministic `logical_values()`;
- explicit environment/protocol;
- no implicit wall clock;
- no implicit identity generation.

## Tests

Contract tests prove:

- the reference client module lives outside the `qore` Core package;
- only Desktop client surfaces are accepted;
- exact session/surface/view-model binding;
- session-expiry containment;
- requests delegate to the canonical client gateway;
- Desktop envelopes use the existing `CEO_COMMAND_CENTER` transport surface;
- no direct Core, broker, execution, retry or native-window surface is exposed.

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
QORE-CEO-IOS-001
```

The iOS reference composition must use the same logical client/session/gateway/state/authority model
without adding native framework dependencies to QORE Core.
