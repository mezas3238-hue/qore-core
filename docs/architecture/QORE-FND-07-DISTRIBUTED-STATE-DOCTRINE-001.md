# QORE-FND-07-DISTRIBUTED-STATE-DOCTRINE-001

## Status

**STAGE-07 / FND-07 — ARCHITECTURE CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #316  
Master roadmap: Issue #303  
Certified starting baseline: `4de2ec96a6deb62d8ae85d30cf43066b7f373335`  
Predecessor: FND-06 / Issue #314 / PR #315 — CLOSED

This artifact freezes the minimum universal doctrine for distributed state ownership,
freshness, concurrency, single-writer authority, reservation obligations,
reconciliation and recovery.

It is intentionally **technology-neutral** and does not create a new global state
store, global revision type, distributed lock, consensus system, broker, database,
scheduler or productive Cloud topology.

The governing objective is:

```text
ONE GOVERNED AUTHORITY PER CANONICAL FACT / AGGREGATE
!=
ONE PHYSICAL COPY
!=
ONE DATABASE
!=
ONE SERVER
```

---

# 1. Governing constitutional invariants

```text
CORE SOVEREIGNTY != PHYSICAL MONOLITH
DOMAIN CENTRALIZATION != RUNTIME CENTRALIZATION
SINGLE AUTHORITY != SINGLE SERVER
SINGLE SOURCE OF TRUTH != SINGLE DATABASE

CANONICAL AUTHORITY != STORAGE LOCATION
REPLICA != SOURCE AUTHORITY
CACHE != SOURCE AUTHORITY
READ MODEL != WRITE AUTHORITY
PROJECTION != CANONICAL MUTATION SOURCE
EVENT != WRITER AUTHORITY
EVIDENCE != WRITER AUTHORITY
HEALTHY != EXECUTION AUTHORITY
UNREACHABLE != SAFE TO START BACKUP
HOSTING CAPACITY != TRADING INTENT

CONTRACT VERSION != STATE REVISION
EVENT VERSION != STATE REVISION
REGISTRY GENERATION != FENCING GENERATION
FENCING GENERATION != AGGREGATE REVISION
OBSERVATION SEQUENCE != WRITER AUTHORITY
REPLAY ORDER != MUTATION AUTHORITY

AMBIGUOUS AUTHORITY -> FAIL CLOSED
STALE SAFETY-CRITICAL STATE -> NO NEW RISK-INCREASING AUTHORITY
UNKNOWN SAFETY-CRITICAL STATE -> NO NEW RISK-INCREASING AUTHORITY
CONFLICT != BEST-EFFORT WRITE

AT MOST ONE ACTIVE FENCED EXECUTION AUTHORITY PER TradingAccountId
NO VALID FENCED EXECUTION AUTHORITY -> NO HOSTED WRITER AUTHORITY

RETRY POLICY != BUSINESS IDEMPOTENCY
IDEMPOTENCY != CAPACITY RESERVATION
REPLAY PROTECTION != CAPACITY RESERVATION
RISK APPROVAL != RISK CAPACITY RESERVED
PRETRADE AUTHORIZATION != CAPITAL / EXPOSURE RESERVED

RECONCILIATION UNCERTAINTY != DUPLICATE REDISPATCH AUTHORITY
RECONCILIATION != AUTOMATIC CORRECTIVE TRADING
FAILOVER READINESS != WRITER AUTHORITY
RECOVERY != SILENT AUTHORITY TRANSFER

NO VERIFICATION -> NO APPROVAL
NO EVIDENCE -> NO CLAIM
NO VERIFIED EVIDENCE -> NO ENGINEERING DECISION
```

---

# 2. Evidence boundary

This freeze is based on repository evidence at exact certified baseline:

`4de2ec96a6deb62d8ae85d30cf43066b7f373335`

No absence claim in this artifact is based solely on connector text search. The
repository tree and directly inspected files are the evidence boundary.

Existing mechanisms are treated as **specialized precedents**, not automatically as
universal implementations.

---

# 3. Evidence ledger

## EVID-FND07-01 — Generic optimistic revision precedent — VERIFIED

`src/qore/domain/aggregates.py`

provides `AggregateVersion` as explicit aggregate revision material.

`src/qore/domain/repositories.py`

provides repository/event-store boundaries carrying expected-version semantics.

This proves:

```text
EXPECTED REVISION / CAS IS AN EXISTING QORE PATTERN
```

It does not prove every mutable state family uses `AggregateVersion`.

## EVID-FND07-02 — Operational persistence CAS/idempotency — VERIFIED

`src/qore/infrastructure/operational_persistence.py`

provides:

- `OperationalRecordKey`;
- `OperationalIdempotencyKey`;
- versioned `OperationalWriteRequest` with `expected_version`;
- `OperationalRecordSnapshot.version`;
- typed version/idempotency conflict;
- stable replay receipt;
- injected persistence boundary.

The contract is explicitly non-trading operational state.

Therefore:

```text
OPERATIONAL CAS != TRADING STATE AUTHORITY
```

## EVID-FND07-03 — Executive governance CAS/state-version precedent — VERIFIED

`src/qore/governance/executive_governance_mutation.py`

uses explicit:

- expected governance snapshot/version;
- requested next snapshot/version;
- observed snapshot/version;
- APPLIED / CONFLICT receipt semantics.

`src/qore/governance/executive_state_sync.py`

separates current/stale/unavailable/unknown synchronized state from canonical
mutation authority.

This proves:

```text
PROJECTION / SYNC STATE != CANONICAL GOVERNANCE WRITER
```

## EVID-FND07-04 — Runtime registry is not writer election — VERIFIED

`src/qore/infrastructure/hosting_runtime_registry.py`

provides runtime registry generation, desired/observed runtime state and explicit
observation timestamps.

Its contract explicitly states that the registry is not a writer-election record.

Therefore:

```text
RUNTIME REGISTRY GENERATION != EXECUTION WRITER GENERATION
RUNTIME DISCOVERY != EXECUTION AUTHORITY
```

## EVID-FND07-05 — Account-scoped execution lease/fencing — VERIFIED

`src/qore/infrastructure/hosting_execution_lease.py`

provides the existing safety-critical precedent for:

- one governed execution lease per account scope;
- monotonic `HostingFencingGeneration`;
- stale-generation rejection;
- lease acquisition / renewal / release semantics;
- action-time validation of account/runtime/generation/expiry;
- at-most-one active fenced writer authority per `TradingAccountId`.

This is the strongest existing single-writer precedent.

It is **not** a universal distributed lock and must not be generalized into one.

## EVID-FND07-06 — Health evidence does not grant authority — VERIFIED

`src/qore/infrastructure/hosting_health_heartbeat.py`

provides explicit heartbeat/health evidence and freshness evaluation.

Health is evidence for operational assessment only.

```text
HEALTHY != WRITER AUTHORITY
```

## EVID-FND07-07 — Failover is evidence-governed and reconciliation-first — VERIFIED

`src/qore/infrastructure/hosting_failover_reconciliation.py`

and:

`src/qore/infrastructure/hosting_evidence_governed_failover.py`

prove the existing sequence:

```text
FAILURE / UNREACHABILITY
-> EVIDENCE
-> RECONCILIATION
-> READINESS
-> CANONICAL LEASE ACQUISITION
-> WRITER AUTHORITY
```

Failover assessment itself never creates writer authority.

Unresolved execution/account state blocks safe handoff.

## EVID-FND07-08 — Execution reconciliation is explicit and non-corrective — VERIFIED

`src/qore/infrastructure/execution_reconciliation.py`

represents explicit reconciliation state rather than inferring a corrective trade.

`src/qore/infrastructure/execution_orchestration.py`

preserves ordered execution states and permits terminal `RECONCILED` only when
reconciliation is `MATCHED`; uncertain failures move to contained behavior rather
than automatic redispatch.

Therefore:

```text
UNKNOWN EXECUTION OUTCOME != SAFE RETRY AUTHORITY
```

## EVID-FND07-09 — Explicit local freshness exists — VERIFIED

`src/qore/infrastructure/pretrade_safety.py`

uses `evaluated_at` / `expires_at` and exact intent binding.

`src/qore/infrastructure/client_execution_agent.py`

provides explicit local freshness policy for account observation, entitlement and
security-attestation age.

`src/qore/infrastructure/account_policy.py`

provides versioned effective/expiry-bounded account policy snapshots.

These prove reusable freshness patterns.

They do **not** prove one universal numeric TTL.

## EVID-FND07-10 — Account observation is consumed, not reserved — VERIFIED

`src/qore/infrastructure/client_execution_agent.py`

contains account-local observed state including balance, equity, drawdown, daily
loss and open positions, plus execution calculations including estimated risk.

It can reject stale state and reject per-trade risk exceeding policy.

The inspected contract does not atomically reserve shared capital/risk capacity.

## EVID-FND07-11 — Portfolio/Risk functional contracts are pure — VERIFIED

`src/qore/modules/portfolio/contracts.py`

creates immutable `AllocationIntent` material.

`src/qore/modules/risk/contracts.py`

evaluates concentration deterministically and returns a `FunctionalDecision`.

Neither contract is a capacity reservation boundary.

Therefore:

```text
ALLOCATION INTENT != CAPITAL RESERVED
RISK APPROVED != RISK BUDGET RESERVED
```

## EVID-FND07-12 — Pre-trade authorization is not reservation — VERIFIED

`src/qore/infrastructure/pretrade_safety.py`

binds a pre-trade decision, expiry and execution switch to an `OrderIntent`.

It does not claim distributed concurrency safety or reserve account/risk capacity.

Therefore:

```text
AUTHORIZED ORDER INTENT != RESERVED CAPACITY
```

## EVID-FND07-13 — Execution idempotency is explicit — VERIFIED

`src/qore/infrastructure/order_intent.py`

contains `ExecutionIdempotencyKey`.

This protects logical retry identity where composed correctly.

It does not prevent two distinct valid intents from concurrently consuming the same
scarce account/risk capacity.

## EVID-FND07-14 — Executive replay claim is distinct from reservation — VERIFIED

`src/qore/governance/executive_replay_idempotency.py`

provides an authoritative replay-claim boundary with:

- ACQUIRED;
- DUPLICATE;
- CONFLICT;
- exact fingerprint binding;
- fail-closed behavior;
- no automatic retry.

