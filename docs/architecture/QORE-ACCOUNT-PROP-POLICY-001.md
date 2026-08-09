# QORE-ACCOUNT-PROP-POLICY-001 — Account & Prop Firm Policy Governance

## Status

**IMPLEMENTED — NON-PRODUCTION POLICY CONTRACTS**

Opening baseline:

```text
main @ 694763cf1287974ca40eeef220cb31457bd3d5c8
```

MISSION-07 Delivery 3 defines versioned, account-scoped policy snapshots before Client Execution Agent contracts are introduced.

## Purpose

Provide one deterministic provider-neutral representation of the account/prop-firm rules that later execution agents must consume without hardcoding prop-firm implementations into the Agent or strategic Core.

The delivery answers:

- which account one policy governs;
- which opaque policy snapshot/version is effective;
- whether the account is brokerage, prop-firm or unresolved;
- which prop firm/program references apply without storing provider credentials;
- account size and explicit drawdown/daily-loss ratios;
- static/trailing drawdown semantics;
- normalized account phase;
- client profit split;
- canonical trading/payout rule declarations;
- whether mandatory semantics are resolved for later new-trade evaluation;
- how a caller resolves an exact current policy fail-closed.

## Canonical reuse

This delivery deliberately does **not** invent replacement money or drawdown primitives.

It reuses from `qore.infrastructure.proprietary_accounts`:

```text
CurrencyCode
MoneyAmount
DrawdownBps
```

It reuses from `QORE-CLIENT-ACCOUNT-FOUNDATION-001`:

```text
TradingAccountId
TradingAccountKind
AccountPolicyReference
```

This keeps account policy aligned with already-merged financial and client-account contracts.

## New contracts

`src/qore/infrastructure/account_policy.py` adds:

```text
AccountPolicySnapshotId
PropFirmReference
PropProgramReference
AccountPolicyVersion
ProfitSplitBps
AccountPhase
DrawdownMode
PolicyRuleScope
PolicyRuleDisposition
AccountPolicyRule
AccountPropPolicySnapshot
AccountPolicyRegistrySnapshot
```

plus typed validation/resolution errors.

## Opaque prop identity

`PropFirmReference` and `PropProgramReference` are UUID-backed QORE references only.

They are not:

- provider credentials;
- account logins;
- API tokens;
- legal/KYC documents;
- SDK/provider objects.

Firm-specific acquisition, source-text interpretation and provider protocols remain behind future policy adapters/boundaries.

## Policy versioning

Each `AccountPropPolicySnapshot` contains:

```text
snapshot_id
policy_ref
account_id
version
effective_at
expires_at
```

All identity/version/time values are explicit and caller supplied.

There is no hidden clock and no implicit UUID/version generation.

The current registry requires exactly one current policy snapshot per account and one unique `policy_ref` per current snapshot.

Historical persistence/version chains are a later storage concern; this contract represents the immutable policy snapshot being evaluated now.

## Account classification

Policy uses the canonical `TradingAccountKind`:

```text
BROKERAGE
PROP_FIRM
UNKNOWN
```

For `PROP_FIRM`:

- `firm_ref` is mandatory;
- `program_ref` is mandatory;
- `phase` cannot be `NOT_APPLICABLE`.

For `BROKERAGE`:

- prop-firm references are forbidden;
- `phase` must be `NOT_APPLICABLE`.

For `UNKNOWN`:

- prop-firm references are forbidden;
- `phase` must be `UNKNOWN`;
- policy completeness fails closed for new trading.

## Normalized account phase

`AccountPhase` currently provides provider-neutral semantic categories:

```text
EVALUATION
VERIFICATION
FUNDED
NOT_APPLICABLE
UNKNOWN
```

These are QORE normalization values, not hardcoded names of a particular firm's commercial products.

A later adapter may map provider-specific phase labels into these canonical categories only when mapping is unambiguous.

## Drawdown and Daily Loss

The snapshot carries:

```text
max_drawdown: DrawdownBps
daily_loss_limit: DrawdownBps
drawdown_mode: STATIC | TRAILING | UNKNOWN
```

The numeric basis-point values reuse the existing canonical `DrawdownBps` contract.

This delivery does not calculate live drawdown, equity, breach status or order size. Those are later Agent/risk evaluation responsibilities.

`UNKNOWN` drawdown semantics cause policy completeness to fail closed.

## Account size

`account_size` uses canonical `MoneyAmount` and must be strictly positive.

The currency is therefore explicit and normalized by the existing `CurrencyCode` contract.

Policy does not infer current balance/equity from account size.

## Profit split

