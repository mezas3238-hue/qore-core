# QORE-EXECUTIVE-READ-DELIVERY-001

## Purpose

Close the final ambiguity between executive read authorization, the projection actually served, and the audit receipt that records that delivery.

## Problem closed

Before this delivery, `ExecutiveReadQueryPort.read()` returned only `ExecutiveReadReceipt`. The receipt proved that an authorized read was served, blocked, or failed, but the port contract did not carry the structured projection that was actually returned to the caller.

That allowed audit metadata and payload delivery to exist as separate, weakly bound concepts.

## Delivery contract

`ExecutiveReadDelivery` binds exactly:

- the `AuthorizedExecutiveReadRequest`;
- one structured `ExecutiveReadProjection`;
- the exact `ExecutiveReadReceipt`.

A successful delivery is valid only when:

- receipt status is `served`;
- receipt request ID equals the authorized request ID;
- receipt principal equals the authorized principal;
- receipt scope equals the authorized scope;
- receipt authority version equals the exact grant version;
- receipt correlation equals the authorized request correlation;
- receipt receipt-time does not predate authorization;
- projection scope equals the authorized scope;
- projection timestamp is timezone-aware;
- projection timestamp does not postdate receipt completion.

Any mismatch fails closed with `ExecutivePortValidationError`.

## Projection boundary

`ExecutiveReadProjection` and `ExecutiveReadProjectionMetadata` are structural `Protocol` contracts. This avoids a central union that would couple the port layer to every current and future executive read-model implementation.

A projection must provide:

- metadata with explicit `ExecutiveReadScope` and timezone-aware `projected_at`;
- deterministic `logical_values()`.

Concrete read models remain responsible for their own stronger domain invariants and evidence semantics.

## Query port evolution

`ExecutiveReadQueryPort.read()` now returns:

`Result[ExecutiveReadDelivery, ExecutivePortError]`

rather than receipt-only output.

A blocked or failed read does not create a successful projection delivery. Those outcomes remain represented by failure paths/audit evidence rather than a payload masquerading as successfully served data.

## Architectural boundary

The delivery is transport-neutral. It does not define JSON, REST, WebSocket, Android, iOS, Desktop, serialization, caching, persistence, or provider access.

Transport adapters may later map a validated delivery to client-specific DTOs without changing executive authorization semantics.

## Safety

No executive command is added. No buy/sell, submit/cancel/close, Risk bypass, broker/provider call, productive credential, Production authorization, real capital, retry loop, scheduler, thread, or automatic corrective behavior is introduced.

MISSION-03 remains active and unchanged.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is permitted.
