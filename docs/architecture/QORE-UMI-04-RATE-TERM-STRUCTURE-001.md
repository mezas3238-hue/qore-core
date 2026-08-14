# QORE-UMI-04-RATE-TERM-STRUCTURE-001

## Status

**PROGRAM D / UMI-04 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #322  
Master roadmap: Issue #303  
Universal Markets / Instruments program: Issue #301  
Certified starting baseline: `86bd54d92bc1d0d6c42888c85bdf59a0998a87b1`  
Predecessor: UMI-03 / #320 / PR #321 — CLOSED

This artifact defines the minimum provider-neutral rates / curves / term-structure
foundation required by UMI-04 after the repository audit recorded on #322.

It is additive to:

- UMI-02 universal economic/reference identity;
- FND-04 semantic separation and temporal law;
- UMI-03 `FinancialTenor`, `FixedIncomeYield`, and `FixedIncomeSpread`;
- existing external source/provenance infrastructure.

It does not implement a bootstrap engine, interpolation, valuation, pricing,
provider curve adapter, derivative payoff contract, execution path, or productive
support claim.

```text
RATE TERM-STRUCTURE CONTRACT
!=
CURVE CONSTRUCTION ENGINE
!=
VALUATION ENGINE
!=
PROVIDER SUPPORT
```

---

# 1. Governing invariants

