# QORE-FND-05-DEPARTMENT-REGISTRY-DEPENDENCY-GRAPH-001

## Status

**STAGE-05 / FND-05 — ARCHITECTURE + MINIMUM TYPED FOUNDATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #312  
Master roadmap: #303  
Certified starting baseline: `ee3939c581d197772be367bcbf0e2e350f21b0e5`

This artifact fulfills the FND-01 obligation to produce a Canonical Department Registry, Department Dependency Graph, Canonical Fact/Aggregate Ownership Matrix and Sync/Async Communication Matrix before FND-06 begins.

It also incorporates the CEO-frozen QORE-owned Hosting/VPS/Cloud service decision through `QORE-MASTER-ROADMAP-QORE-OWNED-CLOUD-FABRIC-AMENDMENT-001`.

## Governing invariants

```text
CORE IS THE SOVEREIGN DOMAIN
DEPARTMENT TECHNICAL AUTONOMY != AUTHORITY AUTONOMY
MODULE / FOLDER != DEPARTMENT AUTHORITY
TYPE LOCATION != FACT OWNERSHIP
SINGLE SOURCE OF TRUTH = SINGLE GOVERNED AUTHORITY PER CANONICAL FACT / AGGREGATE
READ MODEL != WRITE AUTHORITY
PROJECTION != CANONICAL MUTATION SOURCE
SYNC DEPARTMENT DEPENDENCIES MUST BE ACYCLIC
ASYNC FEEDBACK != UNBOUNDED LOOP
CLIENT / SERVICE PLANE != STRATEGIC AUTHORITY
HOSTING CAPACITY != TRADING INTENT
HEALTHY != EXECUTION AUTHORITY
WIDGET != EXECUTION
ACCOUNT IDENTITY != RUNTIME IDENTITY != PROVIDER ACCOUNT REFERENCE != EXECUTION AUTHORITY
NO VERIFIED CONTRACT -> NO CROSS-DEPARTMENT AUTHORITY TRANSFER
NO VERIFICATION -> NO APPROVAL
```

## Evidence ledger

### EVID-FND05-01 — FND-01 mandates this stage

`docs/architecture/QORE-DEPARTMENTAL-SOVEREIGNTY-FREEZE-001.md` requires later stages to produce at minimum:

1. Canonical Department Registry;
2. Department Dependency Graph;
3. Canonical Fact/Aggregate Ownership Matrix;
4. Sync/Async Communication Matrix;
5. safety-critical state/reservation contracts;
6. freshness/degraded-mode matrix;
7. recovery/reconciliation matrix;
8. cross-boundary command/query/event/evidence contracts.

FND-05 owns items 1-4 and the ownership inputs needed by 5-8. FND-06/FND-07 own the detailed contracts that follow.

FND-01 also states that `RuntimePlan` cycle rejection is architectural precedent but the runtime-component graph is **not** the departmental dependency graph.

### EVID-FND05-02 — no canonical DepartmentId/DepartmentRegistry was verified

Repository search on certified baseline did not establish a canonical `DepartmentId` or `DepartmentRegistry` implementation.

`src/qore/domain/modules.py` defines functional module descriptors (`ModuleName`, `ModuleVersion`, `ModuleLayer`, `ModuleDescriptor`) but a module is not a canonical department authority.

Therefore:

```text
MODULE DESCRIPTOR != DEPARTMENT REGISTRY
```

A minimum typed Department Registry is justified in FND-05 rather than leaving Department authority as free-form document text.

### EVID-FND05-03 — RuntimePlan cannot be reused as Department authority

`src/qore/core/runtime_plan.py` validates known runtime component dependencies and rejects cycles through deterministic ordering.

This is reusable validation precedent only.

```text
RuntimeComponentSpec != DepartmentSpec
RuntimePlan != DepartmentRegistry
```

The FND-05 implementation therefore creates a separate domain contract and does not reinterpret runtime deployment components as departments.

### EVID-FND05-04 — UMI-02 owns economic/listing/venue identity

Certified `src/qore/infrastructure/universal_instrument_identity.py` owns the universal economic/listing/venue identity foundation.

Department 4 therefore owns Markets/Instruments canonical identity authority. Other departments consume those identities without inventing parallel symbols/provider IDs as economic identity.

### EVID-FND05-05 — Market data and time are distinct authorities

`src/qore/infrastructure/market_observation.py` provides typed market observations, explicit price semantics and canonical timestamps.

Legacy `src/qore/infrastructure/market_data.py` proves fixed-duration OHLC semantics remain bounded.

Department 5 owns canonical market observations/evidence. Department 6 owns time/calendar/session/lifecycle timing semantics. Neither becomes economic instrument identity authority.

### EVID-FND05-06 — Risk evaluates but does not own Portfolio

Current flow evidence includes CIO/CIBO/Portfolio/Risk separation and typed portfolio/risk contracts. Risk can assess/veto allocation or execution without becoming the owner of account/portfolio state.

Department 8 owns Account/Cash/Collateral/Portfolio canonical state. Department 9 owns Risk/Margin/Exposure/Limits policy and assessments.

Provider-native margin facts remain Department 3 provider facts until transformed by explicit Department 9 contracts.

### EVID-FND05-07 — Execution and post-trade are distinct

`src/qore/infrastructure/order_intent.py`, controlled execution boundaries and provider execution contracts establish Order/Execution semantics.

`src/qore/infrastructure/execution_reconciliation.py` establishes reconciliation as a distinct state/evidence concern.

Department 10 owns order/routing/execution authority contracts. Department 11 owns position/settlement/post-trade/reconciliation state.

### EVID-FND05-08 — research, decision intelligence and validation are distinct

Existing Research/Replay artifacts, CIO/CIBO/Virtual Trader modules and Data Lineage/Statistics/Validation foundations are separate bounded contexts.

Research artifacts do not self-promote to trading authority. Decision Intelligence owns strategic decision products; Data Lineage/Knowledge/Statistics/Validation owns lineage/statistical/validation evidence and promotion inputs.

### EVID-FND05-09 — MISSION-08 is Hosting foundation, not productive Cloud proof

Existing source includes:

- `hosting_execution_unit.py`;
- `hosting_runtime_registry.py`;
- `hosting_execution_lease.py`;
- `hosting_health_heartbeat.py`;
- `hosting_orchestrator.py`;
- `hosting_failover_reconciliation.py`;
- `hosting_telemetry.py`.

MISSION-08 explicitly excluded productive VPS/cloud/Kubernetes integration.

It proves reusable single-writer, lease, fencing, heartbeat, failover and reconciliation contracts, not productive QORE Cloud infrastructure.

### EVID-FND05-10 — signal, EA and Widget authority separation

`src/qore/infrastructure/client_decision_security.py` provides protected client-decision/security foundations.

MISSION-07 client execution artifacts establish the EA/Agent as delegated execution infrastructure.

Client Widget/read-model artifacts are presentation/read-side foundations.

