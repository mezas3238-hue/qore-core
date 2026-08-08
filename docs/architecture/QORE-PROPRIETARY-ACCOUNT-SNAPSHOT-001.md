# QORE-PROPRIETARY-ACCOUNT-SNAPSHOT-001 — Provider-Neutral Proprietary Account Boundary

Status: **CONTRACT PREPARATION — PRODUCTION AUTHORIZATION REMAINS CLOSED**

## Verified base

```text
main @ c43fa31dc97883824132deaae47c8132b99a1425
```

No open pull requests or later main changes altered the approved CEO proprietary-account direction
before this branch was created.

## Why this boundary is required

The Executive Command Center architecture requires future `CAPITAL_STATE` and `CEO_ACCOUNTS`
read surfaces containing proprietary balance, equity, realized/unrealized performance, drawdown and
related account state.

Repository inspection showed no canonical provider-neutral financial/account snapshot contract.
Creating executive monetary read models directly would therefore force the UI contract to invent
provider semantics.

The controlled sequence is instead:

```text
provider / platform account state
        ↓
provider-specific adapter
        ↓
ProprietaryAccountReadPort
        ↓
canonical proprietary snapshots
        ↓
future executive projection adapter
        ↓
CAPITAL_STATE / CEO_ACCOUNTS
```

## Domain boundary

This boundary represents **CEO proprietary operations only**.

It must never carry Client Profit Vault data.

```text
CEO PROPRIETARY ACCOUNTS  X  CLIENT PROFIT VAULT
```

The opaque `ProprietaryAccountId` is a QORE identity. It is deliberately not a broker account
number, username, login, server string, API key or credential reference.

A concrete adapter may hold the external mapping outside this public canonical snapshot contract.

## Canonical money

Financial values use `Decimal`, not binary floating point.

`MoneyAmount` contains:

- explicit three-letter `CurrencyCode`;
- finite signed decimal amount;
- normalized deterministic representation.

The general money value supports signed amounts because PnL can be positive, zero or negative.
Financial snapshot invariants separately require balance, equity and margin used to be nonnegative.

All monetary values in one financial snapshot must use the same currency.

No implicit FX conversion or cross-currency aggregation occurs in this boundary.

## Current financial snapshot

`ProprietaryAccountFinancialSnapshot` contains:

- explicit snapshot identity;
- opaque proprietary account identity;
- explicit external source descriptor;
- timezone-aware observation timestamp;
- account environment classification;
- operational state;
- balance;
- equity;
- unrealized PnL;
- margin used;
- drawdown in integer basis points.

The source must use the canonical namespace:

```text
proprietary-account
proprietary-account.*
```

This prevents a snapshot from being mislabeled as another external boundary.

## Realized performance snapshot

Realized PnL is never exposed without an explicit time window.

`ProprietaryAccountPerformanceSnapshot` contains:

- explicit snapshot identity;
- opaque proprietary account identity;
- explicit source descriptor;
- observation timestamp;
- `period_start`;
- `period_end`;
- signed realized PnL.

Chronology is fail-closed:

```text
period_start < period_end <= observed_at
```

The corresponding request also carries the exact requested window.

This allows future day/week/month/custom performance views without silently changing the meaning of
one field.

## Account environment

The normalized classification supports:

```text
practice
demo
production
unknown
```

`production` is a **descriptive classification only**. This contract does not authorize a
Production account, productive credentials, real capital, order execution or deployment.

The repository's Production gate remains closed and requires its own future authorization mission.

## Operational state

The descriptive account state supports:

```text
active
restricted
paused
closed
unknown
```

It does not imply permission to submit orders. Execution authority remains behind its own governed
boundaries and Risk / Capital Protection veto.

## Port contract

`ProprietaryAccountReadPort` is an `ExternalPort` `Protocol` and returns typed `Result` values.

It exposes only two read operations:

```text
read_financial_snapshot(...)
read_performance_snapshot(...)
```

Requests use explicit `ExternalRequestMetadata`; there is no hidden retry, implicit current time,
scheduler, polling loop or provider branching.

## Security and privacy

The contracts contain no:

- provider credential;
- API token;
- password;
- authorization header;
- broker account number;
- client identity;
- Profit Vault ledger;
- secret-bearing metadata;
- order command.

Concrete adapters remain outside the canonical Core/domain/governance object graph.

## Determinism

- immutable `dataclass(frozen=True, slots=True)` values;
- explicit UUID identities only;
- explicit timezone-aware timestamps only;
- no `datetime.now()`;
- no `uuid4()`;
- normalized Decimal logical representation;
- strict integer drawdown basis points;
- deterministic `logical_values()`.

## Scope intentionally deferred

This first financial boundary does not yet model:

- open positions;
- per-instrument exposure;
- leverage;
- margin level;
- historical equity curve;
- deposits/withdrawals;
- cross-currency consolidation.

Those require separately defined canonical semantics before they can safely appear in executive
read models.

The immediate next delivery may now build the first `CAPITAL_STATE` and `CEO_ACCOUNTS` executive
projections from this normalized source contract, without coupling the Command Center to a broker.

## Safety

This delivery introduces no concrete adapter and performs no external call. It does not activate:

- OANDA or another broker;
- Production;
- real capital;
- order submission/cancellation;
- CIBO execution;
- Mobile/Desktop transport;
- Profit Vault.

MISSION-03 remains active and unchanged.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is authorized.