```text
CURVE != SINGLE SCALAR
ECONOMIC IDENTITY != CURVE CONTENT
CURVE IDENTITY ATTACHMENT != IDENTITY-KIND PROOF
RATE != YIELD != SPREAD
ZERO RATE != PAR RATE != FORWARD RATE
DISCOUNT FACTOR != RATE
YIELD != PRICE
RATE TENOR != MARKET TIMEFRAME
FINANCIAL TENOR != FIXED SECONDS
FORWARD PERIOD != FIXED-SECONDS INTERVAL
NODE ORDER != TENOR-TO-SECONDS SORT
OBSERVED CURVE -> EXPLICIT EXTERNAL SOURCE
COMPUTED CURVE -> EXPLICIT INPUT FINGERPRINT
FINGERPRINT != RETAINED SOURCE EVIDENCE
METHOD CODE != ALGORITHM IMPLEMENTATION
CURVE SNAPSHOT != BOOTSTRAPPING
CURVE SNAPSHOT != INTERPOLATION
CURVE SNAPSHOT != DISCOUNTING / PRESENT VALUE
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO REPRODUCIBILITY -> NO PROMOTION
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

Open repository-wide carry-forwards remain binding:

- `GAP-FND04-TIME-01` — OPEN / HIGH;
- `GAP-FND07-RES-01` — OPEN / HIGH;
- PR #298 — HOLD.

UMI-04 does not claim to close any of them.

---

# 2. Baseline audit and evidence ledger

## 2.1 UMI-02 identity is reused, not duplicated

`EconomicIdentityId` remains the sole canonical attachment point for economic
instrument/reference identity.

A curve or benchmark may be represented by an existing UMI-02 reference-object
identity. UMI-04 does not create a new sovereign economic `CurveId`.

UMI-04 does introduce local artifact identities:

- `RateTermStructureSnapshotId`;
- `RateTermStructureNodeId`.

These identify retained UMI-04 artifacts, not economic entities.

```text
SNAPSHOT ID != ECONOMIC IDENTITY
NODE ID != ECONOMIC IDENTITY
```

An `EconomicIdentityId` value alone does not prove that the referenced identity
has UMI-02 `REFERENCE_OBJECT` kind. Graph/domain composition must validate
identity kind/relationship evidence where that distinction is material.

## 2.2 UMI-03 tenor/yield/spread are reused

UMI-03 certified:

- `FinancialTenor`;
- `FixedIncomeYield`;
- `FixedIncomeSpread`.

UMI-04 composes these values rather than creating duplicate horizon/yield/spread
authorities.

`FinancialTenor` deliberately has no fixed-seconds API.

UMI-04 therefore does not sort nodes by converting month/year horizons to seconds.
Canonical node order is explicit through a typed ordinal.

## 2.3 Market evidence is precedent, not curve authority

Existing Market Evidence v2 already demonstrates:

- exact Decimal material;
- explicit external source identity;
- retained evidence references;
- timezone-aware timestamps;
- UTC-canonical logical timestamp material.

But its `MarketPrice` is observation-scoped and its `MarketTimeframe` is
market-bar-scoped.

They cannot be silently reused as:

- zero/par/forward rates;
- discount factors;
- financial tenor;
- curve nodes;
- term structures.

## 2.4 Verified structural gap

Before this candidate, certified main had no canonical provider-neutral artifact
that simultaneously retained:

- curve/reference economic identity;
- currency economic identity;
- curve semantic kind;
- typed measure;
- multiple typed nodes;
- deterministic node order independent of caller declaration order;
- structural forward periods;
- snapshot as-of and recorded time;
- observed/computed provenance;
- external source for observed artifacts;
- deterministic input fingerprint for computed artifacts;
- node- and snapshot-level evidence references.

The audit therefore classified:

`VERIFIED STRUCTURAL GAP — UMI-04 IMPLEMENTATION DELTA REQUIRED`

Repository search was used only as bounded negative evidence. The positive gap
conclusion follows from direct inspection of UMI-02, UMI-03, FND-04 and market
observation contracts.

---

# 3. Contract architecture

## 3.1 Economic identity attachment

`RateTermStructureSnapshot` carries:

- `curve_identity_id: EconomicIdentityId`;
- `currency_identity_id: EconomicIdentityId`.

The two identities must differ.

The curve identity identifies the economic/reference object. The currency
identity binds the economic denomination/reference currency of the term
structure.

No provider symbol, venue string, adapter name or raw market code replaces either
identity.

## 3.2 Artifact identities and evidence references

UMI-04 introduces UUID-backed:

- `RateTermStructureSnapshotId`;
- `RateTermStructureNodeId`;
- `RateTermStructureEvidenceRef`.

Evidence references are opaque references only.

```text
EVIDENCE REF EXISTS
!=
EVIDENCE CONTENT RETAINED BY THIS OBJECT
```

Credentials, tokens and arbitrary strings cannot enter these UUID fields.

## 3.3 Typed curve measures

The current certified measure set is:

- `ZERO_RATE`;
- `PAR_RATE`;
- `FORWARD_RATE`;
- `YIELD`;
- `SPREAD`;
- `DISCOUNT_FACTOR`.

New scalar types:

- `ZeroRate`;
- `ParRate`;
- `ForwardRate`;
- `DiscountFactor`.

UMI-03 types reused:

- `FixedIncomeYield`;
- `FixedIncomeSpread`.

All rate/yield/spread magnitudes are exact finite `Decimal` fractions.

No universal sign restriction is imposed on zero/par/forward rates, yields or
spreads.

`DiscountFactor` is strictly positive finite Decimal and has no universal upper
bound because negative-rate environments can produce factors greater than one.

```text
NUMERIC EQUALITY
!=
SEMANTIC INTERCHANGEABILITY
```

Logical node material carries an explicit semantic tag even when numeric values
are equal.

## 3.4 Structural coordinates

Ordinary zero/par/yield/spread/discount-factor nodes use `FinancialTenor`.

Forward-rate nodes use:

`ForwardRatePeriod(start_tenor, period_tenor)`

where:

- `start_tenor` may be `None` for spot-start;
- `period_tenor` is a positive `FinancialTenor`.

UMI-04 does not attempt to compare 3M, 90D and 1Y by converting them to seconds.

This avoids inventing a universal calendar arithmetic rule before D06/calendar
composition exists.

## 3.5 Explicit node ordinal

Every node carries `RateTermStructureNodeOrdinal`.

Snapshot composition requires:

- positive strict integer ordinal;
- unique ordinal;
- ordinals contiguous from 1;
- canonical storage sorted by ordinal.

This provides deterministic curve order without asserting:

```text
MONTH == FIXED SECONDS
YEAR == FIXED SECONDS
```

Node coordinates must also be unique within one snapshot.

## 3.6 Measure / coordinate / value compatibility

The snapshot fails closed unless:

- `ZERO_RATE` -> `FinancialTenor` + `ZeroRate`;
- `PAR_RATE` -> `FinancialTenor` + `ParRate`;
- `FORWARD_RATE` -> `ForwardRatePeriod` + `ForwardRate`;
- `YIELD` -> `FinancialTenor` + `FixedIncomeYield`;
- `SPREAD` -> `FinancialTenor` + `FixedIncomeSpread`;
- `DISCOUNT_FACTOR` -> `FinancialTenor` + `DiscountFactor`.

A valid typed value cannot be laundered into the wrong curve measure merely
because its Decimal magnitude matches.

## 3.7 Curve kind

`RateTermStructureKindCode` is an extensible semantic classification.

Examples can include:

- government;
- swap;
- ois;
- benchmark;
- other future certified curve roles.

The code is classification, not identity.

```text
CURVE KIND CODE != CURVE IDENTITY
```

## 3.8 Provenance

`RateTermStructureProvenance` carries:

- `RateTermStructureProvenanceKind`;
- methodology code;
- evidence reference;
- optional `ExternalSourceDescriptor`;
- optional deterministic input fingerprint.

Two provenance modes are explicit.

### OBSERVED

Requires an `ExternalSourceDescriptor`.

An observed snapshot does not claim a computed input fingerprint.

### COMPUTED

Requires a `RateTermStructureInputFingerprint`.

The fingerprint is exactly lowercase SHA-256 hex.

An external source may also be retained when computed inputs originated from one
external boundary.

Both modes require methodology and retained evidence reference.

`RateTermStructureMethodologyCode` describes retained methodology identity only.
It does not execute or certify an algorithm.

```text
METHODOLOGY CODE
!=
BOOTSTRAP / INTERPOLATION IMPLEMENTATION

