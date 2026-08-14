# QORE-FND-06-COMMAND-ROUTE-ADMISSION-001

## Status

**STAGE-06 / FND-06 — PRE-REVIEW NORMATIVE HARDENING; CERTIFICATION PENDING**

Tracking: Issue #314  
PR: #315  
Certified starting baseline: `a5545da0ba7361a50daa7adb9bcfb3cf04bdb41b`

This artifact is a normative amendment to:

- `QORE-FND-06-CROSS-DEPARTMENT-CONTRACTS-001`;
- `QORE-FND-06-CONTRACT-VERSION-AUTHORITY-PROFILE-001`.

If wording conflicts, this amendment governs the COMMAND-route admission question.

---

## 1. Finding that required hardening

Pre-review Integration Gate analysis identified:

`FINDING-FND06-IG-01 — CONTRACT-KIND AUTHORITY LAUNDERING`

Classification before correction:

**BLOCKING**.

The previous candidate validated each `DepartmentContractSpec` against the exact
FND-05 `(consumer, provider, interaction_mode)` route, but it did not additionally
restrict which routes could be registered as `DepartmentContractKind.COMMAND`.

That was insufficient because FND-05 certifies constitutional dependency routes,
not an automatic permission for every semantic contract kind on every route.

A concrete counterexample existed on the previous exact head:

```text
consumer = D19 Client Read Models / Widget
provider = D11 Post-Trade
mode = ASYNCHRONOUS
kind = COMMAND
```

`D19 -> D11 [A]` is a real certified FND-05 dependency.

Therefore the old structural registry accepted that descriptor.

But FND-05 also certifies:

```text
D19 owns presentation/read projection state only.
D19 does not own execution, Risk, account mutations, Hosting authority or strategy.
D19 accepted operations are read/presentation only.
WIDGET != EXECUTION.
```

A generic route-membership test therefore could not be treated as sufficient
admission evidence for a state-changing COMMAND class.

The same defect class applied to evidence/read-side departments such as D24: a
valid evidence dependency could have been mislabeled as a COMMAND descriptor even
though the dependency itself did not certify command authority.

Therefore:

```text
FND-05 ROUTE EXISTS != COMMAND AUTHORITY EXISTS
```

---

## 2. Why this is material

FND-06 defines COMMAND as a request to the provider/authority owner to evaluate and
possibly perform a governed state-changing action.

Consequently COMMAND is the semantic class capable of representing a request for
mutation authority.

Even though:

```text
CONTRACT REGISTRATION != INVOCATION AUTHORIZATION
```

remains true, a constitutional registry must not label an unproven COMMAND profile
as compatible merely because a generic dependency edge exists.

Otherwise a later transport/configuration layer could cite the registry as evidence
that a read/evidence route was a permitted state-changing contract route.

That would violate:

```text
READ MODEL != COMMAND AUTHORITY
NO VERIFIED CONTRACT -> NO CROSS-DEPARTMENT AUTHORITY TRANSFER
NO EVIDENCE -> NO CLAIM
```

---

## 3. Minimum correction

FND-06 now applies two gates to every COMMAND descriptor:

```text
GATE 1:
Exact (consumer, provider, mode) must exist in canonical FND-05.

GATE 2:
That exact route must also appear in the explicit canonical
COMMAND-capable route allowlist.
```

Both are required.

A route may therefore be a valid QUERY/EVENT/EVIDENCE dependency without being a
valid COMMAND dependency.

This avoids inventing a speculative 70 x 4 kind matrix while still failing closed
at the write-authority boundary.

---

## 4. Initial canonical COMMAND-capable routes

The initial allowlist is intentionally minimal:

```text
D18 Client Execution -> D10 Order / Execution [SYNCHRONOUS]
D20 Executive Control -> D01 Core Governance [SYNCHRONOUS]
```

Typed source:

`CANONICAL_DEPARTMENT_COMMAND_ROUTES`

### D18 -> D10 evidence

The certified Client Execution Agent architecture proves that D18 produces an
auditable execution plan only after Core decision, security, account, policy, risk,
entitlement and calculation gates pass.

That plan cannot contact a broker directly and must continue through the repository's
canonical downstream order/execution boundaries, including:

- `OrderIntent`;
- `PreTradeAuthorization`;
- `AuthorizedOrderIntent`;
- `ExecutionSubmission`;
- `ExecutionBoundary`;
- receipt/reconciliation controls.

Therefore D18 consuming D10's governed execution capability is a proven
command-capable cross-department route.

This does not mean every D18 -> D10 command ID/version already exists.

### D20 -> D01 evidence

The certified executive command-dispatch architecture proves dispatch of an
already-authorized `AuthorizedExecutiveControlIntent` through
`ExecutiveControlCommandPort.apply(...)` exactly once, with receipt binding and
fail-closed validation.

D20 is the governed executive control surface and D01 remains constitutional
governance authority.

Therefore D20 -> D01 is a proven command-capable route.

