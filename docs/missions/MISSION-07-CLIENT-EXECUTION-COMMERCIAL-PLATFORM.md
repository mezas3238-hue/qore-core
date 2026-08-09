# MISSION-07 — QORE Client Execution & Commercial Platform

Status: **OPEN — NON-PRODUCTION CLIENT/COMMERCIAL IMPLEMENTATION AUTHORIZED; MISSION-06 AND PRODUCTION CLOSED**

Opening baseline:

```text
main @ 7a6f4e090aaf712e97f6f60b874a7116f2daf845
```

Canonical architecture baseline:

```text
QORE-CLIENT-PLATFORM-ARCH-001
```

External state verified before opening:

```text
MISSION-03 Gate #5 / issue #146 = OPEN / BLOCKED
MISSION-05 = COMPLETED
MISSION-06 = CLOSED
Production = CLOSED
```

## Why MISSION-07

MISSION-05 closed the non-production QORE Mobile & CEO Command Center scope and explicitly kept the future Client EA and Client Widget in a separate product/deliverable family.

`QORE-CLIENT-PLATFORM-ARCH-001` subsequently defined the next client-product boundary and requires an explicit non-production mission before implementation.

MISSION-06 remains the reserved Production Trading Readiness frontier and is not opened, bypassed or reinterpreted by this mission.

Therefore MISSION-07 is the next independent non-production mission for the client execution/commercial product family.

MISSION numbering does not waive earlier gates. MISSION-07 can proceed only on work independent of the externally blocked MISSION-03 operational evidence and of Production authorization.

## Mission purpose

MISSION-07 converts the already-defined client architecture into deterministic, typed, testable non-production contracts and reference composition for:

```text
Client / Account Foundation
        ↓
Account / Prop Policy Governance
        ↓
Client Execution Agent Contracts
        ↓
Cryptographic Decision Security
        ↓
Position Lifecycle / Causal Audit
        ↓
Client Performance Accounting
        ↓
Trial / Licensing / Entitlements
        ↓
Commercial Products / Billing / Payments
        ↓
Corporate Profit Vault Expansion
        ↓
Multi-account Client Read Model / Widget
```

MISSION-07 does not authorize live Client Agent deployment, native broker execution, Managed Hosting runtime or Futures execution.

## Canonical existing foundation

MISSION-07 consumes rather than replaces the architecture and contracts already merged on `main`, including:

- `QORE-CLIENT-EXECUTION-EXPERIENCE-ARCH-001`;
- `QORE-CLIENT-PROFIT-VAULT-ARCH-001`;
- `QORE-CLIENT-PLATFORM-ARCH-001`;
- existing provider/adapter governance boundaries;
- existing secret-reference, observability and resilience contracts;
- canonical order-intent / execution / reconciliation safety contracts where semantics are reusable;
- MISSION-04 replay, audit, transport and executive-governance concepts only where the client boundary can reuse a generic invariant without acquiring executive authority;
- MISSION-05 presentation lessons for freshness/read-only state without coupling the Client Widget to the CEO Command Center.

No delivery may silently redefine a previously closed contract. Where the client domain needs a different contract, it must introduce an explicit new client-scoped type/boundary and document the distinction.

## Maximum trading-authority invariant

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

QORE Core remains the sole strategic authority that can originate a new trade.

A Client Execution Agent:

- does not discover opportunities;
- does not generate independent BUY/SELL decisions;
- does not invent strategy;
- does not infer authorization from billing, hosting or UI state;
- cannot transform a blocked/rejected decision into execution.

The Agent may perform deterministic delegated execution and deterministic protection of an already-authorized position only inside the causal bounds of the originating Core Decision and versioned policies.

## Causal-audit invariant

Every future trading action must preserve reconstructible genealogy:

```text
ACTION -> POSITION -> CORE DECISION -> POLICY -> RATIONALE -> EVIDENCE
```

No orphan execution, protection mutation or exit is allowed.

Structured rationale/evidence must be sufficient to explain why an action occurred without storing private chain-of-thought.

## Multi-account invariant

MISSION-07 adopts:

```text
1 Client -> N independent Trading Accounts
```

