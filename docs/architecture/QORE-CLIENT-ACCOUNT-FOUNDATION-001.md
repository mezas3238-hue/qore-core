# QORE-CLIENT-ACCOUNT-FOUNDATION-001 — Client & Trading Account Foundation

## Status

**IMPLEMENTED — NON-PRODUCTION FOUNDATION CONTRACTS**

Opening baseline:

```text
main @ 0dc4ab3588824595ce3a5c9171d7b75f243dbda7
```

MISSION-07 Delivery 2 defines the minimum client/account identities and deterministic binding model required before prop-firm policy, Client Agent, billing or Widget implementation.

## Purpose

Establish a provider-neutral answer to the following questions without introducing trading execution:

1. What opaque QORE identity represents a commercial client?
2. What opaque QORE identity represents one client trading account?
3. How can one client bind one or many independent accounts?
4. How is exactly one canonical client owner resolved for an account?
5. How can an account carry opaque references to policy, product entitlement and execution runtime without containing secret material?
6. How are basic account classification and lifecycle represented without granting trading authority?

## Contracts

`src/qore/infrastructure/client_accounts.py` defines:

- `ClientId`;
- `TradingAccountId`;
- `AccountPolicyReference`;
- `ProductEntitlementReference`;
- `ExecutionRuntimeReference`;
- `TradingAccountKind`;
- `TradingAccountLifecycleState`;
- `ClientTradingAccountBinding`;
- `ClientAccountRegistrySnapshot`;
- typed validation/resolution errors.

All identity/reference values are caller-supplied UUIDs. No identity is generated implicitly.

## Opaque identity doctrine

`ClientId` is not:

- a name;
- an email address;
- a government identity;
- a payment identity;
- a passport/document reference.

`TradingAccountId` is not:

- a broker login;
- a provider account number;
- a password;
- a broker credential.

The same UUID value is rejected when used simultaneously as the client identity and trading-account identity inside one binding.

## 1 Client -> N Accounts

The canonical relationship is:

```text
ClientId
  ├── TradingAccountId A
  ├── TradingAccountId B
  └── TradingAccountId N
```

A `ClientAccountRegistrySnapshot` may contain bindings for multiple clients, but each `TradingAccountId` may appear exactly once.

Duplicate account bindings are rejected even when they repeat the same owner, because duplicated canonical ownership evidence is ambiguous and unnecessary.

A second client attempting to bind the same account therefore fails at the same invariant.

## Account independence

Each account binding owns independent references for:

```text
policy_ref
product_entitlement_ref
runtime_ref
```

A multi-account client does not receive shared risk, policy, entitlement or runtime authority merely because the owner is the same.

Later deliveries may project or aggregate account state for presentation, but execution/risk/performance semantics remain account-scoped.

## Opaque references are not authority

`AccountPolicyReference`, `ProductEntitlementReference` and `ExecutionRuntimeReference` are identity/provenance references only.

They do not prove that:

- the policy is valid/current;
- the entitlement is active;
- the runtime owns an execution lease;
- a Core Decision exists;
- an account may trade.

Those checks belong to later MISSION-07 deliveries.

In particular:

```text
runtime_ref != execution authority
lifecycle ACTIVE != trading authorization
account_kind != policy resolution
```

## Account classification

`TradingAccountKind` is deliberately broad:

```text
BROKERAGE
PROP_FIRM
UNKNOWN
```

No provider/firm name is hardcoded in the foundation.

Detailed firm/program/phase/risk semantics belong to `QORE-ACCOUNT-PROP-POLICY-001`.

`UNKNOWN` can be represented as observed registry state but does not become implicit authorization.

## Account lifecycle

`TradingAccountLifecycleState` defines:

```text
PROVISIONED
ACTIVE
RESTRICTED
SUSPENDED
CLOSED
UNKNOWN
```

This is a lifecycle classification only.

An `ACTIVE` value is intentionally not a `can_trade` flag and cannot bypass Core Decision, entitlement, policy, risk or later execution-agent checks.