This is replay/idempotency protection, not economic capacity reservation.

## EVID-FND07-15 — Market replay ordering is provenance, not authority — VERIFIED

`src/qore/infrastructure/market_event_replay.py`

retains capture lineage/session ordinal/ingress sequence and explicit visibility
instants.

This proves deterministic replay ordering/availability.

```text
REPLAY ORDER != CANONICAL MUTATION ORDER
REPLAY VISIBILITY != WRITER AUTHORITY
```

## EVID-FND07-16 — FND-01 explicitly requires FND-07 outputs — VERIFIED

`docs/architecture/QORE-DEPARTMENTAL-SOVEREIGNTY-FREEZE-001.md`

requires later stages to produce at minimum:

1. Canonical Fact/Aggregate Ownership Matrix;
2. Safety-Critical State / Reservation Contract;
3. Cross-Department Freshness & Degraded-Mode Matrix;
4. Recovery / Reconciliation Matrix.

It also freezes that replicated exposure/limit state without concurrency protection
is insufficient and that scarce risk capacity requires an atomic or equivalently
safe reservation/commit/release mechanism for its governing scope.

---

# 4. Structural-gap verdict

## GAP-FND07-DOCTRINE-01 — VERIFIED STRUCTURAL GAP — HIGH

Before FND-07, QORE contains multiple strong local mechanisms for:

- optimistic revisions;
- CAS;
- replay protection;
- freshness;
- runtime registry generations;
- account-scoped fencing generations;
- execution reconciliation;
- governance version conflict;
- deterministic market replay.

What is absent is one certified architecture doctrine that tells future departments
**which semantic family applies to which state**, and prevents those families from
being treated as interchangeable.

The missing universal rule is classification/ownership, not another state engine.

Disposition:

**ARCHITECTURE FREEZE REQUIRED.**

## GAP-FND07-RES-01 — VERIFIED IMPLEMENTATION GAP — HIGH

The audited D08/D09/D10 path can consume one account observation repeatedly and can
evaluate multiple individually valid risk-increasing actions without a proven
atomic reservation of shared scarce capacity.

A concrete race class therefore exists conceptually:

```text
OBSERVE CAPACITY C
ACTION A PASSES AGAINST C
ACTION B PASSES AGAINST SAME C
A AND B BOTH ADVANCE
A + B > SAFE AVAILABLE CAPACITY
```

Freshness, per-trade risk checks, idempotency and pre-trade authorization do not by
themselves close this class.

FND-07 freezes the required safety contract but does **not** invent a universal
`Decimal` reservation, global lock or storage implementation.

Carry-forward owner set:

- D08 Account / Cash / Collateral / Portfolio;
- D09 Risk / Margin / Exposure / Limits;
- D10 Order / Execution / Routing.

Additional D12/D13 resource reservation is required only where a future certified
research/optimization resource is actually scarce and shared.

Promotion rule:

```text
NO CERTIFIED CAPACITY RESERVATION / CONSUMPTION MECHANISM
-> NO CLAIM OF SAFE CONCURRENT RISK-INCREASING EXECUTION
```

This implementation gap does not prevent FND-07 doctrine certification; it blocks
productive promotion of the affected concurrent execution path.

## GAP-FND04-TIME-01 — INHERITED OPEN GAP

FND-07 does not close the existing D06 temporal gap by implication.

No broad temporal-determinism certification may infer closure from this artifact.

---

# 5. Canonical state categories

Every cross-department state item must be classified before productive use.

## 5.1 Canonical mutable fact / aggregate

The state whose owner is authorized to commit canonical mutation.

Required:

- stable fact/aggregate identity;
- authority owner;
- writer scope;
- domain-specific revision/conflict rule where concurrent mutation is possible;
- effective/observed time where semantically required;
- reconciliation/recovery rule where external or distributed copies exist.

## 5.2 Replica / cache

A non-authoritative copy optimized for availability/performance.

A replica may satisfy a read only when its certified freshness/validity policy allows
it.

A replica never becomes writer merely because the authority is unavailable.

## 5.3 Projection / read model

Derived presentation/query state.

```text
PROJECTION != CANONICAL SOURCE FACT
READ MODEL != MUTATION AUTHORITY
```

D19 and D20 presentation/read surfaces are especially constrained by this rule.

## 5.4 Retained evidence

Immutable or append-oriented material retained to prove chronology, provenance,
reconciliation, validation or certification.

Evidence can prove a claim only within its certified evidence contract.

Evidence is not a mutation token.

## 5.5 Policy snapshot

Versioned/effective constraints consumed by another decision boundary.

Policy readiness does not itself authorize execution.

## 5.6 Runtime registry state

Operational discovery/placement/health material.

Registry presence, generation or health does not elect the canonical trading writer.

## 5.7 Fenced writer authority

Explicit, scoped and time/generation-bounded authority permitting one writer to
perform safety-critical mutation/execution for the governed scope.

Existing exemplar: D16 account-scoped execution lease.

## 5.8 Reconciliation state

Evidence describing agreement, mismatch or uncertainty between canonical internal
expectation and an external/other authoritative source.

Reconciliation state does not itself authorize a corrective action.

