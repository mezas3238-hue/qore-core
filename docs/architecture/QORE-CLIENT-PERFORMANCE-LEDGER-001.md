# QORE-CLIENT-PERFORMANCE-LEDGER-001 — Client Performance Ledger

## Status

**IMPLEMENTED — NON-PRODUCTION ACCOUNT PERFORMANCE CONTRACTS; BILLING/CORPORATE CASH CLOSED**

Opening baseline:

```text
main @ 4446348a69f1b0049d1b87baf04839950ceb96a0
```

MISSION-07 Delivery 7 defines the canonical append-only performance accounting boundary for each independent client trading account.

## Separation invariant

```text
CLIENT TRADING PERFORMANCE != QORE CORPORATE REVENUE
```

This ledger records client/account economic evidence. It does not invoice, charge, mark corporate cash received or authorize trading.

## Account scope

One `ClientPerformanceLedger` belongs to exactly one `TradingAccountId` and one canonical `CurrencyCode`.

Every record must match both. Records from different accounts cannot be combined into one risk/performance authority.

Client-level aggregation, when introduced later, is read-only presentation.

## Realized performance

`ClientRealizedPerformanceRecord` is created only from a CLOSED `ClientPositionLifecycle` and preserves:

- account ID;
- position ID;
- originating Core `DecisionId`;
- terminal EXIT action ID;
- signed realized P&L (`MoneyAmount`), including losses;
- evidence reference;
- explicit timestamp.

Provider-specific P&L conversion is not invented here. The ledger consumes an already-normalized monetary result and validates its account/currency/causal binding.

A position can have only one canonical realized record.

## Corrections

Historical realized records are immutable.

Corrections are separate append-only delta records with:

```text
correction record id
account id
corrects realized record id
non-zero monetary adjustment
correction timestamp
evidence reference
```

The original record is never rewritten or deleted.

`net_realized_pnl` is reconstructed deterministically from original realized records plus correction deltas.

## Profit vocabulary

The delivery makes the economic separation explicit:

```text
GROSS / REALIZED TRADING RESULT
CLIENT ENTITLED PROFIT
CLIENT PAID PROFIT
ELIGIBLE CLIENT PAID PROFIT
```

These are not interchangeable states.

### ClientEntitledProfitRecord

Represents an evidence-backed contractual client entitlement under a version/reference of payout policy.

Entitlement is not payment.

### ClientPaidProfitRecord

Represents client profit actually paid and requires:

- an existing entitlement record;
- same account/currency;
- amount not exceeding entitlement;
- explicit `ClientPayoutEvidenceReference`;
- `paid_at` not preceding entitlement evaluation.

Realized P&L alone cannot create a PAID record.

### EligibleClientPaidProfitRecord

Represents the verified subset of paid client profit that a later commercial performance-fee policy may use.

It requires:

- an existing paid-profit record;
- explicit eligibility/payout-policy reference;
- evidence reference;
- amount not exceeding the verified paid amount.

This record still does not calculate or book QORE corporate revenue.

## Performance-fee boundary

MISSION-07's canonical rule remains:

```text
QORE Core Performance Fee
 = 20% of verified Eligible Client Paid Profit
```

This delivery deliberately stops before the fee calculation/Invoice/Corporate Profit Vault layers.

Its responsibility is only to produce the typed, evidence-backed `EligibleClientPaidProfitRecord` that those later commercial contracts may consume.

Therefore neither Gross Profit nor Client Entitled Profit can be mistaken for a fee base.

## DUE != PAID

This ledger contains no invoice/payment-reconciliation concept for money owed to QORE.

A client payout `PAID` state here refers only to verified client payout evidence from the prop/account economic domain.

Future QORE Billing must independently prove invoice payment before any corporate Cash Received state exists.

## Determinism

The ledger preserves:

- immutable frozen/slotted records;
- caller-supplied UUID identities;
- explicit timezone-aware timestamps;
- canonical `MoneyAmount` / `CurrencyCode`;
- deterministic logical values;
- globally unique record IDs within one ledger;
- append-only lineage;
- no hidden clock;
- no provider IO;
- no mutable global ledger.

## Tests

`tests/infrastructure/test_client_performance_ledger.py` proves:

- positive and negative realized results are retained;
- net realized result is deterministic;
- one position cannot be realized twice;
- corrections preserve original records and apply explicit deltas;
- PAID requires existing entitlement and payout evidence;
- PAID cannot be inferred directly from trading P&L;
- Eligible Paid is capped by verified paid amount;
- accounts cannot contaminate one another;
- no Billing, Corporate Vault or execution authority is exposed.

## Explicitly not implemented

This delivery does not implement or authorize:

- payout provider integration;
- productive payment verification service;
- QORE invoices or payment processor;
- QORE performance-fee booking;
- Corporate Profit Vault posting;
- client-level cross-account risk aggregation;
- broker/MT5/FCM execution;
- Trial/Licensing;
- Widget;
- Managed Hosting;
- Futures;
- Production;
- MISSION-06 activation;
- MISSION-03 Gate #5 closure.

## Acceptance result

This delivery is complete only after its exact PR head passes the unchanged Quality Gate:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

and merges with only its intended source/tests/architecture files.

After merge the next authorized delivery is:

```text
QORE-CLIENT-TRIAL-LICENSING-001
```