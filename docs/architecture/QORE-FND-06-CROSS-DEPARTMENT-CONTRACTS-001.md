# QORE-FND-06-CROSS-DEPARTMENT-CONTRACTS-001

## Status

**STAGE-06 / FND-06 — ARCHITECTURE + MINIMUM TYPED FOUNDATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #314  
Master roadmap: #303  
Certified starting baseline: `a5545da0ba7361a50daa7adb9bcfb3cf04bdb41b`  
Predecessor: FND-05 / Issue #312 / PR #313 — CLOSED

This artifact freezes the minimum constitutional semantics for QORE cross-department COMMAND, QUERY, EVENT and EVIDENCE contracts.

It does **not** create a universal payload envelope, transport, broker, RPC framework, event store, distributed database, consensus protocol or productive service mesh.

The purpose is narrower and more fundamental:

```text
A CROSS-DEPARTMENT CONTRACT MUST IDENTIFY
WHAT SEMANTIC CLASS IT IS,
WHICH CANONICAL DEPARTMENT CONSUMES IT,
WHICH CANONICAL DEPARTMENT PROVIDES / OWNS THE GOVERNED CAPABILITY OR FACT,
WHICH FND-05 INTERACTION MODE APPLIES,
AND WHICH EXPLICIT LOGICAL CONTRACT VERSION IS IN FORCE.
```

A generic contract descriptor never grants business authority by itself.

---

# 1. Governing invariants

```text
DEPARTMENT IDENTITY != MESSAGE TRANSPORT IDENTITY
COMMAND != QUERY != EVENT != EVIDENCE
CONTRACT DESCRIPTOR != BUSINESS PAYLOAD
CONTRACT REGISTRATION != INVOCATION AUTHORIZATION
EVENT CONSUMPTION != WRITE AUTHORITY
EVIDENCE CONSUMPTION != SOURCE FACT OWNERSHIP
QUERY RESULT != MUTATION AUTHORITY
READ MODEL != COMMAND AUTHORITY
CORRELATION != CAUSATION
CAUSATION ID != COMPUTATIONAL DERIVATION
REFERENCE ID != RETAINED EVIDENCE
EVIDENCE REFERENCE != EVIDENCE CONTENT
SYNC DEPENDENCY != REMOTE RPC REQUIREMENT
ASYNC DEPENDENCY != UNBOUNDED LOOP
PHYSICAL MESSAGE DIRECTION != AUTHORITY DEPENDENCY DIRECTION
GENERIC ENVELOPE != GENERIC AUTHORITY
ROUTE EXISTS != CONCRETE BUSINESS CONTRACT EXISTS
NO FND-05 ROUTE -> NO CANONICAL FND-06 CROSS-DEPARTMENT CONTRACT
NO VERIFIED CONTRACT -> NO CROSS-DEPARTMENT AUTHORITY TRANSFER
NO VERIFICATION -> NO APPROVAL
```

The FND-05 dependency graph remains the constitutional upper bound for FND-06 routes.

FND-06 may instantiate a contract only on an already-certified FND-05 `consumer -> provider + interaction_mode` edge.

A new cross-department route therefore requires an explicit FND-05 architecture change before FND-06 may register it.

---

# 2. Repository evidence ledger

All evidence below was inspected against certified baseline:

`a5545da0ba7361a50daa7adb9bcfb3cf04bdb41b`

## EVID-FND06-01 — Generic command foundation exists — VERIFIED

`src/qore/domain/commands.py`

Verified existing material:

- `CommandId`;
- `CommandName`;
- `IdempotencyKey`;
- `CommandMetadata`;
- explicit `CorrelationId`;
- optional `CausationId`;
- optional idempotency key;
- deterministic sorted immutable metadata;
- explicit timezone-aware command timestamp;
- `CommandResult[T] = Result[T, DomainError]`;
- `CommandHandler` Protocol.

Consequence:

```text
FND-06 MUST NOT CREATE A SECOND GENERIC COMMAND ENVELOPE.
```

The current generic command foundation does not identify canonical D01..D24 consumer/provider authority.

## EVID-FND06-02 — Generic business-event foundation exists — VERIFIED

`src/qore/domain/events.py`

Verified:

- `DomainEventId`;
- `CorrelationId`;
- `CausationId`;
- `DomainEventVersion`;
- `DomainEventCategory`;
- `DomainEventMetadata`;
- `BusinessDomainEvent`;
- explicit event identity/version in the higher-level business event;
- deterministic metadata ordering.

Consequence:

```text
FND-06 MUST NOT CREATE A SECOND GENERIC BUSINESS EVENT ENVELOPE.
```

The existing event foundation does not bind publisher/fact-owner and consumers to the canonical FND-05 department graph.

## EVID-FND06-03 — Current MessageBus is not the FND-06 contract fabric — VERIFIED

`src/qore/domain/message_bus.py`

Verified:

- `Message = Command | BusinessDomainEvent`;
- deterministic in-process synchronous command dispatch;
- one concrete command handler per command type;
- multiple handlers for one concrete event type;
- pure retry-decision Protocol;
- explicit `Result` / `Failure` handling.

