# QORE-MISSION04-E2E-OFFLINE-COMPOSITION-001 — Executive Control Plane Offline E2E

Status: **MISSION-04 DELIVERY 13 — DETERMINISTIC OFFLINE COMPOSITION EVIDENCE**

## Purpose

Demonstrate that the executive governance contracts already merged during MISSION-04 compose into a
complete fail-closed control-plane chain without adding a second orchestration framework or any live
network/provider dependency.

This delivery is evidence of composition. It intentionally adds no new production runtime object.

## Canonical command chain exercised

The deterministic command/mutation scenario composes:

```text
AuthenticatedExecutivePrincipal
  -> ExecutiveAuthorityStateSource.read_current
  -> ExecutiveRequestGuard.authorize_control
  -> build_executive_control_replay_claim
  -> ExecutiveReplayProtector
  -> ExecutiveCommandDispatcher
  -> ExecutiveGovernanceMutationPort.compare_and_set
  -> ExecutiveAuditEvidencePort.append
  -> ExecutiveControlPlaneObservabilityPort.emit
```

The scenario proves exact one-call behavior for:

- authority-state read;
- replay claim;
- command dispatch;
- Governance compare-and-set mutation.

It also proves that authentication, authority, dispatch and mutation evidence are durably representable
through the executive audit boundary and can be projected into typed observability signals.

## Canonical read chain exercised

The deterministic read scenario composes:

```text
AuthenticatedExecutivePrincipal
  -> ExecutiveAuthorityStateSource.read_current
  -> ExecutiveRequestGuard.authorize_read
  -> ExecutiveQueryDispatcher
  -> ExecutiveReadDelivery
  -> ExecutiveAuditEvidencePort.append
```

The projection and read receipt remain bound to the exact authorized request.

## Fail-closed scenario exercised

A current authority snapshot with lifecycle state `UNKNOWN` is evaluated through the same request
guard.

Expected behavior:

```text
UNKNOWN authority
  -> AUTHORITY_NOT_ACTIVE
  -> NO DISPATCH
  -> BLOCKED authority audit evidence
```

The blocked path remains auditable and carries no fabricated authority version.

## Existing contracts only

The E2E tests use the already-merged MISSION-04 contracts directly:

- authenticated executive principal;
- current authority source;
- unified request guard;
- command and query dispatch;
- replay/idempotency protection;
- Governance CAS mutation;
- durable audit evidence;
- control-plane observability.

No replacement wrapper, alternative read model, alternative receipt, alternative authorization rule,
or second state reducer is introduced.

## Deterministic fakes

All external behavior is represented with instance-local deterministic fakes implementing the existing
Protocols.

The fakes:

- perform no network access;
- use explicit fixed IDs;
- use explicit timezone-aware timestamps;
- contain no sleeps;
- contain no retry loops;
- contain no schedulers or threads;
- do not generate hidden identities;
- do not persist outside the test process.

They exist only to prove contract composition.

## Replay and duplicate safety

The command path acquires the explicit replay claim before command dispatch. The test does not bypass
or remove replay protection.

Exactly one command-port invocation is asserted. There is no automatic retry or redispatch.

## Governance mutation safety

The mutation is driven by an already-authorized command and the exact control receipt. The fake CAS
port receives exactly one typed mutation request and returns a receipt built through the canonical
mutation receipt builder.

No history replay or hidden reducer is used to derive current Governance state.

## Audit evidence

The successful command scenario preserves distinct audit evidence for:

```text
authentication
authority
command-dispatch
governance-mutation
```

The read scenario preserves query-dispatch evidence.

The blocked authority scenario preserves blocked authority evidence.

`NO_ACTION`, blocked and failed semantics remain available through the same audit contracts even
though the successful E2E fixture uses an applied command.

## Observability

Durable executive audit evidence is projected into the typed MISSION-04 observability boundary. An
additional `audit` stage observation demonstrates that successful audit persistence can itself be
observed.

Observability remains downstream evidence only; it cannot grant authority or mutate state.

## Provider independence

The E2E composition contains no:

- OANDA client;
- broker adapter;
- market feed;
- HTTP server;
- mobile transport;
- database;
- external credentials;
- external network request.

MISSION-03 Gate #5 remains operationally blocked until OANDA Practice resources are provisioned
through an authorized secret boundary.

## Production boundary

This delivery does **not** authorize or enable:

- Production;
- real capital;
- productive credentials;
- broker orders;
- autonomous real-money execution;
- Risk bypass;
- corrective trading.

Passing offline E2E tests is evidence of MISSION-04 contract composition only.

## Tests

`tests/governance/test_mission04_e2e_offline_composition.py` demonstrates:

1. authenticated control request -> active authority -> authorization -> replay claim -> command
   dispatch -> Governance mutation -> audit -> observability;
2. authenticated read request -> active authority -> authorization -> read delivery -> audit;
3. unknown authority -> fail-closed block before dispatch -> blocked audit evidence.

The tests also assert exact one-call invocation on the mutable/downstream boundaries.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppressions or quality-gate weakening are permitted.

## Closure boundary

A green merge of this delivery proves MISSION-04 offline E2E composition. It does not by itself close
MISSION-04. Delivery 14 must separately verify readiness/closure scope against the repository and must
not open MISSION-05 or Production automatically.
