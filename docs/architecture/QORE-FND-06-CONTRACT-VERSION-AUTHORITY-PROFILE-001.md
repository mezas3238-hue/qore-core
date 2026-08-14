# QORE-FND-06-CONTRACT-VERSION-AUTHORITY-PROFILE-001

## Status

**STAGE-06 / FND-06 — PRE-REVIEW NORMATIVE ALIGNMENT; CERTIFICATION PENDING**

Tracking: Issue #314  
PR: #315  
Certified starting baseline: `a5545da0ba7361a50daa7adb9bcfb3cf04bdb41b`

This artifact is a normative companion to:

`QORE-FND-06-CROSS-DEPARTMENT-CONTRACTS-001`

It freezes one rule already implemented and tested in the FND-06 typed candidate before the first independent review.

If wording in the primary FND-06 artifact could be read to permit a conflicting interpretation, this companion rule governs.

---

# 1. Problem

`DepartmentContractVersion` versions one logical contract identity.

The candidate intentionally allows more than one explicit version of the same `DepartmentContractId` to coexist.

Without an additional invariant, a caller could attempt to reuse one stable contract ID while changing its constitutional meaning across versions, for example:

```text
v1:
contract_id = client-execution.order-apply
kind        = COMMAND
consumer    = D18
provider    = D10
mode        = SYNCHRONOUS

v2:
contract_id = client-execution.order-apply
kind        = QUERY
consumer    = D18
provider    = D09
mode        = SYNCHRONOUS
```

Both routes might individually be valid FND-05 routes, yet the same logical contract identity would now mean different authority relationships depending on version.

That ambiguity is forbidden.

---

# 2. Normative invariant

For every `DepartmentContractId`, all registered versions MUST preserve the exact authority profile:

```text
(
  DepartmentContractKind,
  consumer DepartmentId,
  provider DepartmentId,
  DepartmentInteractionMode,
)
```

Therefore:

```text
SAME CONTRACT ID
-> SAME KIND
-> SAME CONSUMER
-> SAME PROVIDER
-> SAME INTERACTION MODE
```

A change to any of those four dimensions is not merely a new schema revision.

It is a different constitutional contract identity and therefore requires a new `DepartmentContractId`.

---

# 3. What a version may change

FND-06 does not attempt to enumerate every future schema-compatible or schema-breaking change.

A version may represent an explicitly governed evolution of the logical contract while preserving its authority profile.

Examples of material that future domain-specific version policy may govern include:

- payload schema;
- required fields;
- response schema;
- evidence schema;
- validation rules;
- domain-specific semantic refinements.

FND-06 does not certify those changes automatically.

The invariant only freezes the constitutional boundary that may NOT drift under one ID.

---

# 4. Version is not authority indirection

```text
CONTRACT VERSION != AUTHORITY ROUTE SELECTOR
CONTRACT VERSION != DEPARTMENT SELECTOR
CONTRACT VERSION != INTERACTION-MODE SELECTOR
CONTRACT VERSION != CONTRACT-KIND SELECTOR
```

Consumers must not interpret a newer version as permission to redirect authority to another department.

---

# 5. Exact lookup remains mandatory

Multiple versions of one stable contract ID may coexist only when each version is explicitly registered and the authority profile is identical.

There is no implicit:

- latest version;
- compatible version;
- fallback version;
- best-effort version.

Lookup remains exact:

```text
(contract_id, version)
```

---

# 6. Implementation evidence

The FND-06 candidate `DepartmentContractRegistry` constructs an authority profile for each `DepartmentContractId`:

```text
(kind, consumer, provider, mode)
```

The first registered version establishes that ID's profile within the registry.

Any later version of the same ID whose profile differs is rejected with `DepartmentContractValidationError`.

This validation occurs before route acceptance can make the conflicting version part of a valid registry.

---

# 7. Test evidence requirement

The candidate test suite must prove both directions:

1. two explicit versions of one `DepartmentContractId` with the same authority profile are accepted;
2. a later version changing `kind`, `consumer`, `provider`, or `mode` is rejected.

A test that checks only duplicate `(id, version)` rejection is insufficient.

---

# 8. Relationship to FND-05

FND-05 remains the route upper bound.

This rule is stronger than merely checking that each version independently points to some valid FND-05 edge.

A contract identity must remain stable even when two different candidate routes are each individually permitted elsewhere in the graph.

Therefore:

```text
EACH VERSION HAS A VALID ROUTE
!=
ONE CONTRACT ID HAS A STABLE AUTHORITY MEANING
```

Both properties are required.

---

# 9. Non-claims

This companion does not define:

- SemVer;
- backward compatibility;
- schema migration machinery;
- wire negotiation;
- deployment negotiation;
- deprecation periods;
- state revision;
- freshness;
- distributed consensus;
- transport selection.

Those require later evidence and/or domain-specific contracts.

---

# 10. Certification rule

The FND-06 candidate may not be certified unless independent review confirms:

```text
A STABLE DepartmentContractId CANNOT CHANGE
KIND,
CONSUMER,
PROVIDER,
OR INTERACTION MODE
MERELY BY CHANGING DepartmentContractVersion.
```

This companion is part of the exact-head candidate composition submitted for the first FND-06 independent review.
