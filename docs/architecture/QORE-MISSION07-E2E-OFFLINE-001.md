# QORE-MISSION07-E2E-OFFLINE-001 — Mission 07 Deterministic Offline E2E

## Status

**EVIDENCE DELIVERY — NON-PRODUCTION ONLY; PRODUCTIVE EXECUTION CLOSED**

Opening baseline:

```text
main @ dce388d86794c079177bb7aa6196c9afd40430c4
```

MISSION-07 Delivery 14 provides deterministic offline integration evidence across the client execution/commercial boundaries implemented in Deliveries 2–13.

No production runtime is added.

## E2E objective

The tests demonstrate composition of the mission invariants rather than introducing a new orchestration authority.

The exercised chain is:

```text
Core Trade Decision
  -> protected Client Decision envelope
  -> account/runtime/entitlement verification
  -> account-scoped anti-replay claim
  -> Client Execution Agent evaluation
  -> deterministic execution plan
  -> matched execution evidence
  -> position OPEN
  -> authorized trailing
  -> matched EXIT
  -> realized Client Performance
  -> client entitlement / paid / eligible-paid evidence
  -> trial/licensing evidence
  -> commercial invoice
  -> verified payment + allocation
  -> Corporate Revenue / Receivable / Cash facts
  -> multi-account Client Read Model
  -> client-scoped Widget presentation
```

## Same Core Decision, independent accounts

One canonical Core Decision is delivered to two independent trading accounts.

The security layer verifies each exact:

- account ID;
- runtime reference;
- entitlement reference;
- DecisionId;
- protected envelope;
- key lifecycle;
- replay key.

The replay key remains:

```text
(TradingAccountId, DecisionId)
```

Therefore the same Core Decision can legitimately fan out to Account A and Account B while a second delivery to Account A is rejected as duplicate.

The E2E evidence proves that the two accounts then pass through Agent policy/risk evaluation independently: Account A may produce an execution plan while Account B can be risk-blocked without changing Account A.

## Causal position lifecycle

The executable account continues through the merged lifecycle boundary:

```text
EXECUTE plan
 -> accepted + MATCHED entry evidence
 -> OPEN
 -> policy-bound TRAILING_STOP
 -> accepted + MATCHED exit evidence
 -> CLOSED
```

Every lifecycle action retains the exact originating account and Core Decision genealogy.

No automatic redispatch/retry path exists in the E2E fakes or production contracts.

## Client Performance -> Commercial evidence

A CLOSED position produces one realized performance record.

The E2E then composes the explicit economic lineage:

```text
Realized P&L
 -> Client Entitled Profit
 -> Client Paid Profit + payout evidence
 -> Eligible Client Paid Profit
```

The performance fee is calculated only from the final Eligible Paid record.

The E2E uses a smaller deterministic example:

```text
Eligible Client Paid Profit = USD 80
QORE fee                    = USD 16
```

This is the same versioned 20% policy already closed in Delivery 10.

## Trial evidence

The trial is started from the exact first eligible live execution receipt used by the position chain.

The test verifies:

```text
trial_started_at = eligible live execution time
trial_expires_at = trial_started_at + 14 days
```

No installation/device/runtime identifier participates in the trial origin.

## DUE != PAID and Corporate Vault

The E2E creates a real commercial invoice from the canonical EA plan.

Before payment allocation:

```text
invoice = DUE
Corporate Revenue Attribution exists
Accounts Receivable = OPEN
Corporate Cash Received = empty
```

After a VERIFIED payment and exact allocation:

```text
invoice = PAID
Cash Received can be created
Cash retains payment evidence + paid_at
```

No client trading result directly produces Corporate Cash.

## Safe suspension and Widget isolation

The E2E independently verifies commercial failure containment:

```text
EA payment failure + open position
 -> SUSPEND_PENDING_FLAT
 -> new-trade entitlement BLOCKED
 -> no close-position authority
```

The client read model still represents multiple independent accounts.

Widget payment failure produces:

```text
WIDGET SUSPENDED
Widget account payload hidden
```

while leaving the source read model and the other account's licensing state unchanged.

No Widget method can suspend the EA, mutate risk or submit an order.

## Deterministic test architecture

The E2E uses only:

- immutable public QORE contracts;
- explicit UUID fixtures;
- explicit timezone-aware timestamps;
- deterministic fake crypto/key/replay Protocol implementations;
- canonical `Result / Success / Failure` semantics;
- no network;
- no filesystem persistence;
- no broker/provider SDK;
- no secret value;
- no hidden wall clock;
- no background retry or scheduler.

The cryptographic fake proves orchestration only. It does not claim productive cryptographic certification.

## Tests

`tests/infrastructure/test_mission07_e2e_offline.py` contains three integrated scenarios:

1. Core Decision -> two account security/replay paths -> independent Agent risk decisions -> causal position lifecycle.
2. Closed lifecycle -> Client Performance -> trial -> Billing/payment -> Corporate Vault/performance-fee lineage.
3. Safe EA suspension + multi-account read model + isolated Widget suspension.

## Explicitly not implemented

This delivery adds no production `src/qore` runtime object.

It does not implement or authorize:

- productive crypto/key management;
- durable replay storage;
- broker/MT5/FCM calls;
- real order submission;
- real payment processor;
- bank/treasury movement;
- Managed Hosting;
- Native Broker Execution;
- Regional Futures Execution;
- Production;
- MISSION-06 activation;
- MISSION-03 Gate #5 closure.

## Acceptance

Delivery 14 is complete only when its exact PR head passes the unchanged repository Quality Gate:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

After merge the only remaining MISSION-07 delivery is:

```text
QORE-MISSION07-CLOSURE-001
```