Not present:

- QUERY as a generic message class;
- EVIDENCE as a generic message class;
- canonical DepartmentId route binding;
- distributed transport proof;
- durable log proof;
- remote-RPC semantics.

Therefore:

```text
CURRENT MESSAGE BUS != UNIVERSAL CROSS-DEPARTMENT TRANSPORT
CURRENT MESSAGE BUS != DEPARTMENT AUTHORITY REGISTRY
```

## EVID-FND06-04 — Kernel contracts are lower-level and narrower — VERIFIED

`src/qore/kernel/contracts.py`

Contains:

- `EventPublisher` Protocol;
- `EventHandler` Protocol;
- `Repository` Protocol.

These are infrastructure-neutral kernel interfaces, not D01..D24 authority contracts.

## EVID-FND06-05 — Legacy kernel DomainEvent is not a new FND-06 identity foundation — VERIFIED

`src/qore/kernel/domain_event.py`

Legacy `DomainEvent` has a `uuid4()` default for `event_id`.

The higher-level `BusinessDomainEvent` already supplies explicit identity when used through the certified business-event boundary.

FND-06 does not modify or promote the legacy implicit-UUID default into a new constitutional cross-department identity rule.

```text
LEGACY KERNEL DEFAULT != NEW DETERMINISTIC CONTRACT DOCTRINE
```

## EVID-FND06-06 — Result/Success/Failure already exist — VERIFIED

`src/qore/kernel/result.py`

Provides immutable:

- `Success[T]`;
- `Failure[E: KernelError]`;
- `Result[T, E]`.

FND-06 reuses this precedent and does not create another success/failure algebra.

## EVID-FND06-07 — External ports are not department identities — VERIFIED

`src/qore/infrastructure/ports.py`

Provides:

- `AdapterId`;
- `SourceId`;
- `PortName`;
- `ExternalSourceDescriptor`;
- `ExternalRequestMetadata`;
- `ExternalPort`;
- `ReadExternalPort`;
- `WriteExternalPort`.

Those values describe external integration boundaries.

They do not replace:

- `DepartmentId`;
- FND-05 ownership;
- FND-06 contract route identity.

```text
ADAPTER / SOURCE / PORT IDENTITY != DEPARTMENT AUTHORITY IDENTITY
```

## EVID-FND06-08 — Executive control provides strong domain-specific command/query precedent — VERIFIED

`src/qore/governance/executive_ports.py` and `executive_query_dispatch.py`

Verified precedent includes:

- transport-neutral command port;
- transport-neutral query port;
- authorization before dispatch;
- read delivery bound to exact authorized request;
- explicit receipt identity/status/timestamps;
- opaque sanitized evidence references;
- downstream error sanitization.

These are D20 executive-control contracts.

They prove that COMMAND and QUERY should not be collapsed into one universal behavior.

They do **not** constitute a universal D01..D24 route registry.

## EVID-FND06-09 — No generic canonical QueryId was found — VERIFIED ABSENCE AT AUDIT SCOPE

Repository search for `QueryId` returned no result.

Repository search for query classes found domain-specific query/read implementations, including executive query dispatch/ports, but no generic cross-department query envelope equivalent to `Command`.

FND-06 does not invent one merely for symmetry.

## EVID-FND06-10 — Evidence identity/reference vocabulary is domain-specialized — VERIFIED

Repository search found many specialized evidence identities/references in research, hosting, execution, market observation, commercial and governance domains.

No single existing type was proven to mean every form of QORE evidence.

Therefore:

```text
SPECIALIZED EVIDENCE IDS != UNIVERSAL EVIDENCE PAYLOAD TYPE
```

FND-06 defines EVIDENCE as a cross-department contract semantic class without flattening domain-specific evidence schemas.

## EVID-FND06-11 — FND-01 explicitly requires this artifact — VERIFIED

`docs/architecture/QORE-DEPARTMENTAL-SOVEREIGNTY-FREEZE-001.md`

FND-01 states that Core owns canonical command/query/event/evidence semantics and requires every future department charter to define:

- accepted commands;
- published events/evidence;
- queries/projections;
- sync dependencies;
- async dependencies.

It also requires async feedback contracts to carry enough explicit material for correlation/causation, version/revision, idempotency/deduplication where needed, ordering assumptions, loop containment, replay/reprocessing and freshness/evidence.

Mandatory downstream artifact #8 is:

`Cross-Boundary Command / Query / Event / Evidence contracts`.

This is the direct constitutional obligation satisfied by FND-06.

## EVID-FND06-12 — FND-05 supplies the exact authority graph — VERIFIED

`src/qore/domain/departments.py`

Certified FND-05 defines:

- 24 canonical DepartmentIds;
- exact consumer -> provider direction;
- `SYNCHRONOUS` / `ASYNCHRONOUS` modes;
- 70 canonical dependency edges;
- deterministic graph material;
- forbidden authority inversions.

FND-06 does not reopen those edges.

---

# 3. Structural-gap verdict