---

# 6. Canonical Fact / Aggregate Ownership Matrix

This matrix freezes **department-level authority families**, not every future
concrete aggregate class.

A future concrete mutable fact crossing a department boundary must bind to exactly
one authority family below and then define its own stable identity/revision contract.

| Department | Canonical authority family | Writer doctrine |
|---|---|---|
| D01 Core Governance | constitutional/governance state and canonical governance policy | D01 canonical mutation only; D20 requests do not become D01 writer authority |
| D02 Identity/Security | principal, trust, cryptographic/security policy state | D02-owned mutation; consumers may hold assertions/evidence only |
| D03 Platform Connectivity | provider capability/connectivity facts | D03 owns normalized provider capability fact; provider fact does not become Core policy |
| D04 Markets/Instruments | economic instrument/reference identity and lifecycle facts | D04 canonical identity ownership; provider-native identity remains external evidence |
| D05 Market Data | canonical market observations/evidence | D05 owns canonical observation material after normalization; consumers do not rewrite source observation |
| D06 Time/Calendars | calendar/session/lifecycle temporal facts | D06 owns canonical temporal interpretation; TIME-01 remains open where legacy semantics are unresolved |
| D07 Valuation | valuation/pricing/analytics results | D07 owns valuation result semantics; market price input remains D05 evidence |
| D08 Account/Portfolio | account, cash, collateral, portfolio canonical state | D08 owns state and capital/collateral consumption; concurrent scarce capacity requires certified reservation |
| D09 Risk | risk, margin interpretation, exposure and limit state | D09 owns risk policy/limit/exposure semantics; provider margin fact is not D09 policy; concurrent risk capacity requires certified reservation |
| D10 Order/Execution | order intent admission, execution submission and execution-control state | D10 owns governed submission/execution mutation; idempotency does not replace reservation/fencing |
| D11 Post-Trade | position, settlement, post-trade and reconciliation canonical state | D11 owns post-trade source state; D19 projection is read-only |
| D12 Research | research/replay run state and research artifacts | D12 owns research state; replay evidence does not become trading authority |
| D13 Decision Intelligence | Core strategic/functional decision state | D13 owns strategic decision production; D18 cannot originate strategy |
| D14 Lineage/Validation | lineage/statistics/validation evidence and qualification state | D14 owns validation lineage; validation evidence does not become source-domain writer authority |
| D15 Observability | telemetry, reliability and incident operational state | D15 owns observability state only; observation does not grant source mutation |
| D16 Distributed Runtime/Cloud | runtime placement/registry, hosting lease/fencing and operational runtime state | D16 owns runtime authority substrate; runtime health/placement never creates trading intent |
| D17 Signal Distribution | protected signal production/distribution state | D17 owns protected signal distribution state; valid signal still does not bypass downstream execution gates |
| D18 Client Execution | account-scoped agent/execution-plan state | D18 owns agent plan/runtime-facing state, not D13 strategy nor D10 source execution state |
| D19 Client Read Models | client presentation/read projection state | projection writer only for D19-owned read model; never canonical writer of D08/D11/D15/D16/D18/D21 source facts |
| D20 Executive Control | executive request/session/control-surface state | D20 owns control-surface/request state; D01 remains governance source authority |
| D21 Commercial | product, billing, payment and entitlement state | D21 owns commercial/entitlement facts; billing/entitlement does not become Core strategy/execution authority |
| D22 Compliance/Audit | compliance evidence/reporting state | D22 owns compliance/audit material; cannot rewrite source-domain facts by consuming evidence |
| D23 Notifications | notification intent/delivery state | D23 owns notification delivery state only; notification is not canonical business mutation |
| D24 Certification Gate | certification decision/evidence record | D24 owns certification record, not implementation/source state; no self-certification |

A concrete fact cannot claim multiple canonical authority owners for the same logical
revision/scope.

If legitimate sharding exists, each shard must have an explicit non-overlapping
writer scope.

---

# 7. Revision/version family doctrine

QORE must not introduce one universal `StateVersion` merely to make distributed
state look uniform.

Existing semantic families include:

| Existing material | Meaning | Explicitly NOT |
|---|---|---|
| `AggregateVersion` | domain aggregate optimistic revision precedent | contract version or fencing token |
| repository `expected_version` | optimistic write precondition | global writer election |
| operational record `version` | non-trading operational record revision | trading state authority |
| `ExecutiveGovernanceStateVersion` | D01 governance state revision | D16 fencing generation |
| `AccountPolicyVersion` | account-policy snapshot version | account balance/exposure revision |
| `HostingRuntimeRegistryGeneration` | D16 registry snapshot generation | writer authority |
| `HostingFencingGeneration` | stale-writer exclusion for account execution authority | aggregate content revision |
| execution orchestration `sequence` | one orchestration transition sequence | account/portfolio revision |
| `MarketIngressSequence` | retained capture arrival provenance | canonical mutation version |
| `DepartmentContractVersion` | logical cross-department contract version | state revision |
| `DomainEventVersion` | event contract/schema version | state revision |

Rules:

```text
SAME INTEGER SHAPE != SAME SEMANTIC VERSION
SAME UUID SHAPE != SAME AUTHORITY
```