Therefore:

```text
CORE DECISION -> PROTECTED SIGNAL -> EA / AGENT -> EXECUTION
WIDGET -> READ MODEL ONLY
```

Client surfaces do not become strategic authority.

### EVID-FND05-11 — commercial state is not trading authority

Commercial product/entitlement contracts are separately implemented from Account, Risk, Execution and Hosting authority.

Commercial suspension can gate new service availability but cannot create BUY/SELL or liquidate positions by itself.

### EVID-FND05-12 — executive surface is governed, not sovereign replacement

Existing executive governance contracts separate authenticated principal, current authority, guarded request, command/query dispatch, governance mutation and evidence.

Department 20 exposes CEO control surfaces. Department 1 remains the owner of constitutional/governance truth.

## Typed implementation delta

FND-05 adds:

`src/qore/domain/departments.py`

with:

- `DepartmentId` — 24 stable IDs (`D01`..`D24`);
- `DepartmentInteractionMode` — `SYNCHRONOUS` / `ASYNCHRONOUS`;
- immutable `DepartmentSpec`;
- immutable directed `DepartmentDependency` (`consumer -> provider`);
- immutable `DepartmentRegistry`;
- unknown-reference rejection;
- self-dependency rejection;
- duplicate ID/slug/name/edge rejection;
- deterministic canonical logical values;
- synchronous-cycle rejection;
- deterministic provider-before-consumer synchronous ordering;
- the CEO-frozen canonical 24-department specs;
- the minimum canonical dependency graph.

The registry does **not** become a runtime orchestrator, transport, service locator or database.

## Dependency semantics

An edge is written:

```text
CONSUMER -> PROVIDER
```

It means the consumer requires a governed fact/contract/capability from the provider.

`SYNCHRONOUS` means the dependency may participate in a logically synchronous authority/safety decision. It does **not** mandate a remote network call. A local, versioned, bounded and verifiable contract may satisfy the dependency.

`ASYNCHRONOUS` means the consumer may consume events, evidence, projections or feedback without requiring an immediate blocking authority call.

Async cycles are not automatically invalid, but FND-06/FND-07 must prove causation, versioning, idempotency/deduplication where required, ordering assumptions, freshness and loop containment.

## Canonical 24-department registry

| ID | Canonical department | Primary authority |
|---|---|---|
| D01 | Core Governance & Constitutional Contracts | constitution, global invariants, governance/authority rules |
| D02 | Identity, Security & Cryptographic Trust | principals, trust/key/security contracts, secret-reference doctrine |
| D03 | Platform Connectivity & Provider Capability | provider/platform/server/account capability and native boundary facts |
| D04 | Markets, Instruments & Reference Data | economic/listing/venue/reference identity and reference-data authority |
| D05 | Market Data & Market Evidence | canonical market observations and market evidence |
| D06 | Time, Calendars, Sessions & Instrument Lifecycle | time/calendar/session/lifecycle timing semantics |
| D07 | Valuation, Pricing, Yield & Analytics | valuation/analytic outputs and methodology-scoped pricing facts |
| D08 | Account, Cash, Collateral & Portfolio | QORE account/cash/collateral/portfolio aggregates |
| D09 | Risk, Margin, Exposure & Limits | risk policy, exposure/limit/margin assessments and reservations policy |
| D10 | Order, Execution & Routing | order intent, execution/routing authority and execution receipts |
| D11 | Position, Settlement, Post-Trade & Reconciliation | positions, settlement and reconciliation truth |
| D12 | Research, Replay & Quant | research runs, replay/quant execution artifacts and research outputs |
| D13 | Decision Intelligence — CIO / CIBO / Specialized Traders | strategic/functional trading decisions and specialist decision products |
| D14 | Data Lineage, Knowledge, Statistics & Validation | lineage, knowledge, statistical/validation and promotion evidence |
| D15 | Observability, Reliability & Incident Operations | telemetry projections, reliability/incident operational evidence |
| D16 | Distributed Runtime, Hosting, VPS & Cloud Operations | QORE Cloud/Hosting Fabric topology, capacity, placement, runtime/lease infrastructure |
| D17 | Signal Production, Security & Distribution | protected signal production/distribution state derived from valid Core Decisions |
| D18 | Client Execution Ecosystem — EA / Agent | delegated client execution-agent operational state and lifecycle |
| D19 | Client Read Models & Widget Presentation | client-facing read projections only |
| D20 | Executive / CEO Control Surfaces | governed executive request/delivery/control-surface state |
| D21 | Commercial Products, Billing, Payments & Entitlements | product, payment and entitlement truth |
| D22 | Compliance, Regulatory Evidence & Audit Reporting | compliance/regulatory/audit reporting evidence |
| D23 | Notifications & Client/Operational Communication | notification/communication delivery state |
| D24 | Certification & Integration Gate | certification cases, exact-head approval and baseline evidence |

Removal/merging/reidentification of these departments is a material roadmap change.

## Authority ownership matrix

### D01 — Core Governance & Constitutional Contracts

Owns: constitution, authority-separation rules, governance policy state, cross-domain invariants.  
Does not own: specialized market/risk/execution data or Cloud physical state.

### D02 — Identity, Security & Cryptographic Trust

Owns: authenticated identity/trust contracts, key/security policy, secret-reference doctrine.  
Does not own: Department 16 physical secret-store nodes or Department 17 signal delivery state.

### D03 — Platform Connectivity & Provider Capability

Owns: provider/platform/server/provider-account capability facts and native adapter boundary state.  
Does not own: economic instrument identity, Core Risk policy, QORE account identity or provider-native margin as Core policy.

### D04 — Markets, Instruments & Reference Data

Owns: EconomicIdentity, ListingIdentity, venue/reference-data relationships and canonical instrument reference authority.  
Does not own: market observation values, portfolio positions, provider account authority or trading decisions.

### D05 — Market Data & Market Evidence

Owns: canonical quote/trade/bar observations and market evidence provenance.  
Does not own: instrument identity, valuation methodology or execution receipts.

### D06 — Time, Calendars, Sessions & Instrument Lifecycle

Owns: canonical temporal roles, market calendars/sessions, lifecycle timing conventions and time-domain rules.  
Does not own: economic identity itself or family valuation.

### D07 — Valuation, Pricing, Yield & Analytics

Owns: typed valuation/analytic facts and methodologies when implemented.  
Does not own: exchange market observation truth, account balances, Risk policy or instrument identity.

### D08 — Account, Cash, Collateral & Portfolio

Owns: TradingAccountId/Proprietary account-domain state, cash/collateral/portfolio aggregates and portfolio allocation truth.  
Does not own: provider account reference, execution lease, Core Decision or provider margin terms.

### D09 — Risk, Margin, Exposure & Limits

Owns: Core risk policy, limits, exposure assessments, margin/risk interpretation and future concurrency-safe reservations.  
Does not own: Portfolio state, provider-native margin facts, order routing or Cloud leases.