## GAP-FND06-CONTRACT-01 — VERIFIED STRUCTURAL GAP — HIGH

Repository reality before FND-06 contains:

- generic command semantics;
- generic business-event semantics;
- typed Result/error foundations;
- external-port metadata;
- many domain-specific command/query/event/evidence contracts;
- the certified D01..D24 dependency graph.

It does **not** contain one typed constitutional layer that binds a logical cross-department contract to:

1. an explicit contract identity;
2. an explicit logical contract version;
3. one of the four semantic classes COMMAND/QUERY/EVENT/EVIDENCE;
4. a canonical consumer DepartmentId;
5. a canonical provider/authority-owner DepartmentId;
6. the exact certified FND-05 interaction mode;
7. the exact certified FND-05 graph.

Without that binding, a future generic transport/configuration layer could accidentally treat a syntactically valid message as authority between departments that FND-05 never authorized.

That is an authority-laundering risk.

Disposition:

**MINIMUM TYPED FOUNDATION REQUIRED.**

Documentation alone is insufficient because route membership and graph equivalence are machine-verifiable constitutional invariants.

---

# 4. Four semantic contract classes

## COMMAND

A COMMAND requests the provider/authority-owning department to evaluate and possibly perform a governed state-changing action.

A command may still be rejected by:

- authorization;
- policy;
- state;
- risk;
- idempotency;
- freshness;
- domain validation.

Therefore:

```text
COMMAND EXISTS != COMMAND AUTHORIZED
COMMAND ROUTE EXISTS != MUTATION MUST OCCUR
```

Commands that can cause side effects require domain-appropriate duplicate/idempotency protection when retries/replay are possible.

Existing `CommandMetadata.idempotency_key` is the generic precedent.

FND-06 does not force one idempotency key onto every domain command.

## QUERY

A QUERY requests a read/projection governed by the provider department.

The provider remains authority over the source fact; the returned projection may be derived.

```text
QUERY != COMMAND
QUERY RESULT != WRITE AUTHORITY
PROJECTION != SOURCE FACT
```

FND-06 does not create a generic query payload or assume CQRS.

Existing D20 query ports are precedent for transport-neutral read contracts.

## EVENT

An EVENT communicates that a domain occurrence has been recorded/published by the provider/fact-owning side.

Consumption of an event does not transfer ownership of the source fact.

```text
EVENT CONSUMER != EVENT SOURCE AUTHORITY
EVENT HANDLER != SOURCE WRITER
```

An event may trigger a consumer to evaluate its own governed rules, but cannot grant authority outside the consumer's certified domain contract.

## EVIDENCE

EVIDENCE communicates or references material used to prove, audit, validate, certify or explain a claim.

Evidence is not automatically a state-changing command and is not automatically a historical event.

```text
EVIDENCE != COMMAND
EVIDENCE != EVENT
EVIDENCE REFERENCE != EVIDENCE CONTENT
EVIDENCE EXISTS != CLAIM VERIFIED
```

Domain-specific evidence types remain authoritative within their certified domain semantics.

---

# 5. Universal authority-direction rule

For all four FND-06 semantic classes, the typed route uses:

```text
CONSUMER -> PROVIDER / AUTHORITY OWNER
```

This is the same direction as FND-05.

Examples:

- D18 consumes D10 execution capability -> D18 -> D10;
- D20 consumes D01 governance authority/read capability -> D20 -> D01;
- D19 consumes D11 post-trade facts/events -> D19 -> D11;
- D24 consumes D14 validation evidence -> D24 -> D14.

This direction intentionally describes **authority dependency**, not network direction.

---

# 6. Physical message flow is a different dimension

For COMMAND/QUERY, physical request flow will commonly travel consumer -> provider.

For EVENT/EVIDENCE, physical publication/delivery may commonly travel provider -> consumer.

That does not reverse constitutional ownership.

Example:

```text
AUTHORITY DEPENDENCY:
D19 -> D11 [A]

PHYSICAL EVENT DELIVERY MAY BE:
D11 -> D19
```

Both can be true simultaneously.

Therefore:

```text
PHYSICAL MESSAGE DIRECTION != AUTHORITY DEPENDENCY DIRECTION
```

A future transport diagram must label those dimensions separately.

---

# 7. FND-06 typed foundation

New additive domain foundation:

`src/qore/domain/department_contracts.py`

It defines:

- `DepartmentContractError`;
- `DepartmentContractValidationError`;
- `DepartmentContractKind`;
- `DepartmentContractId`;
- `DepartmentContractVersion`;
- `DepartmentContractSpec`;
- `DepartmentContractRegistry`.

No payload type is introduced.

No dispatch function is introduced.

No transport is introduced.

No authorization token is introduced.

No runtime network behavior is introduced.

---

# 8. DepartmentContractKind

Closed StrEnum values:

- `COMMAND`;
- `QUERY`;
- `EVENT`;
- `EVIDENCE`.

A raw string such as `"command"` is not accepted where the typed enum is required.

This prevents the FND-05 class of raw-StrEnum semantic bypass from recurring in FND-06.

