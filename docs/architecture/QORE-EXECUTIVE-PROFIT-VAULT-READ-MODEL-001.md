# QORE-EXECUTIVE-PROFIT-VAULT-READ-MODEL-001 — Corporate Profit Vault Projection

Status: **READ-MODEL PREPARATION — PROFIT VAULT IMPLEMENTATION REMAINS CLOSED**

## Verified base

```text
main @ 520931d4e892bc9193a3e49b5a00bb2e48b94dcd
```

At branch creation there were no open pull requests and no later main change altering the approved
Vault separation.

## Purpose

Define the stable executive projection for the already authorized read scope:

```text
CORPORATE_PROFIT_VAULT
```

without implementing the Profit Vault executable, settlement database, payment provider,
entitlement issuer, or any Core-to-Vault dependency.

The future topology remains:

```text
CLIENT EXECUTION AGENT
        ↓ settlement events
CLIENT PROFIT VAULT
        ↓ corporate projection adapter
ExecutiveCorporateProfitVaultReadModel
        ↓ authorized executive read boundary
CEO COMMAND CENTER
```

and never:

```text
QORE CORE -> PROFIT VAULT
```

## Absolute domain separation

Mandatory invariant:

```text
QORE CORE  X  CLIENT PROFIT VAULT
CEO PROPRIETARY FINANCE  X  CLIENT PROFIT VAULT
```

The projection therefore defines Vault-specific currency and money values and does not import or
reuse the `CEO_ACCOUNTS` / `CAPITAL_STATE` financial value contracts.

The read model contains no:

- client name;
- personal identity;
- broker account number;
- balance;
- equity;
- drawdown;
- open positions;
- CIBO state;
- trader/strategy state;
- CEO proprietary account state.

## Opaque ledger identity

`ExecutiveVaultLedgerRef` and `ExecutiveVaultSettlementPeriodRef` are explicit UUID-backed opaque
references.

They are not client identities or broker account identifiers.

This lets the CEO inspect corporate economics without requiring the Vault read surface to expose
personal or trading-account identity.

## Per-ledger economics

`ExecutiveVaultLedgerSummary` projects one current settlement-period view with:

- opaque ledger identity;
- explicit settlement-period identity;
- explicit timezone-aware period start/end;
- funded/service phase;
- settlement lifecycle state;
- entitlement state;
- policy version;
- positive realized total;
- negative realized total;
- net realized result;
- carryforward balance as reported by the Vault policy engine;
- economically eligible positive base;
- policy-projected profit-share rate in basis points;
- amount due;
- amount paid;
- outstanding amount;
- evidence references.

All monetary values for one ledger period use the same currency.

## Positive and negative history

The contract requires the economic identity:

```text
net_realized = positive_realized + negative_realized
```

with:

```text
positive_realized >= 0
negative_realized <= 0
```

Negative results are therefore preserved rather than discarded from the executive view.

## Approved non-billing invariants

The read projection enforces two already-approved commercial invariants:

```text
net_realized <= 0 -> amount_due = 0
```

and:

```text
EVALUATION   -> amount_due = 0
VERIFICATION -> amount_due = 0
```

A positive `amount_due` also requires a positive eligible base and a positive policy-projected rate.

## What this contract deliberately does not calculate

This read model is not the Profit Vault settlement engine.

It does **not** independently compute:

- high-water-mark adjustments;
- loss carryforward policy;
- commissions/swaps/cost treatment;
- corrections;
- payout/reward eligibility;
- legal settlement finality;
- taxes;
- invoice values;
- payment-provider state transitions.

Those values must be calculated by the future isolated Vault implementation under a versioned
policy and then projected with evidence.

The current approved commercial intention is a 20% share on economically eligible positive profit,
but the read contract represents the rate explicitly in basis points rather than silently embedding
billing logic. A current policy may therefore project:

```text
2000 bps = 20%
```

while the exact contractual policy remains separately versioned and auditable.