A future cross-department contract must carry the domain-specific revision family
required by its fact; it must not coerce unrelated version classes into a universal
counter.

---

# 8. Freshness and degraded-mode matrix

Freshness is semantic and consumer-bound.

No single numeric TTL is frozen by FND-07.

## Class A — Safety-critical action-time state

Examples:

- account/risk capacity;
- entitlement required for new trading;
- security attestation;
- pre-trade authorization;
- execution lease/fencing authority;
- governance authority/current mutation state.

Rule:

```text
STALE / EXPIRED / UNKNOWN / UNAVAILABLE
-> BLOCK NEW RISK-INCREASING OR AUTHORITY-INCREASING ACTION
```

Exact freshness bounds belong to the owning contract and require provenance.

## Class B — Operational health/placement evidence

Examples:

- runtime heartbeat;
- hosting health;
- runtime registry observation.

Stale/unreachable evidence may trigger incident/failover assessment.

It does not grant replacement writer authority.

## Class C — Market/reference observations

Must retain source/effective/observed/ingested/availability semantics required by the
owning D04/D05/D06 contract.

A consumer must define whether stale data blocks, degrades, or is acceptable for a
specific non-risk-increasing operation.

FND-07 does not close `GAP-FND04-TIME-01`.

## Class D — Read projections

A stale projection may be displayable only if explicitly labeled and if the owning
product contract permits it.

A stale projection can never be promoted into canonical write authority.

## Class E — Immutable historical evidence

Historical evidence is not governed by a "freshness TTL" in the same sense as live
state.

It must instead preserve chronology, availability/provenance and revision/dataset
identity sufficient for the claim being made.

---

# 9. Concurrency and conflict doctrine

## 9.1 Optimistic conflict

Where optimistic revision is sufficient:

```text
READ REVISION N
-> PROPOSE N+1
-> COMPARE EXPECTED N
-> APPLY OR CONFLICT
```

Conflict must be explicit.

A conflict cannot silently overwrite the observed state.

## 9.2 Fenced single writer

Where stale writers could cause external side effects, optimistic content revision
alone may be insufficient.

The governing scope must use a fenced writer mechanism or equivalent certified
safety property.

Existing D16 execution lease is the precedent for account-scoped hosted execution.

## 9.3 Multi-resource consumption

Where one action consumes several scarce capacities, a collection of independently
fresh reads is insufficient.

The owning domains must prove atomic or equivalently safe reservation/commit/release
for the governing scope.

FND-07 does not prescribe database transactions, distributed locks, Saga or another
specific mechanism.

## 9.4 Conflict does not authorize retry

A caller may retry only if:

- business idempotency semantics permit it;
- current authoritative state is reacquired as required;
- any prior uncertain side effect is reconciled;
- required capacity is reacquired/reserved safely.

---

# 10. Safety-Critical State / Reservation Contract

This section freezes the **minimum semantic obligation** for scarce shared capacity.

It deliberately does not define a universal reservation amount type.

A domain reservation mechanism must bind at minimum:

1. stable reservation identity;
2. owning department;
3. exact governed scope identity;
4. exact domain-specific capacity semantic type;
5. authoritative basis state/revision;
6. requested capacity consumption;
7. acquisition result;
8. acquisition time and validity/expiry where applicable;
9. business idempotency/replay identity where retries are possible;
10. commit/consume evidence;
11. release/expiry evidence;
12. typed conflict/insufficient-capacity result;
13. deterministic reconciliation rule after uncertainty.

Required safety property:

```text
TWO CONCURRENT REQUESTS CANNOT BOTH CONSUME THE SAME UNAVAILABLE CAPACITY
```

Domain ownership:

### D08 — Capital / cash / collateral / portfolio capacity

D08 owns capital/collateral state and must prevent double consumption of its scarce
capacity.

### D09 — Risk / exposure / limit capacity

D09 owns risk/limit/exposure semantics and must prevent multiple concurrent actions
from each treating the same remaining limit as independently available.

### D10 — Submission / in-flight execution capacity

D10 must account for already authorized/submitted/in-flight actions when those
actions affect scarce capacity or duplicate-order safety.

D10 idempotency protects repeated identity; it does not replace D08/D09 capacity
reservation.

### D12/D13 — Research/optimization resource capacity

A reservation is required only if a future certified resource is scarce, shared and
concurrently consumable.

No generic monetary `Decimal`, quantity, notional, weight or provider volume is
introduced by this freeze.

FND-04 economic-semantic separations remain authoritative.

---

# 11. Single-writer / lease / fencing doctrine

Single-writer scope is not automatically global.

Permitted scopes may include, where certified:

- account;
- portfolio;
- aggregate;
- instrument;
- venue;
- strategy;
- tenant;
- runtime execution unit.

For each single-writer fact, the contract must define:

- scope identity;
- current writer identity;
- writer authority epoch/generation if stale writer exclusion is required;
- acquisition preconditions;
- renewal validity;
- release/revocation;
- expiry behavior;
- action-time validation;
- recovery after authority uncertainty.

For hosted trading execution the frozen invariant is:

```text
AT MOST ONE ACTIVE FENCED EXECUTION AUTHORITY PER TradingAccountId
```