---

# 9. DepartmentContractId

`DepartmentContractId` is a stable logical string identity, not a generated UUID.

Canonical syntax:

`[a-z][a-z0-9.-]*`

Rationale:

- deterministic;
- human-reviewable;
- namespace-friendly;
- transport-neutral;
- no implicit randomness;
- compatible with repository precedent for canonical port names.

The ID names a logical contract, not one message delivery.

```text
CONTRACT ID != MESSAGE INSTANCE ID
```

---

# 10. DepartmentContractVersion

Version is explicit and logical.

Canonical syntax accepts lowercase alphanumeric version material plus `.`, `_`, `-` after the first character.

Examples such as `1.0`, `v1`, `2026-08` can be represented without freezing semantic-versioning policy.

FND-06 deliberately does not claim SemVer.

Multiple explicit versions of one contract ID may coexist in a registry when both are intentionally registered.

There is no implicit latest-version selection.

Consumers must request an exact `(contract_id, version)`.

```text
NO IMPLICIT VERSION FALLBACK
```

---

# 11. DepartmentContractSpec

Fields:

- `contract_id`;
- `version`;
- `kind`;
- `consumer`;
- `provider`;
- `mode`.

All fields receive runtime type validation.

Consumer and provider must differ.

The spec is immutable (`frozen=True`, `slots=True`).

The spec does not carry business payload or user metadata.

Its `logical_values()` is deterministic and contains only explicit logical material.

---

# 12. DepartmentContractRegistry canonical binding

The registry requires a `DepartmentRegistry` whose `logical_values()` are exactly equal to:

`CANONICAL_DEPARTMENT_REGISTRY.logical_values()`.

This is intentionally stronger than object identity.

A separately reconstructed but semantically identical FND-05 registry is acceptable.

A partial, modified or alternate graph is rejected.

Consequences:

```text
ALTERNATE GRAPH != CANONICAL CONTRACT AUTHORITY
OBJECT IDENTITY IS NOT REQUIRED
EXACT LOGICAL GRAPH EQUIVALENCE IS REQUIRED
```

This prevents a caller from manufacturing a permissive alternate DepartmentRegistry solely to register a forbidden FND-06 route.

---

# 13. Route validation

For each `DepartmentContractSpec`, the exact triplet:

```text
(consumer, provider, interaction_mode)
```

must already exist in the certified FND-05 dependency graph.

Mode mismatch fails closed.

Example:

If FND-05 contains:

`D18 -> D10 [S]`

then:

`D18 -> D10 [A]`

is not silently accepted.

A contract registry cannot create a new edge by configuration.

---

# 14. Registration does not grant authority

Even a valid registered route proves only:

- the semantic category is known;
- the route is constitutionally compatible;
- the version is explicit.

It does not prove:

- caller authentication;
- principal authorization;
- business preconditions;
- current state;
- freshness;
- risk approval;
- entitlement;
- delivery;
- handler success;
- evidence truth;
- execution.

```text
REGISTERED CONTRACT != AUTHORIZED INVOCATION
```

This is a critical FND-06 non-escalation rule.

---

# 15. Correlation doctrine

`CorrelationId` already exists in QORE domain foundations.

FND-06 freezes:

- cross-department work must preserve an explicit correlation identity when it participates in a larger workflow;
- a root workflow may establish its correlation identity explicitly at its certified boundary;
- FND-06 does not introduce implicit UUID generation for correlation;
- correlation only groups related work.

```text
CORRELATION != CAUSATION
CORRELATION != AUTHORIZATION
```

---

# 16. Causation doctrine

`CausationId` already exists.

FND-06 freezes:

- when one cross-department message materially causes another message/evidence publication, the later domain contract must retain an explicit causal link where the owning contract requires it;
- a root occurrence may legitimately have no prior causation ID;
- a causation ID proves a declared message relationship, not computational derivation.

```text
CAUSATION ID != COMPUTATIONAL DERIVATION
```

Research lineage remains subject to its stronger producer/derivation rules.

---

# 17. Idempotency / duplicate doctrine

`IdempotencyKey` already exists for generic commands.

FND-01 requires idempotency/deduplication semantics **where needed**.

FND-06 therefore does not force one global rule such as:

`EVERY MESSAGE MUST HAVE IDEMPOTENCY KEY`.

Instead:

- side-effecting command contracts must explicitly define duplicate semantics when retry/replay is possible;
- replayable async event/evidence consumers must define deduplication/idempotency semantics where duplicate delivery could change outcome;
- read-only query repetition is not automatically a mutation-idempotency problem;
- transport retry policy cannot invent business idempotency.

Detailed durable replay/ordering/loop-containment implementation remains downstream.

---

# 18. Version vs state revision

FND-06 `DepartmentContractVersion` versions the logical contract schema/meaning.

It is not a mutable business-state revision.

```text
CONTRACT VERSION != AGGREGATE REVISION
CONTRACT VERSION != FRESHNESS
```

State revision, freshness, concurrency and reconciliation belong to FND-07.