INPUT FINGERPRINT
!=
RETAINED INPUT DATA
```

## 3.9 Timestamp semantics

A snapshot carries:

- `as_of`;
- `recorded_at`.

Both must be timezone-aware `datetime`.

Chronology:

```text
recorded_at >= as_of
```

Logical material canonicalizes each instant to UTC microsecond ISO-8601.

Therefore two offset representations of the same instant produce identical
logical material.

This is a local UMI-04 compliance improvement and does not close the inherited
repository-wide `GAP-FND04-TIME-01`.

## 3.10 Snapshot determinism

`RateTermStructureSnapshot` requires:

- immutable non-empty tuple input;
- exact typed nodes;
- unique node IDs;
- unique coordinates;
- unique ordinals;
- contiguous ordinals from 1;
- exact measure/node compatibility;
- deterministic ordinal ordering.

Caller declaration order therefore cannot alter `logical_values()`.

---

# 4. Authority ownership

## UMI-02

Owns canonical economic/reference identity and relationships.

UMI-04 only attaches those identities.

## UMI-03

Owns the already-certified reusable `FinancialTenor`, yield and spread scalar
semantics used by the curve contract.

UMI-04 does not redefine fixed-income bond terms.

## D05 — Market Data & Market Evidence

Owns external/observed market facts and evidence at the market-data boundary.

An `OBSERVED` UMI-04 snapshot can retain an external source descriptor without
becoming the external source authority.

## D07 — Valuation, Pricing, Yield & Analytics

Owns future construction/calculation/valuation implementations where those
algorithms belong.

UMI-04 provides the canonical retained term-structure artifact such a department
may produce or consume. The contract itself has no valuation engine.

## UMI-10

Owns the future universal valuation-observation boundary across price/yield/rate/
spread/NAV/mark/IV/cash-flow observations.

UMI-04 is narrower: it establishes a multi-node rate/curve term-structure
semantic artifact with explicit provenance.

UMI-04 must not be used as a substitute for UMI-10's broader observation model.

---

# 5. Explicit non-goals

This candidate does not implement or certify:

- bootstrapping;
- interpolation;
- extrapolation;
- curve fitting;
- spline/polynomial methods;
- discounting;
- present value;
- bond pricing;
- accrued-interest calculation;
- YTM/YTW solving;
- duration;
- modified duration;
- convexity;
- futures/options/swaps payoff semantics;
- provider-native curve feeds;
- a provider catalog;
- database/storage;
- live market-data ingestion;
- execution;
- positions;
- settlement mutation;
- risk-capacity reservation;
- productive Cloud;
- production readiness;
- real capital.

No specific government/swap/OIS curve is operationally supported merely because
the semantic type can represent it.

---

# 6. Adversarial test obligations

`tests/infrastructure/test_rate_term_structure.py` must prove at minimum:

1. zero/par/forward/yield/spread/discount-factor values remain semantically
   distinct at equal numeric magnitude;
2. non-finite Decimal values fail closed;
3. discount factor must be positive but may exceed one;
4. signed/exponent zero canonicalizes deterministically;
5. forward periods remain structural and expose no fixed-seconds contract;
6. node ordinal rejects bool/zero/negative values;
7. kind/methodology codes fail closed;
8. input fingerprint requires exact lowercase SHA-256 hex;
9. OBSERVED provenance requires external source;
10. OBSERVED provenance rejects computed input fingerprint;
11. COMPUTED provenance requires input fingerprint;
12. provenance fields reject raw-string laundering;
13. equal instants under different offsets produce identical logical material;
14. naive timestamps fail closed;
15. recorded time cannot predate as-of time;
16. curve and currency identity must differ;
17. raw measure/kind laundering fails closed;
18. nodes require non-empty immutable tuple;
19. duplicate node IDs fail;
20. duplicate ordinals fail;
21. duplicate coordinates fail;
22. ordinals must be contiguous from one;
23. every measure accepts only its exact coordinate/value contract;
24. UMI-03 yield/spread types are reused rather than duplicated;
25. forward curves require `ForwardRatePeriod`;
26. input caller order does not change canonical node order;
27. UUID/digest evidence fields reject credential-like arbitrary strings;
28. snapshot exposes no curve-engine or valuation methods;
29. logical material is deterministic and secret-free.

---

# 7. Compatibility and blast radius

Intended PR delta:

- `src/qore/infrastructure/rate_term_structure.py`;
- `tests/infrastructure/test_rate_term_structure.py`;
- this architecture artifact.

No existing source, test, provider adapter, execution path, runtime, database,
storage backend or migration is modified.

Dependency direction:

```text
UMI-02 EconomicIdentityId
+
UMI-03 FinancialTenor / FixedIncomeYield / FixedIncomeSpread
+
ExternalSourceDescriptor provenance
->
UMI-04 RateTermStructureSnapshot
```

not:

```text
UMI-04 -> provider SDK
UMI-04 -> execution
UMI-04 -> valuation engine
```

---

# 8. Certification discipline

This candidate is materially designed and implemented through the Integration
Gate workflow and cannot self-certify.

Required sequence:

```text
IMPLEMENT
-> ADVERSARIAL TEST
-> QORE QUALITY GATE
-> DIFF AUDIT
-> DRAFT PR
-> FREEZE EXACT HEAD
-> CLAUDE INDEPENDENT ADVERSARIAL REVIEW
-> INTEGRATION GATE FALSIFICATION
-> CORRECTION / NEW HEAD / NEW CI / FULL RE-REVIEW IF REQUIRED
-> EXPECTED-HEAD MERGE
-> VERIFY ACTUAL MERGE
-> VERIFY POST-MERGE MAIN
-> FREEZE NEW CERTIFIED BASELINE
-> CLOSE UMI-04
```

Until that sequence completes:

```text
IMPLEMENTED CANDIDATE != CERTIFIED UMI-04
CURVE TYPE EXISTS != CURVE PRODUCER EXISTS
CURVE SNAPSHOT EXISTS != PROVIDER CURVE SUPPORT
CI GREEN != ENGINEERING APPROVAL
```
