# QORE-EXECUTIVE-CONTROL-PLANE-OBSERVABILITY-001 — Typed Executive Observability Signals

Status: **MISSION-04 DELIVERY 11 — CONTROL-PLANE OBSERVABILITY**

## Purpose

Expose deterministic, secret-free observability signals for the executive control plane without
introducing a metrics backend, mutable counter state, telemetry transport, or hidden instrumentation.

This delivery reuses the durable `ExecutiveAuditEvidenceRecord` produced by Delivery 8. It does not
create a second audit history model.

## Observable stages

The closed stages are:

```text
authentication
authority
authorization
command-dispatch
query-dispatch
governance-mutation
audit
```

The first six stages are projected directly from durable executive audit evidence. The `audit` stage
represents successful persistence of one exact durable audit record.

## Outcomes

The closed outcomes are:

```text
succeeded
no-action
blocked
failed
```

The observation preserves the exact audit outcome. `NO_ACTION`, blocked and failed paths therefore
remain observable rather than disappearing from telemetry.

## Metric semantics

Each immutable observation exposes a stable aggregation key:

```text
executive.control-plane.<stage>.<outcome>
```

For example:

```text
executive.control-plane.authentication.succeeded
executive.control-plane.authority.blocked
executive.control-plane.command-dispatch.no-action
executive.control-plane.governance-mutation.failed
```

QORE Core emits facts only. It does not keep counters, histograms, rolling windows, exporters, or
background telemetry state. A future observability adapter may aggregate the emitted facts.

## Observation content

`ExecutiveControlPlaneObservation` contains only:

- explicit observation ID;
- closed stage;
- closed outcome;
- executive principal;
- correlation ID;
- explicit timezone-aware observation time;
- exact durable audit record ID;
- sanitized evidence references already validated by the audit boundary;
- optional authority version.

It intentionally contains no arbitrary metadata map, free-text error, payload, reason narrative,
credential, or private reasoning.

## Boundary

`ExecutiveControlPlaneObservabilityPort` is a structural `Protocol`:

```text
emit(ExecutiveControlPlaneObservation)
  -> Result[ExecutiveControlPlaneObservation, ExecutiveControlPlaneObservabilityError]
```

No backend is selected. No retry semantics are hidden in this boundary.

## Audit relationship

Observability never becomes the source of truth for authority, authorization, dispatch, Governance
state, or audit history.

The direction is one way:

```text
control-plane result
  -> durable audit evidence
  -> immutable observability signal
```

If observability fails, it must not reconstruct or mutate executive state.

## Relationship to existing observability

Existing adapter and MISSION-03 observability contracts remain intact. They observe external adapter
health and real-market preparation surfaces.

This delivery is specifically scoped to MISSION-04 executive governance stages and therefore does not
reuse provider-oriented adapter descriptors or market-test observation categories.

## Determinism

- `dataclass(frozen=True, slots=True)` values;
- explicit UUID observation IDs;
- explicit timezone-aware timestamps;
- deterministic evidence ordering inherited from executive audit records;
- stable metric names derived from closed enums;
- deterministic `logical_values()`;
- no implicit wall clock;
- no implicit identity generation;
- no hidden scheduler, thread, retry, sleep, or aggregation state.

## Secret discipline

The observation does not expose:

- passwords;
- bearer/access tokens;
- authorization headers;
- client secrets;
- provider credentials;
- biometric material;
- arbitrary upstream errors;
- free-text control reasons;
- projection payloads;
- private reasoning.

## Provider independence

No OANDA, broker, provider, database, telemetry vendor, mobile SDK, HTTP stack, or platform dependency
is introduced.

MISSION-03 Gate #5 remains operationally blocked pending authorized OANDA Practice secret
provisioning.

## Safety

Nothing in this delivery enables:

- Production;
- real capital;
- productive credentials;
- autonomous trading;
- broker orders;
- Risk bypass;
- corrective trading.

Observability has no authority.

## Tests

Contract tests cover:

- every audited executive stage;
- success, no-action, blocked and failed outcomes;
- stable metric naming;
- exact audit record/correlation/authority binding;
- dedicated audit-persistence observation;
- immutable deterministic signals;
- no payload/reason/metadata field leakage;
- explicit ID and chronology validation;
- structural observability sink substitution.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppressions or gate weakening are permitted.