A runtime registry entry, healthy heartbeat or failover-readiness certificate cannot
substitute for the active lease.

---

# 12. Split-brain containment

If two physical actors each believe they are writer for the same certified
single-writer scope, the system is in a safety fault.

Required behavior:

```text
AMBIGUOUS WRITER AUTHORITY -> FAIL CLOSED
STALE FENCING GENERATION -> REJECT
UNKNOWN CURRENT AUTHORITY -> NO NEW WRITES
```

Recovery must establish one authoritative current writer before new risk-increasing
external actions resume.

No "last healthy node wins" or "first responder wins" rule is permitted unless a
future certified authority protocol explicitly proves that property.

---

# 13. Recovery / Reconciliation Matrix

| Failure/uncertainty class | Required action | Forbidden inference |
|---|---|---|
| optimistic revision conflict | reacquire authoritative state; reevaluate | overwrite because local copy is newer by wall clock |
| stale/unknown projection | refresh or degrade/block per contract | promote projection to writer |
| runtime unreachable | collect evidence and assess failover | unreachable means old writer is safely dead |
| lease expired/unknown | block writer actions; reacquire through canonical lease protocol | health or placement grants lease |
| split-brain suspicion | fence/block affected writer scope | allow both until reconciliation finishes |
| external execution outcome unknown | contain and reconcile provider/external truth | blind redispatch |
| account/post-trade mismatch | reconcile against certified source before restoring discretionary authority | automatic corrective trade |
| duplicate replay claim | block duplicate protected action | execute again because payload is equal |
| replay fingerprint conflict | fail closed and investigate | choose latest request by arrival time |
| stale safety-critical account/risk state | block new risk increase and reacquire current capacity | accept because observation is internally consistent |
| reservation acquisition conflict | reject/retry only after authoritative capacity reevaluation | double-spend remaining capacity |
| reservation commit uncertainty | reconcile prior side effect and reservation state | allocate a second reservation automatically |

Reconciliation source must be explicit per domain.

No universal "database wins" or "provider wins" rule is frozen.

---

# 14. Retry / idempotency / replay / ordering matrix

| Mechanism | Solves | Does NOT solve |
|---|---|---|
| command/business idempotency key | repeat identity for one logical side effect | capacity oversubscription by two distinct requests |
| executive replay claim | duplicate/conflicting protected executive request | portfolio/risk reservation |
| execution idempotency key | duplicate submission identity | safe remaining exposure calculation |
| optimistic expected version | stale write conflict | external stale-writer fencing by itself |
| fencing generation | stale writer exclusion for governed scope | content/business-state revision |
| market ingress sequence | retained replay arrival order | mutation authority |
| orchestration sequence | local execution state transition order | global event order |
| reconciliation receipt | observed agreement/mismatch state | automatic corrective action |

No hidden automatic retry loop is introduced by FND-07.

---

# 15. Cross-department async feedback containment

An async dependency must define, where material:

- correlation identity;
- causal relationship;
- duplicate semantics;
- ordering assumptions;
- state revision/freshness consumed;
- loop termination/containment;
- replay/reprocessing behavior;
- degraded-mode behavior.

Receiving an event does not authorize the consumer to mutate the provider's source
state.

If an event causes the consumer to issue a command, that command must independently
pass FND-06 route/admission and the owning domain's current-state/authorization
checks.

---

# 16. Regional / cell / account-scale doctrine

QORE may distribute runtime and storage physically.

Distribution must preserve logical authority partitions.

## Account isolation

One account's writer lease, reservation, failure or reconciliation uncertainty must
not silently become authority for another account.

## Cell / region isolation

A regional/cell outage may remove availability but cannot manufacture new authority.

A replacement cell must acquire the same governed authority required by any other
writer.

## Replication

Replicated state must retain:

- canonical source identity;
- revision/provenance;
- freshness/validity semantics;
- deterministic conflict/reconciliation behavior.

Replication lag is not evidence that the source has stopped writing.

## Scale

`N accounts` requires `N` independently governed account scopes where account-scoped
authority is the contract.

No global singleton lease is implied.

---

# 17. Degraded-mode doctrine

Every safety-relevant dependency must state one of the following outcomes when it is
stale/unavailable/unknown:

- continue safely with explicitly bounded stale/read-only behavior;
- degrade to read-only/presentation behavior;
- block new risk-increasing actions;
- contain an in-flight uncertain action pending reconciliation;
- trigger incident/failover assessment without transferring authority.

Forbidden:

```text
DEPENDENCY FAILED -> INVENT DEFAULT AUTHORITY
DEPENDENCY UNKNOWN -> ASSUME LAST VALUE IS CURRENT
```

---

# 18. Security / evidence / provenance

State authority artifacts must not carry raw secrets.

Evidence references remain opaque and secret-free.

```text
REFERENCE ID != RETAINED SOURCE EVIDENCE
HASH != RETAINED SOURCE EVIDENCE
```

Authority transitions that matter to safety must retain sufficient evidence to
reconstruct:

- previous authority/revision;
- requested transition;
- observed state;
- result/conflict;
- relevant timestamps;
- correlation/causation where applicable;
- reconciliation evidence where required.

No sensitive provider credential becomes logical state material.

---

