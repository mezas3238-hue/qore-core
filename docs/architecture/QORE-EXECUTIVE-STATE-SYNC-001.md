# QORE-EXECUTIVE-STATE-SYNC-001 — Executive State Sync & Freshness

## Status

**IMPLEMENTED — PRESENTATION-ONLY STATE FRESHNESS BOUNDARY**

Opening baseline:

```text
main @ 84fdac6db5d937f2dc5cddb98aadac1bcfdd26fd
```

This is MISSION-05 Delivery 5.

## Purpose

Make client-visible state freshness explicit so Desktop/iOS/Android never treat cached presentation data as silently current governance state.

The boundary reuses an already-authorized `ExecutiveReadDelivery` as the source of every concrete snapshot.

## State model

The only presentation-state classifications are:

```text
CURRENT
STALE
UNAVAILABLE
UNKNOWN
```

They have distinct meanings:

- `CURRENT` — an exact authorized snapshot exists and the explicit freshness deadline has not passed;
- `STALE` — an exact authorized snapshot exists but its explicit freshness deadline has passed;
- `UNAVAILABLE` — no snapshot is being represented as current because the source/delivery is unavailable;
- `UNKNOWN` — no snapshot is being represented because current state cannot be established safely.

The contract does not guess current state from a local cache.

## Snapshot contract

`ExecutiveClientStateSnapshot` binds:

- explicit snapshot id;
- strict positive integer version;
- exact `ExecutiveReadDelivery`;
- explicit client receipt time;
- explicit freshness deadline.

A snapshot cannot be received before the underlying authorized read completed.

The freshness deadline cannot predate snapshot receipt.

The snapshot read scope is derived from the exact authorized request already contained in the `ExecutiveReadDelivery`.

## Freshness evaluation

`evaluate_executive_client_state_snapshot(...)` receives a caller-supplied timezone-aware evaluation timestamp.

It returns:

```text
evaluated_at <= fresh_until  -> CURRENT
evaluated_at >  fresh_until  -> STALE
```

Evaluation before the snapshot was received fails closed.

No clock read, timer or background expiry task exists in the contract.

## Absent state

`build_executive_client_absent_state(...)` creates only:

```text
UNAVAILABLE
UNKNOWN
```

Absent state carries no snapshot.

This prevents a client from attaching stale/cached data to `UNAVAILABLE` or `UNKNOWN` while making it look authoritative.

If prior data is intentionally shown after its freshness deadline, it must remain an exact `STALE` snapshot.

## Version doctrine

`ExecutiveClientStateVersion` is:

- an explicit positive `int`;
- not a `bool`;
- not a string coerced to int;
- supplied by the caller/source rather than auto-generated.

Version identity is presentation synchronization metadata. It does not replace domain/projection versions inside the underlying read model.

## Subscription contract

`ExecutiveClientSubscription` contains only:

- subscription id;
- client surface id;
- exact `ExecutiveReadScope`;
- explicit creation timestamp.

A subscription grants no command authority.

It contains no executive grant, control action, broker operation or execution method.

`ExecutiveClientSubscriptionUpdate` binds one subscription to one exact snapshot and enforces:

- read scope equality;
- delivery timestamp not before snapshot receipt;
- delivery timestamp not before subscription creation.

Subscription delivery is presentation synchronization only.

## Command safety

No state snapshot, subscription or update can authorize a command.

A sensitive action must still enter through the current chain:

```text
client session
  -> client gateway
  -> MISSION-04 authentication/current authority/request guard
  -> replay/idempotency
  -> command dispatch
  -> deterministic receipt
  -> audit/evidence
```

A client looking at `CURRENT` state does not receive implicit future command authority.

A client looking at `STALE`, `UNAVAILABLE` or `UNKNOWN` state must not silently promote that state to a command precondition.

## Fail-closed invariants

The implementation rejects:

- zero/negative/non-int/bool versions;
- naive timestamps;
- snapshot receipt before underlying read completion;
- freshness deadline before snapshot receipt;
- subscription/snapshot scope mismatch;
- update delivery before snapshot/subscription creation;
- `CURRENT` classification after freshness expiry;
- `STALE` classification before freshness expiry;
- `CURRENT` or `STALE` without a snapshot;
- `UNAVAILABLE` or `UNKNOWN` carrying a snapshot.

## Determinism

The implementation preserves QORE doctrine:

- immutable `dataclass(frozen=True, slots=True)` values;
- explicit UUIDs;
- explicit timezone-aware timestamps;
- strict bool/int handling;
- deterministic `logical_values()`;
- typed `Result / Success / Failure`;
- typed errors;
- no hidden retry;
- no timer/scheduler/thread;
- no automatic cache promotion;
- no secret material.

## Validation evidence

`tests/governance/test_executive_state_sync.py` proves:

- the same exact snapshot deterministically evaluates `CURRENT` then `STALE` across the freshness boundary;
- unavailable/unknown state is explicit and snapshot-free;
- absent-state builder cannot manufacture current/stale state;
- state version rejects bool/coercion/invalid values;
- subscription update requires exact read scope;
- subscription values expose no command/authority surface;
- timestamp chronology fails closed;
- direct manual current/stale misclassification fails closed.

## Explicitly not implemented

This delivery does not implement:

- a WebSocket event loop;
- background polling;
- local database/cache authority;
- push notifications;
- automatic reconnect;
- offline command queue;
- command retry;
- Production deployment.

## Acceptance result

The delivery is complete only after unchanged QORE CI passes and the expected module, tests and architecture document merge.

The next authorized MISSION-05 delivery is:

```text
QORE-EXECUTIVE-NOTIFICATIONS-001
```

That delivery may define deterministic interruption/notification contracts. A notification will remain presentation evidence and will not execute commands.