## Deterministic registry snapshot

`ClientAccountRegistrySnapshot`:

- is immutable;
- rejects an empty canonical snapshot in this boundary;
- accepts only `ClientTradingAccountBinding` values;
- rejects duplicate account identities;
- sorts bindings deterministically by client UUID then account UUID;
- exposes deterministic `logical_values()`;
- resolves all accounts for one client;
- resolves an exact `(client_id, account_id)` binding;
- fails closed when the account is missing or belongs to another client.

The snapshot is not a database and does not introduce mutable global registry state.

## Fail-closed resolution

An exact binding lookup succeeds only when:

```text
requested client_id
    + requested account_id
    == one canonical binding
```

Failure examples include:

```text
account unknown
account belongs to another client
client has no bound accounts
invalid runtime input type
```

Resolution returns typed `Result / Success / Failure` values.

## Secret and privacy boundary

No foundation contract contains fields for:

- broker account number;
- broker login;
- password;
- access token;
- API key;
- provider credential;
- payment card;
- civil identity document;
- strategy;
- Core reasoning.

Opaque UUID references are safe identities, not containers for secret values.

## Trading authority boundary

This delivery implements **zero trading operations**.

It does not define or expose:

```text
execute
submit_order
buy
sell
close_position
calculate_lot
calculate_sl
calculate_tp
move_trailing
```

An account may be represented as `ACTIVE` while still having no authority to trade.

The MISSION-07 invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

## Dependency direction

The contracts live under `qore.infrastructure` as a client/account external boundary similar in architectural placement to provider-neutral proprietary account snapshots.

This does not make Core depend on Client Registry state.

Prohibited dependency direction remains:

```text
Core strategic decision generation -> Client Registry
Core strategic decision generation -> Billing
Core strategic decision generation -> Client identity
```

Later Client Agent/commercial composition may depend on these contracts outward from the Core decision boundary.

## Determinism and typing

The implementation preserves repository doctrine:

- `dataclass(frozen=True, slots=True)`;
- caller-supplied UUID identity;
- strict runtime type validation;
- no implicit clock;
- no implicit UUID generation;
- deterministic ordering;
- deterministic `logical_values()`;
- typed errors;
- typed `Result / Success / Failure` for resolution;
- no mutable global state;
- no retry, thread, polling or scheduler;
- no `type: ignore`;
- no cast-based typing bypass;
- no suppression.

## Validation evidence

`tests/infrastructure/test_client_accounts.py` proves:

- opaque client/account identities are typed and immutable;
- invalid runtime identity values fail validation without typing suppressions;
- bindings contain no broker credential/account-login fields;
- client/account identity collision fails;
- untyped account-scoped references fail;
- one client can own multiple independent accounts;
- deterministic registry ordering;
- duplicate account bindings fail;
- the same account cannot bind to two clients;
- empty/non-binding registry state fails;
- exact resolution succeeds;
- cross-client and missing-account resolution fail closed;
- a client with no account binding fails closed;
- `UNKNOWN` classification and `ACTIVE` lifecycle do not grant trading authority.

## Explicitly not implemented

This delivery does not implement or authorize:

- Prop Firm Registry;
- detailed account risk/payout policy;
- Client Execution Agent;
- Core Decision transport/security;
- order execution;
- broker/provider connectivity;
- sizing;
- SL/TP/trailing logic;
- Client Performance Ledger;
- billing/payment processing;
- trial activation;
- Client Widget;
- Managed Hosting;
- native broker execution;
- Futures;
- Production;
- MISSION-06;
- MISSION-03 Gate #5 closure.

## Acceptance result

This delivery is complete only after the exact PR head passes the unchanged QORE Quality Gate and is merged to `main` with only the intended architecture document, source contract and tests.

After merge, the next authorized MISSION-07 delivery is:

```text
QORE-ACCOUNT-PROP-POLICY-001
```

That delivery may define versioned account/prop-firm policy snapshots and normalized phase/risk rules. It may not grant trading without a Core Decision or introduce live provider execution.