## Funded/service phases

The executive projection formalizes the architecture's normalized phases:

```text
evaluation
verification
reward-eligible
payout-eligible
suspended
unknown
```

Phase is an economic/service classification only. It contains no trading authority.

## Settlement states

The read surface supports:

```text
open
calculating
ready
due
paid
past-due
disputed
corrected
closed
unknown
```

These describe the Vault's corporate settlement state and cannot modify Core behavior.

## Entitlement states

The executive projection can show:

```text
active
payment-due
grace
suspended
expired
reactivated
unknown
```

This is read-only visibility.

The architecture remains:

```text
Vault does not renew lease
        ↓
lease expires
        ↓
Client Agent rejects NEW signals
```

Core remains unaware and existing-position protection remains outside this read model.

## Corporate currency aggregates

`ExecutiveVaultCurrencySummary` provides executive corporate aggregates for one currency:

- positive realized total;
- negative realized total;
- eligible positive base;
- receivable;
- collected;
- outstanding;
- evidence references.

No cross-currency aggregation is permitted implicitly.

```text
USD aggregate
EUR aggregate
GBP aggregate
```

remain separate unless a future explicit, versioned, auditable FX-conversion policy is introduced.

## Ledger counts

The first projection includes deterministic current result counts:

```text
total
positive
negative
break-even
```

The counts must exactly match the included ledger summaries.

Phase, settlement, and entitlement classifications remain available per ledger and can be surfaced
by the Command Center without duplicating inconsistent aggregate state in this first narrow
contract.

A future paginated/large-scale corporate projection may introduce separately evidenced aggregate
count snapshots if required by scale.

## Evidence and auditability

Projection-level provenance remains in `ExecutiveProjectionMetadata`.

Each ledger and currency aggregate also requires explicit `ExecutiveEvidenceRef` values.

The executive surface therefore supports drill-down without carrying raw settlement events,
signatures, payment credentials, or secret material directly.

## No Profit Vault implementation authorization

This delivery does not authorize or implement:

- Profit Vault executable;
- settlement event ingestion;
- settlement database;
- payment integration;
- billing engine;
- invoice generation;
- entitlement signing;
- client identity database;
- legal/commercial contract terms;
- tax/accounting treatment.

It defines only the stable output shape that a future isolated Corporate Plane projection adapter
may supply to the authorized CEO read boundary.

## No trading authority

The model has no:

- BUY/SELL;
- signal creation/modification;
- order submit/cancel/close;
- SL/TP modification;
- Risk bypass;
- Core restriction command.

Commercial entitlement state cannot become corrective trading authority.

## Determinism

- immutable `dataclass(frozen=True, slots=True)` values;
- explicit UUID identities;
- explicit timezone-aware period timestamps;
- finite normalized Decimal money;
- strict integer basis-point rates;
- deterministic ledger/currency/evidence ordering;
- duplicate ledger/currency refs rejected;
- explicit ledger-count reconciliation;
- deterministic `logical_values()`;
- no implicit current time or identity generation.

## Scope binding

```text
ExecutiveCorporateProfitVaultReadModel -> CORPORATE_PROFIT_VAULT
```

A scope mismatch fails closed.

## MISSION / Production status

MISSION-03 remains active and unchanged.

This preparatory read contract does not operationally activate MISSION-04 or MISSION-05 and does
not authorize Production, productive credentials, real capital, Mobile, or deployment.

## Quality gate

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

No suppression or gate weakening is authorized.

## Next architecture gate

After this delivery, every scope currently present in the canonical `ExecutiveReadScope` allowlist
has an explicit executive read-model family.

The CEO Command Center product architecture also names a Governance read surface, but the canonical
allowlist still has no `ExecutiveReadScope.GOVERNANCE`.

Therefore Governance remains fail-closed until a separate controlled authorization change explicitly
extends `ExecutiveReadScope` and its authorization tests before any Governance read model is added.