This separation prevents FND-06 from prematurely defining universal state storage semantics.

---

# 19. Evidence references

Existing QORE domains contain opaque evidence-reference types.

FND-06 does not replace them with one universal `EvidenceRef`.

Rules:

- a reference must remain within the semantics of the owning evidence contract;
- opaque reference text must not contain secrets;
- reference existence alone does not prove retained bytes/content;
- hash existence alone does not prove retained source evidence;
- evidence consumers cannot mutate source facts by virtue of possessing a reference.

```text
REFERENCE ID != RETAINED SOURCE EVIDENCE
HASH != RETAINED SOURCE EVIDENCE
```

---

# 20. Exact FND-05 route summary inherited by FND-06

FND-06 inherits 70 canonical FND-05 edges.

Grouped by consumer:

```text
D05 Market Data
  -> D03 [A]
  -> D04 [S]
  -> D06 [S]

D07 Valuation
  -> D04 [S]
  -> D05 [A]
  -> D06 [S]

D08 Account / Portfolio
  -> D04 [S]
  -> D07 [A]
  -> D11 [A]

D09 Risk
  -> D04 [S]
  -> D05 [A]
  -> D07 [A]
  -> D08 [S]
  -> D11 [A]

D10 Order / Execution
  -> D03 [S]
  -> D04 [S]
  -> D08 [S]
  -> D09 [S]

D11 Post-Trade
  -> D03 [S]
  -> D04 [S]
  -> D08 [A]
  -> D10 [S]

D12 Research
  -> D04 [S]
  -> D05 [A]
  -> D06 [S]

D13 Decision Intelligence
  -> D04 [S]
  -> D05 [A]
  -> D06 [S]
  -> D07 [A]
  -> D08 [A]
  -> D12 [A]

D14 Lineage / Validation
  -> D05 [A]
  -> D12 [A]
  -> D13 [A]

D16 Distributed Runtime / Cloud
  -> D02 [S]
  -> D08 [S]
  -> D15 [A]
  -> D21 [A]

D17 Signal Distribution
  -> D02 [S]
  -> D13 [S]
  -> D15 [A]
  -> D21 [S]

D18 Client Execution
  -> D02 [S]
  -> D08 [S]
  -> D09 [S]
  -> D10 [S]
  -> D16 [S]
  -> D17 [S]
  -> D21 [S]

D19 Client Read Models / Widget
  -> D08 [A]
  -> D11 [A]
  -> D15 [A]
  -> D16 [A]
  -> D18 [A]
  -> D21 [A]

D20 Executive Control
  -> D01 [S]
  -> D02 [S]
  -> D15 [A]

D21 Commercial Entitlements
  -> D02 [S]

D22 Compliance / Audit
  -> D01 [A]
  -> D14 [A]
  -> D15 [A]
  -> D21 [A]

D23 Notifications
  -> D15 [A]
  -> D19 [A]
  -> D21 [A]

D24 Certification Gate
  -> D01 [A]
  -> D14 [A]
  -> D15 [A]
  -> D22 [A]
```

D01, D02, D03, D04, D06 and D15 currently have no outgoing FND-05 dependency edges.

That means they may be providers/owners to other consumers; it does not mean they publish no messages.

---

# 21. Route exists != concrete business contract exists

The 70 FND-05 edges are **allowable constitutional dependencies**.

FND-06 does not assert that every edge already has:

- a concrete command class;
- a query class;
- an event class;
- an evidence schema.

A test fixture may instantiate all four semantic kinds on representative valid routes to prove registry mechanics.

Those fixtures are not production contract declarations.

```text
TEST FIXTURE != CANONICAL BUSINESS CONTRACT INVENTORY
```

Concrete per-domain contracts continue to require repository evidence and domain-owner implementation/certification.

---

# 22. Forbidden authority laundering

The registry must reject examples such as:

- D19 Widget -> D10 Execution command authority;
- D21 Commercial -> D13 Decision strategy authority;
- D12 Research -> D10 direct execution authority;
- D15 Observability -> D08 account write authority;
- D16 Cloud -> D13 strategy authority.

Those routes are absent from FND-05.

Therefore they cannot be legalized merely by creating a FND-06 descriptor.

---

# 23. D15 observability rule

D15 may own:

- telemetry projections;
- reliability state;
- incident evidence.

Other departments can consume D15 output where FND-05 permits it.

D15 cannot acquire source-domain write authority because it observed telemetry.

```text
OBSERVATION != CANONICAL MUTATION AUTHORITY
```

FND-06 does not create a generic observability command backdoor.

---

# 24. D14 lineage / validation rule

D14 may consume and produce lineage/statistical/validation evidence under its domain contracts.

It cannot turn EVIDENCE into direct D10 execution authority.

```text
VALIDATION EVIDENCE != TRADING AUTHORITY
```

Any promotion path must traverse the certified strategic/governance chain.

---

# 25. D22 compliance rule

Compliance may later constrain, block, report or require governed controls where certified contracts authorize those actions.

It cannot become D13 strategy origin by calling an ordinary contract descriptor a command.