### D10 — Order, Execution & Routing

Owns: OrderIntent, execution/routing authority contracts, execution request/receipt semantics.  
Does not own: strategy generation, account aggregate truth or post-trade reconciliation truth.

### D11 — Position, Settlement, Post-Trade & Reconciliation

Owns: canonical position lifecycle state, settlement/post-trade state and reconciliation results.  
Does not own: pre-trade Risk policy, provider capability or strategic decisions.

### D12 — Research, Replay & Quant

Owns: research/replay execution artifacts, datasets/run bindings where assigned and quantitative research outputs.  
Does not own: productive strategy authority, validation approval or execution authority.

### D13 — Decision Intelligence

Owns: CIO/CIBO/Specialized Trader strategic/functional decision products and their decision evidence.  
Does not own: Cloud capacity, Widget state, commercial entitlement, execution lease, broker order truth or validation promotion authority.

### D14 — Data Lineage, Knowledge, Statistics & Validation

Owns: lineage, statistical/validation evidence, retained knowledge and certification inputs for research/model promotion.  
Does not own: productive execution authority or market observation authority.

### D15 — Observability, Reliability & Incident Operations

Owns: telemetry/read projections, reliability state, incident-operational evidence and alerting inputs.  
Does not own: writer authority merely because a runtime is healthy, or canonical trading facts merely because they are observed.

### D16 — Distributed Runtime, Hosting, VPS & Cloud Operations

Owns: QORE-owned Cloud/Hosting/VPS fabric operational domain, compute/virtualization inventory, storage/network fabric operations, cluster/cell topology, placement, capacity, runtime registry, deployment state, hosting execution-unit placement, account-scoped lease/fencing infrastructure, backup/DR infrastructure and Cloud operational evidence.  
Does not own: Core Decision, Risk policy, account economic truth, broker account truth, entitlement truth or Widget authority.

Security split: D02 owns trust/security contracts; D16 operates the Cloud secret/security substrate under those contracts.  
Observability split: D16 emits infrastructure facts; D15 owns cross-system observability/reliability projections.  
Commercial split: D21 decides service entitlement; D16 enforces Hosting availability without Billing acquiring trading authority.

Latency obligation: D16 owns infrastructure placement/capacity/latency evidence for the Cloud execution path. No numeric SLA exists without measured provenance.

### D17 — Signal Production, Security & Distribution

Owns: protected signal envelopes, issue/expiry/routing/replay-protection/distribution evidence derived from valid Core Decisions.  
Does not own: the strategic decision itself or account execution authority.

### D18 — Client Execution Ecosystem — EA / Agent

Owns: delegated EA/Agent operational state, installation/runtime binding and deterministic execution lifecycle within authorized bounds.  
Does not own: independent BUY/SELL strategy, Hosting lease authority, Risk policy or Widget truth.

### D19 — Client Read Models & Widget Presentation

Owns: authorized client read models/projections and Widget presentation state.  
Does not own: execution, Risk, account mutations, Hosting authority or strategic decisions.

### D20 — Executive / CEO Control Surfaces

Owns: governed executive surface request/delivery state.  
Does not own: constitutional governance truth; D01 remains authority and D02 validates identity/trust.

### D21 — Commercial Products, Billing, Payments & Entitlements

Owns: products/plans, billing/payment evidence and entitlement/service-availability facts.  
Does not own: Core Decisions, position-close authority, Risk policy or execution leases.

### D22 — Compliance, Regulatory Evidence & Audit Reporting

Owns: compliance/regulatory reporting state and audit-report evidence.  
Does not own: strategic or execution authority.

### D23 — Notifications & Client/Operational Communication

Owns: message/notification delivery state and communication evidence.  
Does not own: the source business fact or any trading authority.

### D24 — Certification & Integration Gate

Owns: certification status/evidence, exact-head approval records, merge/baseline certification state.  
Does not own: implementation domain state and cannot self-certify code it authored/directed.

## Canonical dependency matrix

The typed source contains the exact edge set. This matrix is the human-readable projection.

| Consumer | Synchronous providers | Asynchronous/evidence providers |
|---|---|---|
| D01 Governance | — | — |
| D02 Identity/Security | — | — |
| D03 Platform Connectivity | — | — |
| D04 Markets/Instruments | — | — |
| D05 Market Data | D04, D06 | D03 |
| D06 Time/Lifecycle | — | — |
| D07 Valuation | D04, D06 | D05 |
| D08 Account/Portfolio | D04 | D07, D11 |
| D09 Risk | D04, D08 | D05, D07, D11 |
| D10 Order/Execution | D03, D04, D08, D09 | — |
| D11 Post-Trade | D03, D04, D10 | D08 |
| D12 Research | D04, D06 | D05 |
| D13 Decision Intelligence | D04, D06 | D05, D07, D08, D12 |
| D14 Lineage/Validation | — | D05, D12, D13 |
| D15 Observability | — | domain/runtime/service evidence as emitted |
| D16 QORE Cloud/Hosting | D02, D08 | D15, D21 |
| D17 Signal | D02, D13, D21 | D15 |
| D18 Client EA/Agent | D02, D08, D09, D10, D16, D17, D21 | — |
| D19 Widget/Read Models | — | D08, D11, D15, D16, D18, D21 |
| D20 Executive Control | D01, D02 | D15 |
| D21 Commercial | D02 | — |
| D22 Compliance | — | D01, D14, D15, D21 |
| D23 Notifications | — | D15, D19, D21 |
| D24 Certification Gate | — | D01, D14, D15, D22 |

D15 observational intake from many domains is intentionally not encoded as a mandatory synchronous upstream dependency. Telemetry consumption cannot create reverse write authority.

## Forbidden reverse-dependency matrix

The following reverse-authority patterns are constitutionally forbidden unless a future independently certified roadmap change explicitly replaces them:

```text
D19 Widget -> D13 Decision Intelligence AS STRATEGIC INPUT AUTHORITY      FORBIDDEN
D19 Widget -> D10 Execution AS ORDER ORIGIN                               FORBIDDEN
D21 Billing -> D13 Decision Intelligence AS BUY/SELL AUTHORITY             FORBIDDEN
D21 Billing -> D10 Execution AS LIQUIDATION AUTHORITY                      FORBIDDEN
D16 Cloud health -> D13 Decision Intelligence AS STRATEGIC AUTHORITY       FORBIDDEN
D16 Cloud health -> D10 Execution AS LEASE SUBSTITUTE                      FORBIDDEN
D18 EA -> D13 Decision Intelligence AS INDEPENDENT OPPORTUNITY SOURCE      FORBIDDEN
D15 Observability -> ANY DOMAIN AS CANONICAL WRITER BY OBSERVATION          FORBIDDEN
D03 Provider facts -> D09 Risk AS UNTRANSFORMED CORE POLICY                FORBIDDEN
D03 Provider native ID -> D04 AS ECONOMIC IDENTITY SUBSTITUTE              FORBIDDEN
D11 Reconciliation -> D10 AS AUTOMATIC DUPLICATE ORDER REDISPATCH          FORBIDDEN
D24 Certification -> DOMAIN IMPLEMENTATION AS SELF-CERTIFICATION           FORBIDDEN
```

