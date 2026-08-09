# QORE-CLIENT-WIDGET-MULTIACCOUNT-001 — Multi-Account Client Widget

## Status

**IMPLEMENTED — NON-PRODUCTION CLIENT PRESENTATION SURFACE; TRADING AUTHORITY ABSENT**

Opening baseline:

```text
main @ 72018094693a63335759af94b22c437e1d4db36a
```

MISSION-07 Delivery 13 defines one client-scoped Widget presentation model over the merged multi-account Client Read Model.

## Commercial scope

The Widget product is:

```text
CLIENT_WIDGET
billing unit = CLIENT
```

The Widget standing rejects any other product kind or billing scope. An EA/account-scoped plan cannot activate a Widget surface.

Pricing remains owned by Products & Plans:

```text
USD 9.99 / client / month
```

The Widget view model intentionally does not copy or mutate price.

## One client -> one Widget -> N accounts

`ClientWidgetViewModel` binds one exact `ClientId` and may present the N independent account snapshots already composed by `ClientMultiAccountReadModel`.

It does not create another account registry, performance ledger or risk aggregation layer.

## Access states

Closed Widget access vocabulary:

```text
ACTIVE
SUSPENDED
```

Commercial standing maps deterministically:

```text
CURRENT        -> ACTIVE
PAYMENT_FAILED -> SUSPENDED
UNKNOWN        -> SUSPENDED
```

Unknown state fails closed.

## Immediate Widget suspension

Unlike EA/Hosting safe suspension, the Widget is outside the execution path and can be suspended immediately.

```text
WIDGET PAYMENT FAILED -> WIDGET SUSPENDED
```

A suspended Widget does not expose the multi-account read payload.

This is presentation access control only.

It does **not** modify or suspend:

- Client Execution Agent;
- QORE Core;
- open positions;
- account risk;
- licensing records;
- Managed Hosting;
- broker/provider state.

The underlying read-model object remains unchanged.

## Data source

The Widget consumes only `ClientMultiAccountReadModel`.

It therefore inherits the presentation-safe data already defined there:

- per-account status;
- balance;
- generated today;
- generated week;
- trade pulse;
- service/license/billing state;
- per-currency summaries.

It never talks directly to a broker/provider and does not form part of the execution path.

## Chronology

Widget standing and view generation use explicit timezone-aware timestamps.

An ACTIVE Widget cannot present a Read Model from the future, and its client identity must exactly match the Read Model client.

## Tests

`tests/infrastructure/test_client_widget_multiaccount.py` verifies:

- one active Widget presents N client accounts;
- price is not duplicated into the view model;
- PAYMENT_FAILED suspends immediately and removes account payload;
- suspension leaves source account/license state unchanged;
- UNKNOWN commercial state fails closed;
- EA/account-scoped plan cannot become Widget standing;
- foreign-client read model is rejected;
- Widget suspension cannot suspend EA, set risk, close positions or stop Hosting;
- no broker, payment-mutation or trading authority exists.

## Non-goals

No native Android/iOS UI framework, payment processor, broker IO, risk mutation, EA suspension, Hosting orchestration, Futures, Production, MISSION-06 activation or MISSION-03 Gate #5 closure is introduced.

## Next delivery

After exact-head Quality Gate GREEN and merge:

```text
QORE-MISSION07-E2E-OFFLINE-001
```