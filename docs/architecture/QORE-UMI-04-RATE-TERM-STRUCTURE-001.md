# QORE-UMI-04-RATE-TERM-STRUCTURE-001

## Status

**PROGRAM D / UMI-04 — FULL CLOSURE RECERTIFICATION RECORD; FINAL CLOSURE STATUS GOVERNED BY #301**

Tracking: Issue #322  
Master roadmap: Issue #303  
Universal Markets / Instruments program: Issue #301  
Historical certified starting baseline: `86bd54d92bc1d0d6c42888c85bdf59a0998a87b1`  
Full Closure reconstruction baseline: `de24ef93c05c86fc09f23378bb17bb017ba8dc85`  
Full Closure reconstruction tree: `8cb5bc98ddcf01b6a7e2edcceada80b8568286ba`  
Predecessor: UMI-03 / #320 / PR #321 — historically CLOSED; Full Closure predecessor separately governed by #301

This artifact defines the minimum provider-neutral rates / curves / term-structure
foundation required by UMI-04 after the repository audit recorded on #322.

Sections 1-9 preserve the historical implementation/certification record. Section
10 is the current Full Closure recertification addendum and is authoritative for
current certification sequencing, evidence reconciliation, cross-owner ownership,
and final closure status. This document does not self-certify final closure; the
final disposition is governed by the serial Full Closure protocol and durable #301
evidence.

It is additive to:

- UMI-02 universal economic/reference identity;
- FND-04 semantic separation and temporal law;
- UMI-03 `FinancialTenor`, `FixedIncomeYield`, `FixedIncomeSpread`, day-count,
  compounding and yield-convention semantics;
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
RATE MAGNITUDE WITHOUT QUOTE CONVENTION != REPRODUCIBLE RATE
YIELD MAGNITUDE WITHOUT YIELD CONVENTION != REPRODUCIBLE YIELD
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

UMI-04 introduces local artifact identities:

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

## 2.2 UMI-03 semantic contracts are reused

UMI-03 certified:

- `FinancialTenor`;
- `FixedIncomeYield`;
- `FixedIncomeSpread`;
- `DayCountConventionCode`;
- `CompoundingConventionCode`;
- `YieldConvention`.

UMI-04 composes these values rather than creating duplicate horizon, yield,
spread, day-count or compounding authorities.

`FinancialTenor` deliberately has no fixed-seconds API.

UMI-04 therefore does not sort nodes by converting month/year horizons to
seconds. Canonical node order is explicit through a typed ordinal.

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
- economically material rate/yield quote convention;
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

# 3. Pre-review falsification correction

The first UMI-04 implementation draft represented `ZeroRate`, `ParRate` and
`ForwardRate` magnitudes but did not bind day-count and compounding semantics to
the rate snapshot.

That draft was rejected before independent review because:

```text
5% CONTINUOUS
!=
5% PERIODIC SEMIANNUAL
```

and the numerical magnitude alone does not make either rate reproducible.

The historical candidate therefore introduced `RateCurveConvention` and made the
snapshot convention measure-dependent:

```text
ZERO_RATE / PAR_RATE / FORWARD_RATE
-> RateCurveConvention REQUIRED

YIELD
-> existing UMI-03 YieldConvention REQUIRED

SPREAD / DISCOUNT_FACTOR
-> rate/yield convention MUST NOT be attached
```

That correction was part of the historically certified UMI-04 candidate. Earlier
heads and failed CI are historical only and are not transferable certification
evidence for any later head.

---

# 4. Contract architecture

## 4.1 Economic identity attachment

`RateTermStructureSnapshot` carries:

- `curve_identity_id: EconomicIdentityId`;
- `currency_identity_id: EconomicIdentityId`.

The two identities must differ.

The curve identity identifies the economic/reference object. The currency
identity binds the economic denomination/reference currency of the term
structure.

No provider symbol, venue string, adapter name or raw market code replaces either
identity.

## 4.2 Artifact identities and evidence references

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

