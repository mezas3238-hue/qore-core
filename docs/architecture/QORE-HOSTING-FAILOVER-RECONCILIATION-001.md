# QORE-HOSTING-FAILOVER-RECONCILIATION-001 — Failover & Reconciliation

## Status

**MISSION-08 DELIVERY 7 — NON-PRODUCTION CONTRACTS**

This delivery composes the existing Runtime Registry, Health/Heartbeat, Execution Lease/Fencing and execution-reconciliation doctrine into a fail-closed readiness boundary for transferring account-scoped writer authority.

It does not implement productive failover, provider IO or automatic backup activation.

## Canonical sequence

The only authorized sequence remains:

```text
suspect runtime containment
 -> previous lease revoked or expired
 -> previous generation fenced
 -> external account/orders/positions reconciled
 -> relevant execution state reconciled
 -> ambiguity resolved
 -> candidate proven current/healthy
 -> request new monotonic fenced lease
```

There is no direct path from heartbeat loss to backup authority.

## Readiness, not acquisition

`evaluate_hosting_failover_readiness(...)` returns either:

```text
READY_FOR_LEASE_ACQUISITION
BLOCKED
```

READY carries only the next required `HostingFencingGeneration`. It does not create a lease and does not grant execution authority.

The actual replacement lease still uses the existing `acquire_hosting_execution_lease(...)` boundary, preserving the single-writer invariant and atomic-acquisition responsibility.

## Required evidence

The assessment requires:

- exact previous and candidate runtimes registered to the same TradingAccountId;
- previous runtime health containment;
- no currently authoritative lease for the account;
- previous account lease history to establish the fencing generation;
- candidate `HEALTHY` + `CURRENT` with no containment;
- provider-neutral external account reconciliation marked `MATCHED` with evidence;
- every supplied canonical `ExecutionReconciliationSnapshot` marked `MATCHED`;
- explicit timestamps covered by registry and lease snapshots.

Ambiguous/unknown account state or any DIVERGED/MISSING/UNEXPECTED execution reconciliation blocks authority transfer.

## External account reconciliation

`HostingExternalAccountReconciliation` is a narrow provider-neutral attestation for the account/order/position state needed by hosting failover.

Its closed states are:

```text
MATCHED
AMBIGUOUS
UNKNOWN
```

Only MATCHED may carry a matched evidence reference. AMBIGUOUS/UNKNOWN cannot masquerade as successful evidence.

Provider-specific account/order/position discovery remains behind adapters and is not implemented here.

## Fencing

The next generation is derived from the latest account lease history:

```text
previous generation N -> replacement request generation N+1
```

The assessment cannot reuse generation N and cannot itself mutate lease state.

A stale reconnecting writer therefore cannot regain authority simply because its process or heartbeat returns.

## Candidate health

A replacement candidate must be:

- bound to the same account;
- a distinct runtime;
- `HEALTHY`;
- heartbeat `CURRENT`;
- under no new-work containment.

Candidate health is necessary but never sufficient for execution authority.

```text
HEALTHY != EXECUTION AUTHORITY
```

## Ambiguity containment

Any unresolved external-state ambiguity produces BLOCKED and no next generation. The contract exposes no retry, redispatch, duplicate submission or corrective execution API.

The existing execution reconciliation object remains a pure comparison result and is reused rather than replaced.

## Authority boundary

This delivery does not create a Core Decision, trading signal, order intent, provider submission or broker connection.

```text
NO CORE DECISION -> NO NEW TRADING ACTION
AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT
```

Both invariants remain unchanged.

## MISSION-08 relationship

This is Delivery 7 of 11. The next ordered delivery is `QORE-HOSTING-TELEMETRY-001`.

MISSION-03 issue #146 remains externally blocked. MISSION-06 and Production remain CLOSED. Native Broker and Regional Futures remain out of scope.

## Quality gate

The exact PR head must pass the unchanged gate:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No ignores, casts, suppressions, test removal or gate weakening.