```text
COMPLIANCE CONSTRAINT AUTHORITY != STRATEGY ORIGINATION
```

---

# 26. D16 Cloud rule

D16 owns QORE Cloud operational fabric under the certified FND-05 amendment.

FND-06 permits operational contracts only on certified D16 routes.

A healthy runtime, placement or lease fact cannot become trading intent.

```text
HOSTING CAPACITY != TRADING INTENT
HEALTHY != EXECUTION AUTHORITY
```

The D18 -> D16 route permits Client Execution to consume valid runtime/lease capability; it does not permit D16 to originate D13 strategy.

---

# 27. D19 Widget rule

All certified D19 dependencies are asynchronous.

The Widget/read-model side may consume projections/events/evidence.

It cannot create a new command route to D10 because no D19 -> D10 FND-05 edge exists.

```text
WIDGET != EXECUTION
```

---

# 28. D21 commercial rule

D21 is a provider of commercial/entitlement facts to permitted consumers.

It cannot become D13 strategy or D10 execution authority.

```text
BILLING != CORE AUTHORITY
ENTITLEMENT != CORE DECISION
```

---

# 29. D24 certification rule

D24 consumes governance, validation, observability and compliance evidence through async dependencies.

Certification evidence does not make D24 the writer of source-domain facts.

D24 cannot self-certify implementation it authored/directed.

FND-06 does not weaken the independent-review doctrine.

---

# 30. Sync semantics

`DepartmentInteractionMode.SYNCHRONOUS` means a logical authority dependency must be satisfied at the relevant decision boundary.

It does not require a network RPC.

Possible future physical realizations may include:

- same-process call;
- local replicated certified state;
- colocated service;
- remote request;
- another certified mechanism.

FND-06 freezes no transport.

```text
SYNCHRONOUS != REMOTE
```

---

# 31. Async semantics

`ASYNCHRONOUS` means the consuming department need not synchronously block the producing/provider department for that interaction.

It does not mean:

- unordered forever;
- duplicate-safe by default;
- infinitely replayable without policy;
- loop-safe by default;
- stale state is acceptable.

Async feedback still requires domain-specific causal, idempotency, ordering, replay and loop-containment semantics.

Detailed distributed enforcement belongs to FND-07 and later implementation tracks.

---

# 32. Determinism

New typed foundation uses:

- frozen dataclasses;
- slots;
- explicit string identities;
- explicit versions;
- typed enums;
- explicit DepartmentIds;
- no wall clock;
- no implicit UUID;
- no random source;
- no network;
- no mutable global state.

Registry `logical_values()` sorts contracts deterministically and includes the exact logical material of the FND-05 graph.

Declaration order therefore does not alter canonical registry logical values.

---

# 33. Runtime type safety

FND-05 correction R1 proved that static type annotations alone are insufficient for constitutional runtime invariants.

FND-06 therefore performs explicit runtime type checks on:

- contract ID wrapper;
- version wrapper;
- kind enum;
- consumer DepartmentId;
- provider DepartmentId;
- interaction mode;
- department registry;
- contract tuple;
- contract tuple members;
- public lookup/filter parameters.

Raw strings such as:

- `"D18"`;
- `"command"`;
- `"synchronous"`;

must fail closed when supplied where typed values are required.

---

# 34. Security / secret hygiene

Contract identity/version values are restricted canonical identifiers.

The new descriptor carries no arbitrary metadata, credentials, tokens, secrets, payload or free-form evidence body.

That deliberately reduces the risk of using the constitutional registry as a secret-carrying transport.

Payload/security schemas remain in their owning domain boundaries.

```text
CONTRACT REGISTRY != SECRET STORE
```

---

# 35. Compatibility with existing command semantics

`src/qore/domain/commands.py` remains unchanged.

Existing command subclasses/handlers continue to work.

A future department contract may reference the logical class/route of an existing command without forcing that command to inherit a second base envelope.

FND-06 avoids multiple-inheritance or envelope-wrapping requirements.

---

# 36. Compatibility with existing event semantics

`src/qore/domain/events.py` and `src/qore/kernel/domain_event.py` remain unchanged.

Existing `BusinessDomainEvent` remains the business-event foundation.

FND-06 does not change its payload or dispatch semantics.

---

# 37. Compatibility with MessageBus

Current MessageBus remains an internal deterministic dispatcher.

FND-06 registry may later be consulted by composition/adapters, but this stage does not modify MessageBus.

No claim is made that MessageBus enforces the department registry today.

```text
FOUNDATION EXISTS != ALL RUNTIMES ALREADY COMPOSE IT
```

---

# 38. Compatibility with external ports

External ports retain adapter/source/port identity.

A provider adapter may implement a capability needed by a department, but that external identity does not become the department contract identity.

```text
EXTERNAL SOURCE != DEPARTMENT PROVIDER AUTHORITY
```

Department authority remains governed by D01..D24 ownership and per-domain contracts.

---

# 39. Compatibility with executive command/query contracts