## FND-04 deferred ownership resolution

### GAP-FND04-PROVIDER-ID-01

Owner split:

- D03 owns provider/platform/server/provider-account external identity/capability boundary;
- D08 owns QORE TradingAccount identity/state;
- D04 owns economic/listing/venue identity;
- D16 may hold hosting/runtime bindings to those identities but owns none of them.

PR #298 remains HOLD until FND-05/FND-06 typed provider-scope relationships are implemented and independently certified.

### GAP-FND04-PORTFOLIO-01

D08 owns future canonical Portfolio aggregate identity/authority. No `PortfolioId` is created in FND-05 because exact aggregate lifecycle semantics belong to the owning Department 8 contract work.

### GAP-FND04-COLLATERAL-01

D08 owns collateral aggregate/state. D09 consumes collateral/margin capacity for Risk authority. D03 may expose provider-native margin/collateral facts as external evidence only.

### GAP-FND04-TIME-01

D06 owns the temporal semantic doctrine. Individual owning departments remain responsible for correct canonical timestamp serialization in their contracts. The gap remains OPEN; FND-08 may not certify broad Levels 0-3 temporal determinism while required remediation remains unresolved.

## QORE-owned Cloud Fabric freeze

The companion roadmap amendment is part of this FND-05 certification set.

Department 16 must be designed so QORE can provide Hosting/VPS/Cloud without a required external cloud provider.

Target infrastructure includes:

- QORE-owned/operated compute and virtualization;
- QORE network fabric;
- QORE storage fabric;
- orchestration/control plane;
- regional/cell topology and placement;
- account/runtime tenant isolation;
- runtime registry, lease and fencing;
- secret infrastructure under D02 contracts;
- observability/incident integration with D15;
- backup/DR;
- image/version/deployment control;
- capacity management;
- security hardening and compromise containment;
- latency evidence and futures proximity placement where material.

The design target is thousands of accounts/runtimes with horizontal scaling and bounded blast radius.

No numeric latency/capacity/security guarantee is claimed without reproducible operational evidence.

## Mobile-only hosted automation freeze

A client may use only the QORE mobile Widget while one or more account execution units run continuously inside QORE Cloud.

```text
VALID CORE DECISION / PROTECTED SIGNAL
 -> ACCOUNT / RISK / POLICY / ENTITLEMENT / SECURITY GATES
 -> VALID FENCED EXECUTION LEASE
 -> HOSTED EA / AGENT
 -> CERTIFIED PROVIDER ADAPTER
 -> EXECUTION
 -> RECONCILIATION / EVIDENCE
 -> READ MODEL
 -> WIDGET
```

The phone is outside the execution path.

```text
PHONE OFFLINE != HOSTED EXECUTION STOP
WIDGET != EXECUTION
EA != STRATEGIC TRADER
```

## Department charter freeze

Each department below instantiates the FND-01 charter schema. Detailed command/query/event/evidence names remain FND-06 scope.

### D01 Charter — Core Governance & Constitutional Contracts

1. purpose: constitutional governance and cross-domain authority rules.
2. core_governed_contracts: Core constitution and authority-separation contracts.
3. owned facts: governance policy/authority state and global invariants.
4. derived state: executive/governance read projections.
5. accepted commands: governed constitutional/governance mutations only.
6. published events/evidence: policy/authority revision evidence.
7. queries/projections: governed authority/policy reads.
8. synchronous dependencies: none required as a department.
9. asynchronous dependencies: evidence may be consumed from certified domains.
10. prohibited reverse dependencies: client/commercial/provider state cannot rewrite constitution.
11. version/freshness: explicit authority/policy version and validity.
12. degraded mode: unknown authority fails closed.
13. recovery/reconciliation: durable governance source, no history guessing.
14. security/secrets: D02 principal/trust boundary.
15. deployment/scaling: no mandatory remote hot-path centralization.
16. prohibitions: no domain implementation ownership by convenience.

### D02 Charter — Identity, Security & Cryptographic Trust

1. purpose: identity, authentication/trust and cryptographic policy.
2. core_governed_contracts: principal, key/trust, secret-reference rules.
3. owned facts: security/trust identity and revocation state.
4. derived state: authorization/security projections.
5. accepted commands: governed key/trust/security lifecycle mutations.
6. published events/evidence: auth/trust/revocation evidence.
7. queries/projections: identity/trust status.
8. synchronous dependencies: none frozen by FND-05.
9. asynchronous dependencies: incident/compliance evidence where required.
10. prohibited reverse dependencies: Cloud/provider/commercial cannot redefine trust.
11. version/freshness: key/authority version, expiry/revocation explicit.
12. degraded mode: unknown/unverifiable identity fails closed.
13. recovery/reconciliation: no implicit trust restoration.
14. security/secrets: owns security contract, not raw secret leakage.
15. deployment/scaling: independently scalable trust infrastructure allowed.
16. prohibitions: no secret values in canonical evidence/logical values.

### D03 Charter — Platform Connectivity & Provider Capability

1. purpose: isolate external platform/provider capability and native facts.
2. core_governed_contracts: provider-neutral adapter boundaries.
3. owned facts: provider/platform/server/account capability/native mappings.
4. derived state: capability projections and adapter health facts.
5. accepted commands: connection/discovery/native adapter operations within authority.
6. published events/evidence: provider observations/capability evidence.
7. queries/projections: provider capabilities and mappings.
8. synchronous dependencies: none mandated globally.
9. asynchronous dependencies: operational evidence to D15.
10. prohibited reverse dependencies: provider native facts cannot define Core identity/Risk.
11. version/freshness: provider capability snapshot revision/freshness explicit.
12. degraded mode: unavailable/unknown provider fails closed for required actions.
13. recovery/reconciliation: reconnect never implies execution redispatch.
14. security/secrets: opaque refs; provider secrets behind certified boundary.
15. deployment/scaling: adapter/provider scaling independent.
16. prohibitions: no provider SDK inside sovereign domain semantics.

### D04 Charter — Markets, Instruments & Reference Data

1. purpose: canonical economic/listing/venue/reference identity.
2. core_governed_contracts: UMI-02 universal identity/lifecycle contracts.
3. owned facts: EconomicIdentity, ListingIdentity, venue/reference relationships.
4. derived state: instrument-universe projections.
5. accepted commands: governed identity/reference lifecycle mutations where defined.
6. published events/evidence: identity/mapping revision evidence.
7. queries/projections: canonical instrument/reference lookup.
8. synchronous dependencies: none frozen by FND-05.
9. asynchronous dependencies: external mapping evidence may arrive from D03.
10. prohibited reverse dependencies: symbols/provider IDs cannot become parallel authority.
11. version/freshness: effective-dated identity/mapping revisions.
12. degraded mode: unknown identity blocks universal claims.
13. recovery/reconciliation: external IDs reconcile to canonical identity.
14. security/secrets: no provider credentials.
15. deployment/scaling: reference services may scale independently.
16. prohibitions: no market price/position/execution ownership.

