# QORE-EXECUTIVE-CAPITAL-ACCOUNT-READ-MODELS-001 — Capital State & CEO Accounts Projections

Status: **PREPARATION READY — PRODUCTION AND MOBILE ACTIVATION REMAIN CLOSED**

## Verified base

```text
main @ eca77b6191183ed81e4b209c161590bad2d8e747
```

This delivery starts only after the provider-neutral proprietary-account snapshot boundary was
merged and verified on `main`.

## Purpose

Define the first stable proprietary financial projections for the future CEO Command Center:

```text
CAPITAL_STATE
CEO_ACCOUNTS
```

without returning internal infrastructure contracts directly to Desktop/iOS/Android.

The required flow is now explicit:

```text
provider/platform account state
        ↓
provider adapter
        ↓
ProprietaryAccountReadPort
        ↓
canonical proprietary snapshots
        ↓
executive projection adapter
        ↓
ExecutiveCapitalStateReadModel / ExecutiveCeoAccountsReadModel
        ↓
authorized ExecutiveReadQueryPort
        ↓
CEO Command Center
```

## Projection isolation

The executive contracts intentionally define their own stable value objects rather than exposing
`MoneyAmount`, `CurrencyCode`, `DrawdownBps`, `ProprietaryAccountId`, or snapshot objects from the
infrastructure layer directly.

This preserves the approved rule:

```text
Internal / infrastructure state
        ↓
explicit executive projection
        ↓
authorized read surface
```

and prevents UI clients from coupling to adapter or infrastructure object layouts.

## CEO_ACCOUNTS

`ExecutiveCeoAccountsReadModel` exposes only CEO proprietary accounts.

Each account summary contains:

- opaque executive account reference;
- source observation timestamp;
- descriptive environment classification;
- descriptive operational state;
- balance;
- equity;
- unrealized PnL;
- margin used;
- drawdown in basis points;
- zero or more realized-performance windows;
- evidence references.

The account reference is not a broker account number.

No field exposes:

- provider account id;
- login;
- password;
- server;
- token;
- credential reference;
- Client Profit Vault identity.

## Realized performance

Every realized-PnL value is tied to an explicit reporting window:

```text
period_start < period_end <= observed_at
```

This supports future day/week/month/custom performance views without changing the meaning of one
ambiguous cumulative field.

A realized-performance window must use the same currency as its account.

## CAPITAL_STATE

`ExecutiveCapitalStateReadModel` is a consolidated proprietary view, but consolidation is strictly
currency-isolated.

Each `ExecutiveCapitalCurrencySummary` contains:

- currency;
- account count;
- total balance;
- total equity;
- total unrealized PnL;
- total margin used;
- worst individual account drawdown.

The model never silently adds unlike currencies.

Example:

```text
USD bucket
EUR bucket
GBP bucket
```

remains three distinct values unless a separately governed FX-conversion boundary is introduced in
the future.

There is deliberately no:

```text
converted_total
implicit_fx_rate
base_currency_conversion
```

## Drawdown semantics

The capital summary exposes `worst_account_drawdown`, not a fabricated consolidated drawdown.

A portfolio-level or consolidated drawdown requires an explicit historical-capital methodology and
cannot be derived safely from a single point-in-time account snapshot.

## Current intentional scope limit

The merged proprietary-account boundary does not yet define canonical:

- open positions;
- per-instrument exposure;
- leverage;
- margin level;
- historical equity curve;
- deposits/withdrawals.

Therefore this executive delivery does not invent those fields despite their presence in the
long-term Command Center product map.

They remain future, separately governed contracts.

## Evidence and freshness

Projection-level provenance remains supplied by `ExecutiveProjectionMetadata`:

- exact read scope;
- source observation time;
- projection time;
- explicit freshness;
- evidence refs;
- policy-version refs when applicable.

Account summaries and realized-performance windows also carry their own evidence refs so individual
financial assertions remain drill-down capable.

## Domain separation

Mandatory invariant:

```text
CEO PROPRIETARY FINANCE  X  CORPORATE CLIENT PROFIT VAULT
```

These models contain no:

- client ledger;
- profit-share percentage;
- settlement state;
- payment due;
- entitlement;
- client account identity.

A later `CORPORATE_PROFIT_VAULT` read model must remain a different surface and boundary.

## Production classification

The executive environment may descriptively represent:

```text
practice
demo
production
unknown
```

This is not authorization.

Neither the source snapshot boundary nor these read models activate productive credentials, real
capital, trading authority, execution, deployment or Mobile.

The Production gate remains closed.

## Determinism

- immutable `dataclass(frozen=True, slots=True)` contracts;
- explicit UUID account references;
- explicit timezone-aware timestamps;
- normalized finite Decimal money;
- explicit currency on every amount;
- strict integer drawdown/account counts;
- deterministic ordering of accounts, reporting windows, currency buckets, and evidence refs;
- duplicate account refs, reporting windows, and currency buckets rejected;
- deterministic `logical_values()`;
- no implicit time or identity generation.

## Scope binding

```text
ExecutiveCapitalStateReadModel -> CAPITAL_STATE
ExecutiveCeoAccountsReadModel  -> CEO_ACCOUNTS
```

A scope mismatch fails closed.

## Capital preservation

These read models are descriptive only.

They do not provide:

- buy;
- sell;
- close;
- submit/cancel order;
- leverage change;
- Risk bypass;
- capital-protection bypass.

The CEO may later govern or restrict QORE through authorized command boundaries, but financial
visibility itself creates no execution authority.

## Safety

This delivery introduces no concrete provider adapter, external call, HTTP/WebSocket/gRPC, mobile
backend, Production activation, real-money execution, Client Profit Vault coupling, retry loop,
scheduler or thread.

MISSION-03 remains active and unchanged.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is authorized.

## Next controlled read surface

After these proprietary financial projections are merged, the remaining currently authorized
executive read scope is:

```text
CORPORATE_PROFIT_VAULT
```

That scope must be implemented from the separately approved Profit Vault architecture and must not
reuse CEO-account financial objects or create a Core-to-Vault dependency.
