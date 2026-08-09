# QORE-COMMERCIAL-BILLING-PAYMENTS-001 — Billing, Payments & Reconciliation

## Status

**IMPLEMENTED — NON-PRODUCTION COMMERCIAL ACCOUNTING CONTRACTS; PAYMENT PROCESSOR CLOSED**

Opening baseline:

```text
main @ 727f83f34add37c99be6a5714ad60f841137889f
```

MISSION-07 Delivery 10 defines the commercial invoice/payment evidence boundary and the versioned QORE Core performance-fee calculation policy.

## Maximum accounting invariant

```text
DUE != PAID
```

A commercial obligation never becomes paid because time passed, because an invoice exists, because a client entitlement changed, or because trading generated profit.

Only verified external payment evidence can enter the Billing ledger and only explicit allocations against that verified payment can settle an invoice.

## Invoices

`CommercialInvoice` binds:

- invoice identity;
- client identity;
- account identity when the plan is account-scoped;
- exact `CommercialPlanId` + version;
- product kind;
- billing unit;
- canonical `MoneyAmount`;
- service period;
- issue timestamp;
- due timestamp.

Invoices are immutable. They contain no `paid` flag and expose no `mark_paid()` operation.

Initial status is derived as:

```text
no verified allocations -> DUE
```

## Verified payments

`VerifiedCommercialPayment` carries:

- payment ID;
- client ID;
- positive canonical monetary amount;
- paid timestamp;
- verification classification;
- opaque payment evidence reference.

Only:

```text
verification == VERIFIED
```

may be appended to the Billing ledger.

REJECTED or UNKNOWN payment observations cannot settle an invoice.

## Reconciliation / allocation

`CommercialPaymentAllocation` explicitly connects one verified payment to one invoice.

The ledger enforces:

- invoice exists;
- payment exists;
- payment is VERIFIED;
- exact client binding;
- exact currency binding;
- allocation timestamp does not predate payment evidence;
- total invoice allocations cannot exceed amount due;
- total allocations from one payment cannot exceed verified payment amount;
- unique allocation identity.

Invoice status is reconstructed from verified allocations:

```text
0 allocated            -> DUE
0 < allocated < amount -> PARTIALLY_PAID
allocated == amount    -> PAID
```

No manual status mutation exists.

## Plan scope

Invoices are generated from a priced `CommercialPlan`.

The existing billing-unit contract is preserved:

```text
ACCOUNT plan -> account_id required
CLIENT plan  -> account_id forbidden
```

Therefore EA invoices remain account-scoped and Widget invoices remain client-scoped.

## Core performance fee

The canonical MISSION-07 economic rule is implemented as a versioned policy:

```text
QORE Core Performance Fee = 20% of verified Eligible Client Paid Profit
```

The current policy requires exactly:

```text
2000 basis points
```

The calculation function accepts by type only:

```text
EligibleClientPaidProfitRecord
```

It cannot accept Gross/Realized Profit or Client Entitled Profit.

Example:

```text
Eligible Client Paid Profit = USD 8,000
QORE fee                     = USD 1,600
```

The calculation produces a typed assessment; it does not itself create cash received or prove that QORE was paid.

## Billing -> licensing boundary

Commercial payment standing may be projected into the already-closed licensing vocabulary:

```text
CURRENT        -> CURRENT
PAYMENT_FAILED -> PAYMENT_FAILED
UNKNOWN        -> UNKNOWN
```

Licensing then applies its existing safe-suspension policy.

Billing never receives authority to close or liquidate positions. With open positions, the downstream licensing rule remains `SUSPEND_PENDING_FLAT` while new entries are blocked.

## Corporate Vault boundary

Billing owns invoices, verified payments and allocations.

It does not own Corporate Cash Received.

The next delivery will consume this evidence to distinguish:

```text
Revenue Attribution
Accounts Receivable
Cash Received
```

and Cash Received will still require verified payment evidence.

## Tests

`tests/infrastructure/test_commercial_billing.py` verifies:

- invoices begin DUE and cannot be manually marked PAID;
- rejected payment cannot enter the ledger;
- partial/full status derives only from verified allocations;
- invoice overallocation fails closed;
- one verified payment cannot be overallocated across invoices;
- invoice scope follows the plan billing unit;
- 20% fee of USD 8,000 Eligible Paid Profit is USD 1,600;
- fee policy cannot silently change from 20%;
- PAYMENT_FAILED projects to Licensing without close authority;
- no broker/trade/corporate-cash authority is exposed.

## Non-goals

This delivery does not implement a payment processor SDK, card/bank credentials, automatic collections, Corporate Profit Vault cash posting, broker execution, position closing, Widget, Hosting, Futures, Production, MISSION-06 activation or MISSION-03 Gate #5 closure.

## Next delivery

After exact-head Quality Gate GREEN and merge:

```text
QORE-CORPORATE-PROFIT-VAULT-EXPANSION-001
```