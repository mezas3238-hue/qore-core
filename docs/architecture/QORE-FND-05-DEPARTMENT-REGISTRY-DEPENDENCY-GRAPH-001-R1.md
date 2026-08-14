# QORE-FND-05-DEPARTMENT-REGISTRY-DEPENDENCY-GRAPH-001-R1

## Status

`INTEGRATION GATE CORRECTION R1 — CERTIFICATION PENDING`

This artifact is an append-only normative correction to:

`QORE-FND-05-DEPARTMENT-REGISTRY-DEPENDENCY-GRAPH-001`.

On conflict, this R1 artifact governs.

The first independent review of PR #313 on exact head
`cd9f6b939075b3be249c39e98c3948931a347881` returned:

`READY FOR STAGE-05 / FND-05 CERTIFICATION — VERIFIED`.

That review remains useful historical evidence, but its READY verdict is not a
current certification verdict because the Integration Gate independently found a
material fail-closed defect after review.

`cd9f6b939075b3be249c39e98c3948931a347881` is therefore HISTORICAL ONLY.

No merge is authorized by this document.

---

## R1-01 — runtime type integrity is part of the constitutional graph boundary

The original implementation relied on Python type annotations plus mypy for the
runtime types of:

- `DepartmentSpec.department_id`;
- `DepartmentSpec.slug`;
- `DepartmentSpec.canonical_name`;
- `DepartmentDependency.consumer`;
- `DepartmentDependency.provider`;
- `DepartmentDependency.mode`;
- `DepartmentRegistry.departments`;
- `DepartmentRegistry.dependencies`;
- `DepartmentRegistry.spec(...)` input;
- `DepartmentRegistry.dependencies_for(...)` inputs.

The Integration Gate determined that this was insufficient for a constitutional
fail-closed contract.

Python dataclasses do not enforce annotations at runtime.

The material defect was not merely hypothetical future deserialization.
A raw string such as:

`"synchronous"`

could be passed as the runtime value of `DepartmentDependency.mode`.

The synchronous graph resolver intentionally selects edges with identity against:

`DepartmentInteractionMode.SYNCHRONOUS`.

A raw string therefore could fail to enter the synchronous subgraph instead of
failing closed at construction time.

That creates a path by which malformed authority material could bypass the very
synchronous-cycle validation FND-05 exists to guarantee.

Normative rule:

`TYPE ANNOTATION != RUNTIME VALIDATION`

`MALFORMED DEPARTMENT TYPE -> FAIL CLOSED`

`MALFORMED INTERACTION MODE -> FAIL CLOSED BEFORE GRAPH RESOLUTION`

`NO MALFORMED EDGE MAY SILENTLY FALL OUT OF THE SYNCHRONOUS SUBGRAPH`

The production correction therefore adds explicit runtime validation for the
contract fields and public registry lookup/filter inputs listed above.

This is a correction of contract integrity, not an external-input feature.

---

## R1-02 — D15 telemetry publication direction is distinct from dependency direction

The canonical Department Dependency Graph uses:

`CONSUMER -> PROVIDER`

A dependency such as:

`D16 -> D15 [A]`

means:

D16 consumes governed reliability/incident state owned by D15.

It does **not** mean that telemetry physically flows only from D15 to D16.

D16 may publish infrastructure telemetry/evidence that D15 observes or aggregates.
That operational publication direction is a separate concern from the canonical
authority dependency represented by the FND-05 graph.

Likewise:

`D17 -> D15 [A]`

means D17 consumes D15 reliability/incident state. It does not erase D17's ability
to publish signal-distribution telemetry for D15 observation.

Normative rules:

`DEPENDENCY CONSUMPTION DIRECTION != TELEMETRY PUBLICATION DIRECTION`

`OBSERVATION != WRITE AUTHORITY`

`D15 RELIABILITY OUTPUT MAY BE CONSUMED WITHOUT D15 OWNING SOURCE BUSINESS FACTS`

No additional reverse dependency is implied merely by telemetry publication.
FND-06/FND-07 may later type the publication/evidence contracts.

---

## R1-03 — additional adversarial cases

### FND05-CASE-19 — observability writer escalation

Attempted condition:

D15 observes telemetry or health state and is then treated as the canonical
writer of the source domain fact.

Required result:

`REJECTED`

Rules:

`OBSERVATION != CANONICAL MUTATION AUTHORITY`

`HEALTHY != EXECUTION AUTHORITY`

`READ MODEL != WRITE AUTHORITY`

D15 may own telemetry projections, reliability state and incident evidence.
It does not acquire ownership of D08 account facts, D09 Risk facts, D10 execution
facts, D13 decisions, D16 execution leases, or any other source-domain fact merely
by observing them.

### FND05-CASE-20 — research / lineage self-promotion

Attempted condition:

D12 Research or D14 Lineage/Validation output is treated as direct D10 execution
authority without the governed Decision Intelligence / signal / execution chain.

Required result:

`REJECTED`

Rules:

`RESEARCH RESULT != TRADING AUTHORITY`

`VALIDATION EVIDENCE != TRADING AUTHORITY`

`LINEAGE EVIDENCE != ORDER ORIGIN`

Research and validation may inform or qualify D13 decision production under later
contracts, but they cannot bypass the canonical strategic and execution authority
chain.

---

## R1-04 — additional forbidden reverse-authority entries

The following are explicitly frozen as forbidden:

### D12 Research -> D10 Execution as direct trading authority

`FORBIDDEN`

Research evidence, replay outputs, statistical results or hypothesis products do
not directly authorize orders.

### D14 Lineage / Validation -> D10 Execution as direct trading authority

`FORBIDDEN`

Lineage, certification, validation or statistical evidence does not directly
originate execution.

### D22 Compliance -> D13 Decision Intelligence as strategy authority

`FORBIDDEN`

Compliance may constrain, block, report or require governed controls when later
contracts authorize such behavior. It does not invent BUY/SELL strategy or become
CIO/CIBO/Specialized-Trader decision authority.

These additions strengthen explicit doctrine. They do not create new production
edges in FND-05.

---

## R1-05 — first independent review classification

Claude's first independent review correctly verified many properties of exact head
`cd9f6b939075b3be249c39e98c3948931a347881`, including the 24-department identity,
canonical edge direction, synchronous acyclicity, minimum-delta architecture and
QORE-owned Cloud ownership model.

However, its `OBS-FND05-01` classified runtime type validation as non-blocking.
The Integration Gate rejects that classification for FND-05 because malformed
`DepartmentInteractionMode` material could bypass synchronous-edge participation
instead of failing closed.

Therefore:

`CLAUDE FIRST READY VERDICT -> HISTORICAL ONLY`

`INTEGRATION GATE FINDING-FND05-IG-01 -> BLOCKING ON cd9f6b93...`

`CORRECTION -> SAME BRANCH -> NEW EXACT HEAD -> NEW CI -> INDEPENDENT RE-REVIEW`

No finding is considered closed until the corrected exact head is mechanically
green and independently re-reviewed.

---

## R1-06 — unchanged boundaries

This correction does not change:

- the 24 canonical DepartmentIds;
- canonical department names;
- ownership assignments;
- dependency edge direction;
- the canonical dependency edge set;
- synchronous/asynchronous classification of existing canonical edges;
- QORE-owned Cloud/Hosting/VPS direction;
- mobile-only hosted-client doctrine;
- at-most-one active fenced execution authority per TradingAccountId doctrine;
- PR #298 HOLD status;
- GAP-FND04-TIME-01 OPEN status;
- FND-06/FND-07/FND-08 sequencing.

No productive Cloud/VPS, real-capital or provider authority is introduced.

---

## Required correction gate

Before FND-05 certification:

1. exact corrected PR head must be frozen;
2. `ruff check .` must pass;
3. `mypy src tests` must pass;
4. `pytest --cov=src/qore --cov-report=term-missing` must pass;
5. runtime malformed-type tests must prove fail-closed behavior;
6. full base-to-head blast radius must be re-audited;
7. independent correction re-review must evaluate `FINDING-FND05-IG-01`;
8. only then may the Integration Gate reconsider READY state and merge.

`NO NEW EXACT-HEAD GREEN CI -> NO RE-REVIEW APPROVAL`

`NO INDEPENDENT CORRECTION RE-REVIEW -> NO MERGE`
