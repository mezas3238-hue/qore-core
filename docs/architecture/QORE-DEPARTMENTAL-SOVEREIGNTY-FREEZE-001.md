# QORE-DEPARTMENTAL-SOVEREIGNTY-FREEZE-001

## Status

**STAGE-01 / FND-01 — ARCHITECTURE CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #302  
Master roadmap: #303  
Certified starting baseline: `c7be7b8c224924d0765617c1f9f63ca522007216`

This artifact freezes the constitutional relationship between sovereign QORE Core and technically autonomous departments before departmental expansion, universal provider promotion or universal instrument-catalog promotion.

It defines authority, state ownership, interaction, freshness, safety-critical synchronization, degraded-mode and recovery obligations. It deliberately does **not** select a distributed database, message broker, Event Sourcing, CQRS, Saga, consensus system or cloud topology.

## Governing invariants

```text
CORE IS THE SOVEREIGN DOMAIN
DEPARTMENT TECHNICAL AUTONOMY != AUTHORITY AUTONOMY
CORE SOVEREIGN AUTHORITY != CENTRAL REMOTE SYNCHRONOUS CHOKE POINT
SINGLE SOURCE OF TRUTH = SINGLE GOVERNED AUTHORITY PER CANONICAL FACT/AGGREGATE, NOT ONE DATABASE
SYNCHRONOUS SAFETY DECISION != REMOTE SYNCHRONOUS NETWORK CALL
HEALTH / HEARTBEAT != EXECUTION AUTHORITY
UNKNOWN / AMBIGUOUS STATE CANNOT CREATE NEW RISK-INCREASING AUTHORITY
DERIVED PROJECTION != CANONICAL WRITE AUTHORITY
NO RECONCILIATION -> NO AUTHORITY TRANSFER WHEN EXTERNAL STATE IS AMBIGUOUS
NO VERIFIED UNIVERSAL INSTRUMENT IDENTITY -> NO UNIVERSAL INSTRUMENT-CATALOG PROMOTION
```

## Repository evidence ledger

The following evidence is verified at the certified starting baseline.

### EVID-01 — Core runtime foundations — CLOSED

- `src/qore/core/engine.py`: `CoreEngine` is a minimal Core execution-cycle coordinator and its `start()` explicitly runs no business logic.
- `src/qore/core/runtime_supervisor.py`: `RuntimeSupervisor` deterministically starts/stops declared runtime components and exposes explicit stopped/running/degraded state.
- `src/qore/core/runtime_plan.py`: `RuntimePlan` validates known dependencies and rejects runtime-component cycles through stable topological ordering.
- `src/qore/core/event_bus.py`: the current `EventBus` is synchronous and in-memory.

Consequence:

```text
CORE HAS VERIFIED RUNTIME FOUNDATIONS
!=
ALL DEPARTMENTS MUST CALL A CENTRAL CORE NETWORK SERVICE
```

The current EventBus is not evidence for a durable global distributed event log.

### EVID-02 — Pre-trade authorization — CLOSED

`src/qore/infrastructure/pretrade_safety.py` provides typed immutable `PreTradeAuthorization`, explicit `evaluated_at` / `expires_at`, exact intent binding, an execution switch, and fail-closed authorization.

This proves a reusable local authorization/freshness pattern. It does **not** prove distributed concurrency safety, atomic exposure reservation, or that stale replicated risk capacity cannot be oversubscribed.

### EVID-03 — Explicit freshness semantics — CLOSED

`src/qore/governance/executive_state_sync.py` defines explicit `CURRENT`, `STALE`, `UNAVAILABLE`, and `UNKNOWN` presentation-state semantics with version and freshness deadlines. Current/stale states require an exact snapshot; unavailable/unknown states cannot masquerade as one.

`src/qore/infrastructure/hosting_health_heartbeat.py` separately defines health and heartbeat freshness, and derives containment. Missing heartbeat evidence is `UNKNOWN` and fail-closed for new work.

Consequence: local freshness contracts are reusable precedent, but a universal cross-department freshness policy still requires explicit ownership and per-dependency semantics.

### EVID-04 — Hosting lease, fencing and failover — CLOSED

`src/qore/infrastructure/hosting_execution_lease.py` provides account-scoped writer leases, monotonic fencing generation, stale-generation rejection and explicit current-authority evaluation. Its acquisition function states that durable adapters must make acquisition atomic.

`docs/architecture/QORE-HOSTING-EXECUTION-LEASE-001.md` explicitly states that an immutable in-memory snapshot is not a distributed lock.

`src/qore/infrastructure/hosting_failover_reconciliation.py` blocks replacement-writer readiness until previous authority is contained, candidate state is current/healthy, external account state is reconciled, execution reconciliation is matched and the next fencing generation is known. The readiness result does not itself acquire authority.

Consequence: MISSION-08 is a reusable single-writer/fencing/reconciliation foundation, not universal proof for every department or aggregate.