This does not give D20 arbitrary domain mutation authority.

---

## 5. Deliberately NOT admitted as COMMAND by route existence alone

Examples that now fail closed include:

```text
D19 -> D11 [A] + COMMAND
D19 -> D08 [A] + COMMAND
D24 -> D14 [A] + COMMAND
D24 -> D22 [A] + COMMAND
D14 -> D13 [A] + COMMAND
D22 -> D01 [A] + COMMAND
```

The underlying dependency may be valid for queries, projections, events, evidence
or other later-certified semantics.

It is not automatically a state-changing command route.

---

## 6. Future extension rule

Adding a new COMMAND-capable route requires all of the following:

1. exact route already certified in FND-05, or a separately governed FND-05 change;
2. repository evidence that the consumer may request the provider's mutation
   capability without violating department prohibitions;
3. domain-owner command semantics and failure/authorization boundaries;
4. tests proving forbidden neighboring authority does not become reachable;
5. exact-head Quality Gate;
6. independent adversarial review;
7. Integration Gate approval.

Therefore:

```text
FUTURE LEGITIMATE COMMAND != FORBIDDEN FOREVER
UNVERIFIED COMMAND ROUTE != PERMITTED BY DEFAULT
```

The allowlist is a fail-closed constitutional gate, not an artificial permanent
limitation on QORE capability.

---

## 7. QUERY / EVENT / EVIDENCE treatment

This amendment does not introduce a speculative full kind matrix.

QUERY, EVENT and EVIDENCE remain subject to:

- exact FND-05 route membership;
- exact interaction mode;
- department ownership/prohibitions;
- concrete domain-contract certification before productive use;
- `REGISTERED CONTRACT != AUTHORIZED INVOCATION`;
- `ROUTE EXISTS != CONCRETE BUSINESS CONTRACT EXISTS`.

They do not grant source-domain writer authority merely by registration.

If future evidence proves that one of those semantic classes also requires an
additional universal route-level admission matrix, that must be added through a
separate governed correction rather than inferred here.

---

## 8. Runtime enforcement

`DepartmentContractRegistry.__post_init__` now validates in this order:

1. canonical DepartmentRegistry equivalence;
2. tuple/member runtime types;
3. unique `(contract_id, version)` identity;
4. stable authority profile across versions;
5. exact FND-05 route existence;
6. if `kind is COMMAND`, exact membership in
   `CANONICAL_DEPARTMENT_COMMAND_ROUTES`.

A valid dependency route with an unadmitted COMMAND kind raises:

`DepartmentContractValidationError`

with a closed reason indicating that the command route must be explicitly
command-capable.

There is no coercion, fallback or inferred admission.

---

## 9. Required adversarial tests

Tests must prove at minimum:

- the initial command-capable allowlist is exact;
- every allowlisted command route is an actual FND-05 route;
- D18 -> D10 COMMAND remains accepted;
- a valid D19 -> D11 asynchronous dependency cannot be laundered into COMMAND;
- a valid D24 -> D14 asynchronous evidence dependency cannot be laundered into
  COMMAND;
- an absent route still fails as absent before command admission can legitimize it;
- wrong interaction mode still fails closed;
- existing exact-version/profile invariants remain unchanged.

---

## 10. Compatibility / blast radius

This correction:

- adds no department;
- changes no FND-05 edge;
- changes no existing certified contract;
- changes no provider adapter;
- changes no runtime transport;
- adds no network/storage/clock/UUID behavior;
- creates no productive Cloud capability;
- creates no trading authority;
- does not promote PR #298;
- does not close `GAP-FND04-TIME-01`;
- does not begin FND-07.

It narrows only the admission semantics of new FND-06 COMMAND descriptors.

---

## 11. Non-claims

This amendment does not claim:

- every legitimate future COMMAND route has already been enumerated;
- D18 -> D10 concrete contract IDs/versions are fully implemented;
- D20 -> D01 replaces existing executive authorization;
- QUERY/EVENT/EVIDENCE automatically have productive implementations on all FND-05
  edges;
- route admission is runtime authorization;
- command-capable route admission proves handler success or delivery.

---

## 12. Governing corrected invariants

```text
FND-05 ROUTE EXISTS != COMMAND AUTHORITY EXISTS
COMMAND REQUIRES EXPLICIT COMMAND-CAPABLE ROUTE ADMISSION
NO EXPLICIT COMMAND ROUTE -> NO FND-06 COMMAND REGISTRATION
READ MODEL DEPENDENCY != MUTATION AUTHORITY
EVIDENCE DEPENDENCY != COMMAND AUTHORITY
REGISTERED COMMAND != AUTHORIZED COMMAND INVOCATION
FUTURE LEGITIMATE COMMAND REQUIRES NEW VERIFIED EVIDENCE
```

`FINDING-FND06-IG-01` may be called CLOSED only after the corrected exact head passes
its exact-head Quality Gate and independent adversarial correction review.