Accounts remain independent in execution, risk, drawdown, daily-loss policy, prop policy, product entitlement, hosting entitlement and performance accounting.

Cross-account aggregation may exist only as a read model. It must never silently combine independent risk or settlement authority.

## Single-account execution authority

Each account must have at most one active execution authority.

MISSION-07 may define the logical identities and bindings required by later hosting/runtime work, but actual distributed lease/fencing/failover infrastructure remains outside this mission.

No delivery may normalize a design in which two active Agents can write concurrently to one account.

## Core Decision security doctrine

MISSION-07 must define a canonical client decision-security contract that is suitable for later concrete cryptographic adapters.

It must cover at least:

- canonical logical decision representation;
- decision identity;
- protocol/schema version;
- authenticity/integrity evidence;
- issue time / expiry;
- nonce/sequence or equivalent replay evidence;
- account/runtime routing binding where applicable;
- entitlement binding/reference;
- key identity/version;
- revocation/rotation state;
- fail-closed verification outcome.

MISSION-07 may implement deterministic cryptographic-policy contracts and reference verification using safe test keys/fixtures only if the delivery explicitly authorizes it.

Productive private keys, key-management service integration and public signal distribution remain CLOSED.

## Client / Account privacy doctrine

Core does not become a civil-identity database.

Client/account contracts must prefer opaque identifiers and minimum necessary data.

MISSION-07 must not place into Core contracts:

- passport/selfie data;
- government identity documents;
- broker passwords;
- platform logins;
- bearer tokens;
- private keys;
- payment-card data.

When a future external identity/KYC service is required, QORE contracts should consume only safe attestations/references and explicit provenance required by the service boundary.

## Account / Prop Firm policy doctrine

Policy is explicit, versioned and evidence-bound.

Unknown, contradictory, incomplete, expired or unsupported mandatory policy state fails closed for new trading.

Policy may influence deterministic account-local execution/protection, including:

- drawdown rules;
- daily loss;
- static/trailing DD semantics;
- trading restrictions;
- account phase;
- profit split;
- payout eligibility;
- sizing/protection limits.

No client UI setting may override mandatory account/risk policy.

## Position-protection doctrine

Commercial state may block future eligibility, but it may not abandon an already-open authorized position.

For Agent entitlement failure/non-payment:

```text
NO NEW TRADES
-> SUSPEND_PENDING_FLAT
-> existing authorized lifecycle/protection continues
-> account FLAT
-> AGENT SUSPENDED
```

Billing cannot force-close a trade merely to collect money.

MISSION-07 must preserve no-automatic-redispatch semantics after ambiguous execution outcomes.

## Performance-accounting doctrine

Client trading performance is not corporate revenue.

The required boundary is:

```text
Execution / Realized Result
        ↓
Client Performance Ledger
        ↓
Commercial eligibility / payout evidence
        ↓
Billing / payment evidence
        ↓
Corporate Profit Vault projection
```

Per-account economic state must remain isolated before any client-level or corporate read projection.

## Performance-fee doctrine

Future contracts must distinguish:

```text
GROSS TRADING PROFIT
CLIENT ENTITLED PROFIT
CLIENT PAID PROFIT
ELIGIBLE CLIENT PAID PROFIT
QORE PERFORMANCE FEE
```

The current canonical design rule is:

```text
QORE Core Performance Fee
 = 20% of verified Eligible Client Paid Profit
```

`DUE != PAID`.

No payment or payout may be inferred from realized P&L alone.

A future payment/payout evidence contract must exist before a value can become `PAID` or enter Cash Received.

## Trial doctrine

Current design hypothesis:

```text
Client Execution Agent = USD 29 / account / month
Trial = 14 days
```

The trial trigger is not download/install/registration.

It is:

```text
FIRST ELIGIBLE LIVE EXECUTION
```

MISSION-07 may define the deterministic evidence and immutable state-transition contracts for this trigger.

It must not fake live-execution evidence. Non-production fixtures can prove transition semantics without representing real commercial activation.

Pricing belongs to versioned Products/Plans, not to execution logic.

## Widget doctrine

Current design hypothesis:

```text
Client Widget = USD 9.99 / client / month
```

The Client Widget is multi-account and presentation-only.

It may present authorized read state such as:

- account status;
- balance;
- today realized result;
- week realized result;
- trade pulse;
- per-account drill-down;
- service status.

It cannot:

- originate a Core Decision;
- submit broker orders;
- change risk;
- move SL/TP;
- alter account policy;
- bypass entitlement;
- access provider credentials.

Widget non-payment can suspend the Widget independently and must not suspend the Agent, Core, positions or account protection.

## Commercial Platform doctrine

MISSION-07 may implement deterministic non-production contracts/reference state for:

- Client Registry;
- Account Registry;
- Products & Plans;
- Trial Management;
- Billing;
- Invoice Ledger;
- Payment State;
- Payment Reconciliation;
- Entitlements;
- Performance Accounting;
- Account/Prop Policy;
- Corporate Profit Vault projections.

MISSION-07 does not integrate a productive payment processor or tax/accounting system.

Billing has commercial authority only.

## Corporate Profit Vault doctrine

Corporate Profit Vault may contain only QORE corporate financial state, for example:

- EA subscription revenue;
- Widget revenue;
- future Hosting revenue;
- future Futures revenue;
- Core performance-fee revenue;
- Accounts Receivable;
- Cash Received.

It must preserve product/client/account/invoice/period/currency/payment attribution as applicable.

It must not treat raw client P&L as QORE cash.

## Repository / dependency boundary

MISSION-07 remains inside the current repository as the canonical architecture/contract source-of-truth, but dependency direction remains strict.

Rules:

- strategic Core logic must not import commercial/client runtime modules;
- Client Agent contracts must not become dependencies of Core decision generation;
- billing/payment modules must not become dependencies of Core or Risk;
- Widget/read-model modules must not become dependencies of execution;
- provider-specific SDKs must not enter Core domain modules;
- no mobile/UI framework dependency is added to `src/qore`;
- concrete MT5/native broker/mobile runtimes remain outside MISSION-07 unless a later explicit repository-boundary delivery authorizes placement.

Platform-neutral contracts may live in the existing package structure only when they preserve inward dependency direction and do not make Core depend on the client/commercial domain.

## Determinism and quality doctrine

MISSION-07 implementation deliveries must preserve repository conventions:

- `dataclass(frozen=True, slots=True)` for immutable value contracts where appropriate;
- explicit caller-supplied identity;
- timezone-aware explicit timestamps;
- no hidden `datetime.now()` for contract state;
- no implicit UUID generation in deterministic domain operations;
- strict type validation;
- deterministic ordering / `logical_values()` where canonical representation is needed;
- typed `Result / Success / Failure` for fallible boundaries;
- typed errors;
- no mutable global authority state;
- no hidden retry/scheduler/thread behavior;
- no secret-bearing logs/evidence;
- no `type: ignore`, unsafe cast or suppression as a shortcut.

The unchanged repository Quality Gate remains:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

## Official MISSION-07 delivery sequence

```text
1.  QORE-MISSION07-DOCS-001
    Mission scope, authority doctrine, repository boundary, sequence and closure criteria

2.  QORE-CLIENT-ACCOUNT-FOUNDATION-001
    Opaque Client/TradingAccount identities, 1->N binding, account classification/lifecycle and independence

3.  QORE-ACCOUNT-PROP-POLICY-001
    Versioned account/prop-firm policy snapshots, normalized phases and fail-closed mandatory rules

4.  QORE-CLIENT-EXECUTION-AGENT-CONTRACTS-001
    Deterministic delegated-execution inputs/verdicts, account-state consumption, sizing/SL/TP/trailing authority boundaries

5.  QORE-CLIENT-DECISION-SECURITY-001
    Canonical Core Decision envelope verification, freshness, expiry, replay, binding, key-version/revocation contracts

6.  QORE-CLIENT-POSITION-LIFECYCLE-001
    Decision->execution->position->protection->exit causal genealogy and auditable lifecycle evidence

7.  QORE-CLIENT-PERFORMANCE-LEDGER-001
    Append-only per-account realized-performance evidence, payout evidence references and corrections

8.  QORE-CLIENT-TRIAL-LICENSING-001
    First Eligible Live Execution evidence contract, immutable 14-day trial state and safe Agent entitlement suspension

9.  QORE-COMMERCIAL-PRODUCTS-PLANS-001
    Versioned EA/Widget product-plan contracts, per-account vs per-client charging scope and non-execution authority

10. QORE-COMMERCIAL-BILLING-PAYMENTS-001
    Invoice/payment/reconciliation evidence, DUE != PAID, entitlement consequences and no trading authority

11. QORE-CORPORATE-PROFIT-VAULT-EXPANSION-001
    Corporate receivable/cash projections from verified commercial/performance-fee evidence without client-P&L contamination

12. QORE-CLIENT-MULTIACCOUNT-READ-MODEL-001
    Client-scoped portfolio/read projection across N independent accounts with explicit freshness and service state

13. QORE-CLIENT-WIDGET-MULTIACCOUNT-001
    Presentation-only cross-platform logical Widget state consuming the client read model without execution access

14. QORE-MISSION07-E2E-OFFLINE-001
    Deterministic offline composition proving multi-account independence, decision-only execution authority, commercial separation and safe suspension

15. QORE-MISSION07-CLOSURE-001
    Security/architecture/readiness closure review without MISSION-06 or Production activation
```