## DSF-01 — Core sovereignty / runtime boundary — ACTIVE UNTIL CERTIFIED

Core owns constitutional authority, not necessarily every physical process.

### Core-owned authority

Core constitutionally owns:

- canonical cross-domain identity and semantic contracts;
- strategic trading-decision authority and rules governing delegation;
- global invariants and authority-separation rules;
- canonical command/query/event/evidence semantics;
- cross-department ownership rules;
- governance and authorization contracts;
- rules for promotion, certification and roadmap change.

### Department-owned capability

A department may independently own and operate:

- specialized computation;
- workers/processes;
- databases and caches;
- queues/transports behind canonical boundaries;
- adapters;
- deployment topology;
- local read models and projections;
- domain-specific durable state explicitly assigned to that department.

Technical independence never gives a department permission to redefine Core contracts, manufacture strategic authority, bypass governance or turn a local projection into canonical truth.

### Runtime adjudication rule

A proposed runtime dependency does **not** belong on a mandatory remote Core hot path merely because Core owns the governing contract.

A remote synchronous Core call is justified only when the required authority cannot be safely represented by a locally verifiable, versioned, bounded, revocable and evidence-bearing contract **and** the failure semantics are explicitly proven. Convenience, centralization preference or existing implementation location is not sufficient justification.

Therefore:

```text
CORE CONTRACT OWNERSHIP != REMOTE CALL REQUIREMENT
LOCAL VERIFICATION != LOCAL AUTHORITY INVENTION
```

## DSF-02 — Department authority and interaction model — ACTIVE UNTIL CERTIFIED

Every department charter produced later in Program E / FND-05 must instantiate the following mandatory schema.

### Department Charter Schema

For each department define:

1. `purpose` — specialized capability only;
2. `core_governed_contracts` — canonical contracts it consumes or implements;
3. `owned_canonical_facts_or_aggregates` — exact facts/aggregates for which it is authoritative;
4. `derived_state` — projections/caches that are explicitly non-authoritative;
5. `accepted_commands` — commands it may execute;
6. `published_events_or_evidence` — outputs it may emit;
7. `queries_or_projections` — read surfaces it may expose;
8. `synchronous_dependencies`;
9. `asynchronous_dependencies`;
10. `prohibited_reverse_dependencies`;
11. `version_and_freshness_contract`;
12. `degraded_mode_contract`;
13. `recovery_and_reconciliation_contract`;
14. `security_and_secret_boundary`;
15. `deployment_and_scaling_autonomy`;
16. `authority_prohibitions`.

### Interaction constraints

Synchronous service-call dependencies must form an acyclic graph.

Async feedback is permitted only when the contract carries enough information to prove:

- causation/correlation;
- version or revision;
- idempotency/deduplication semantics where needed;
- ordering assumptions if any;
- loop containment;
- replay/reprocessing behavior;
- freshness/evidence.

`RuntimePlan` cycle rejection is architectural precedent for deterministic dependency validation, but its current runtime-component graph is **not** the departmental dependency graph.

## DSF-03 — Distributed state / single-authority model — ACTIVE UNTIL CERTIFIED

The system must distinguish canonical authority from storage location.

### Canonical Fact Ownership Record

Every mutable canonical fact/aggregate that crosses a department boundary must eventually declare:

- `authority_owner`;
- `writer_scope`;
- `aggregate_or_fact_identity`;
- `revision_or_version`;
- `effective_at` / observation time where relevant;
- `freshness_or_validity_boundary` where relevant;
- `evidence_reference`;
- `replication_or_projection_rules`;
- `reconciliation_source`;
- `split_brain_containment`;
- `recovery_rule`.

### Single-writer rule

Where a fact/aggregate requires a single writer, exactly one governed writer authority may exist for the relevant scope at a given logical time.

Single-writer scope is not automatically global. It may be account-, portfolio-, instrument-, venue-, strategy-, tenant- or aggregate-scoped as established by the certified domain contract.

Replicas and projections may serve reads but cannot silently acquire writer authority.

### Version and projection rules

A projection must identify the authoritative revision or evidence from which it was derived. A projection cannot be treated as current merely because it is locally available.

```text
LOCAL COPY EXISTS != CURRENT
CURRENT != AUTHORITATIVE WRITER
PROJECTION != CANONICAL MUTATION SOURCE
```

### Technology neutrality

No global Event Sourcing, CQRS, Saga, database, broker or consensus choice is frozen by this artifact. Those may be selected later only if they satisfy the certified ownership, consistency, failure and evidence requirements.

## DSF-04 — Safety-critical synchronous semantics — ACTIVE UNTIL CERTIFIED

Safety decisions that gate new risk must be logically current at the point where new authority is created.

This does not require a remote synchronous Core network call.

### Required safety proof

Before a department may create new risk-increasing execution authority, the design must prove how all relevant current constraints are consumed without double-spending capacity, including as applicable:

- current exposure;
- current limits;
- pending/in-flight orders;
- reservations;
- collateral/margin capacity;
- account restrictions;
- market/instrument restrictions;
- kill-switch / halt state;
- authorization expiry;
- writer/fencing authority.

A replicated limit or exposure snapshot with no concurrency control is insufficient.

### Reservation doctrine

When concurrent actions could consume the same scarce risk capacity, the future implementation must use a concurrency-safe mechanism that provides an atomic or equivalently safe reservation/commit/release model for the governing scope.

This artifact freezes the requirement, **not** the implementation technology.

`PreTradeAuthorization` is reusable evidence for explicit authorization lifetime and binding but is not itself the distributed reservation mechanism.

## DSF-05 — Cross-department degraded-mode framework — ACTIVE UNTIL CERTIFIED

No department may invent an undocumented failure policy for a dependency.

Every material dependency must define a failure/freshness matrix using the smallest domain-appropriate state vocabulary, mapped at minimum to the following semantic classes when applicable:

- `AVAILABLE_CURRENT` — required evidence/state is available and within its validity boundary;
- `AVAILABLE_STALE` — evidence exists but is outside the certified freshness boundary;
- `UNAVAILABLE` — dependency cannot currently provide required state;
- `UNKNOWN_OR_AMBIGUOUS` — authority/current external truth cannot be established.

Existing domain vocabularies such as `CURRENT/STALE/UNAVAILABLE/UNKNOWN` or hosting `HEALTHY/DEGRADED/UNREACHABLE/UNKNOWN` remain valid; this framework does not replace them with one global enum.

For each state the department charter must declare:

- allowed action classes;
- prohibited action classes;
- whether existing-risk protection/lifecycle may continue;
- whether new risk may be created;
- maximum age/freshness if applicable;
- required evidence;
- containment action;
- recovery preconditions;
- reconciliation requirements.

### Global fail-closed rule

```text
UNKNOWN / AMBIGUOUS STATE CANNOT CREATE NEW RISK-INCREASING AUTHORITY
```

This rule does not mandate blanket liquidation. Existing authorized lifecycle/protection actions may continue only where the certified owning policy explicitly permits them and writer authority remains valid.

Heartbeat/liveness is evidence, never election or trading authority.

## DSF-06 — Universal instrument identity dependency — ACTIVE UNTIL CERTIFIED

Department ownership cannot be finalized around a provider-specific or symbol-only instrument identity.

The certified master roadmap already freezes:

```text
SYMBOL TEXT != UNIVERSAL INSTRUMENT IDENTITY
```

STAGE-01 therefore freezes only the dependency:

- Markets/Instruments department ownership must bind to the future typed universal economic-instrument identity;
- Market Data must bind observations to that canonical identity plus venue/listing/provider provenance as applicable;
- Execution/Position/Risk/Valuation/Research departments must consume the same governed identity relationships without inventing parallel symbol identity;
- provider-native identifiers remain adapter/boundary facts, not substitutes for economic identity.

The actual universal taxonomy, identity, lifecycle and reference relationships are **not** implemented in STAGE-01. They belong to #301 UMI-01 / UMI-02 after #302 closes.

PR #298 may remain useful cTrader-specific work but stays blocked from promotion as the final universal instrument-catalog foundation until identity compatibility is certified.

## Mandatory downstream artifacts

This freeze requires later stages to produce, at minimum:

1. Canonical Department Registry;
2. Department Dependency Graph;
3. Canonical Fact/Aggregate Ownership Matrix;
4. Sync/Async Communication Matrix;
5. Safety-Critical State / Reservation Contract;
6. Cross-Department Freshness & Degraded-Mode Matrix;
7. Recovery / Reconciliation Matrix;
8. Cross-Boundary Command / Query / Event / Evidence contracts.

These artifacts must conform to this freeze; they may refine it only through governed roadmap/ADR change.

## Explicit non-claims

This artifact does **not** claim:

- distributed concurrency is already solved;
- every department has a completed charter;
- one global durable event log exists;
- Event Sourcing/CQRS/Saga is selected;
- current `EventBus` is a distributed transport;
- MISSION-08 hosting leases solve every department's writer problem;
- existing freshness contracts are already universal;
- PR #298 is a universal identity foundation;
- production distributed infrastructure is authorized.

## Gate and closure

DSF-01 through DSF-06 remain `ACTIVE` until this exact artifact passes:

```text
EXACT-HEAD QUALITY GATE
-> INDEPENDENT ADVERSARIAL REVIEW
-> CORRECTION IF REQUIRED
-> EXACT-HEAD RE-REVIEW
-> INTEGRATION GATE
-> VERIFY MAIN NO DRIFT
-> EXPECTED-HEAD MERGE
-> VERIFY MERGE COMMIT
-> VERIFY POST-MERGE MAIN
-> FREEZE NEW BASELINE
-> #302 CLOSED
-> DSF-01..DSF-06 CLOSED
```

Only after #302 and all DSF cases are `CLOSED` may STAGE-02 / UMI-01 begin.