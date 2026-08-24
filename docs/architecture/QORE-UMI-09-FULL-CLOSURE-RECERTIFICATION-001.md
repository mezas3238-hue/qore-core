# QORE-UMI-09-FULL-CLOSURE-RECERTIFICATION-001

## Status

**FULL CLOSURE / UMI09 — GATE B OWNER-LOCAL CORRECTION CANDIDATE**

This record is a Full Closure recertification ledger. It does not replace the historical
UMI09 architecture record and does not claim certification, merge, seal, or closure.

Tracking anchors:

- Universal Markets / Instruments program: #301
- historical UMI09 work order: #352
- historical UMI09 integration PR: #354
- logical-identity retrospective: #405

## 1. Current serial authority

The current Full Closure predecessor is the sealed UMI08 baseline:

```text
main = a2b0ad2912ede5b0eb18865fe5b000f2572ecaa5
tree = 924f142f6d9afb7fd7765d2fa55b55250735b1d0
GitHub verification = verified=true / reason=valid
```

Gate-B working branch:

```text
agent/qore-umi09-full-closure-001
```

The branch was created exactly from the UMI08 sealed main SHA above.

## 2. Historical UMI09 certification reconstructed

UMI09 was historically certified before the current serial Full Closure regime.
That historical certification remains repository history, not the current Full Closure seal.

Historical integration:

```text
PR #354
approved candidate = 6b485c76cf3a2ffffe9e9f171f45eec9b6ceeaee
candidate tree = 1ef58be8af7b044774211fcca932643607211652
actual merge = ff2db4c75f0e3ff620ce14da356e6c65640d3c6f
merge verification = verified=true / reason=valid
```

Historical owner surface integrated by PR #354:

```text
src/qore/infrastructure/structured_hybrid_synthetic_semantics.py
  blob 5378ebbe06a8ef8d0e36c3ac5e3c67d415e00cd6

tests/infrastructure/test_structured_hybrid_synthetic_semantics.py
  blob 057842ebddeb93dc01984add924b78a5fbb13293

tests/infrastructure/test_structured_hybrid_synthetic_reference_context.py
  blob f24dbf8a4b533ff22de5e163da60cb616b572f88

tests/infrastructure/test_structured_hybrid_synthetic_top_level_guards.py
  blob bdd46309c9baa5eddad93f027fdc55fe8c8635db

tests/infrastructure/test_structured_hybrid_synthetic_zero_level.py
  blob 7986a6041f002e3c808df492f9d44369d6e8620a

docs/architecture/QORE-UMI-09-STRUCTURED-HYBRID-SYNTHETIC-COMPOSITION-001.md
  blob e293e184cf1e4df8053f985dfccac58c92b4b41f
```

The six historical UMI09 owner artifacts were reconstructed as unchanged through the
Gate-A current-main audit.

## 3. Full Closure findings

### FC09-01 — historical lifecycle metadata

Classification: `HISTORICAL_STALE / NONCODE`

The historical issue/PR wording records its own earlier gate lifecycle. It must not be
interpreted as current Full Closure authority.

Disposition: non-production; superseded for current lifecycle purposes by this record and
live Full Closure evidence.

### FC09-02 — logical material oracle completeness

Classification: `TEST_ORACLE`

Severity: `MEDIUM / FULL-CLOSURE BLOCKING`

Retrospective #405 established:

```text
UMI09-LI-01 = CONFIRMED ORACLE GAP / MEDIUM
```

No current production semantic or projection omission was established by that finding.
Production source therefore is not reopened by default.

The confirmed oracle gaps include independent materiality protection for:

- `StructuredTermsId`;
- `StructuredFeatureId`;
- `StructuredEvidenceRef`;
- discrete schedule-code observation material;
- `StructuredComponentBinding` including complete embedded UMI02 relationship material;
- all six structured feature records;
- `StructuredHybridSyntheticTerms` complete canonical parent projection.

Gate-B correction adds:

```text
tests/infrastructure/test_structured_hybrid_synthetic_semantics_full_closure.py
```

The new expected material is hand-authored independently. It does not construct expected
values from the target `logical_values()`, production enum `.value`, production serializers,
production ordering helpers, or target constants.

The top-level oracle intentionally supplies components and features in reverse caller order
while expecting canonical relationship-ID and feature-ID order. UMI02 relationship ordinal
material is retained exactly but is not reinterpreted as a UMI09-global order.

A malicious `UUID` subclass counterexample is included for all three UMI09 local UUID
wrappers. The production source already requires exact `UUID` runtime type, so no production
correction is indicated by that counterexample.

### FC09-03 — fail-closed coverage ledger

Classification: `TEST_COVERAGE / FAIL-CLOSED ORACLE`

Severity: `MEDIUM / FULL-CLOSURE BLOCKING`

Current-main QORE CI before Gate B reported:

```text
structured_hybrid_synthetic_semantics.py
352 statements / 26 missed / 93%
```

Exact pre-correction miss set:

```text
154,
362, 370, 374,
400, 408, 415, 419,
450, 458, 462, 466, 474, 478,
508, 516, 524, 528, 532,
560, 568, 572, 576,
603, 611, 620
```

Line adjudication against the exact current owner source:

```text
154  StructuredObservationScheduleCode.logical_values() return
     -> reachable positive projection path
     -> protected by exact DISCRETE schedule-code projection oracle

362  capital-protection wrong feature_id guard
370  capital-protection wrong ratio guard
374  capital-protection wrong evidence_ref guard

400  conversion wrong feature_id guard
408  conversion wrong units_per_source_unit guard
415  conversion wrong conversion_level guard
419  conversion wrong evidence_ref guard

450  barrier wrong feature_id guard
458  barrier wrong barrier_kind guard
462  barrier wrong direction guard
466  barrier wrong level guard
474  barrier wrong observation guard
478  barrier wrong evidence_ref guard

508  autocall wrong feature_id guard
516  autocall wrong trigger_level guard
524  autocall wrong observation guard
528  autocall wrong redemption_ratio guard
532  autocall wrong evidence_ref guard

560  participation wrong feature_id guard
568  participation wrong direction guard
572  participation wrong participation_ratio guard
576  participation wrong evidence_ref guard

603  redemption wrong feature_id guard
611  redemption wrong redemption_ratio guard
620  redemption wrong evidence_ref guard
```

All 25 validation misses are reachable fail-closed guards. The Full Closure suite directly
constructs the invalid wrapper/type input for every one of them and requires the typed UMI09
validation error. No `pragma: no cover`, skip, xfail, coverage reduction, invalid-state object
mutation, or source churn is used to manufacture coverage.

Expected result after exact-candidate CI is 100% statement coverage for the UMI09 owner
source if no environment-dependent discrepancy exists. That result is not claimed until the
exact GitHub CI logs prove it.

### FC09-04 — recertification ledger

Classification: `DOCUMENTATION / FULL-CLOSURE PROCEDURE`

This document is the owner-local correction for the previously absent UMI09 Full Closure
recertification record.

## 4. Production source disposition

Current owner source:

```text
src/qore/infrastructure/structured_hybrid_synthetic_semantics.py
blob 5378ebbe06a8ef8d0e36c3ac5e3c67d415e00cd6
```

Gate-A inspection found no current projection omission or semantic production defect.
The source already enforces exact UUID runtime type.

Gate-B rule:

```text
NO INDEPENDENT ORACLE FALSIFICATION -> NO PRODUCTION MUTATION
```

At this stage the production source remains intentionally unchanged.

## 5. Owner semantics retained

UMI09 continues to own only provider-neutral higher-order structured/hybrid/synthetic
contractual qualification.

The following authority boundaries remain unchanged:

```text
UMI02 / D04 -> economic identity, relationship and relationship-ordinal authority
UMI05       -> generic derivative primitives and narrow derivative composition
UMI06       -> corporate-action rights distribution
UMI09       -> higher-order structured contractual qualification
D06         -> schedule/calendar resolution
UMI10 / D07 -> observed valuation, pricing and trigger evaluation
D08 / D09   -> account, collateral and risk authority
D10 / D18   -> order and execution authority
D11         -> exercise, conversion and settlement mutation
```

Hard retained distinctions include:

```text
RELATIONSHIP ORDINAL != UMI09 GLOBAL COMPONENT ORDER
CONTRACTUAL TRIGGER != OBSERVED TRIGGER EVENT
CONVERSION TERMS != CONVERSION EXECUTION
CAPITAL PROTECTION TERM != CREDIT OR PAYMENT FINALITY
CONTRACTUAL LEVEL != OBSERVED VALUE
STRUCTURED CONTRACT LEVEL != OPTION STRIKE
EVIDENCE REF != ECONOMIC TRUTH
```

## 6. Cross-owner reconciliation

`#332 / GAP-FND07-RES-01` remains open D08/D09/D10 capacity-reservation work and is not
exported as UMI09 debt.

`#333 / GAP-FND04-TIME-01` is closed and is not an open UMI09 blocker.

The Gate-A open-PR filename audit found no live PR modifying the UMI09 historical owner paths.

## 7. Security and negative space

This correction introduces no:

- provider adapter or network I/O;
- wallet, custody, RPC or signing authority;
- market-data read or current observed value;
- payoff valuation or trigger/event evaluation;
- executable formula, callback, AST, `eval` or `exec` payload;
- mutable generic parameter bag;
- account/risk authority;
- order or execution authority;
- exercise, conversion or settlement mutation;
- wall clock, implicit UUID, random source, retry, sleep, thread or scheduler;
- Production authorization or real-capital authority;
- secret material in logical values, tests or evidence.

## 8. Gate state

At this Gate-B record:

```text
GATE A = COMPLETE / CONSUMED
GATE B = AUTHORIZED / ACTIVE
GATE C = NOT AUTHORIZED
GATE D = NOT AUTHORIZED
GATE E = NOT AUTHORIZED
GATE F = NOT AUTHORIZED

PR = NOT CREATED
EXACT-CANDIDATE CLAUDE AUDIT = NOT STARTED
MERGE = NOT AUTHORIZED / NOT EXECUTED
POST-MERGE CI = NOT APPLICABLE YET
#301 UMI09 FINAL EVIDENCE = NOT WRITTEN
UMI09 FULL CLOSURE = NOT SEALED / NOT CLOSED
```

No later lifecycle state may be inferred from this document. Every authorization is local to
its explicit gate and never propagates.
