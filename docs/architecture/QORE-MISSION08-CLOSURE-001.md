# QORE-MISSION08-CLOSURE-001 — Managed Hosting & Single-Writer Closure

## Status

**CLOSURE DELIVERY — NON-PRODUCTION READINESS REVIEW**

Opening baseline:

```text
main @ 4a381f477401be65f3e28a2197a7c5591673bc64
```

This delivery performs the final readiness, authority and safety review for the scope authorized by MISSION-08. It adds no production runtime and modifies no `src/qore` contract.

## Closure objective

Re-verify that the eleven-delivery MISSION-08 program forms one coherent provider-neutral Managed Hosting boundary while preserving single-writer execution control and all pre-existing Core authority rules.

The closure does not reinterpret Hosting as a trading engine.

## Strategic authority review

The governing invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

No Hosting contract owns or invents:

- BUY/SELL strategy;
- a new Core Decision;
- risk or sizing policy;
- SL/TP/trailing strategy;
- strategic close authority;
- broker/provider order submission.

Hosting may only act on infrastructure state already authorized by its contracts.

## Single-writer review

The closure re-validates:

```text
AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT
```

The hierarchy remains:

```text
Runtime Registry
  != execution authority

Health / Heartbeat
  != execution authority

Telemetry
  != execution authority

Hosting Orchestrator
  != lease authority

Canonical account-scoped execution lease
  = current infrastructure writer authority when valid
```

Fencing generations are monotonic and stale/revoked/expired authority fails closed.

## Failover review

The valid handoff sequence remains:

```text
failure/unreachable observation
 -> contain new work
 -> revoke/expire previous lease
 -> fence old generation
 -> reconcile account/orders/positions/execution evidence
 -> resolve ambiguity
 -> certify candidate health/freshness
 -> acquire new N+1 lease
 -> resume only authorized work
```

No `UNREACHABLE -> ACTIVATE BACKUP` shortcut exists.

No failover readiness object acquires the replacement lease itself.

Any ambiguous account or execution reconciliation state remains `BLOCKED`.

## Retry / redispatch review

MISSION-08 introduces no automatic order retry or redispatch mechanism.

The repository continues to require:

```text
AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE
```

Lost ACK, unknown external state or provider uncertainty is not permission to resend a trading action.

## Health / orchestration review

Health and heartbeat remain observational inputs.

Containment decisions can stop assignment of new work without electing another writer.

Hosting Orchestrator actions remain deployment-control decisions only:

```text
PREPARE_RUNTIME
REQUEST_DRAIN
CONTAIN_NEW_WORK
STOP_RUNTIME
NO_ACTION
```

The Orchestrator cannot acquire/revoke a lease, fence an account, create a Core Decision or mutate a provider.

## Telemetry review

Telemetry is a read-only projection of registry, health, lease and failover facts.

The current canonical writer observation vocabulary is:

```text
CURRENT_WRITER
OTHER_RUNTIME_IS_WRITER
NO_CURRENT_WRITER
```

Only `CURRENT_WRITER` telemetry may carry current lease and fencing identities.

Telemetry never grants writer authority.

## Commercial review

Hosting commercial failure is a gate on future hosted work, not position-close authority.

```text
PAYMENT_FAILED + OPEN POSITION
 -> SUSPEND_PENDING_FLAT
 -> NO NEW TRADES
 -> PRESERVE AUTHORIZED POSITION LIFECYCLE
```

After flat:

```text
SUSPENDED
MAY_STOP_WHEN_FLAT
```

Billing cannot liquidate, close strategically, mutate risk or automatically stop a writer.

`STOP_RUNTIME` remains a separate infrastructure decision and may apply only when its own authority conditions are satisfied.

## Secrets review

MISSION-08 reuses the canonical opaque `SecretRef` model.

The Hosting Execution Unit exposes `secret_refs` only. No password/token/bearer/Authorization/secret-value field is added to Managed Hosting contracts.

## Deterministic E2E evidence

Delivery 10 (`QORE-MISSION08-E2E-OFFLINE-001`) proves offline:

1. one account with two registered candidate runtimes;
2. Runtime A owns generation N;
3. telemetry observes only A as current writer;
4. A becoming unreachable causes containment, not backup activation;
5. active previous authority blocks failover;
6. canonical revocation removes A authority;
7. ambiguous account reconciliation blocks;
8. diverged execution reconciliation blocks;
9. matched reconciliation + healthy/current B produces readiness only;
10. canonical lease acquisition gives B generation N+1;
11. exactly one writer exists after handoff;
12. only B telemetry carries current lease/fencing identity;
13. commercial failure with an open position blocks new trades while preserving lifecycle;
14. flat suspension does not itself stop a runtime;
15. an explicit non-writer desired-stop state may produce `STOP_RUNTIME`.

No network, broker, provider SDK, productive secret or real-capital path is exercised.

## External evidence boundary

Issue #146 remains the independent MISSION-03 OANDA Practice operational-evidence blocker.

The closure does not claim that a real OANDA Practice run occurred and does not close or bypass that issue.

## Production review

The closure reasserts:

```text
Production = CLOSED
Futures Production = CLOSED
Native Broker Production = CLOSED
Real capital = CLOSED
```

No productive cloud/VPS/Kubernetes integration, automatic productive failover or productive broker credential is authorized by this delivery.

## Post-mission transition

The already merged roadmap:

```text
QORE-POST-MISSION08-FUTURES-RELIABILITY-ROADMAP
```

is the canonical planning input after MISSION-08 closes.

It does not itself open Production and does not justify retrospectively adding Futures implementation to MISSION-08.

The next program must be formally scoped from repository evidence before implementation begins.

## Closure artifacts

This delivery adds only:

- `docs/architecture/QORE-MISSION08-CLOSURE-001.md`;
- `docs/missions/MISSION-08-CLOSURE.md`;
- `tests/governance/test_mission08_closure_readiness.py`.

No file under `src/qore` is added or modified.

## Quality Gate

The exact closure PR head must pass:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Only after that exact GREEN head merges may MISSION-08 be considered formally completed.
