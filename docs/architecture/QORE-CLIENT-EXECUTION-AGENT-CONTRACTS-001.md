# QORE-CLIENT-EXECUTION-AGENT-CONTRACTS-001 — Deterministic Delegated Execution Contracts

## Status

**IMPLEMENTED — NON-PRODUCTION AGENT CONTRACTS; NO BROKER EXECUTION**

Opening baseline:

```text
main @ ab0c61ca967640faf101c001c2e7388cf77de975
```

MISSION-07 Delivery 4 defines the platform-neutral Client Execution Agent contract between a strategic Core trade decision and the repository's existing controlled order/execution boundaries.

## Maximum authority invariant

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

The Client Agent does not discover opportunities, generate BUY/SELL direction or reinterpret strategy.

Its role is:

```text
Core strategic decision
+ decision-security evidence
+ client/account binding
+ account/prop policy
+ observed account state
+ entitlement state
+ authorized execution-calculation policy
+ deterministic sizing/protection calculation
        ↓
account-local execution verdict
        ↓
if all gates pass: auditable ClientExecutionPlan
```

`ClientExecutionPlan` is not an order submission and cannot contact a broker.

## Canonical contracts reused

This delivery does not invent a parallel trading vocabulary.

It reuses:

- `FunctionalDecision`, `DecisionId`, `DecisionStatus`, `DecisionOutcome` from the canonical functional decision model;
- `ExecutionInstrument`, `OrderSide`, `OrderType`, `OrderQuantity`, `OrderPrice` from canonical `order_intent` contracts;
- `ClientId`, `TradingAccountId`, account binding, policy/entitlement/runtime references from `QORE-CLIENT-ACCOUNT-FOUNDATION-001`;
- `AccountPropPolicySnapshot` and `AccountPolicySnapshotId` from `QORE-ACCOUNT-PROP-POLICY-001`;
- `MoneyAmount` and `DrawdownBps` from the canonical financial snapshot contracts.

The existing `OrderIntent`, `PreTradeAuthorization`, `AuthorizedOrderIntent`, `ExecutionSubmission` and `ExecutionBoundary` remain downstream canonical contracts.

This delivery does not bypass or replace them.

## CoreTradeDecision

`CoreTradeDecision` is a strict projection of a canonical `FunctionalDecision` into provider-neutral trading semantics.

It requires:

```text
decision_type = core.trade
explicit DecisionId
explicit timezone-aware decision timestamp
instrument
side
order type
explicit expiry
limit price only when order type = LIMIT
```

It deliberately does not contain:

- account-specific quantity;
- lot size;
- Stop Loss;
- Take Profit;
- trailing mutation;
- broker account/login;
- broker credentials.

Those account-local values are delegated deterministic calculations, not strategic decisions.

A pending/rejected/blocked Core decision may be represented for audit, but the Agent evaluation cannot create a new execution plan unless the decision is `RESOLVED + APPROVED` and unexpired.

## Decision-security attestation boundary

Delivery 5 owns the actual canonical cryptographic decision-security protocol.

Delivery 4 defines only the downstream attestation contract that the Client Agent expects:

```text
DecisionSecurityAttestation
  decision_id
  account_id
  runtime_ref
  VERIFIED / REJECTED / UNKNOWN
  evidence_ref
  verified_at
```

This means the Client Agent contract already requires account/runtime-bound security evidence, but **does not claim to cryptographically produce it**.

Non-production unit tests may construct a `VERIFIED` fixture to prove downstream composition semantics. Such a fixture is test evidence only and is not a productive cryptographic verification.

A future implementation must obtain this attestation from `QORE-CLIENT-DECISION-SECURITY-001`; arbitrary construction cannot be treated as productive authority.

## Account observation

`ClientAccountObservedState` is account-scoped and immutable:

```text
observation_id
account_id
observed_at
balance
equity
current_drawdown
daily_loss
open_positions
```

Balance/equity use canonical `MoneyAmount` and must share currency.

Drawdown and Daily Loss use canonical `DrawdownBps`.

The Agent does not infer current state from stale snapshots. Freshness is an explicit policy input.

## Minimal entitlement boundary

`ClientAgentEntitlementSnapshot` intentionally defines only what Delivery 4 needs:

```text
entitlement_ref
account_id
ENABLED / BLOCKED / UNKNOWN
evaluated_at
```

Billing, trial, payment and safe-suspension state machines remain later MISSION-07 deliveries.

An entitlement snapshot is commercial eligibility input only. It does not create a Core Decision or bypass risk.

## Authorized execution-calculation policy

`ClientExecutionPolicy` defines the account-local delegated calculation envelope:

```text
policy_id
sizing_policy_ref
protection_policy_ref
optional trailing_policy_ref
max_risk_per_trade
max account-state age
max entitlement age
max security-attestation age
```

All policy identities are explicit opaque UUID references.

The policy gives the Agent deterministic calculation boundaries. It does not contain strategy direction.

## Sizing / SL / TP / trailing boundary

The EA requirement that lot sizing and protection be calculated locally is represented by two contracts:

```text
ClientExecutionCalculator (Protocol)
ClientExecutionCalculation (immutable output)
```

The calculation output binds:

```text
decision_id
account_id
calculated_at
quantity
entry reference price
Stop Loss
Take Profit
estimated risk
sizing policy ref
protection policy ref
optional trailing policy ref
```

This delivery intentionally defines the deterministic boundary but not a universal formula.

Reason: lot-size economics and price-value conversion can depend on instrument/runtime/provider capabilities. Those provider-specific facts must be normalized behind adapters before a deterministic calculator consumes them; they must not be guessed or hardcoded into strategic Core.

Later concrete reference calculators can implement this Protocol with explicit normalized inputs and tests.

## Stop Loss / Take Profit geometry

Before an execution plan can be produced, protection geometry must be directionally coherent:

```text
BUY:
    Stop Loss < entry reference < Take Profit

SELL:
    Take Profit < entry reference < Stop Loss
```

A violation is `RISK_BLOCKED`.

For a LIMIT Core decision, the calculation entry reference must equal the Core-authorized limit price.

For MARKET decisions, the calculation may use a current normalized entry reference supplied to the deterministic calculator.

## Trailing Stop authority

Delivery 4 does not move a trailing stop.

It only binds an optional `TrailingPolicyReference` into:

```text
ClientExecutionPolicy
ClientExecutionCalculation
ClientExecutionPlan
```

The calculation's trailing reference must exactly match the authorized execution policy.

Actual position lifecycle/trailing actions and causal receipts belong to `QORE-CLIENT-POSITION-LIFECYCLE-001`.

The governing invariant remains:

```text
TRAILING ACTION
 = Core Decision
 + Authorized Trailing Policy
 + Observed State
```

## Evaluation verdicts

`ClientExecutionVerdict` defines:

```text
EXECUTE
DECISION_BLOCKED
SECURITY_BLOCKED
ACCOUNT_BLOCKED
PROP_POLICY_BLOCKED
RISK_BLOCKED
ENTITLEMENT_BLOCKED
UNRESOLVED
```

`EXECUTE` means only:

> All non-production Client Agent gates represented by this delivery passed and an auditable plan may be handed to later canonical authorization/execution composition.

It does **not** mean:

- an order was submitted;
- a broker accepted anything;
- Production is enabled;
- cryptographic verification was performed by this module;
- global pre-trade safety can be bypassed.

Business/policy blocks return `Success[ClientExecutionEvaluation]` with a typed verdict/reason because the evaluation itself completed deterministically.

Structurally invalid arguments return typed `Failure`.

## Gate order

`evaluate_client_execution(...)` fails closed through this logical sequence:

```text
1. Core decision resolved + approved + unexpired
2. security attestation exact decision/account/runtime binding
3. security status VERIFIED
4. security temporal validity/freshness
5. account lifecycle ACTIVE
6. exact account-policy binding
7. account-policy effective/current/complete
8. exact observed-account binding
9. account-state temporal validity/freshness
10. account/policy currency coherence
11. positive equity
12. maximum drawdown guard
13. Daily Loss guard
14. exact entitlement binding
15. entitlement enabled/current
16. exact calculation decision/account binding
17. calculation temporal validity
18. exact sizing/protection/trailing policy binding
19. calculated risk <= authorized per-trade risk
20. Core LIMIT price consistency where applicable
21. SL/TP directional protection geometry
22. construct auditable ClientExecutionPlan
```

No failed gate falls through to a later execution path.

## Drawdown and Daily Loss

New trading is risk-blocked when observed:

```text
current_drawdown >= policy.max_drawdown
```

or:

```text
daily_loss >= policy.daily_loss_limit
```

A zero mandatory DD/Daily Loss policy threshold is treated as unresolved policy for new trading in this delivery rather than guessed as an operational rule.

This protects against accidentally interpreting an incomplete external policy snapshot as permission.

## Multi-account independence

The same `CoreTradeDecision` can be evaluated independently for multiple accounts.

Each account has its own:

- binding;
- runtime ref;
- cryptographic attestation target;
- prop/account policy;
- observed DD/Daily Loss/equity;
- entitlement;
- calculation policy;
- lot/protection calculation;
- verdict.

Therefore this is valid:

```text
Core Decision D
  -> Account A -> EXECUTE
  -> Account B -> RISK_BLOCKED
  -> Account C -> ENTITLEMENT_BLOCKED
```

No account verdict mutates or grants authority to another account.

## Auditable plan genealogy

An `EXECUTE` verdict carries `ClientExecutionPlan` with enough explicit provenance to begin the causal chain:

```text
Core DecisionId
TradingAccountId
ClientId
AccountPolicyReference
AccountPolicySnapshotId
ClientExecutionPolicyId
SizingPolicyReference
ProtectionPolicyReference
TrailingPolicyReference (optional)
ProductEntitlementReference
ExecutionRuntimeReference
ClientAccountObservationId
DecisionSecurityEvidenceReference
calculated quantity / SL / TP
created_at
```

This is the pre-position portion of the required genealogy:

```text
ACTION -> POSITION -> CORE DECISION -> POLICY -> RATIONALE -> EVIDENCE
```

Position/action receipts are added later by the lifecycle delivery.

The structured `FunctionalDecision.reasons` remain the strategic rationale; this delivery does not store private chain-of-thought.

## Existing pre-trade/execution boundaries preserved

The repository already requires controlled execution to pass through canonical contracts such as:

```text
OrderIntent
PreTradeAuthorization
ExecutionSafetySwitchSnapshot
AuthorizedOrderIntent
ExecutionSubmission
ExecutionBoundary
ExecutionReceipt
reconciliation
```

`ClientExecutionPlan` has no `submit`, `send_order`, broker or credentials API.

A later composition delivery must adapt a valid ClientExecutionPlan into the canonical order/pre-trade path without removing its existing authorization, switch, idempotency or reconciliation controls.

## No automatic retry / redispatch

This delivery defines no:

- retry loop;
- redispatch;
- thread;
- timer;
- scheduler;
- network call;
- provider IO.

Execution ambiguity remains governed by the existing reconciliation doctrine. No Client Agent contract may automatically create duplicate exposure after an uncertain execution outcome.

## Determinism and typing

Contracts preserve repository standards:

- `dataclass(frozen=True, slots=True)`;
- explicit caller-supplied UUIDs;
- explicit timezone-aware timestamps;
- no hidden `datetime.now()`;
- no hidden UUID generation;
- canonical imported order/financial primitives;
- typed enums for verdicts/reasons;
- typed `Result / Success / Failure`;
- deterministic `logical_values()`;
- no mutable global authority state;
- no `type: ignore`;
- no unsafe cast;
- no suppression.

## Tests

`tests/infrastructure/test_client_execution_agent.py` proves:

- Core trade decisions reuse canonical FunctionalDecision/order semantics;
- quantity does not live in strategic Core trade decision;
- LIMIT decisions require canonical limit prices;
- observed account and execution policy contracts are strict;
- a valid independent account evaluation produces an auditable plan without submission capability;
- rejected/expired Core decisions block new trading;
- security must be verified and exact-account/runtime bound;
- security evidence must be temporally valid/fresh;
- non-active account blocks;
- mismatched/unresolved/expired prop policy blocks;
- stale/wrong-account observed state fails closed;
- max DD, Daily Loss and non-positive equity block;
- entitlement must be enabled, account-bound and fresh;
- calculations must bind the exact decision/account/policies;
- calculated risk over policy blocks;
- invalid SL/TP geometry blocks;
- BUY and SELL geometry are directionally distinct;
- LIMIT calculation must honor the Core limit price;
- one Core decision can produce independent outcomes for two accounts;
- the calculator Protocol has no broker submission API.

## Explicitly not implemented

This delivery does not implement or authorize:

- a concrete lot-sizing formula;
- provider/instrument contract-value conversion;
- cryptographic signing/verification;
- nonce/replay store;
- key rotation/revocation;
- canonical decision envelope serialization;
- `OrderIntent` submission from Client Agent;
- broker/MT5/FCM IO;
- live account execution;
- position lifecycle mutations;
- trailing stop movement;
- execution receipts specific to Client Agent;
- Client Performance Ledger;
- trial/billing/payment implementation;
- Widget;
- Managed Hosting;
- Futures;
- Production;
- MISSION-06 activation;
- MISSION-03 Gate #5 closure.

## Acceptance result

This delivery is complete only when the exact PR head passes the unchanged repository Quality Gate and merges with only the intended source, tests and architecture documentation.

After merge, the next authorized MISSION-07 delivery is:

```text
QORE-CLIENT-DECISION-SECURITY-001
```

That delivery must replace the current attestation assumption with the actual canonical cryptographic decision envelope/verifier semantics, including authenticity, integrity, expiry, replay protection, account/runtime binding, key versioning and revocation — still without opening Production.
