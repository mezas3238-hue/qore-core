# QORE-CLIENT-MULTIACCOUNT-READ-MODEL-001 — Client Multi-Account Read Model

## Status

**IMPLEMENTED — NON-PRODUCTION PRESENTATION READ MODEL; TRADING AUTHORITY ABSENT**

Opening baseline:

```text
main @ 75645e67d059f8cdba062a31d1aa2bfd2e8ac71c
```

MISSION-07 Delivery 12 defines one deterministic client-facing read model over N independent trading accounts.

## Authority boundary

```text
READ MODEL = PRESENTATION ONLY
```

It cannot:

- originate a Core Decision;
- submit/close orders;
- change risk;
- activate licensing;
- mark invoices paid;
- access broker/provider credentials.

## Multi-account model

One `ClientId` may own N account snapshots.

Every `ClientAccountReadSnapshot` preserves its exact `TradingAccountId`; duplicate accounts and cross-client ownership fail closed.

Account-level state remains independent:

- account lifecycle;
- balance;
- generated today;
- generated this week;
- service status;
- license status;
- billing status;
- trade pulse.

No account state grants another account execution or risk authority.

## Explicit performance windows

"Today" and "week" are not derived from a hidden wall clock.

The caller supplies explicit timezone-aware:

```text
ClientPerformanceWindow(started_at, ended_at)
```

for today and week, and both must end exactly at the read model's `generated_at`.

This makes snapshots deterministic and testable across deployment regions/time zones.

## Currency isolation

Balance/today/week are canonical `MoneyAmount` values.

Each account snapshot uses one currency for its monetary fields.

Client-level summaries are grouped by `CurrencyCode` only:

```text
USD accounts -> USD summary
EUR accounts -> EUR summary
```

There is deliberately no cross-currency `total_balance` and no implicit FX conversion.

## No risk aggregation

The read model does not aggregate drawdown, daily loss or trading risk across accounts.

The commercial/product rule remains:

```text
1 Client -> N independent Trading Accounts
```

Portfolio presentation does not transform those accounts into one risk authority.

## Trade pulse

`ClientTradePulse` exposes presentation-safe facts:

- account ID;
- position ID;
- originating DecisionId;
- instrument/pair;
- side;
- position state;
- event time.

It contains no order-submission or position-mutation method.

Trade pulses are deterministically ordered newest-first.

## Service/commercial state

The account snapshot may display:

- service status;
- existing `ClientLicenseState`;
- existing `CommercialBillingStandingState`.

These are projections only. The read model cannot mutate their source systems.

## Tests

`tests/infrastructure/test_client_multiaccount_read_model.py` verifies:

- multiple same-currency accounts aggregate deterministically;
- different currencies remain separate;
- trade pulse exposes account/time/instrument/state;
- foreign-client account snapshots fail closed;
- duplicate accounts fail closed;
- today/week windows are explicit;
- service/license/billing statuses remain presentation-only;
- no broker, trading or risk authority exists.

## Non-goals

No UI framework, broker IO, FX conversion, risk aggregation, Billing mutation, licensing mutation, Widget subscription control, Managed Hosting, Futures, Production, MISSION-06 activation or MISSION-03 Gate #5 closure.

## Next delivery

After exact-head Quality Gate GREEN and merge:

```text
QORE-CLIENT-WIDGET-MULTIACCOUNT-001
```