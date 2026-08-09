# QORE-EXECUTIVE-CONTROL-PLANE-RESILIENCE-001 — Fail-Closed Timeout & Recovery Contracts

Status: **MISSION-04 DELIVERY 12 — CONTROL-PLANE RESILIENCE**

## Purpose

Define explicit timeout and recovery contracts for executive control-plane boundaries without hiding
retries, redispatch, sleeps, schedulers, threads, clocks, or transport behavior inside QORE Core.

This delivery is intentionally stricter than generic external-adapter retry policy. Executive control
operations may change governance state, so uncertain outcomes must be contained before any new action.

## Operations

The closed operation set is:

```text
authority-read
replay-claim
command-dispatch
read-dispatch
governance-mutation
audit-append
observability-emit
```

## Timeout contracts

`ExecutiveControlPlaneTimeout` is an explicit positive integer duration in milliseconds. It never
measures time or sleeps.

`ExecutiveControlPlaneOperationPolicy` binds one operation to one timeout and explicitly reports:

```text
automatic_retry_allowed = False
```

`ExecutiveControlPlaneResiliencePolicy` is a deterministic, fail-closed policy pack. It must contain
**exactly one timeout policy for every closed control-plane operation**; partial packs and duplicate
operations are rejected. It is configuration data only and never starts timers or retries.

## Failure kinds

The closed failure categories are:

```text
timeout
unavailable
ambiguous-outcome
```

These categories do not contain arbitrary upstream exception text.

## Recovery containment

`plan_executive_control_plane_recovery(...)` returns an immutable recovery requirement. It does not
perform the recovery itself.

Canonical requirements are:

```text
authority-read       -> reread-authority
replay-claim         -> verify-replay-claim
command-dispatch     -> verify-control-receipt
read-dispatch        -> issue-new-read-request
governance-mutation  -> reread-governance-state
audit-append         -> verify-audit-record
observability-emit   -> observability-can-degrade
```

Every recovery plan explicitly states:

```text
automatic_retry_allowed = False
automatic_redispatch_allowed = False
```

## Ambiguous command outcomes

A timeout or unavailable response after command dispatch does **not** prove that the command was not
applied. Therefore QORE must not send the same command again automatically.

The required next action is to verify the control receipt or equivalent authoritative result first.

## Ambiguous mutation outcomes

A compare-and-set mutation timeout does not prove failure. The required next action is to re-read the
current Governance state and compare it with expected/requested state before any new mutation attempt.

The existing replay/mutation identity remains protected; there is no automatic release or resubmit.

## Replay claim ambiguity

If replay-claim outcome is unknown, dispatch remains blocked. The authoritative claim must be
verified before proceeding.

This prevents a network/storage ambiguity from becoming a duplicate command.

## Read recovery

Read dispatch is non-mutating, but the same authorized request is not silently repeated. Recovery
requires an explicit new read request, preserving chronology and auditability.

## Audit recovery

Audit append ambiguity requires verification of the exact audit record before resubmission. Audit
persistence must not be assumed successful or failed from transport ambiguity alone.

## Observability degradation

Observability is not an authority source and must never mutate executive state. An observability sink
failure may degrade telemetry, but it must not trigger a corrective control action.

## Relationship to existing resilience

Existing adapter/connectivity/MISSION-03 resilience contracts remain unchanged. They may permit
explicit external-adapter retry schedules where appropriate.

This MISSION-04 contract deliberately forbids automatic retries and redispatch for executive control
operations because duplicate governance actions carry different safety consequences.

## Determinism

- immutable `dataclass(frozen=True, slots=True)` values;
- strict positive integer timeout values (`bool` rejected);
- exactly one timeout policy for every closed operation;
- explicit recovery UUID supplied by caller;
- explicit timezone-aware failure/planning timestamps;
- closed operation/failure/recovery enums;
- deterministic sorting and `logical_values()`;
- no implicit wall clock;
- no implicit identity generation;
- no hidden retry, sleep, scheduler, thread, or timer.

## Provider independence

No OANDA, broker, provider, network stack, database, retry library, scheduler, or platform dependency
is introduced.

MISSION-03 Gate #5 remains operationally blocked pending authorized OANDA Practice secret
provisioning.

## Safety

This delivery does not enable:

- Production;
- real capital;
- productive credentials;
- broker execution;
- autonomous trading;
- Risk bypass;
- corrective trading after reconciliation divergence.

A recovery plan is a requirement for the caller; it is not an action executor.

## Tests

Contract tests prove:

- strict timeout validation;
- complete deterministic policy packs;
- no automatic retry on any operation policy;
- operation-specific verification/re-read requirements;
- timeout/unavailable/ambiguous outcomes are all contained;
- command ambiguity never becomes automatic redispatch;
- explicit identity and timezone-aware chronology;
- immutable deterministic recovery plans.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppressions or gate weakening are permitted.