This order may change only through an explicit architecture change merged to `main`.

## Delivery 2 — Client & Account Foundation

The first implementation delivery must define the minimum stable identities/bindings required by every later client feature.

It must prove:

- `ClientId` is opaque and contains no civil identity;
- `TradingAccountId` is opaque and is not a broker login/credential;
- one client can bind one or many accounts;
- one account has exactly one client owner/binding in the canonical relationship;
- account lifecycle/classification is explicit;
- account-scoped references for product/policy/runtime can be represented without embedding secret values;
- duplicate, contradictory or ambiguous bindings fail closed;
- accounts remain independent for risk/performance/execution semantics;
- no trading operation is introduced.

## Delivery 3 — Account / Prop Policy

Must define versioned, attributable policy snapshots without hardcoding provider implementations into Core.

At least:

- firm/program identity/reference;
- normalized account phase;
- account size/classification where needed;
- daily loss;
- max drawdown;
- static/trailing DD semantics;
- profit split;
- payout restrictions/evidence requirements;
- trading restrictions;
- effective/version identity;
- fail-closed unresolved state.

No policy can grant a trade without a Core Decision.

## Delivery 4 — Client Execution Agent Contracts

Must define the platform-neutral delegated execution contract before a concrete EA exists.

The contract must separate:

```text
Core Decision authority
Account/Prop policy
Observed account/platform state
Deterministic execution/protection calculation
Execution verdict
```

Expected verdicts must distinguish execution from policy/risk/entitlement/unresolved blocks.

No concrete broker SDK or MT5 code is authorized.

## Delivery 5 — Decision Security

Must protect against stolen/replayed/modified/misrouted decisions.

A success verdict means only that decision-security requirements passed. It does not by itself mean the account may execute; later account/risk/policy checks still apply.

No productive key material enters tests or repository content.

## Delivery 6 — Position Lifecycle / Causal Audit

Must prove every execution/protection/exit state transition can trace to the originating decision and policy/evidence.

Trailing changes must be first-class auditable actions.

Ambiguous execution outcomes must not auto-redispatch.

## Delivery 7 — Client Performance Ledger

Must retain account-scoped positive and negative realized results and correction lineage.

It is not Corporate Profit Vault and has no billing authority.

Payout evidence is represented separately from raw realized result.

## Delivery 8 — Trial / Licensing

Must model `FIRST ELIGIBLE LIVE EXECUTION` as an evidence-gated transition.

In deterministic tests, fixtures may prove the state machine; they must not be described as real live-execution evidence.

Once trial timestamps exist they are immutable and cannot be reset by reinstall/runtime migration.

Non-payment/expiration blocks new trades but preserves already-authorized open-position lifecycle until flat.

## Deliveries 9–10 — Products, Billing & Payments

Commercial state remains outside trading authority.

Products/Plans must model charging scope explicitly:

```text
EA -> per account
Widget -> per client
```

Current prices may be represented only as versioned plan data/policy where explicitly required; they must not be hardcoded into execution logic.

Payments must distinguish due/received/reconciled states using evidence.

