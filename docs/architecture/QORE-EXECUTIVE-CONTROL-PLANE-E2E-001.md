# QORE-EXECUTIVE-CONTROL-PLANE-E2E-001 — Offline Executive Control Plane Composition

Status: **MISSION-04 DELIVERY 13 — OFFLINE END-TO-END COMPOSITION**

## Purpose

Demonstrate that the MISSION-04 executive control-plane contracts already merged in `main` compose
end to end with deterministic in-process fakes, without introducing a second production orchestrator,
network transport, provider adapter, database, scheduler, thread, hidden retry, or implicit clock.

This delivery is integration evidence. It does not replace any canonical boundary.

## Control path proven offline

The deterministic control fixture proves the following chain:

```text
AuthenticatedExecutivePrincipal
  -> ExecutiveAuthorityStateSource
  -> ExecutiveRequestGuard
  -> AuthorizedExecutiveControlIntent
  -> ExecutiveReplayClaimPort / ExecutiveReplayProtector
  -> ExecutiveCommandDispatcher
  -> ExecutiveControlCommandPort
  -> ExecutiveGovernanceMutationPort.compare_and_set()
  -> ExecutiveGovernanceMutationReceipt
  -> ExecutiveControlReceipt
  -> ExecutiveAuditEvidencePort.append()
```

The command fixture reserves the exact control receipt identity before Governance mutation, so the
materialized state mutation and final command receipt share the provenance contract established by
Delivery 7.

The integration test proves exactly one authority read, one replay claim, one command dispatch and one
Governance mutation call. No retry or duplicate dispatch occurs.

## Read path proven offline

The deterministic read fixture proves:

```text
AuthenticatedExecutivePrincipal
  -> ExecutiveAuthorityStateSource
  -> ExecutiveRequestGuard
  -> AuthorizedExecutiveReadRequest
  -> ExecutiveQueryDispatcher
  -> ExecutiveReadQueryPort
  -> ExecutiveReadDelivery
  -> ExecutiveAuditEvidencePort.append()
```

The served projection remains bound to its exact authorization and receipt. The audit record stores
only the already-established secret-free evidence references and identities; it does not persist the
projection payload.

## Fail-closed path proven offline

An `UNKNOWN` current authority snapshot is exercised explicitly.

The result is:

```text
UNKNOWN authority
  -> request guard Failure
  -> no replay claim
  -> no dispatch
  -> no Governance mutation
  -> BLOCKED durable audit evidence
```

This preserves the MISSION-04 rule that only `ACTIVE` current authority authorizes. A blocked path is
still auditable, but audit evidence never upgrades it into authority or action.

## Existing boundaries remain canonical

This delivery reuses, rather than duplicates:

- external validated executive authentication assertions;
- current authority state source;
- unified request guard;
- replay/idempotency claim protection;
- command and query dispatchers;
- executive command/query ports and receipts;
- Governance compare-and-set mutation boundary;
- durable executive audit evidence boundary;
- explicit control-plane resilience doctrine.

No new authorization logic or current-state model is introduced.

## Deterministic fixtures only

The integration fixtures are local and deterministic:

- all UUIDs are explicit constants;
- all timestamps are explicit and timezone-aware;
- all source snapshots and receipts are explicit;
- no `datetime.now()` is used;
- no `uuid4()` is used;
- no sleep, scheduler, thread, process or timer is used;
- no hidden retry or redispatch is used;
- no network call is made.

## Audit evidence

The control path appends durable records for:

```text
authentication
authority
command-dispatch
governance-mutation
```

The read path appends a `query-dispatch` record.

The fail-closed authority path appends a `BLOCKED` authority record.

All records preserve the same principal/correlation chain and, when authority exists, the exact
authority version. `NO_ACTION`, `BLOCKED` and `FAILED` remain first-class outcomes under the durable
audit contract even though this specific happy-path control fixture ends in `APPLIED`.

## Replay and resilience preservation

The happy control path must acquire replay protection before command dispatch.

This delivery does not release a replay claim after downstream ambiguity and does not invent automatic
recovery. Delivery 12 remains authoritative for timeout/unavailable/ambiguous outcomes:

- command ambiguity requires receipt verification;
- Governance mutation ambiguity requires current-state re-read;
- replay ambiguity requires authoritative claim verification;
- automatic retry and automatic redispatch remain forbidden.

## Provider independence

No OANDA, broker, provider, mobile platform, HTTP stack, database or external service is introduced.

MISSION-03 Gate #5 remains operationally blocked pending authorized OANDA Practice account/token
provisioning through the established secret boundary. Offline MISSION-04 evidence does not close that
gate.

## Safety

This delivery does not enable or authorize:

- Production;
- real capital;
- productive credentials;
- broker orders;
- autonomous real-money execution;
- Risk bypass;
- corrective trading;
- provider connectivity.

A green offline E2E test proves contract composition only.

## Scope choice

No production `ExecutiveControlPlaneOrchestrator` is added deliberately. The repository already owns
the individual canonical boundaries; Delivery 13 exists to prove their composition through tests,
not to create another object graph that could bypass those boundaries.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppressions or quality-gate weakening are permitted.

## Next delivery

After merge and verification, continue with MISSION-04 Delivery 14 closure/readiness. That closure is
limited to the MISSION-04 offline control-plane scope and must not activate MISSION-05 or Production.
