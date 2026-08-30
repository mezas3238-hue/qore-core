# QORE-UMI-13-RECURSIVE-REGISTRY-REVALIDATION-001

## Status and scope

**PROGRAM D / UMI-13 — OWNER-STAGE CORRECTION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #465

Parent final audit: Issue #363

Discovery baseline: `main@5a158ef0fb2e21db95f2be0685373780bf1ab197`
Accepted finding: `UMI14-R2-UMI13-REVALIDATION-001`

This additive evidence records the bounded correction to the retained-state trust
boundary in `instrument_universe_registry.py`. It does not rewrite either the
historical 2026-08-15 inventory or the later UMI-13 full-closure ledger.

```text
EXACT RUNTIME TYPE
!= VALID RETAINED CHILD STATE

SUCCESSFUL ORIGINAL CONSTRUCTION
!= PERMANENT VALIDITY AFTER REFLECTIVE CORRUPTION

LOGICAL PROJECTION
= TRUST BOUNDARY THAT MUST REVALIDATE
```

## Accepted defect

The prior contract validated local values and exact child types during ordinary
construction, but trusted those frozen/slotted objects during later projections.
Python reflective mutation through `object.__setattr__` could therefore corrupt a
retained reason or evidence locator after construction. Re-entering snapshot
`__post_init__()` did not recursively validate the child state, and
`logical_values()` could emit credential-like material.

The accepted witness retained both:

- `token=PLAINTEXT-SECRET` in an `InstrumentUniverseReason`;
- `https://alice:password@example.invalid/evidence` in an evidence locator.

The defect is classified as a material D04 / UMI-13 canonical-evidence integrity
defect. It is not evidence of provider, operational, execution, risk, settlement or
Production readiness.

## Corrected trust edges

The correction revalidates before hashing, set construction, sorting, relationship
checks or output:

1. evidence, owner and semantic refs plus reasons re-enter their local validators in
   every `logical_values()` call;
2. evidence records revalidate their exact evidence ref and all content fields in
   `__post_init__()`, `content_logical_values()` and `logical_values()`;
3. entries revalidate the imported `IdentityFamilyCode` through its canonical UMI-02
   validator after enforcing exact class and exact plain-`str` state, then revalidate
   every local ref and reason;
4. snapshots recursively revalidate every exact entry and evidence record before
   any graph operation;
5. snapshot `logical_values()` re-enters full graph validation;
6. `entry_for_family()` revalidates both the snapshot graph and the query
   `IdentityFamilyCode` before returning a retained child.

All boundary failures remain deterministic
`InstrumentUniverseRegistryValidationError` failures. Valid tuple shapes and
canonical ordering remain unchanged.

## Permanent falsification evidence

`tests/infrastructure/test_instrument_universe_registry_recursive_revalidation.py`
uses independently written primitive expected tuples and direct reflective
corruption. It covers:

- credential material injected into a reason;
- URL userinfo injected into an evidence locator;
- corrupt evidence, owner and semantic reference codes;
- construction of new aggregates from exact children already corrupted, including an
  unhashable ref value rejected by the owner validator before hashing;
- corrupt imported `IdentityFamilyCode` state in an entry and lookup query;
- explicit `__post_init__()` re-entry;
- evidence content/full projections, entry projection, snapshot projection and
  snapshot lookup;
- unchanged valid logical output and deterministic ordering.

## Non-claims and gate

```text
THIS CORRECTION DOES NOT AUTHORIZE PRODUCTION
THIS CORRECTION DOES NOT AUTHORIZE REAL CAPITAL
THIS CORRECTION DOES NOT ESTABLISH PROVIDER OR OPERATIONAL READINESS
THIS CORRECTION DOES NOT BYPASS RISK
```

CI green is mechanical evidence only. The candidate requires exact-head quality
evidence, independent review, Integration Authority adjudication, protected merge,
post-merge quality validation and a fresh execution of parent audit #363.