### D05 Charter — Market Data & Market Evidence

1. purpose: canonical market observations/evidence.
2. core_governed_contracts: typed observation and provenance contracts.
3. owned facts: quotes/trades/bars and observation evidence.
4. derived state: aggregated bars/read projections.
5. accepted commands: ingestion/normalization operations, not strategy.
6. published events/evidence: market observations and quality evidence.
7. queries/projections: market evidence reads.
8. synchronous dependencies: D04, D06.
9. asynchronous dependencies: D03 provider feed/evidence.
10. prohibited reverse dependencies: feed symbol cannot redefine D04 identity.
11. version/freshness: observed/received time and freshness explicit.
12. degraded mode: stale/missing/invalid market evidence explicit.
13. recovery/reconciliation: retained evidence/replay where applicable.
14. security/secrets: no provider secrets in observations.
15. deployment/scaling: feed ingestion may scale by venue/instrument/region.
16. prohibitions: no decision/execution authority.

### D06 Charter — Time, Calendars, Sessions & Instrument Lifecycle

1. purpose: canonical temporal/calendar/session/lifecycle timing semantics.
2. core_governed_contracts: instant/duration/calendar/session/tenor boundaries as implemented.
3. owned facts: calendars, sessions and temporal rule state.
4. derived state: open/closed/current-session projections.
5. accepted commands: governed calendar/session/lifecycle rule updates.
6. published events/evidence: temporal/lifecycle transition evidence.
7. queries/projections: calendar/session/time-rule reads.
8. synchronous dependencies: none frozen by FND-05.
9. asynchronous dependencies: reference/lifecycle inputs from D04 where required.
10. prohibited reverse dependencies: fixed seconds cannot redefine calendar/tenor semantics.
11. version/freshness: explicit effective/recorded time and rule revision.
12. degraded mode: uncertain temporal state fails closed where safety-critical.
13. recovery/reconciliation: reconcile rule revisions, not wall-clock guesses.
14. security/secrets: none intrinsic.
15. deployment/scaling: local verifiable time/calendar contracts preferred on hot paths.
16. prohibitions: no economic identity or strategy authority.

### D07 Charter — Valuation, Pricing, Yield & Analytics

1. purpose: valuation/analytic computations with explicit semantics/provenance.
2. core_governed_contracts: FND-04 price/value/rate/yield distinctions.
3. owned facts: methodology-scoped valuation/analytic outputs.
4. derived state: valuation projections/curves/metrics.
5. accepted commands: valuation computation requests.
6. published events/evidence: valuation result/methodology evidence.
7. queries/projections: valuation/analytics reads.
8. synchronous dependencies: D04, D06.
9. asynchronous dependencies: D05 market evidence.
10. prohibited reverse dependencies: valuation cannot rewrite market observation truth.
11. version/freshness: input/source/methodology/time version explicit.
12. degraded mode: missing inputs fail closed for quantitative claims.
13. recovery/reconciliation: reproducible recomputation from retained inputs.
14. security/secrets: no unnecessary secrets.
15. deployment/scaling: computation may scale independently.
16. prohibitions: no execution or Risk policy authority.

### D08 Charter — Account, Cash, Collateral & Portfolio

1. purpose: canonical account financial/portfolio aggregate state.
2. core_governed_contracts: account/client identities and FND-04 ownership split.
3. owned facts: QORE account, cash, collateral and portfolio aggregates.
4. derived state: client/account read projections.
5. accepted commands: governed account/portfolio state changes.
6. published events/evidence: account/portfolio revision evidence.
7. queries/projections: balances, portfolio/account state.
8. synchronous dependencies: D04.
9. asynchronous dependencies: D07 valuation, D11 post-trade.
10. prohibited reverse dependencies: provider account/lease cannot replace QORE account identity.
11. version/freshness: aggregate revision/freshness explicit.
12. degraded mode: ambiguous external/account state blocks unsafe mutation.
13. recovery/reconciliation: reconcile external account/position evidence through D11.
14. security/secrets: account IDs are not credentials.
15. deployment/scaling: account/portfolio sharding allowed under single authority.
16. prohibitions: no strategic/execution/provider authority.

### D09 Charter — Risk, Margin, Exposure & Limits

1. purpose: risk policy, exposure, margin and limit enforcement.
2. core_governed_contracts: pretrade authorization and future reservation semantics.
3. owned facts: risk policy/limits/assessments/reservations.
4. derived state: exposure/risk projections.
5. accepted commands: risk assessment/reservation/policy operations.
6. published events/evidence: authorization/rejection/risk evidence.
7. queries/projections: current risk/limit state.
8. synchronous dependencies: D04, D08.
9. asynchronous dependencies: D05, D07, D11.
10. prohibited reverse dependencies: provider margin fact != Core Risk policy.
11. version/freshness: current constraint version and authorization expiry explicit.
12. degraded mode: unknown/stale safety state cannot create new risk.
13. recovery/reconciliation: reservations/exposure require safe reconciliation.
14. security/secrets: no provider credentials.
15. deployment/scaling: safety logic may be local/verifiable without central remote choke point.
16. prohibitions: no portfolio ownership or order routing ownership.

### D10 Charter — Order, Execution & Routing

1. purpose: governed order intent, routing and execution authority.
2. core_governed_contracts: OrderIntent, execution guards/adapters/receipts.
3. owned facts: canonical order/execution lifecycle and routing authority facts.
4. derived state: execution status projections.
5. accepted commands: authorized order/execution operations.
6. published events/evidence: execution receipts/status evidence.
7. queries/projections: order/execution state.
8. synchronous dependencies: D03, D04, D08, D09.
9. asynchronous dependencies: none mandatory in FND-05 graph.
10. prohibited reverse dependencies: EA/Widget/Hosting cannot invent order intent.
11. version/freshness: intent/auth/risk/provider binding explicit.
12. degraded mode: ambiguity blocks retry/new execution authority.
13. recovery/reconciliation: D11 reconciliation before uncertain continuation.
14. security/secrets: provider credentials behind D03 boundary.
15. deployment/scaling: routing/execution can scale regionally under authority contracts.
16. prohibitions: no strategy creation or automatic corrective trading.

### D11 Charter — Position, Settlement, Post-Trade & Reconciliation