Existing D20 executive command/query ports remain more specific and stronger than the generic FND-06 route descriptor.

FND-06 does not replace:

- executive principal authorization;
- authority version;
- exact read scope;
- executive receipts;
- read delivery binding;
- sanitized evidence refs.

Generic route compatibility cannot bypass those D20-specific requirements.

---

# 40. FND-07 boundary

FND-06 intentionally does not universalize:

- mutable aggregate revision;
- freshness deadline;
- staleness state;
- concurrency control;
- atomic reservation;
- single-writer lease semantics;
- reconciliation source;
- split-brain recovery;
- durable ordering;
- exactly-once delivery.

Those belong to FND-07 distributed state/freshness/concurrency/reconciliation doctrine.

FND-06 only ensures the contract has an unambiguous constitutional route and semantic class/version.

---

# 41. Temporal obligation

`GAP-FND04-TIME-01` remains OPEN under D06.

FND-06 does not mass-rewrite legacy timestamp serialization.

The new typed foundation introduces no timestamp field, so it does not add another temporal serialization policy.

FND-08 remains unable to broadly certify temporal determinism while required TIME-01 remediation remains unresolved.

---

# 42. PR #298

PR #298 remains HOLD.

FND-06 does not promote it.

Its future provider/account/server scope work belongs to the certified D03/D04 path and must be reconciled with the cross-department contracts after this foundation closes.

No typed FND-06 descriptor may convert provider-native identifiers into canonical department or economic identity.

---

# 43. Adversarial case matrix

## FND06-CASE-01 — Raw contract kind

Attempt: `kind="command"`.

Required: typed fail-closed rejection.

## FND06-CASE-02 — Raw department identity

Attempt: `consumer="D18"` or `provider="D10"`.

Required: typed fail-closed rejection.

## FND06-CASE-03 — Raw interaction mode

Attempt: `mode="synchronous"`.

Required: typed fail-closed rejection before route validation.

## FND06-CASE-04 — Alternate department graph

Attempt: construct a valid but noncanonical DepartmentRegistry and bind contracts to it.

Required: reject because logical graph material does not match canonical FND-05 registry.

## FND06-CASE-05 — Reconstructed identical graph

Attempt: reconstruct a separate DepartmentRegistry object with exact canonical logical values.

Required: accept; authority is based on certified logical material, not Python object identity.

## FND06-CASE-06 — Route absent

Attempt: register a contract on a consumer/provider pair absent from FND-05.

Required: reject.

## FND06-CASE-07 — Interaction-mode mismatch

Attempt: same known pair but use an uncertified mode.

Required: reject.

## FND06-CASE-08 — Duplicate id/version

Attempt: register two different specs under the same `(contract_id, version)`.

Required: reject ambiguity.

## FND06-CASE-09 — Explicit version coexistence

Attempt: register `1.0` and `2.0` of the same logical contract ID.

Required: allowed when both exact versions are explicit; no implicit latest selection.

## FND06-CASE-10 — Widget authority laundering

Attempt: D19 -> D10 COMMAND.

Required: reject because no FND-05 route exists.

## FND06-CASE-11 — Billing strategy laundering

Attempt: D21 -> D13 COMMAND.

Required: reject.

## FND06-CASE-12 — Research direct execution

Attempt: D12 -> D10 COMMAND.

Required: reject.

## FND06-CASE-13 — Observability writer escalation

Attempt: D15 -> D08 COMMAND.

Required: reject.

## FND06-CASE-14 — Cloud strategy escalation

Attempt: D16 -> D13 COMMAND.

Required: reject.

## FND06-CASE-15 — Event consumer becomes writer

Attempt: infer that receiving an event allows consumer to mutate provider-owned source fact.

Required: reject doctrinally; event consumption does not transfer fact ownership.

## FND06-CASE-16 — Evidence consumer becomes source owner

Attempt: infer that D24/D22/D14 evidence consumption grants source-domain write authority.

Required: reject.

## FND06-CASE-17 — Contract descriptor treated as authorization token

Attempt: valid registry spec used as proof that a concrete request is authorized.

Required: reject; authorization remains domain-specific.

## FND06-CASE-18 — Sync means network RPC

Attempt: require remote service call solely because mode=SYNCHRONOUS.

Required: reject architectural assumption.

## FND06-CASE-19 — Async means duplicate-safe

Attempt: omit idempotency/deduplication because mode=ASYNCHRONOUS.

Required: reject; duplicate semantics remain explicit per contract/domain.

## FND06-CASE-20 — Evidence reference treated as retained evidence

Attempt: use opaque reference/hash alone as proof retained source content exists.

Required: reject.

---

# 44. Minimum-delta decision

Candidate implementation delta is intentionally limited to:

1. one additive typed domain module;
2. one additive adversarial test module;
3. this architecture artifact.

No existing certified production module is modified.

Why code is required:

- canonical graph equivalence is machine-verifiable;
- route membership is machine-verifiable;
- exact mode membership is machine-verifiable;
- runtime enum/DepartmentId integrity is machine-verifiable;
- duplicate contract identity/version is machine-verifiable;
- deterministic registry material is machine-verifiable.