## 4.3 Typed curve measures

The current bounded measure set is:

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

## 4.4 Rate quotation convention

`RateCurveConvention` retains:

- `DayCountConventionCode`;
- `CompoundingConventionCode`;
- optional structural compounding tenor.

One fail-closed rule is explicit:

```text
compounding == periodic
-> compounding_tenor REQUIRED
```

The contract does not calculate year fractions, accrued values, discount factors
or rates. It only prevents a rate magnitude from losing the conventions required
to interpret it.

Zero, par and forward rate term structures require `RateCurveConvention`.

## 4.5 Yield convention reuse

A `YIELD` term structure reuses UMI-03 `YieldConvention`, which retains:

- yield semantic code;
- day-count convention;
- compounding convention;
- required periodic compounding tenor where applicable;
- optional typed benchmark/reference attachment.

UMI-04 therefore does not invent a second yield convention authority.

## 4.6 Spread and discount-factor convention boundary

`SPREAD` and `DISCOUNT_FACTOR` snapshots do not accept a rate/yield convention.

A spread's economic classification remains explicit through the curve identity,
curve-kind code and retained methodology/provenance. A later specialized spread
contract may add further certified semantics when evidence requires them; UMI-04
does not silently reinterpret spread as a rate.

A discount factor is a distinct positive dimensionless scalar and is not given a
rate compounding convention merely because a rate may later be derived from it.

## 4.7 Structural coordinates

Ordinary zero/par/yield/spread/discount-factor nodes use `FinancialTenor`.

Forward-rate nodes use:

`ForwardRatePeriod(start_tenor, period_tenor)`

where:

- `start_tenor` may be `None` for spot-start;
- `period_tenor` is a positive `FinancialTenor`.

UMI-04 does not attempt to compare 3M, 90D and 1Y by converting them to seconds.

This avoids inventing a universal calendar arithmetic rule before D06/calendar
composition exists.

## 4.8 Explicit node ordinal

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

Exact syntactic coordinates such as `12M` and `1Y` are not silently treated as
equivalent because doing so would require calendar/roll semantics that this
contract does not own.

## 4.9 Measure / coordinate / value / convention compatibility

The snapshot fails closed unless:

- `ZERO_RATE` -> `FinancialTenor` + `ZeroRate` + `RateCurveConvention`;
- `PAR_RATE` -> `FinancialTenor` + `ParRate` + `RateCurveConvention`;
- `FORWARD_RATE` -> `ForwardRatePeriod` + `ForwardRate` + `RateCurveConvention`;
- `YIELD` -> `FinancialTenor` + `FixedIncomeYield` + `YieldConvention`;
- `SPREAD` -> `FinancialTenor` + `FixedIncomeSpread` + no rate/yield convention;
- `DISCOUNT_FACTOR` -> `FinancialTenor` + `DiscountFactor` + no rate/yield convention.

A valid typed value cannot be laundered into the wrong curve measure merely
because its Decimal magnitude matches.

## 4.10 Curve kind

`RateTermStructureKindCode` is an extensible semantic classification.

Examples can include:

- government;
- swap;
- ois;
- benchmark;
- credit-spread;
- other future certified curve roles.

The code is classification, not identity.

```text
CURVE KIND CODE != CURVE IDENTITY
```

## 4.11 Provenance

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

## 4.12 Timestamp semantics

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

## 4.13 Snapshot determinism

`RateTermStructureSnapshot` requires:

- immutable non-empty tuple input;
- exact typed nodes;
- unique node IDs;
- unique coordinates;
- unique ordinals;
- contiguous ordinals from 1;
- exact measure/node/convention compatibility;
- deterministic ordinal ordering.

Caller declaration order therefore cannot alter `logical_values()`.

---

# 5. Authority ownership

## UMI-02

Owns canonical economic/reference identity and relationships.

UMI-04 only attaches those identities.

## UMI-03

Owns the already-certified reusable financial tenor, yield, spread, day-count,
compounding and yield-convention semantics used by the curve contract.

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

