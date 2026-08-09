# QORE-COMMERCIAL-PRODUCTS-PLANS-001 — Products & Plans

## Status

**IMPLEMENTED — NON-PRODUCTION PRODUCT CATALOG; BILLING/PAYMENTS CLOSED**

Opening baseline:

```text
main @ 4363c21cbbbdc3f1b50637a9b5bbd1a59fbeefa0
```

MISSION-07 Delivery 9 defines the versioned commercial product catalog used by later Billing/Entitlements without granting any trading authority.

## Independent products

The canonical product family is:

```text
CLIENT_EXECUTION_AGENT
CLIENT_WIDGET
CORE_SERVICES
MANAGED_HOSTING
MANAGED_FUTURES
```

Each product has an independent identity and availability state.

No product is implicitly bundled into another product.

In particular:

```text
EA subscription != Managed Hosting
Widget subscription != EA subscription
```

## Confirmed pricing

The only pricing decisions confirmed for the current MISSION-07 catalog are:

### QORE Client Execution Agent

```text
USD 29 / trading account / month
```

Canonical billing unit:

```text
ACCOUNT
```

### QORE Client Widget

```text
USD 9.99 / client / month
```

Canonical billing unit:

```text
CLIENT
```

A client with N accounts still has one client-scoped Widget plan.

## Managed Hosting

Managed Hosting is an independent premium product.

It is **not included automatically** in the EA USD 29/account/month plan.

Its production price is not confirmed by this delivery and therefore remains:

```text
availability = VALIDATION_REQUIRED
price = None
```

## Core Services

Core Services exists as an independent catalog identity but this delivery does not invent a production price.

It remains `VALIDATION_REQUIRED` until a later canonical commercial decision authorizes pricing.

## Managed Futures

Managed Futures remains:

```text
availability = VALIDATION_REQUIRED
price = None
```

The previously discussed USD 149/account/month value remains a **provisional financial hypothesis**, not a canonical production plan.

This contract intentionally rejects assigning a canonical price to a `VALIDATION_REQUIRED` product.

Before Managed Futures pricing can become confirmed, the required external/business validation remains outside this delivery, including broker/FCM agreements, market-data costs, infrastructure economics, redundancy, account density, support, payment costs, legal/compliance and margin validation.

## Versioning

Commercial plan identity and version are explicit:

```text
CommercialPlanId
CommercialPlanVersion
```

A price or billing-unit change must be represented by a new canonical plan version rather than silently mutating historical commercial state.

## Billing units

Closed billing-unit vocabulary:

```text
ACCOUNT
CLIENT
SERVICE
```

Closed cadence vocabulary for the current catalog:

```text
MONTHLY
```

The contract enforces:

```text
CLIENT_EXECUTION_AGENT -> ACCOUNT
CLIENT_WIDGET -> CLIENT
```

Other products remain explicitly scoped by their own plan.

## Price representation

Prices reuse canonical provider-neutral:

```text
MoneyAmount
CurrencyCode
```

No floating-point commercial amount is introduced.

Confirmed plans require a positive explicit `MoneyAmount`.

Validation-required products must not carry a canonical price.

## Catalog invariants

`CommercialCatalog` requires:

- unique product identities;
- unique product kinds;
- unique `(plan_id, version)` pairs;
- every plan references a product present in the catalog;
- exact plan lookup by product kind + version;
- immutable deterministic logical values.

## Authority boundary

Products/Plans owns commercial catalog classification only.

It does **not**:

- charge a payment method;
- create or settle an invoice;
- prove payment;
- activate a trading entitlement;
- close a position;
- submit an order;
- access a broker/provider;
- enable Production.

The later Billing delivery may consume plan price/version but cannot acquire trading authority from this catalog.

## Tests

`tests/infrastructure/test_commercial_products.py` verifies:

- EA = USD 29/account/month;
- Widget = USD 9.99/client/month;
- wrong EA/Widget billing scopes fail closed;
- Hosting remains separate from EA and has no canonical price;
- Managed Futures remains validation-required without USD 149 hardcoding;
- all five products coexist independently in one catalog;
- exact versioned plan resolution;
- no payment or trading authority.

## Non-goals

This delivery does not implement payment processor integration, invoices, reconciliation, Corporate Profit Vault posting, productive entitlement activation, broker IO, Managed Hosting runtime, Futures runtime, Production, MISSION-06 activation or MISSION-03 Gate #5 closure.

## Next delivery

After exact-head Quality Gate GREEN and merge:

```text
QORE-COMMERCIAL-BILLING-PAYMENTS-001
```