# QORE-CORPORATE-PROFIT-VAULT-EXPANSION-001 — Corporate Profit Vault Expansion

## Status

**IMPLEMENTED — NON-PRODUCTION CORPORATE ACCOUNTING FACTS; CASH MOVEMENT CLOSED**

Opening baseline:

```text
main @ 5a1a665ddd09b1545499c0cc7eb5d5f47d9e3cc9
```

MISSION-07 Delivery 11 expands the Corporate Profit Vault boundary so QORE corporate economics are represented separately from client trading performance.

## Fundamental separation

```text
CLIENT PERFORMANCE != CORPORATE REVENUE
REVENUE ATTRIBUTION != ACCOUNTS RECEIVABLE != CASH RECEIVED
DUE != PAID
```

Client trading P&L never posts directly into the Corporate Profit Vault.

The only supported paths are evidence-backed commercial facts produced by the Billing layer.

## Corporate revenue sources

Closed source vocabulary:

```text
EA_SUBSCRIPTION
WIDGET_SUBSCRIPTION
CORE_SERVICES
MANAGED_HOSTING
MANAGED_FUTURES
CORE_PERFORMANCE_FEE
```

Invoice-backed products map deterministically to their corporate revenue source.

Core performance-fee revenue uses the Billing `PerformanceFeeAssessment`, which itself can only be calculated from verified `EligibleClientPaidProfitRecord`.

## Revenue Attribution

`CorporateRevenueAttribution` records why QORE has a corporate revenue claim.

Invoice-backed attribution preserves:

- client ID;
- account ID when applicable;
- invoice ID;
- product kind/source;
- service period;
- amount/currency;
- attribution timestamp.

Performance-fee attribution instead preserves:

- client ID;
- trading account ID;
- performance-fee policy identity;
- Eligible Client Paid Profit record identity;
- accounting period;
- fee amount.

Revenue Attribution does not mean cash was received.

## Accounts Receivable

`CorporateAccountsReceivable` is a point-in-time debt snapshot derived from the commercial Billing ledger.

States:

```text
OPEN
PARTIALLY_SETTLED
SETTLED
```

Its outstanding amount is taken from Billing's allocation-derived invoice state.

A DUE invoice therefore remains a receivable even when revenue is already attributed.

## Cash Received

`CorporateCashReceived` is the strictest accounting fact in this delivery.

It can be created only from an existing `CommercialPaymentAllocation` whose payment is present in the Billing ledger and verified.

The resulting cash fact preserves:

- client/account attribution;
- invoice and product;
- allocation ID;
- payment ID;
- amount/currency;
- payment evidence reference;
- `paid_at` from the verified payment;
- corporate recording timestamp.

No invoice, entitlement, trading result or elapsed due date can synthesize Cash Received.

A payment allocation may create corporate Cash Received at most once in a `CorporateProfitVault` snapshot.

## Existing Executive read model

The repository already contains the MISSION-05 Executive Profit Vault read-model contracts.

This delivery does not rewrite or reopen that completed presentation work.

It introduces infrastructure accounting facts that future projection/composition may expose through existing executive read surfaces while preserving their presentation-only authority.

## Performance fee lineage

The permitted lineage is:

```text
Client Paid Profit evidence
  -> Eligible Client Paid Profit
  -> Billing PerformanceFeeAssessment (20%)
  -> Corporate Revenue Attribution
```

Cash Received remains a later payment-evidence fact and is not implied by the assessment.

## Tests

`tests/infrastructure/test_corporate_profit_vault.py` verifies:

- DUE invoice creates revenue attribution + open receivable but no cash;
- cash requires exact verified payment allocation evidence;
- missing allocation cannot be inferred as cash;
- one allocation cannot create cash twice;
- receivable reaches SETTLED only after Billing allocation settles the invoice;
- performance-fee revenue preserves Billing policy + eligible-paid lineage;
- no direct Client Performance, trading or manual mark-paid authority exists.

## Non-goals

No bank account, treasury transfer, payment processor, broker execution, client-money custody, cross-currency conversion, Managed Hosting runtime, Futures runtime, Production, MISSION-06 activation or MISSION-03 Gate #5 closure is introduced.

## Next delivery

After exact-head Quality Gate GREEN and merge:

```text
QORE-CLIENT-MULTIACCOUNT-READ-MODEL-001
```