Owns the universal valuation-observation boundary across price/yield/rate/
spread/NAV/mark/IV/cash-flow observations.

UMI-04 is narrower: it establishes a multi-node rate/curve term-structure
semantic artifact with explicit provenance and rate/yield conventions.

UMI-04 must not be used as a substitute for UMI-10's broader observation model.

---

# 6. Explicit non-goals

This contract does not implement or certify:

- bootstrapping;
- interpolation;
- extrapolation;
- curve fitting;
- spline/polynomial methods;
- year-fraction calculation;
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

No specific government/swap/OIS/credit curve is operationally supported merely
because the semantic type can represent it.

---

# 7. Adversarial test obligations

`tests/infrastructure/test_rate_term_structure.py` must prove at minimum:

1. zero/par/forward/yield/spread/discount-factor values remain semantically
   distinct at equal numeric magnitude;
2. non-finite Decimal values fail closed;
3. discount factor must be positive but may exceed one;
4. signed/exponent zero canonicalizes deterministically;
5. `RateCurveConvention` retains day-count and compounding semantics;
6. periodic rate compounding requires explicit frequency tenor;
7. rate measures require `RateCurveConvention`;
8. rate measures reject `YieldConvention`;
9. yield measure requires certified UMI-03 `YieldConvention`;
10. yield measure rejects `RateCurveConvention`;
11. spread/discount-factor measures reject rate/yield convention laundering;
12. forward periods remain structural and expose no fixed-seconds contract;
13. node ordinal rejects bool/zero/negative values;
14. kind/methodology codes fail closed;
15. input fingerprint requires exact lowercase SHA-256 hex;
16. OBSERVED provenance requires external source;
17. OBSERVED provenance rejects computed input fingerprint;
18. COMPUTED provenance requires input fingerprint;
19. provenance fields reject raw-string laundering;
20. equal instants under different offsets produce identical logical material;
21. naive timestamps fail closed;
22. recorded time cannot predate as-of time;
23. curve and currency identity must differ;
24. raw measure/kind laundering fails closed;
25. nodes require non-empty immutable tuple;
26. duplicate node IDs fail;
27. duplicate ordinals fail;
28. duplicate coordinates fail;
29. ordinals must be contiguous from one;
30. every measure accepts only its exact coordinate/value/convention contract;
31. UMI-03 yield/spread types are reused rather than duplicated;
32. forward curves require `ForwardRatePeriod`;
33. input caller order does not change canonical node order;
34. UUID/digest evidence fields reject credential-like arbitrary strings;
35. snapshot exposes no curve-engine or valuation methods;
36. logical material is deterministic and secret-free.

The later `UMI04-LI-01` hardening expanded the oracle obligations around complete
logical projection and provenance. Section 10 records that evidence and its final
disposition.

---

# 8. Compatibility and blast radius

Historical implementation delta was exactly:

- `src/qore/infrastructure/rate_term_structure.py`;
- `tests/infrastructure/test_rate_term_structure.py`;
- this architecture artifact.

The Full Closure correction represented by the current addendum is documentation
only. It does not alter the production contract or its tests.

Dependency direction:

```text
UMI-02 EconomicIdentityId
+
UMI-03 FinancialTenor / rate-yield convention / yield / spread
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

# 9. Historical certification discipline

The historical candidate was materially designed and implemented through the
Integration Gate workflow and could not self-certify.

Historical sequence:

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

That historical sequence is evidence, not the current Full Closure authority.
Section 10 supersedes it for recertification.

```text
IMPLEMENTED CANDIDATE != CERTIFIED UMI-04
CURVE TYPE EXISTS != CURVE PRODUCER EXISTS
CURVE SNAPSHOT EXISTS != PROVIDER CURVE SUPPORT
CI GREEN != ENGINEERING APPROVAL
HISTORICAL UMI CERTIFICATION != FULL CLOSURE RECERTIFICATION
```

---

# 10. Full Closure recertification addendum

## 10.1 Full Closure reconstruction baseline

The read-only Full Closure reconstruction started from exact `main`:

- SHA: `de24ef93c05c86fc09f23378bb17bb017ba8dc85`;
- tree: `8cb5bc98ddcf01b6a7e2edcceada80b8568286ba`;
- GitHub merge signature: verified / valid;
- parent baseline includes the formally sealed UMI-01, UMI-02 and UMI-03 Full
  Closure corrections already integrated before UMI-04 reconstruction.

No moving `main`, historical branch head, issue prose, review verdict, or CI label
may replace exact Git object verification.

```text
NO VERIFICATION -> NO APPROVAL
NO EVIDENCE -> NO CLAIM
CI GREEN ALONE != ENGINEERING APPROVAL
HISTORICAL VERDICT != CURRENT-HEAD VERDICT
```

## 10.2 Historical PR #323 certification ledger

UMI-04 historical implementation owner:

- tracking issue: #322;
- PR: #323 — `QORE-UMI-04 — Rates / Curves / Term Structures`;
- base: `86bd54d92bc1d0d6c42888c85bdf59a0998a87b1`;
- final reviewed head: `04a3a5d0d0c9e33f923b21c59521abe403c11e0e`;
- candidate tree: `83b9550c438a75e8f14bddd409a4a6b80165b44f`;
- synthetic merge tested at review: `1945ae348b413754724bc05ad4663cdeaa082e59`;
- final candidate scope: nine commits, three additive files, `+1935/-0`;
- authoritative exact-head QORE CI: #1029 / run `31819226649` / SUCCESS;
- exact-head quality evidence: Ruff PASS; Mypy PASS on 572 source files;
  Pytest 2441 passed with six inherited warnings; total coverage 84%;
  `rate_term_structure.py` 96%;
- actual merge: `c1b18750782a3a16bfb037f2f100dedcf2b1f238`;
- actual merge tree: `83b9550c438a75e8f14bddd409a4a6b80165b44f`;
- merge parents: `86bd54d92bc1d0d6c42888c85bdf59a0998a87b1` +
  `04a3a5d0d0c9e33f923b21c59521abe403c11e0e`;
- merge signature: verified / valid.

Historical heads such as `196b6a116a51e8b72f84f9e31a66cc9154543bba`,
`2078d9bf7278d392d039336e7ddd183d269efc85`,
`89fe3a10d35c5a3b19183afb506258fd6ee9b11f`, and
`62f6ed6056257fe1f200d1ed7e41f3f273a92a67` are preserved only as branch-history
facts. They are not the final reviewed head and no verdict transfers from or to
them.

The pre-review semantic gap around naked zero/par/forward-rate magnitude was
corrected before final independent review by requiring exact quotation convention
semantics. That correction is part of the final certified tree above.

## 10.3 Later owner-local hardening — UMI04-LI-01

A later logical-identity/oracle audit found a test-oracle completeness gap owned by
UMI-04. It did not establish a production defect.

Durable ledger:

- tracker: #405 / `UMI04-LI-01`;
- PR: #411 — `QORE-UMI04-LI-01 — complete rate-term projection oracles`;
- classification: TEST-ONLY ORACLE GAP / MEDIUM;
- base: `af9a3a3c5ac1d993d994a274a221ed22597d912a`;
- final head: `cab14b88dc14c2f6564e2d91b5216727dd41f336`;
- candidate tree: `6765098ae92f296c782ae1371b53fa1f0bf846f4`;
- changed owner: `tests/infrastructure/test_rate_term_structure.py` only;
- full delta: two commits, one file, `+312/-0`;
- production source: unchanged;
- architecture docs: unchanged;
- CI/config: unchanged;
- authoritative QORE CI: #1206 / run `32188132937` / SUCCESS;
- Ruff PASS; Mypy PASS on 612 source files; Pytest 3217 passed with six inherited
  warnings; total statement coverage 86%; `rate_term_structure.py` 96%;
- final merge: `c9e7467bcd65f7cd4afdc8f7cd3ab7b5f7f5564a`;
- merge tree: `6765098ae92f296c782ae1371b53fa1f0bf846f4`.

The hardening proves complete logical projections for observed/computed
provenance, tenor/forward nodes, ZERO_RATE/YIELD/SPREAD snapshot material and
canonical ordering. In particular, COMPUTED provenance is protected for both
legal `source=None` and legal retained populated external source material.

Disposition:

`UMI04-LI-01 = CLOSED`

It is evidence that must be retained in UMI-04 Full Closure, not a reason to
invent a new production change.

## 10.4 Full Closure Gate-A findings

The Full Closure reconstruction found four UMI-04-owned material recertification
findings and no verified production or test defect still pending.

### FC04-01 — historical status / exact certification ledger

Classification: `UMI04_INTERNAL_NONCODE`.

The live artifact still described itself as an implementation candidate and did
not durably reconcile final PR #323 Git objects against intermediate heads.

Resolution in this addendum:

- top status now records Full Closure recertification posture;
- final PR #323 base/head/tree/CI/merge evidence is explicit;
- intermediate branch heads remain historical only;
- exact Git object evidence, not narrative snapshots, governs certification.

`FC04-01 -> RESOLVED IN CANDIDATE`

### FC04-02 — missing UMI04-LI-01 durable evidence

Classification: `UMI04_INTERNAL_NONCODE`.

The architecture artifact predated PR #411 and therefore omitted the later
owner-local oracle-completeness correction.

Resolution in this addendum:

- #405 / PR #411 / exact head/tree / CI #1206 / merge ledger retained;
- TEST-ONLY classification preserved;
- no false production-defect claim introduced.

`FC04-02 -> RESOLVED IN CANDIDATE`

### FC04-03 — current authority / downstream ownership reconciliation

Classification: `UMI04_INTERNAL_NONCODE`.

The historical artifact correctly bounded its authority, but Full Closure needs a
current-main authority ledger against later Program-D and departmental work.

Resolution is defined in section 10.5.

`FC04-03 -> RESOLVED IN CANDIDATE`

### FC04-04 — historical protocol is not current Full Closure protocol

Classification: `UMI04_INTERNAL_NONCODE`.

Historical certification did not contain the later mandatory whole-UMI Full
Closure chain.

Resolution is defined in sections 10.8-10.10.

`FC04-04 -> RESOLVED IN CANDIDATE`

### FC04-05 — stale current cross-owner disposition for TIME-01

Classification: `UMI04_INTERNAL_NONCODE`.

Independent exact-candidate review followed by IA falsification established that
the current Full Closure addendum still listed `GAP-FND04-TIME-01` as an open
carry-forward even though its authoritative downstream tracker #333 is now
CLOSED / completed after the independently governed TIME-01 remediation.

Resolution in this Gate-B2 correction:

- the historical `OPEN / HIGH` statements in sections 1-9 remain preserved as
  historical UMI-04 certification facts;
- the current addendum records `GAP-FND04-TIME-01` as
  `CLOSED_DOWNSTREAM_VERIFIED` under FND-04 ownership;
- downstream evidence binds #333 closure to merged PR #408 and the verified
  post-merge baseline `a88aa34677ca3778275d8fcca972627ff6b2714a`;
- no UMI-04 production or test change is inferred from that downstream closure;
- `GAP-FND07-RES-01` remains independently OPEN / HIGH under #332.

`FC04-05 -> RESOLVED IN CORRECTED CANDIDATE`

No additional material UMI-04-owned gap is established by the current correction
ledger. If later independent review proves one, it must be corrected inside
UMI-04 before closure rather than exported merely because another owner is nearby.

## 10.5 Current authority and downstream ownership reconciliation

### UMI-04 owns

UMI-04 remains the bounded semantic owner of the provider-neutral retained
rate-term-structure contract:

- canonical attachment to UMI-02 economic/reference identity;
- curve and currency identity attachment without claiming identity-kind proof;
- zero/par/forward/yield/spread/discount-factor semantic distinction;
- structural ordinary-tenor and forward-period coordinates;
- explicit deterministic node ordinal and canonical node ordering;
- rate quotation convention binding;
- reuse of UMI-03 yield/spread/day-count/compounding semantics;
- OBSERVED vs COMPUTED provenance structure;
- external source requirement for observed curves;
- deterministic input fingerprint requirement for computed curves;
- immutable multi-node snapshot shape;
- deterministic, secret-free logical material;
- local timezone-aware/UTC-canonical as-of and recorded-time semantics.

### UMI-02 owns

UMI-02 remains the canonical economic/reference identity and relationship owner.
UMI-04 consumes `EconomicIdentityId`; it does not establish identity-kind proof,
listing/native mapping or mapping-currentness authority.

### UMI-03 owns

UMI-03 remains the owner of reusable `FinancialTenor`, fixed-income yield/spread,
day-count, compounding and yield-convention semantics. UMI-04 composes those
contracts and does not redefine bond economics.

### D05 owns external observed facts

D05 Market Data / Market Evidence owns acquisition and qualification of external
observed market facts. An UMI-04 OBSERVED curve can retain an external source
binding without becoming a market-feed producer.

### D07 owns concrete valuation / curve-construction methodology and producer

Issue #350 remains the explicit D07 backlog for concrete computed-valuation
methodology, exact inputs, producer invocation and reproducibility. UMI-04 does
not absorb it.

```text
CURVE TYPE EXISTS != CURVE CONSTRUCTED
METHODOLOGY CODE EXISTS != METHOD IMPLEMENTED
INPUT FINGERPRINT EXISTS != INPUTS RETAINED / COMPUTATION PROVEN
UMI-04 COMPUTED PROVENANCE != D07 PRODUCER CERTIFICATION
```

Any future bootstrap, interpolation, extrapolation, curve-fitting, discounting,
pricing, risk analytics or model execution remains outside this UMI unless a
separate authority explicitly moves it.

### UMI-10 owns universal valuation observation

UMI-10 owns the broader universal valuation-observation envelope across scalar
and structured value kinds. UMI-04 remains the narrower structured curve
semantic artifact. Neither authority erases the other.

### UMI-14 is final Program-D audit authority, not UMI-04 implementation owner

Issue #363 remains the active UMI-14 reconstruction/falsification authority. It
must verify UMI-04 curve/tenor/rate/provenance semantics without conflating a
retained curve observation with a concrete valuation methodology.

UMI-14 may discover a defect and route a correction back to UMI-04, but the audit
stage does not silently become the owner of UMI-04 semantics.

## 10.6 Cross-owner disposition ledger

Current downstream dispositions independently revalidated for this correction:

- #350 — OPEN / BACKLOG-PREPARATORY; D07 concrete computed-valuation
  methodology/producer/reproduction remains external to UMI-04;
- `GAP-FND04-TIME-01` / #333 — `CLOSED_DOWNSTREAM_VERIFIED`; #333 is CLOSED /
  completed after merged PR #408, with post-merge closure evidence on baseline
  `a88aa34677ca3778275d8fcca972627ff6b2714a`; historical UMI-04 statements that
  TIME-01 was `OPEN / HIGH` remain historical only;
- `GAP-FND07-RES-01` / #332 — OPEN / HIGH under the separate scarce-capacity
  reservation owner;
- #363 — OPEN / ACTIVE as UMI-14 final Program-D reconstruction/falsification
  audit authority, not UMI-04 implementation ownership;
- PR #298 — OPEN / DRAFT / HOLD at the provider-catalog boundary;
- provider-native curve catalog/feed support remains external and uncertified by
  this semantic artifact;
- provider operational activation remains external;
- execution/account/position/settlement/risk-capacity state remains external;
- Production readiness or real-capital authority remains external;
- any product-specific curve methodology not separately certified remains
  external.

A cross-owner label is not permission to export UMI-04 internal debt. Open items
above remain external only because their ownership is independently evidenced and
the current reconstruction established no missing UMI-04 implementation required
to close them. A downstream item already closed by its own authority is recorded
as closed downstream rather than kept artificially open in UMI-04.

## 10.7 Current non-claims

Full Closure recertification of UMI-04 does not claim:

- a curve bootstrap/interpolation/extrapolation implementation;
- a calibrated government, swap, OIS, credit or other operational curve;
- a valuation/pricing/PV/YTM/YTW/duration/convexity engine;
- complete exact-input retention for a computed valuation;
- D07 producer authority;
- UMI-10 scalar/universal valuation replacement;
- provider-native curve ingestion or catalog support;
- a database or storage backend;
- execution or routing authority;
- positions/account/settlement/risk reservation authority;
- productive Cloud support;
- Production readiness;
- productive credentials;
- real-money trading or real capital.

```text
SEMANTIC REPRESENTABILITY != OPERATIONAL SUPPORT
PLATFORM SUPPORT != PRODUCTION AUTHORITY
FULL CLOSURE UMI-04 != QORE PRODUCTION AUTHORIZATION
```

## 10.8 Full Closure laws

The current UMI-04 recertification is governed by:

```text
NO PARTIAL UMI WORK
NO ISOLATED FIX AS UMI CLOSURE
NO FRAGMENTED DELIVERY
NO VERIFICATION -> NO APPROVAL
NO EVIDENCE -> NO CLAIM
CI GREEN ALONE != ENGINEERING APPROVAL
DOCUMENT EXISTS != IMPLEMENTATION EXISTS
TYPE EXISTS != PRODUCER EXISTS
CONTRACT FITNESS != OPERATIONAL SUPPORT
PLATFORM SUPPORT != PRODUCTION AUTHORITY
NO GREEN EXACT HEAD -> NO MERGE
NO POST-MERGE VERIFICATION -> NO NEXT STEP
NO SELF-CERTIFICATION
AUDIT DISCOVERS GAP != AUDIT OWNS DOWNSTREAM IMPLEMENTATION
CROSS-OWNER LABEL != PERMISSION TO EXPORT INTERNAL DEBT
HISTORICAL UMI CERTIFICATION != FULL CLOSURE RECERTIFICATION
```

If Full Closure reconstruction or review finds N material UMI-04-owned defects,
all N must be corrected before UMI-04 can close. A later external owner may remain
open only when current UMI-04 has already completed its own required contract.

## 10.9 Mandatory current Full Closure sequence

The authoritative current sequence is:

```text
FULL READ-ONLY RECONSTRUCTION
-> IDENTIFY ALL CURRENT UMI-04-OWNED MATERIAL FINDINGS
-> ONE COMPLETE UMI-04 CORRECTION
-> ZERO KNOWN UMI-04 INTERNAL PENDING WORK
-> FULL QORE QUALITY GATE ON EXACT CANDIDATE
-> DIFF / OWNERSHIP / SECURITY AUDIT
-> DRAFT PR
-> FREEZE EXACT CANDIDATE HEAD + TREE
-> CLAUDE INDEPENDENT WHOLE-CANDIDATE REVIEW
-> COMPLETE CORRECTION OF MATERIAL CANDIDATE FINDINGS
-> NEW EXACT-HEAD CI + FULL RE-REVIEW IF HEAD CHANGES
-> IA CANDIDATE FALSIFICATION
-> EXPLICIT READY GATE
-> PROTECTED EXPECTED-HEAD MERGE
-> VERIFY ACTUAL MERGE SHA / TREE / PARENTS / SIGNATURE
-> VERIFY POST-MERGE QORE CI ON EXACT MAIN MERGE
-> RECONSTRUCT INTEGRATED UMI-04 STATE / ZERO INTERNAL PENDING
-> CLAUDE FINAL WHOLE-UMI-04 INTEGRATED-STATE AUDIT
-> COMPLETE CORRECTION OF ANY MATERIAL FINAL-AUDIT FINDING
-> RE-AUDIT UNTIL CLAUDE CLEAN
-> IA FINAL INDEPENDENT FALSIFICATION
-> EXPLICIT #301 EVIDENCE AUTHORIZATION
-> ONE DURABLE #301 FINAL CLOSURE RECORD
-> FREEZE FINAL MAIN SHA + TREE + EVIDENCE ID
-> UMI-04 FULL-CLOSURE RECERTIFIED / SEALED / CLOSED
-> ONLY THEN UMI-05 MAY START
```

A candidate review before merge does not substitute for the mandatory final
whole-UMI-04 audit of integrated `main`.

## 10.10 Full Closure Definition of Done

UMI-04 may be finally recorded as Full Closure only when every item below is
independently evidenced:

1. exact Full Closure starting main SHA verified;
2. exact Full Closure starting tree verified;
3. starting commit signature/repository identity verified where available;
4. issue #322 and PR #323 historical scope reconstructed;
5. final PR #323 base verified;
6. final reviewed PR #323 head verified;
7. final PR #323 candidate tree verified;
8. final PR #323 exact-head QORE CI verified;
9. final PR #323 actual merge SHA/tree/parents verified;
10. historical intermediate heads explicitly non-authoritative;
11. UMI04-LI-01 / #405 / PR #411 reconstructed;
12. PR #411 exact final head/tree verified;
13. PR #411 exact-head CI #1206 verified;
14. PR #411 merge and TEST-ONLY disposition verified;
15. no unresolved production defect is hidden behind the oracle correction;
16. UMI-04 semantic ownership is enumerated;
17. UMI-02 identity ownership remains non-colliding;
18. UMI-03 fixed-income convention ownership remains non-colliding;
19. D05 external observation ownership remains non-colliding;
20. D07 producer/methodology boundary remains external and explicit;
21. UMI-10 universal valuation-observation boundary remains non-colliding;
22. UMI-14 audit authority remains audit rather than silent implementation owner;
23. #350 is not silently closed;
24. repository-wide/open carry-forwards are classified by actual owner;
25. provider support is not inferred from semantic representability;
26. Production authority is explicitly denied;
27. Full Closure correction contains no unrelated source/test/runtime/provider mutation;
28. complete repository quality gate is green on exact correction head;
29. exact candidate diff is audited against the frozen base;
30. independent Claude whole-candidate review is clean after any correction loop;
31. IA independently falsifies the exact candidate;
32. Ready occurs only after explicit authorization;
33. merge occurs only after explicit expected-head authorization;
34. actual merge object exactly preserves the approved candidate tree;
35. post-merge main CI is green on the exact merge SHA;
36. integrated main is reconstructed for zero remaining UMI-04 internal work;
37. Claude performs the mandatory final whole-UMI-04 integrated-state audit;
38. every material final-audit finding is corrected and re-audited;
39. IA performs final independent falsification after Claude is clean;
40. exactly authorized final evidence is written to #301;
41. final main SHA/tree/evidence ID are frozen;
42. #301 remains governed by the wider Program-D serial process unless separately
    authorized to change state;
43. UMI-05 is not started before UMI-04 is formally sealed/closed;
44. no Production/real-capital authority is inferred at any point.

## 10.11 Current candidate posture

This addendum resolves FC04-01 through FC04-05 inside the authorized Gate-B/Gate-B2
candidate. It does not declare the UMI closed.

At this point the permitted claim is only:

`UMI-04 FULL CLOSURE CORRECTION CANDIDATE — INTERNAL FINDINGS ADDRESSED; INDEPENDENT CANDIDATE CERTIFICATION STILL REQUIRED`

The eventual terminal wording is reserved for the final #301 evidence record:

`UMI04 FULL-CLOSURE RECERTIFIED / SEALED / CLOSED`

No document edit, branch commit, CI result, PR merge, or favorable review may
self-issue that terminal status before the complete sequence in section 10.9 is
satisfied.