# 19. Technology non-selection

FND-07 intentionally does not select:

- PostgreSQL;
- Redis;
- Kafka;
- NATS;
- RabbitMQ;
- Raft;
- etcd;
- Kubernetes;
- database advisory locks;
- distributed mutexes;
- two-phase commit;
- Saga;
- CQRS;
- event sourcing;
- a specific cloud topology.

A future implementation may use a technology only after its required safety property,
failure modes and evidence are independently certified.

```text
TECHNOLOGY NAME != SAFETY PROPERTY
```

---

# 20. Adversarial cases

## FND07-CASE-01 — Replica-as-writer laundering

Attempt: canonical owner unavailable; fresh replica begins mutation.

Required: reject unless replica separately acquires certified writer authority.

## FND07-CASE-02 — Read-model mutation laundering

Attempt: D19/D20 projection is treated as canonical account/governance source.

Required: reject.

## FND07-CASE-03 — Runtime registry election

Attempt: highest runtime registry generation becomes execution writer.

Required: reject; registry generation is not fencing generation.

## FND07-CASE-04 — Healthy backup authority

Attempt: healthy candidate starts orders because active runtime is unhealthy.

Required: reject until reconciliation + canonical lease acquisition.

## FND07-CASE-05 — Stale fenced writer

Attempt: generation N writes after N+1 became authoritative.

Required: reject.

## FND07-CASE-06 — Lease expiry hidden by heartbeat

Attempt: runtime remains healthy after its lease expires and continues writing.

Required: reject at action-time authority validation.

## FND07-CASE-07 — CAS conflict overwrite

Attempt: expected revision differs but caller writes anyway.

Required: explicit conflict/fail closed.

## FND07-CASE-08 — Policy version used as account-state revision

Attempt: `AccountPolicyVersion` is cited as proof that balance/exposure state is current.

Required: reject semantic substitution.

## FND07-CASE-09 — Contract version used as state revision

Attempt: `DepartmentContractVersion("2.0")` is treated as mutable fact revision.

Required: reject.

## FND07-CASE-10 — Double risk consumption

Attempt: A and B both read the same available risk budget; both independently pass;
both consume it.

Required: impossible in any future promoted concurrent path through atomic/equivalent
reservation/commit/release.

Current disposition: implementation gap `GAP-FND07-RES-01` blocks such promotion.

## FND07-CASE-11 — Idempotency mistaken for reservation

Attempt: A and B have different idempotency keys but consume the same scarce capacity.

Required: capacity mechanism must still prevent oversubscription.

## FND07-CASE-12 — Pretrade authorization mistaken for reservation

Attempt: two approved unexpired authorizations are assumed jointly safe without
capacity reservation.

Required: reject.

## FND07-CASE-13 — Blind retry after unknown submission

Attempt: network failure occurs after external placement; caller resubmits because no
receipt was observed.

Required: contain/reconcile first; no duplicate redispatch authority.

## FND07-CASE-14 — Reconciliation-driven corrective trade

Attempt: mismatch automatically creates offsetting order.

Required: reject.

## FND07-CASE-15 — Unreachable means dead

Attempt: backup is promoted solely because former writer cannot be contacted.

Required: reject.

## FND07-CASE-16 — Wall-clock last-write-wins

Attempt: conflicting states are resolved by whichever has later local timestamp.

Required: reject unless a future domain specifically certifies that rule.

## FND07-CASE-17 — Replay sequence becomes mutation authority

Attempt: later market ingress sequence is treated as permission to rewrite state.

Required: reject.

## FND07-CASE-18 — D15 health becomes D16/D10 authority

Attempt: observability declares a runtime healthy and thereby activates execution.

Required: reject.

## FND07-CASE-19 — D21 entitlement becomes strategy authority

Attempt: paid/entitled state creates D13 decision or D10 order authority.

Required: reject.

## FND07-CASE-20 — Cross-account authority leakage

Attempt: lease/reservation for account A is reused for account B.

Required: reject exact scope mismatch.

## FND07-CASE-21 — Stale projection displayed as current

Attempt: D19 presents stale state without explicit stale/degraded semantics.

Required: reject product contract unless explicit labeling/age policy allows it.

## FND07-CASE-22 — Global version normalization

Attempt: unrelated revision/generation/version types are converted to one integer and
compared as if they share chronology.

Required: reject.

---

# 21. Minimum implementation delta decision

## Decision: DOCUMENTATION-ONLY FOUNDATION DELTA

No new runtime type or generic state engine is justified in FND-07.

Reasons:

1. Existing safety-critical mechanisms are already typed in their owning domains.
2. Their revision/generation semantics are intentionally different.
3. A new generic `StateVersion`, `GlobalLease` or `ReservationAmount` would erase
   FND-04/FND-07 semantic distinctions.
4. The unresolved reservation problem requires domain-specific economic semantics and
   a concurrency-safe implementation boundary; inventing a generic payload here would
   not solve the race.
5. FND-07's missing structural artifact is the universal doctrine/matrix that tells
   future implementations which local mechanism is required and what may never be
   inferred.

Therefore the candidate delta is intentionally limited to this architecture artifact.

```text
DOCTRINE REQUIRED
GENERIC DISTRIBUTED-STATE RUNTIME NOT JUSTIFIED
```

