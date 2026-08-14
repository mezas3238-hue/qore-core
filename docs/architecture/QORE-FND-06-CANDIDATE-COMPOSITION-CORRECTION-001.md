# QORE-FND-06-CANDIDATE-COMPOSITION-CORRECTION-001

## Status

**STAGE-06 / FND-06 — INTEGRATION-GATE CORRECTION; INDEPENDENT RE-REVIEW REQUIRED**

Tracking: Issue #314  
PR: #315  
Certified starting baseline: `a5545da0ba7361a50daa7adb9bcfb3cf04bdb41b`

This artifact is an evidence-preserving normative correction to the candidate-composition statements in:

`QORE-FND-06-CROSS-DEPARTMENT-CONTRACTS-001`

Specifically, it supersedes the stale file-composition wording in primary sections:

- `# 44. Minimum-delta decision` only where that section states that the candidate contains one test module and one architecture artifact;
- `# 47. Compatibility / blast-radius target` only where that section describes the earlier three-file candidate.

All architectural semantics in the primary artifact remain in force unless a later certified amendment explicitly supersedes them.

---

## 1. Integration Gate finding

After independent code review returned `READY FOR INTEGRATION GATE` on exact head:

`000dee49adbf1292002699f17d15a5d3d08fd16e`

Integration Gate re-read the normative architecture artifacts and compared them to the live PR blast radius.

It found:

`FINDING-FND06-IG-02 — CANDIDATE COMPOSITION / BLAST-RADIUS STALENESS`

The primary architecture document still described the earlier candidate as:

```text
one additive typed domain module
one additive adversarial test module
this architecture artifact
```

and its expected blast-radius section named only that initial architecture document, source module, and one test module.

The actual exact-head candidate had already expanded through governed pre-review hardening to four architecture documents, one production module, and four test modules.

Therefore the stale primary wording was no longer an accurate exact-head composition claim.

This was a documentation-integrity defect even though the additional files were additive and within authorized FND-06 scope.

Rule:

```text
HISTORICAL MINIMUM-DELTA DESCRIPTION != CURRENT EXACT-HEAD BLAST RADIUS
NO EVIDENCE -> NO CLAIM
```

---

## 2. Why the expanded candidate remains minimum-scope

The minimum *semantic implementation* remains one additive typed domain module:

`src/qore/domain/department_contracts.py`

No second command envelope, query payload, evidence payload, transport, broker, RPC layer, database, distributed-state implementation, or FND-07 mechanism has been introduced.

The additional architecture and test files exist to preserve correction history and independently test constitutional invariants discovered during FND-06 hardening:

- stable authority profile across contract versions;
- explicit COMMAND-route admission after `FINDING-FND06-IG-01`;
- COMMAND policy as captured reproducibility material;
- runtime fail-closed validation;
- explicit duplicate/superset COMMAND-policy adversarial coverage after independent review.

Therefore:

```text
MORE REVIEW / TEST ARTIFACTS != BROADER RUNTIME AUTHORITY
ADDITIVE HARDENING != NEW PRODUCTIVE CAPABILITY
MINIMUM SEMANTIC IMPLEMENTATION != MINIMUM FILE COUNT
```

---

## 3. Current candidate composition

After this correction, the FND-06 PR candidate consists of exactly ten additive files relative to certified base, subject to live GitHub re-verification at every later gate:

### Architecture — 5 additive files

1. `docs/architecture/QORE-FND-06-CANDIDATE-COMPOSITION-CORRECTION-001.md`
2. `docs/architecture/QORE-FND-06-COMMAND-ADMISSION-POLICY-MATERIAL-001.md`
3. `docs/architecture/QORE-FND-06-COMMAND-ROUTE-ADMISSION-001.md`
4. `docs/architecture/QORE-FND-06-CONTRACT-VERSION-AUTHORITY-PROFILE-001.md`
5. `docs/architecture/QORE-FND-06-CROSS-DEPARTMENT-CONTRACTS-001.md`

### Production source — 1 additive file

6. `src/qore/domain/department_contracts.py`

### Tests — 4 additive files

7. `tests/domain/test_department_command_routes.py`
8. `tests/domain/test_department_contract_identity_versions.py`
9. `tests/domain/test_department_contracts.py`
10. `tests/domain/test_department_contracts_runtime_types.py`

No certified pre-existing source file or certified pre-existing test file is part of the intended net diff.

---

## 4. Integration Gate test hardening

The same Integration Gate pass evaluated Claude's non-blocking recommendations concerning malformed COMMAND policy material.

Because COMMAND admission is a constitutional authority boundary, the final candidate requires explicit adversarial proof for both:

```text
DUPLICATE CANONICAL COMMAND ROUTE MATERIAL -> REJECT
CANONICAL COMMAND POLICY + EXTRA ROUTE -> REJECT
```

The implementation already rejects both through exact sorted-tuple equality.

The correction adds explicit tests so these cases are no longer established only by reviewer reasoning.

This does not change production behavior.

---

## 5. Independent-review coverage correction

Claude's review of `000dee49...` explicitly stated that the architecture documents were referenced by blob hash but were not supplied as full text.

Therefore that READY verdict is valid evidence for the executable source/tests it reviewed, but it is insufficient to certify the complete normative FND-06 composition.

Rule:

```text
CODE REVIEW != COMPLETE ARCHITECTURE REVIEW
BLOB HASH != REVIEWED DOCUMENT CONTENT
```

Any new exact head created by this correction also makes the prior READY historical only.

The new candidate must receive:

- a new exact-head Quality Gate;
- one complete independent correction re-review package containing the full normative architecture text, current source, and current tests;
- a new independent verdict;
- a new Integration Gate pass.

---

## 6. Non-claims

This correction does not:

- change a DepartmentId;
- change an FND-05 dependency edge;
- add a COMMAND-capable route;
- alter `DepartmentContractRegistry` production semantics;
- authorize any invocation;
- create productive Cloud capability;
- authorize real capital;
- promote PR #298;
- close `GAP-FND04-TIME-01`;
- begin FND-07.

---

## 7. Governing corrected composition rule

```text
CURRENT FND-06 CANDIDATE COMPOSITION
= 5 ARCHITECTURE ARTIFACTS
+ 1 TYPED DOMAIN MODULE
+ 4 ADVERSARIAL TEST MODULES
= 10 ADDITIVE FILES

LIVE GITHUB COMPARE REMAINS SOURCE OF TRUTH.
```

If later exact-head evidence differs, this document must not be used to override repository reality.

FND-06 remains uncertified until independent re-review and Integration Gate both pass on the same exact head.