1. purpose: canonical post-trade state and external-state reconciliation.
2. core_governed_contracts: execution reconciliation and lifecycle evidence.
3. owned facts: positions, settlement state and reconciliation results.
4. derived state: post-trade/client projections.
5. accepted commands: reconciliation/settlement processing, not new strategy.
6. published events/evidence: position/settlement/reconciliation evidence.
7. queries/projections: reconciled position/post-trade state.
8. synchronous dependencies: D03, D04, D10.
9. asynchronous dependencies: D08.
10. prohibited reverse dependencies: reconciliation uncertainty cannot authorize redispatch.
11. version/freshness: external observation/reconciliation revision explicit.
12. degraded mode: ambiguity remains blocked.
13. recovery/reconciliation: this department owns reconciliation result semantics.
14. security/secrets: no raw credentials in evidence.
15. deployment/scaling: account/provider scoped workers allowed.
16. prohibitions: no independent close/open trading strategy.

### D12 Charter — Research, Replay & Quant

1. purpose: deterministic research/replay/quant execution.
2. core_governed_contracts: dataset/replay/research-run contracts.
3. owned facts: research run/replay/quant artifacts assigned to this domain.
4. derived state: research results/diagnostics.
5. accepted commands: research/replay execution requests.
6. published events/evidence: reproducible research output/evidence.
7. queries/projections: research artifact reads.
8. synchronous dependencies: D04, D06.
9. asynchronous dependencies: D05.
10. prohibited reverse dependencies: research result cannot self-promote to trading.
11. version/freshness: dataset/revision/strategy binding explicit.
12. degraded mode: missing lineage/data blocks claims.
13. recovery/reconciliation: deterministic replay/rebuild from retained evidence.
14. security/secrets: research artifacts secret-free unless explicit governed refs.
15. deployment/scaling: replay workers scale independently.
16. prohibitions: no productive execution authority.

### D13 Charter — Decision Intelligence

1. purpose: compute CIO/CIBO/Specialized Trader decisions under Core authority.
2. core_governed_contracts: FunctionalDecision and specialist decision contracts.
3. owned facts: strategic/functional decision products and decision evidence.
4. derived state: decision summaries/read projections.
5. accepted commands: governed decision/evaluation requests.
6. published events/evidence: decisions/analyses with lineage.
7. queries/projections: decision state/diagnostics.
8. synchronous dependencies: D04, D06.
9. asynchronous dependencies: D05, D07, D08, D12.
10. prohibited reverse dependencies: D16/D18/D19/D21 cannot originate strategy.
11. version/freshness: input/decision/model/version/time explicit.
12. degraded mode: missing current required evidence blocks decision promotion.
13. recovery/reconciliation: recompute only from valid retained inputs; no execution guessing.
14. security/secrets: strategic models remain protected from client/EA boundaries.
15. deployment/scaling: specialist computation may scale independently.
16. prohibitions: no direct provider SDK or client UI authority.

### D14 Charter — Data Lineage, Knowledge, Statistics & Validation

1. purpose: prove provenance, statistics, validation and promotion evidence.
2. core_governed_contracts: lineage/calibration/OOS/statistical contracts.
3. owned facts: lineage graph, validation results, statistical evidence, knowledge artifacts.
4. derived state: validation/read dashboards.
5. accepted commands: validation/statistical/knowledge processing requests.
6. published events/evidence: certification/promotion inputs.
7. queries/projections: lineage/validation/statistical reads.
8. synchronous dependencies: none frozen by FND-05.
9. asynchronous dependencies: D05, D12, D13.
10. prohibited reverse dependencies: evidence cannot mutate source truth.
11. version/freshness: dataset/run/model/evidence revision explicit.
12. degraded mode: missing provenance blocks quantitative claim/promotion.
13. recovery/reconciliation: rebuild from retained evidence where possible.
14. security/secrets: no secret leakage into lineage/evidence.
15. deployment/scaling: validation/statistics workers independent.
16. prohibitions: no self-promotion or execution authority.

### D15 Charter — Observability, Reliability & Incident Operations

1. purpose: operational visibility, reliability and incident handling.
2. core_governed_contracts: health/telemetry/incident evidence contracts.
3. owned facts: observability/reliability/incident operational state.
4. derived state: dashboards, health/read projections.
5. accepted commands: incident/observability operations within infrastructure authority.
6. published events/evidence: alerts/incidents/reliability evidence.
7. queries/projections: system/service health.
8. synchronous dependencies: none mandated as trading authority.
9. asynchronous dependencies: consumes emitted evidence from domains/services.
10. prohibited reverse dependencies: observation/heartbeat cannot elect writer or create trade.
11. version/freshness: health freshness explicit.
12. degraded mode: unknown health is explicit, not implied healthy.
13. recovery/reconciliation: incident recovery needs owning-domain evidence.
14. security/secrets: sanitize telemetry; no secret values.
15. deployment/scaling: regional/global observability layers permitted.
16. prohibitions: no canonical business-fact write authority by observation.

### D16 Charter — Distributed Runtime, Hosting, VPS & Cloud Operations

1. purpose: operate the QORE-owned distributed Cloud/Hosting/VPS Fabric.
2. core_governed_contracts: MISSION-08 runtime/lease/fencing + FND-05 Cloud amendment.
3. owned facts: infrastructure inventory/topology/capacity/placement/runtime/deployment/lease/fencing/DR state.
4. derived state: hosting readiness/telemetry projections.
5. accepted commands: governed infrastructure placement/deployment/containment/lease operations.
6. published events/evidence: runtime/lease/fencing/latency/capacity/health/DR evidence.
7. queries/projections: Hosting/VPS/Cloud operational state.
8. synchronous dependencies: D02, D08.
9. asynchronous dependencies: D15, D21.
10. prohibited reverse dependencies: health/capacity/payment cannot create trade intent.
11. version/freshness: runtime/lease/fencing/deployment/placement revisions explicit.
12. degraded mode: stale/unknown writer/external state fails closed for new authority.
13. recovery/reconciliation: fence + reconcile before writer transfer; DR preserves single-writer.
14. security/secrets: zero-trust/segregated secret infrastructure under D02 contracts.
15. deployment/scaling: horizontal cells/regions; thousands of accounts; no central synchronous choke point.
16. prohibitions: no strategy, Risk policy, Widget authority, account/provider identity redefinition.

Additional D16 service requirements:

- QORE is the Hosting/VPS/Cloud provider;
- external cloud is not a required authority/substrate dependency;
- low/ultra-low deterministic latency is a certification dimension for futures where material;
- strong tenant isolation and compromise containment are mandatory;
- client may have only a phone; hosted runtimes remain server-side;
- no numeric latency/security/capacity guarantee without evidence.

### D17 Charter — Signal Production, Security & Distribution