If independent review proves a machine-enforceable constitutional bypass that this
artifact cannot close, a new exact-head correction may add the minimum typed layer.

---

# 22. Carry-forward implementation obligations

## GAP-FND07-RES-01 — OPEN

Owner set: D08 / D09 / D10.

Blocks:

- claims of safe concurrent risk-capacity consumption;
- productive promotion of concurrent risk-increasing execution relying only on
  snapshots/authorizations/idempotency.

Does not block:

- certification of this FND-07 doctrine;
- read-only analysis;
- existing offline/research work;
- existing local mechanisms that make no unsupported reservation claim.

Closure requires a separately governed implementation with:

- exact domain capacity semantics;
- atomic/equivalently safe acquire;
- commit/release/expiry;
- conflict/insufficient-capacity behavior;
- idempotency interaction;
- uncertainty reconciliation;
- adversarial concurrency tests;
- independent review;
- Integration Gate.

## GAP-FND04-TIME-01 — REMAINS OPEN

FND-07 does not change its owner or closure criteria.

## PR #298 — REMAINS HOLD

FND-07 grants no provider-native identity/policy authority.

---

# 23. Compatibility / blast-radius target

Expected FND-07 candidate blast radius at first review:

- additive architecture artifact only;
- no production source modification;
- no test modification;
- no FND-05 department change;
- no FND-06 contract change;
- no hosting lease change;
- no execution change;
- no governance change;
- no account/risk implementation change;
- no provider adapter change;
- no PR #298 promotion;
- no TIME-01 closure.

Any later expansion must be justified by new verified evidence.

---

# 24. Independent-review obligations

Independent review must attempt to falsify at minimum:

1. whether documentation-only is sufficient for FND-07 doctrine;
2. whether a generic typed foundation is actually required;
3. whether any revision/generation classes have been incorrectly conflated;
4. whether the 24-department ownership-family matrix violates FND-05 ownership;
5. whether D19/D20 projection semantics can accidentally become writer authority;
6. whether D16 health/registry state can be mistaken for lease authority;
7. whether failover readiness can bypass reconciliation/lease acquisition;
8. whether stale generation/writer can regain authority;
9. whether freshness classes are too broad or too weak;
10. whether FND-07 accidentally closes TIME-01;
11. whether idempotency/replay is incorrectly claimed to solve capacity reservation;
12. whether `GAP-FND07-RES-01` is correctly classified and scoped;
13. whether leaving reservation implementation open makes FND-07 doctrine itself
    uncertifiable;
14. whether any technology has been prematurely frozen;
15. whether recovery rules could authorize duplicate execution or automatic corrective
    trading;
16. whether account/cell/region isolation is sufficiently explicit;
17. whether evidence/reference material is mistaken for source authority;
18. whether any productive Cloud/real-capital capability is implied.

CI green alone is not approval.

---

# 25. Certification gate

This artifact remains a candidate until the exact PR head passes:

```text
EXACT-HEAD QUALITY GATE
-> DIFF / BLAST-RADIUS AUDIT
-> INDEPENDENT ADVERSARIAL ARCHITECTURE REVIEW
-> CORRECTION IF REQUIRED
-> NEW EXACT HEAD / NEW CI / RE-REVIEW IF CHANGED
-> INTEGRATION GATE FALSIFICATION
-> VERIFY MAIN NO DRIFT
-> EXPECTED-HEAD MERGE
-> VERIFY ACTUAL MERGE COMMIT
-> VERIFY POST-MERGE MAIN
-> FREEZE NEW CERTIFIED BASELINE
-> CLOSE ISSUE #316 / FND-07
```

Only then may FND-08 begin.

FND-08 remains constrained by inherited open `GAP-FND04-TIME-01` for broad temporal
determinism claims and by any explicit open implementation gaps for productive
capability claims.

---

# 26. Candidate closure condition

FND-07 doctrine may close only if independent evidence confirms:

```text
CANONICAL FACT AUTHORITY IS DISTINCT FROM STORAGE LOCATION,
EVERY CROSS-DEPARTMENT MUTABLE FACT HAS ONE GOVERNED AUTHORITY FAMILY,
REPLICA / CACHE / PROJECTION / EVIDENCE CANNOT BECOME WRITER BY INFERENCE,
REVISION / VERSION / GENERATION FAMILIES ARE NOT CONFLATED,
SAFETY-CRITICAL FRESHNESS FAILS CLOSED,
SINGLE-WRITER SCOPES REQUIRE EXPLICIT AUTHORITY,
FAILOVER CANNOT BYPASS RECONCILIATION + FENCING,
RETRY / IDEMPOTENCY / REPLAY DO NOT SUBSTITUTE FOR CAPACITY RESERVATION,
SCARCE CONCURRENT CAPACITY REQUIRES ATOMIC OR EQUIVALENT RESERVATION,
RECONCILIATION UNCERTAINTY CANNOT AUTHORIZE DUPLICATE OR CORRECTIVE TRADING,
AND NO DISTRIBUTED-STATE TECHNOLOGY IS PREMATURELY FROZEN.
```

Until that chain passes:

**STAGE-07 / FND-07 REMAINS OPEN.**
