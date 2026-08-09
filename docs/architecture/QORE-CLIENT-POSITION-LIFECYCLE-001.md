# QORE-CLIENT-POSITION-LIFECYCLE-001 — Position Lifecycle & Causal Audit

## Status

**IMPLEMENTED — NON-PRODUCTION LIFECYCLE CONTRACTS; PRODUCTIVE EXECUTION CLOSED**

Opening baseline:

```text
main @ 4364890a7dbeaecf7571ec53162b7f1811c39f28
```

MISSION-07 Delivery 6 extends the already-verified Client Execution Agent plan into an immutable position lifecycle whose every state mutation is causally attributable to the originating Core Decision, account policy, execution policy, protection policy, rationale and evidence.

## Maximum authority invariant

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

This delivery does not originate strategy and does not add a broker/order submission path.

It consumes the `ClientExecutionPlan` produced only after the upstream decision/security/account/policy/risk/entitlement gates.

## Required genealogy

Every lifecycle action preserves:

```text
ACTION
  -> POSITION
  -> TRADING ACCOUNT
  -> CORE DECISION
  -> ACCOUNT POLICY + SNAPSHOT
  -> EXECUTION POLICY
  -> PROTECTION / TRAILING POLICY
  -> RATIONALE CODE
  -> EVIDENCE REFERENCE
```

No orphan lifecycle action is accepted.

The lifecycle constructor validates the exact causal references against the originating `ClientExecutionPlan` for every appended action.

## Canonical execution evidence reuse

This delivery deliberately does not invent a second execution identity or reconciliation subsystem.

It reuses the existing canonical:

- `ExecutionReceipt` / `ExecutionReceiptId`;
- `ExecutionStatus`;
- `ExecutionReconciliationSnapshot`;
- `ExecutionReconciliationStatus`.

A position transition that depends on execution evidence requires:

```text
receipt.status == ACCEPTED
reconciliation.status == MATCHED
reconciliation.expected == exact receipt
reconciliation.observed is present
transition timestamp >= receipt/reconciliation timestamps
```

`DIVERGED`, `MISSING`, `UNEXPECTED` or otherwise ambiguous execution evidence cannot create/close a position lifecycle.

There is no automatic corrective execution, retry or redispatch.

## ClientExecutionConfirmation

A confirmed entry binds:

- the exact `ClientExecutionPlan`;
- the accepted canonical execution receipt;
- matched reconciliation evidence;
- explicit fill price;
- explicit confirmation timestamp;
- opaque lifecycle evidence reference.

Only such a confirmation can be supplied to `open_client_position(...)`.

## ClientPositionId

`ClientPositionId` is a caller-supplied opaque UUID scoped to the client lifecycle contract.

It is not a broker ticket, broker account number, provider credential or substitute for `ExecutionReceiptId`.

## Lifecycle states

The closed lifecycle vocabulary is:

```text
OPEN
CLOSED
```

A lifecycle is immutable and append-only. Transition functions return a new object and never mutate an earlier snapshot.

A CLOSED lifecycle rejects further trailing and further close transitions.

## Action vocabulary

The first-class auditable actions are:

```text
OPEN
TRAILING_STOP
EXIT
```

Every action has an explicit caller-supplied action ID, timestamp, rationale code and evidence reference.

### OPEN

`OPEN` is the first and only initial action.

It binds the entry execution receipt and the initial Stop Loss from the authorized execution plan.

### TRAILING_STOP

Trailing is permitted only when the originating execution plan contains a `TrailingPolicyReference`.

Every trailing action records:

```text
position_id
decision_id
trailing_policy_ref
previous_stop
new_stop
occurred_at
rationale_code
evidence_ref
```

Stop continuity is mandatory: the next action's `previous_stop` must equal the lifecycle's previously established stop.

Trailing protection must be monotonic:

```text
BUY  -> previous_stop < new_stop < take_profit
SELL -> take_profit < new_stop < previous_stop
```

A move that worsens protection or crosses the target fails closed.

Trailing remains deterministic delegated protection under the policy already bound to the Core Decision; it is not an independent strategic decision.

### EXIT

An exit requires a distinct accepted execution receipt and exact MATCHED reconciliation.

The terminal action records the exit price, closed reason, rationale and evidence while retaining the same originating account/decision/policy genealogy.

Exit reasons are explicit, closed values:

```text
STOP_LOSS
TAKE_PROFIT
CORE_POLICY
AUTHORIZED_MANUAL
```

This vocabulary records causal classification only. It does not create an order-submission authority.

## Chronology / action integrity

The lifecycle requires:

- one non-empty action history;
- `OPEN` first;
- globally unique action IDs within the position;
- monotonic action timestamps;
- no action after `EXIT`;
- exact stop continuity through every trailing action;
- `current_stop` equal to the stop reconstructed from action history;
- OPEN state without exit/closed timestamp;
- CLOSED state with a terminal EXIT matching `closed_at`.

## Ambiguity containment

An uncertain execution result is not interpreted optimistically.

If canonical reconciliation is not `MATCHED`:

```text
NO POSITION TRANSITION
NO RETRY
NO AUTOMATIC REDISPATCH
```

The caller must reconcile the external state explicitly through the existing reconciliation boundary before a lifecycle transition is accepted.

This preserves the no-automatic-redispatch doctrine established by earlier execution and MISSION-04/05 work.

## Determinism

The delivery uses:

- frozen/slotted immutable contracts;
- explicit caller-supplied UUIDs;
- explicit timezone-aware timestamps;
- typed enum states/reasons;
- typed `Result / Success / Failure` transition boundaries;
- deterministic `logical_values()`;
- no hidden clock;
- no background threads/schedulers;
- no mutable global state.

## Tests

`tests/infrastructure/test_client_position_lifecycle.py` covers:

- opening only from exact matched execution confirmation;
- complete causal genealogy from action to position/account/Core Decision/policies/evidence;
- rejection of ambiguous/diverged execution evidence;
- BUY trailing monotonic improvement with explicit previous/new stop evidence;
- SELL trailing monotonic improvement;
- rejection of worsening or target-crossing trailing moves;
- rejection of trailing when no trailing policy is authorized;
- close only from a distinct matched execution receipt;
- ambiguous exit leaves the original position OPEN and causes no redispatch;
- closed lifecycle cannot be trailed or closed again;
- orphan/mismatched account action is rejected;
- absence of broker/order/redispatch authority.

## Explicitly not implemented

This delivery does not implement or authorize:

- concrete MT5/EA runtime;
- broker/FCM API calls;
- order submission;
- provider credentials;
- automatic retry/redispatch;
- durable lifecycle database;
- productive telemetry/evidence store;
- account risk aggregation;
- Billing/Payments;
- Trial/Licensing;
- Widget;
- Managed Hosting/failover;
- Futures;
- Production;
- MISSION-06 activation;
- MISSION-03 Gate #5 closure.

## Acceptance result

This delivery is complete only after the exact PR head passes the unchanged repository Quality Gate:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

and merges with only the intended architecture, contracts and tests.

After merge, the next authorized MISSION-07 delivery is:

```text
QORE-CLIENT-PERFORMANCE-LEDGER-001
```

That delivery will consume closed, causally attributable position outcomes and keep account performance strictly separate from QORE corporate revenue.