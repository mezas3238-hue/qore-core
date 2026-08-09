# QORE-EXECUTIVE-CLIENT-GATEWAY-001 — Non-Production Executive Client Gateway

## Status

**IMPLEMENTED — NON-PRODUCTION NORMALIZATION BOUNDARY**

Opening baseline:

```text
main @ 52967706ebeb2041f9edd1f7858b4b696bfdded1
```

This is MISSION-05 Delivery 4.

## Purpose

Normalize one safe Desktop/iOS/Android client request into the already-existing MISSION-04 `ExecutiveTransportEnvelope` after revalidating the MISSION-05 client session at the exact receive timestamp.

This delivery is not a public HTTP/WebSocket server and does not parse or retain raw transport headers, cookies, bearer tokens or socket objects.

## Composition

```text
ExecutiveClientSessionBinding
        +
ExecutiveControlIntent / ExecutiveReadRequest
        +
explicit non-production gateway provenance
        │
        ▼
build_executive_client_gateway_ingress(...)
        │
        ├── re-evaluate client session at received_at
        ├── validate route/payload agreement
        ├── call existing MISSION-04 envelope builder
        └── validate Delivery-2 surface binding
        │
        ▼
ExecutiveClientGatewayIngress
        │
        ▼
MISSION-04 ExecutiveTransportEnvelope
```

No MISSION-04 authorization, replay, dispatch or audit rule is reimplemented here.

## Non-production environment boundary

The only gateway environments represented by the contract are:

```text
LOCAL
TEST
DEMO
STAGING
```

There is deliberately no `PRODUCTION` enum value.

A caller passing a string or cast value such as `production` fails strict runtime validation.

This is a code-level expression of the mission invariant that public Production deployment remains closed.

## Protocol classification

The safe protocol classification is:

```text
IN_PROCESS
HTTP
WEBSOCKET
```

This value describes normalized ingress provenance only. It does not contain a socket, connection, request body, raw header set, URL credential or network client.

## Route semantics

The gateway exposes only transport-neutral route semantics matching existing MISSION-04 message kinds:

```text
CONTROL -> ExecutiveTransportMessageKind.CONTROL
READ    -> ExecutiveTransportMessageKind.READ
```

A control payload on the read route fails closed.

A read payload on the control route fails closed.

Unknown route values fail strict validation.

The gateway creates no buy/sell/order route.

## Session revalidation

A previously created `ExecutiveClientSessionBinding` is not treated as permanently current.

At `received_at`, the gateway calls `bind_executive_client_session(...)` again using the same session, surface and authenticated principal.

Therefore:

- an expired session fails closed;
- an expired authentication assertion fails closed;
- revoked/unknown sessions fail closed;
- mismatched session provenance remains blocked;
- no automatic refresh or renewal occurs.

The refreshed session evaluation timestamp and normalized envelope `received_at` are required to be identical.

## Existing envelope reuse

The gateway uses only the existing MISSION-04 builders:

- `build_executive_control_transport_envelope(...)`;
- `build_executive_read_transport_envelope(...)`.

The authenticated principal comes from the validated session binding.

The transport surface comes from the validated Delivery-2 client surface.

The gateway then applies `validate_executive_client_envelope_binding(...)` before producing a successful ingress value.

No second envelope model is introduced.

## Security boundary

`ExecutiveClientGatewayIngress` intentionally has no fields for:

- raw HTTP/WebSocket headers;
- cookies;
- Authorization values;
- access/refresh tokens;
- passwords;
- request body bytes;
- network sockets;
- provider/broker clients;
- provider credentials;
- platform secure-storage contents.

Only safe typed environment/protocol/route/session/envelope provenance is retained.

## Authority boundary

Successful gateway normalization is not authorization.

The required downstream chain remains:

```text
gateway normalization
   → MISSION-04 request guard
   → current authority
   → replay/idempotency
   → governed dispatch
   → deterministic receipt
   → audit/evidence
```

A gateway cannot force a trade, bypass Risk/Portfolio/Capital Protection or transform an unauthorized request into an authorized request.

## Determinism

The implementation preserves:

- immutable `dataclass(frozen=True, slots=True)` ingress;
- caller-supplied UUID/timestamps;
- explicit timezone-aware receive time;
- deterministic `logical_values()`;
- typed `Result / Success / Failure`;
- typed errors;
- no clock reads;
- no retries;
- no hidden reconnect;
- no polling/scheduler/thread;
- no Production environment value.

## Validation evidence

`tests/governance/test_executive_client_gateway.py` proves:

- control payload normalizes into the existing control envelope;
- read payload normalizes into the existing read envelope;
- Delivery-2 mobile transport mapping is preserved;
- route/payload mismatch fails closed;
- session is rechecked at gateway receipt time;
- Production is not a valid gateway environment;
- unknown protocol/route/payload values fail closed;
- ingress is immutable, deterministic and secret-free;
- direct construction with inconsistent receive timestamps fails closed.

## Explicitly not implemented

This delivery does not implement:

- public listeners;
- TLS termination;
- DNS;
- HTTP routing framework;
- WebSocket server lifecycle;
- OAuth/OIDC/passkey exchange;
- Production deployment;
- productive credentials;
- broker/provider connectivity;
- real-money execution.

## Acceptance result

The delivery is complete only after the unchanged QORE CI passes and the module, tests and architecture document merge.

The next authorized MISSION-05 delivery is:

```text
QORE-EXECUTIVE-STATE-SYNC-001
```

That delivery may define snapshots/subscriptions/version/freshness and `CURRENT / STALE / UNAVAILABLE / UNKNOWN` semantics. It must not turn local cache into authority.