`ProfitSplitBps` represents the client contractual entitlement ratio from 0 through 10,000 basis points.

Example:

```text
8000 bps = 80% client entitlement
```

This value does not prove payout or payment.

MISSION-07 continues to distinguish:

```text
GROSS TRADING PROFIT
CLIENT ENTITLED PROFIT
CLIENT PAID PROFIT
ELIGIBLE CLIENT PAID PROFIT
QORE PERFORMANCE FEE
```

`client_profit_split` helps later calculate contractual entitlement; it cannot turn realized P&L into `PAID` without independent payout/payment evidence.

## Trading and payout rules

Firm/program rules vary and must not become a giant hardcoded enum inside an EA.

The policy therefore defines `AccountPolicyRule` as:

```text
code
scope = TRADING | PAYOUT
disposition = ALLOW | PROHIBIT | REQUIRE | UNKNOWN
```

Rule codes use canonical uppercase QORE identifiers.

Examples in tests such as `NEWS_TRADING` and `PAYOUT_CONFIRMATION` demonstrate contract semantics only; they do not claim that every prop firm has those rules.

Provider/source text belongs outside this canonical contract.

Duplicate rule codes are rejected inside one snapshot.

Any rule with `UNKNOWN` disposition makes the snapshot incomplete for new-trade evaluation.

## Policy completeness is not trading authority

`AccountPropPolicySnapshot.is_complete_for_new_trading()` answers only:

> Are the mandatory policy semantics represented here resolved enough for later evaluation?

It does **not** answer:

> May the account trade?

Success cannot replace any later requirement, including:

```text
valid Core Decision
cryptographic decision verification
account binding
entitlement
observed account state
capital-protection/risk checks
execution capability
single-writer authority
```

The maximum invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

## Fail-closed registry resolution

`AccountPolicyRegistrySnapshot.resolve_for_new_trading(...)` requires explicit:

```text
account_id
policy_ref
evaluated_at
```

It fails when:

- the policy reference is missing;
- the policy belongs to another account;
- it is not yet effective;
- it is expired;
- mandatory semantics are unresolved;
- evaluation time is invalid/naive.

A `Success[AccountPropPolicySnapshot]` means **policy readiness only**.

No method submits an order or produces a trading decision.

## Deterministic ordering

Rules are normalized deterministically by:

```text
(scope, code, disposition)
```

Registry policies are normalized by:

```text
(account_id, policy_ref)
```

All contracts expose `logical_values()` where canonical comparison/evidence is useful.

## Security and privacy boundary

This delivery contains no:

- broker passwords;
- API keys;
- bearer tokens;
- trading account login numbers;
- client civil identity;
- payment-card information;
- provider SDK dependency;
- executable strategy;
- Core reasoning.

## Tests

`tests/infrastructure/test_account_policy.py` proves, among other cases:

- opaque identity/version/profit-split validation;
- provider-neutral canonical rule codes;
- deterministic rule ordering;
- canonical `MoneyAmount`/`DrawdownBps` reuse;
- prop-firm firm/program requirements;
- brokerage/prop classification separation;
- representable but fail-closed unknown policy state;
- unknown rule disposition blocks policy readiness;
- timezone/effective/expiry invariants;
- strictly positive account size;
- duplicate current policy/account rejection;
- exact deterministic registry resolution;
- wrong-account/missing-policy failure;
- pre-effective/expired failure;
- unresolved mandatory semantics failure;
- naive evaluation-time failure;
- policy readiness never grants execution authority.

No `type: ignore`, cast or suppression is used to force the negative tests.

## Explicitly not implemented

This delivery does not implement or authorize:

- provider-specific prop-firm adapters;
- automatic scraping/import of prop-firm terms;
- live account DD/Daily Loss computation;
- lot sizing;
- SL/TP/trailing calculation;
- Client Execution Agent;
- Core Decision envelope/security;
- broker execution;
- payout verification;
- payment verification;
- Client Performance Ledger;
- Billing;
- Widget;
- Managed Hosting;
- Futures;
- Production;
- MISSION-06;
- MISSION-03 Gate #5 closure.

## Acceptance result

This delivery is complete only after the exact PR head passes the unchanged repository Quality Gate and merges to `main` with only the intended architecture, source and test files.

After merge, the next authorized MISSION-07 delivery is:

```text
QORE-CLIENT-EXECUTION-AGENT-CONTRACTS-001
```

That delivery may define platform-neutral delegated-execution inputs, calculations and verdict boundaries. It still may not introduce a concrete production MT5/broker runtime or create strategic trading authority outside Core.