Why more code is **not** justified:

- generic Command already exists;
- BusinessDomainEvent already exists;
- Result already exists;
- D20 query precedent already exists;
- evidence schemas are domain-specialized;
- no transport is selected;
- FND-07 state semantics are not yet authorized.

Verdict:

```text
MINIMUM TYPED ROUTE/SEMANTIC REGISTRY IS REQUIRED.
NEW UNIVERSAL PAYLOAD/TRANSPORT ENVELOPES ARE NOT JUSTIFIED.
```

---

# 45. Test obligations

The candidate test suite must prove at minimum:

- exact four semantic kinds;
- canonical ID/version validation;
- deterministic logical values;
- representative valid COMMAND/QUERY/EVENT/EVIDENCE routes;
- reconstructed canonical graph accepted;
- alternate graph rejected;
- absent route rejected;
- mode mismatch rejected;
- service-plane/authority-inversion attempts rejected;
- duplicate id/version rejected;
- explicit multiple versions supported;
- exact lookup fail closed;
- deterministic filtering/sorting;
- declaration-order-independent logical values;
- raw runtime types rejected;
- self-route rejected;
- wrong container/member types rejected;
- raw public filter types rejected.

The new module should reach 100% statement coverage before independent review unless a documented unreachable defensive path is proven.

---

# 46. Non-claims

This candidate does **not** claim:

- all 70 dependency edges already have concrete business contracts;
- all commands have universal idempotency rules;
- a generic Query payload now exists;
- one universal evidence payload exists;
- MessageBus is a distributed bus;
- remote RPC is required for synchronous dependencies;
- Kafka/NATS/RabbitMQ is selected;
- gRPC/HTTP is selected;
- database/consensus/event sourcing/CQRS/Saga is selected;
- exactly-once delivery exists;
- distributed state concurrency is solved;
- FND-07 is implemented;
- GAP-FND04-TIME-01 is closed;
- PR #298 is promotable;
- productive QORE Cloud exists;
- real capital is authorized.

---

# 47. Compatibility / blast-radius target

Expected blast radius:

- additive architecture doc;
- additive `src/qore/domain/department_contracts.py`;
- additive `tests/domain/test_department_contracts.py`;
- no changes to `departments.py`;
- no changes to `commands.py`;
- no changes to `events.py`;
- no changes to `message_bus.py`;
- no changes to kernel contracts/result/domain_event;
- no changes to infrastructure ports;
- no changes to executive ports;
- no changes to UMI-02;
- no changes to PR #298.

Any expansion beyond that must be justified by new evidence.

---

# 48. Certification gate

This artifact and its typed foundation remain a candidate until the exact PR head passes:

```text
EXACT-HEAD QUALITY GATE
-> DIFF / BLAST-RADIUS AUDIT
-> INDEPENDENT ADVERSARIAL ARCHITECTURE + CODE REVIEW
-> CORRECTION IF REQUIRED
-> NEW EXACT HEAD
-> NEW QUALITY GATE
-> INDEPENDENT RE-REVIEW
-> INTEGRATION GATE
-> VERIFY MAIN NO DRIFT
-> EXPECTED-HEAD MERGE
-> VERIFY ACTUAL MERGE COMMIT
-> VERIFY POST-MERGE MAIN
-> FREEZE NEW CERTIFIED BASELINE
-> CLOSE ISSUE #314 / FND-06
```

Only after that may FND-07 begin.

---

# 49. Required independent-review focus

Independent review must specifically attempt to falsify:

1. whether a contract registry can bind to a noncanonical graph;
2. whether a forbidden FND-05 route can be registered;
3. whether mode mismatch can be hidden;
4. whether raw StrEnum/string values can bypass validation;
5. whether a contract descriptor can be mistaken for invocation authorization;
6. whether EVENT/EVIDENCE direction is confused with physical delivery direction;
7. whether multiple versions create ambiguous implicit resolution;
8. whether generic registry semantics duplicate existing command/event/query/evidence foundations;
9. whether FND-07 state semantics were accidentally pulled forward;
10. whether service-plane departments can acquire D13/D10 authority through the new abstraction.

No reviewer may approve based solely on CI green.

---

# 50. Candidate closure condition

FND-06 may close only if evidence proves:

```text
THE CROSS-DEPARTMENT CONTRACT CLASS IS EXPLICIT,
THE CONTRACT IDENTITY/VERSION IS EXPLICIT,
THE CONSUMER/PROVIDER AUTHORITY ROUTE IS EXPLICIT,
THE ROUTE EXISTS IN THE EXACT CANONICAL FND-05 GRAPH,
THE INTERACTION MODE MATCHES,
MALFORMED TYPES FAIL CLOSED,
NO GENERIC CONTRACT DESCRIPTOR GRANTS BUSINESS AUTHORITY,
AND NO TRANSPORT/STATE TECHNOLOGY WAS PREMATURELY FROZEN.
```

Until then:

**STAGE-06 / FND-06 REMAINS OPEN.**