No billing state can issue BUY/SELL/CLOSE.

## Delivery 11 — Corporate Profit Vault Expansion

Must consume only verified commercial/economic projection inputs.

For performance fees, the future base is verified `Eligible Client Paid Profit`, not gross trading profit.

Cross-client netting is prohibited for fee calculation.

## Deliveries 12–13 — Multi-account Read Model / Widget

The read model may aggregate N accounts for display while retaining every account identity and freshness independently.

The Widget consumes only authorized read state and remains outside execution.

One client may have one Widget while having many paid Agent/account entitlements.

## Delivery 14 — Offline E2E

The E2E harness must prove with deterministic fakes/reference adapters that:

- no Core Decision means no new account execution action;
- one valid Core Decision can be evaluated independently for multiple accounts;
- one account may EXECUTE while another BLOCKS without cross-account state corruption;
- duplicated/replayed decision security fails closed;
- account/policy ambiguity fails closed;
- no account receives another account's binding/policy/performance state;
- lifecycle actions retain causal genealogy;
- client performance stays outside Corporate Profit Vault until explicit commercial/economic evidence allows projection;
- `DUE` does not become `PAID` without payment evidence;
- entitlement expiry blocks new trades but preserves open-position protection;
- Widget remains read-only;
- no broker/provider credentials are reachable from Widget/commercial state;
- Core runtime identity/strategic authority remains unaffected by client/commercial composition.

Offline evidence does not authorize live trading or commercial launch.

## Mission closure criteria

MISSION-07 may be marked `COMPLETED` only when all official deliveries have merged and the closure review proves that:

- Client/Account identities and 1->N bindings are deterministic and opaque;
- account independence is enforced;
- account/prop policy is explicit/versioned/fail-closed;
- Client Agent contracts cannot originate trading strategy;
- no new trading action exists without Core Decision authority;
- decision security has freshness/expiry/anti-replay/binding semantics;
- all lifecycle actions preserve causal genealogy/evidence;
- Client Performance Ledger is account-scoped and separate from corporate revenue;
- trial/licensing behavior is evidence-gated and safe for open positions;
- billing/payment state cannot control trading;
- `DUE != PAID` is enforced;
- performance-fee projection uses verified Eligible Client Paid Profit;
- Corporate Profit Vault cannot ingest raw client P&L as cash;
- multi-account read models preserve account boundaries/freshness;
- Client Widget is presentation-only;
- deterministic E2E covers success, block, replay, stale/ambiguous commercial evidence and safe suspension;
- no Production/native broker/Managed Hosting/Futures runtime was activated;
- MISSION-03 #146 remains governed only by its own external evidence;
- MISSION-06 remains CLOSED unless separately authorized.

## Explicitly out of scope

MISSION-07 does **not** authorize or implement:

- MISSION-03 OANDA Practice evidence fabrication;
- MISSION-03 Gate #5 closure without real evidence;
- MISSION-06 Production Trading Readiness;
- Production deployment;
- productive broker/provider credentials;
- real capital activation;
- autonomous real-money execution;
- a concrete MT5/MT4/cTrader production Agent;
- public signal distribution;
- productive cryptographic key management;
- native broker/FCM live connection;
- Managed Hosting orchestrator/deployment/failover runtime;
- regional Futures execution runtime;
- broker/FCM commercial agreements;
- market-data licensing agreements;
- tax/legal conclusions;
- identity-document storage in Core;
- payment-card storage;
- direct Widget/billing access to execution.

## Future boundaries after MISSION-07

The following architectural phases from `QORE-CLIENT-PLATFORM-ARCH-001` remain intentionally outside this mission and require their own future authorization:

```text
K. Managed Hosting
L. Native Broker Execution
M. Regional Futures Execution
N. Commercial Futures Validation
```

This document does not assign future mission IDs to those boundaries.

## Opening result

After this delivery passes the unchanged QORE Quality Gate and merges to `main`, the next authorized MISSION-07 delivery is:

```text
QORE-CLIENT-ACCOUNT-FOUNDATION-001
```

That delivery may add platform-neutral non-production contracts and tests for Client/TradingAccount identities and bindings only. It may not add trading execution, billing runtime, provider credentials or Production capability.
