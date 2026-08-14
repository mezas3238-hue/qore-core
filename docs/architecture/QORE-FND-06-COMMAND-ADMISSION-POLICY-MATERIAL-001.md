# QORE-FND-06-COMMAND-ADMISSION-POLICY-MATERIAL-001

## Status

**STAGE-06 / FND-06 — PRE-REVIEW NORMATIVE HARDENING; CERTIFICATION PENDING**

Tracking: Issue #314  
PR: #315  
Certified starting baseline: `a5545da0ba7361a50daa7adb9bcfb3cf04bdb41b`

This artifact supplements:

- `QORE-FND-06-CROSS-DEPARTMENT-CONTRACTS-001`;
- `QORE-FND-06-COMMAND-ROUTE-ADMISSION-001`;
- `QORE-FND-06-CONTRACT-VERSION-AUTHORITY-PROFILE-001`.

If wording conflicts, this supplement governs the logical-material treatment of
COMMAND admission policy.

---

## 1. Problem

`CANONICAL_DEPARTMENT_COMMAND_ROUTES` is part of the constitutional decision that
determines whether a valid FND-05 dependency route may be registered as
`DepartmentContractKind.COMMAND`.

Therefore it is not implementation-only configuration.

If a registry's canonical logical material contained only:

- the FND-05 DepartmentRegistry; and
- the concrete DepartmentContractSpec values;

then a later software version could change COMMAND admission policy while the same
registry instance material continued to produce identical logical values.

That would make reproducibility incomplete.

A consumer comparing fingerprints/evidence could not prove which COMMAND policy was
in force when the registry was constructed.

---

## 2. Governing rule

```text
COMMAND ADMISSION POLICY IS CANONICAL LOGICAL MATERIAL
POLICY CHANGE != SAME REGISTRY LOGICAL IDENTITY
```

`DepartmentContractRegistry.logical_values()` must therefore retain:

1. exact canonical FND-05 graph material;
2. exact canonical COMMAND-capable route policy material;
3. exact registered contract material.

---

## 3. Canonical representation

The COMMAND policy is represented deterministically as sorted tuples of:

```text
consumer DepartmentId value
provider DepartmentId value
DepartmentInteractionMode value
```

For the initial FND-06 candidate:

```text
("D18", "D10", "synchronous")
("D20", "D01", "synchronous")
```

No object identity, clock, UUID, insertion order or mutable global state participates
in this material.

---

## 4. Consequences

If a later certified change adds, removes or changes a COMMAND-capable route:

```text
DepartmentContractRegistry.logical_values()
```

must also change.

That remains true even if the currently registered concrete contracts happen not to
use the changed route.

Reason: the registry represents both registered material and the constitutional
admission policy governing what it could validly register.

---

## 5. Non-claims

Including COMMAND admission policy in logical values does not mean:

- the policy authorizes a concrete invocation;
- every command-capable route already has a concrete command ID/version;
- a logical-values tuple is retained source evidence by itself;
- a hash of the tuple proves historical bytes were retained;
- runtime authorization/freshness/risk/idempotency is solved.

The existing invariants remain:

```text
REGISTERED COMMAND != AUTHORIZED INVOCATION
HASH != RETAINED SOURCE EVIDENCE
REFERENCE ID != RETAINED SOURCE EVIDENCE
```

---

## 6. Required proof

Tests must prove the registry's logical values contain exactly the current canonical
COMMAND admission route material and remain deterministic.

The exact-head Quality Gate and independent adversarial review must verify this
supplement together with the source and other FND-06 architecture artifacts before
`FINDING-FND06-IG-01` may be considered closed.