1. purpose: produce/distribute protected signals derived from valid Core Decisions.
2. core_governed_contracts: protected client decision/signal security contracts.
3. owned facts: signal envelope/version/issue/expiry/routing/distribution evidence.
4. derived state: delivery/read projections.
5. accepted commands: governed signal production/distribution operations.
6. published events/evidence: signal delivery/replay/security evidence.
7. queries/projections: signal status/delivery state.
8. synchronous dependencies: D02, D13, D21.
9. asynchronous dependencies: D15.
10. prohibited reverse dependencies: distribution cannot create/modify strategic decision.
11. version/freshness: issue/expiry/key/version explicit.
12. degraded mode: invalid/expired/unknown-key signal fails closed.
13. recovery/reconciliation: replay/dedup/security evidence required.
14. security/secrets: key material through D02 boundary; no plaintext reusable BUY/SELL.
15. deployment/scaling: regional distribution allowed.
16. prohibitions: no broker execution authority.

### D18 Charter — Client Execution Ecosystem — EA / Agent

1. purpose: deterministic delegated execution of valid Core authority for client accounts.
2. core_governed_contracts: client execution-agent, account/risk/order/signal/hosting contracts.
3. owned facts: EA installation/runtime binding and agent operational lifecycle.
4. derived state: EA status/read projections.
5. accepted commands: execute/protect already-authorized lifecycle within bounds.
6. published events/evidence: agent execution/status evidence.
7. queries/projections: agent/runtime/account execution status.
8. synchronous dependencies: D02, D08, D09, D10, D16, D17, D21.
9. asynchronous dependencies: none mandatory in FND-05 graph.
10. prohibited reverse dependencies: EA cannot originate independent opportunity/strategy.
11. version/freshness: signal/account/risk/lease/runtime/entitlement binding current.
12. degraded mode: invalid signal/lease/risk/account/provider state blocks new action.
13. recovery/reconciliation: D11/D16 reconciliation before uncertain continuation.
14. security/secrets: no broad access to Core strategy; provider refs constrained.
15. deployment/scaling: many account-scoped runtimes under D16.
16. prohibitions: no Core Decision bypass, no independent BUY/SELL.

### D19 Charter — Client Read Models & Widget Presentation

1. purpose: client presentation/read models.
2. core_governed_contracts: authorized read-model/freshness/entitlement contracts.
3. owned facts: presentation projection state only.
4. derived state: all client-facing account/EA/Hosting/performance views.
5. accepted commands: read/presentation operations only.
6. published events/evidence: presentation delivery telemetry where applicable.
7. queries/projections: account status/balance/performance/trade pulse/EA/Hosting/freshness.
8. synchronous dependencies: none.
9. asynchronous dependencies: D08, D11, D15, D16, D18, D21.
10. prohibited reverse dependencies: Widget cannot change trading/risk/hosting authority.
11. version/freshness: projection source revision/freshness explicit.
12. degraded mode: stale/unavailable shown honestly.
13. recovery/reconciliation: refresh from authoritative sources.
14. security/secrets: no provider credentials.
15. deployment/scaling: mobile/web projection delivery independent.
16. prohibitions: WIDGET != EXECUTION.

### D20 Charter — Executive / CEO Control Surfaces

1. purpose: authenticated governed CEO control/query surface.
2. core_governed_contracts: executive principal/authority/guard/dispatch/evidence.
3. owned facts: surface request/delivery state, not governance truth.
4. derived state: executive read projections.
5. accepted commands: guarded executive intents only.
6. published events/evidence: executive request/dispatch evidence.
7. queries/projections: authorized executive reads.
8. synchronous dependencies: D01, D02.
9. asynchronous dependencies: D15.
10. prohibited reverse dependencies: UI cannot bypass governance/authority.
11. version/freshness: principal/authority/correlation/current state explicit.
12. degraded mode: unknown authority fails closed.
13. recovery/reconciliation: no replay as new authority without idempotency controls.
14. security/secrets: auth secrets external to Core contracts.
15. deployment/scaling: surface separate from governing state.
16. prohibitions: no direct unguarded domain mutation.

### D21 Charter — Commercial Products, Billing, Payments & Entitlements

1. purpose: commercial product/service availability truth.
2. core_governed_contracts: product/plan/payment/entitlement contracts.
3. owned facts: product, billing/payment evidence, entitlement status.
4. derived state: client commercial projections.
5. accepted commands: governed commercial lifecycle operations.
6. published events/evidence: entitlement/payment/service-availability evidence.
7. queries/projections: product/entitlement state.
8. synchronous dependencies: D02.
9. asynchronous dependencies: operational evidence where required.
10. prohibited reverse dependencies: payment != Core Decision; Billing cannot liquidate.
11. version/freshness: entitlement validity/version explicit.
12. degraded mode: uncertain entitlement fails closed for new paid service access.
13. recovery/reconciliation: payment/provider reconciliation does not create trade.
14. security/secrets: payment secrets behind certified boundary.
15. deployment/scaling: commercial services scale independently.
16. prohibitions: no Risk/execution/position authority.

### D22 Charter — Compliance, Regulatory Evidence & Audit Reporting

1. purpose: compliance/regulatory/audit reporting.
2. core_governed_contracts: audit/evidence/provenance rules.
3. owned facts: compliance/reporting state and generated audit artifacts.
4. derived state: regulatory/audit reports.
5. accepted commands: governed reporting/compliance processing.
6. published events/evidence: audit/compliance evidence.
7. queries/projections: compliance/report status.
8. synchronous dependencies: none frozen.
9. asynchronous dependencies: D01, D14, D15, D21.
10. prohibited reverse dependencies: reporting cannot mutate source facts.
11. version/freshness: source evidence/revision explicit.
12. degraded mode: missing evidence blocks report claim.
13. recovery/reconciliation: regenerate from retained evidence.
14. security/secrets: privacy/access controls explicit downstream.
15. deployment/scaling: reporting independent.
16. prohibitions: no trading authority.

### D23 Charter — Notifications & Client/Operational Communication

1. purpose: deliver notifications/communications.
2. core_governed_contracts: notification/communication routing contracts.
3. owned facts: delivery/acknowledgement state.
4. derived state: communication projections.
5. accepted commands: governed notification delivery.
6. published events/evidence: delivery/failure evidence.
7. queries/projections: notification status.
8. synchronous dependencies: none frozen.
9. asynchronous dependencies: D15, D19, D21.
10. prohibited reverse dependencies: notification response cannot become trading authority.
11. version/freshness: source/delivery time explicit.
12. degraded mode: delivery failure does not mutate source business state.
13. recovery/reconciliation: idempotent/redelivery semantics belong FND-06.
14. security/secrets: minimize sensitive payloads.
15. deployment/scaling: channel/provider workers independent.
16. prohibitions: no source-domain write authority.

### D24 Charter — Certification & Integration Gate

1. purpose: independent certification/integration governance.
2. core_governed_contracts: Quality Gate, review, exact-head, merge/baseline rules.
3. owned facts: certification/approval/baseline evidence.
4. derived state: certification dashboards/status.
5. accepted commands: review/integration workflow actions within authority.
6. published events/evidence: pass/fail/correction/merge/baseline evidence.
7. queries/projections: certification status.
8. synchronous dependencies: none in runtime hot path.
9. asynchronous dependencies: D01, D14, D15, D22 evidence.
10. prohibited reverse dependencies: CI or author cannot self-certify.
11. version/freshness: exact SHA/head/base/workflow evidence mandatory.
12. degraded mode: missing evidence -> NOT VERIFIED.
13. recovery/reconciliation: correction creates new exact head and new gate.
14. security/secrets: evidence must remain secret-free.
15. deployment/scaling: independent review/integration tooling allowed.
16. prohibitions: no implementation-domain authority by certification role.

## Adversarial conformance cases

### FND05-CASE-01 — duplicate department

Two specs with the same DepartmentId or slug must fail closed.

### FND05-CASE-02 — unknown dependency

Any dependency referencing a department absent from the registry must fail closed.

### FND05-CASE-03 — self dependency

A department cannot depend on itself.

### FND05-CASE-04 — synchronous cycle

`A -> B -> A` through synchronous dependencies must fail closed.

### FND05-CASE-05 — asynchronous feedback

Async feedback cycles may exist only as representable graph edges; FND-06/FND-07 must supply loop containment/idempotency/version/freshness contracts.

### FND05-CASE-06 — Widget authority leak

D19 may consume account/position/hosting/EA/commercial projections but cannot be synchronous strategic upstream for D13 or an order origin for D10.

### FND05-CASE-07 — Billing authority leak

D21 entitlement/payment state may gate service availability but cannot create BUY/SELL or liquidation authority.

### FND05-CASE-08 — Hosting authority leak

D16 runtime health/capacity/placement cannot become Core Decision or substitute for a valid execution lease.

### FND05-CASE-09 — EA strategy leak

D18 cannot originate independent opportunity/BUY/SELL. It consumes valid protected Core authority.

### FND05-CASE-10 — provider identity leak

D03 provider native identifiers cannot replace D04 EconomicIdentity/ListingIdentity authority.

### FND05-CASE-11 — provider margin leak

D03 ProviderMarginTerms cannot become D09 Core Risk policy without an explicit typed transformation/contract.

### FND05-CASE-12 — reconciliation redispatch

D11 ambiguity cannot trigger automatic duplicate order resubmission through D10.

### FND05-CASE-13 — Cloud multi-account scale

Thousands of hosted account runtimes must not imply one global writer. Writer authority remains account-scoped and fenced.

### FND05-CASE-14 — mobile-only client

Loss of the client's phone cannot itself stop an otherwise valid QORE-hosted runtime, and the Widget cannot enter the execution path.

### FND05-CASE-15 — Cloud attack containment

Compromise of one client/runtime/cell must not by architecture grant access or writer authority to another account or sovereign Core.

### FND05-CASE-16 — futures latency

Latency-sensitive futures execution must allow regional/proximity placement and a bounded hot path without requiring a central remote synchronous Core call.

### FND05-CASE-17 — external cloud outage

QORE's target service architecture cannot require a third-party cloud provider as the authoritative dependency for QORE Hosting/VPS/Cloud availability.

### FND05-CASE-18 — certification self-authority

D24 cannot certify its own authored implementation merely because CI is green.

## Tests required by this candidate

`tests/domain/test_departments.py` verifies:

- exactly 24 canonical DepartmentIds;
- Department 16 canonical identity/name;
- unique IDs/slugs;
- known dependency references;
- self-dependency rejection;
- duplicate edge rejection;
- synchronous-cycle rejection;
- async feedback-cycle representability;
- deterministic provider-before-consumer sync ordering;
- deterministic logical values independent of declaration order;
- service planes absent as strategic upstream dependencies to D13;
- D18 depends on D16/D17/D10 while D16 does not depend on D18 as authority;
- D19 Widget dependencies are asynchronous/read-side only.

## PR #298 compatibility ownership path

PR #298 remains HOLD.

Future promotion requires:

```text
FND-05 certified ownership
 -> FND-06 typed provider/account/server relationship contracts
 -> rebase PR #298 on then-certified main
 -> replace/bridge legacy Instrument binding through D04 UMI-02 authority
 -> bind provider-native catalog facts to D03 typed provider scope
 -> keep ProviderMarginTerms as D03 provider evidence, not D09 Risk policy
 -> exact-head CI
 -> independent compatibility review
 -> Integration Gate
```

## Minimum-delta conclusion

Unlike FND-04, documentation-only is not sufficient for FND-05 because FND-01 explicitly requires a Canonical Department Registry and dependency graph, while the certified baseline has no canonical typed registry.

The minimum production delta is limited to a pure immutable domain contract with deterministic validation. It introduces no network, storage, runtime, broker, provider SDK, Cloud deployment or trading side effect.

## Explicit non-claims

FND-05 does not claim:

- productive QORE Cloud exists;
- physical datacenters/servers are provisioned;
- a hypervisor/container platform has been selected;
- a distributed database/broker/consensus technology has been selected;
- numeric latency or capacity targets have been certified;
- all security attacks can be prevented;
- FND-04 TIME-01 is closed;
- FND-06 command/query/event/evidence contracts are implemented;
- FND-07 distributed reservation/freshness/reconciliation doctrine is implemented;
- FND-08 is complete;
- PR #298 is promotable;
- UMI-03 may begin before the foundation sequence permits it;
- Production or real capital is authorized.

## Downstream gate

If this exact FND-05 candidate is certified:

```text
FND-05 CLOSED
 -> FND-06 cross-department command/query/event/evidence contracts
 -> FND-07 distributed state/freshness/concurrency/reconciliation + Cloud security/latency doctrine
 -> FND-08 independent Levels 0-3 audit
 -> only then downstream universal/domain/service implementation programs may rely on the certified department fabric
```

The QORE-owned Cloud amendment must be referenced from Master Roadmap #303 only after the exact reviewed FND-05 head is merged and post-merge main is verified.

## Certification sequence

```text
EXACT BASELINE VERIFICATION
 -> REPOSITORY EVIDENCE AUDIT
 -> MINIMUM TYPED REGISTRY / GRAPH IMPLEMENTATION
 -> TESTS
 -> FULL DIFF / BLAST-RADIUS AUDIT
 -> EXACT-HEAD QORE CI
 -> INDEPENDENT ADVERSARIAL REVIEW
 -> CORRECTION IF REQUIRED
 -> NEW EXACT HEAD + NEW CI + RE-REVIEW
 -> INTEGRATION GATE
 -> VERIFY MAIN NO DRIFT
 -> MERGE(expected_head_sha)
 -> VERIFY MERGE COMMIT / PARENTS
 -> VERIFY POST-MERGE MAIN
 -> COMPARE MERGE VS MAIN
 -> FREEZE NEW CERTIFIED BASELINE
 -> UPDATE #303 WITH CERTIFIED CLOUD AMENDMENT REFERENCE
 -> CLOSE #312 / FND-05
 -> ONLY THEN FND-06
```
