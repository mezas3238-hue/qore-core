# QORE-UMI-09-STRUCTURED-HYBRID-SYNTHETIC-COMPOSITION-001

## Status

**PROGRAM D / UMI-09 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #352  
Master roadmap: #303  
Universal Markets / Instruments: #301  
Certified starting baseline: `78142031c1a857d9d5f1c54d5d6b7873d1b0de23`  
Predecessor UMI-08 / #330 / PR #331: CERTIFIED/CLOSED.

## 1. Stage objective

Roadmap #301 requires:

`UMI-09 — Structured / hybrid / synthetic composition — Explicit component/payoff relationships without flattening.`

UMI-09 closes the missing provider-neutral **higher-order contractual qualification** layer.
It does not become a pricing engine, market-observation source, event detector, execution
engine, settlement engine, provider adapter or parallel identity graph.

## 2. Constitutional authority map

```text
ECONOMIC IDENTITY / SYNTHETIC-COMPOSITE CLASSIFICATION -> UMI-02 / D04
IDENTITY RELATIONSHIPS / ENDPOINTS / EFFECTIVE MATERIAL -> UMI-02 / D04
IDENTITY RELATIONSHIP ORDINAL SEMANTICS -> UMI-02 / D04

FIXED-INCOME ECONOMICS -> UMI-03
GENERIC DERIVATIVE CONTRACTS + NARROW LONG/SHORT/RATIO COMPOSITION -> UMI-05
CORPORATE-ACTION RIGHTS DISTRIBUTION -> UMI-06
CRYPTO / PERPETUAL / FUNDING / NETWORK QUALIFICATION -> UMI-08

HIGHER-ORDER STRUCTURED / HYBRID / SYNTHETIC CONTRACT QUALIFICATION -> UMI-09

CALENDAR / SCHEDULE RESOLUTION -> D06
CURRENT VALUE OBSERVATION / PAYOFF VALUATION / TRIGGER EVALUATION -> UMI-10 / D07
ACCOUNT / COLLATERAL / CURRENT RISK -> D08 / D09
ORDER / EXECUTION AUTHORITY -> D10 / D18
EXERCISE / CONVERSION / CASH / POSITION / SETTLEMENT MUTATION -> D11
```

Hard distinctions:

```text
RELATIONSHIP OBJECT != CROSS-REVISION CURRENTNESS RESOLVER
RELATIONSHIP ORDINAL != UMI-09 GLOBAL COMPONENT ORDINAL
CONTRACTUAL TRIGGER != OBSERVED TRIGGER EVENT
AUTOCALL TERMS != AUTOCALL EXECUTED
CONVERSION TERMS != CONVERSION EXECUTED
CAPITAL PROTECTION TERM != CREDIT / PAYMENT FINALITY
PARTICIPATION RATIO != CURRENT LEVERAGE / RISK
CONTRACTUAL LEVEL != OBSERVED VALUE
STRUCTURED CONTRACT LEVEL != OPTION STRIKE
EVIDENCE REF != ECONOMIC TRUTH
```

## 3. Exact-baseline repository audit

### 3.1 UMI-02 identity authority

At the certified baseline UMI-02 already owns:

- `EconomicIdentityId`;
- `IdentityConstructionKind.SYNTHETIC`;
- `IdentityConstructionKind.COMPOSITE`;
- immutable effective-dated `IdentityRelationship`;
- exact source/target identities;
- relationship code;
- evidence and optional positive `ordinal`.

UMI-09 therefore does not create another economic identity or another relationship graph.
Direct component bindings retain the exact UMI-02 relationship object.

### 3.2 Exact owner meaning of `IdentityRelationship.ordinal`

UMI-02 architecture states that optional positive `ordinal` preserves ordered composition
where leg ordering is material. It does **not** define one global ordinal sequence over every
relationship attached to an instrument.

The certified UMI-02 graph mechanically scopes ordinal uniqueness by:

```text
source_identity_id
+ relationship code
+ effective_from
+ effective_until
+ ordinal
```

and canonicalizes the graph relationship collection by `relationship_id`, not ordinal.

UMI-02 does not require:

- every relationship for one source to carry an ordinal;
- ordinals across heterogeneous relationship codes to be globally unique;
- ordinals to be contiguous from 1 across an arbitrary UMI-09 component set;
- UMI-09 to reinterpret the owner field as its own sequence authority.

Therefore UMI-09 MUST preserve any UMI-02 ordinal inside the retained relationship but MUST NOT
use it to impose a UMI-09-global ordering or additional all-present/contiguous constraints.

Frozen law:

```text
UMI-02 RELATIONSHIP ORDINAL -> RETAIN EXACTLY
UMI-09 COMPONENT CANONICAL ORDER -> RELATIONSHIP ID
UMI-09 VALIDITY != UMI-02 GRAPH-LEVEL VALIDITY CERTIFICATION
```

If future structured payoff semantics require a new UMI-09-specific semantic leg order that is
not already represented by UMI-02 owner semantics, that must be introduced explicitly as a
future typed UMI-09 contract rather than laundering `IdentityRelationship.ordinal`.

### 3.3 UMI-05 remains narrower

UMI-05 provides `DerivativeCompositionLeg` / `DerivativeCompositionTerms` with explicit local
`DerivativeLegOrdinal`, LONG/SHORT and ratio semantics. Its certified architecture explicitly
states this composition is narrower than UMI-09 and reserves higher-order structured/hybrid/
synthetic products, capital protection, embedded non-derivative components and custom payoff
transformation to UMI-09.

```text
UMI-05 DERIVATIVE COMPOSITION != UMI-09 STRUCTURED PAYOFF QUALIFICATION
```

The local UMI-05 `DerivativeLegOrdinal` precedent also demonstrates that family-specific leg
ordering is owned explicitly by that family rather than inferred from unrelated generic graph
material.

### 3.4 UMI-06 corporate-action rights remain separate

UMI-06 `RightsDistributionTerms` is corporate-action distribution authority. An embedded
conversion/exchange right inside a convertible or structured product is not a corporate-action
right merely because both can reference another identity.

### 3.5 UMI-08 does not close UMI-09

UMI-08 adds crypto/perpetual/funding/network contractual qualification only. It introduces no
structured capital-protection, conversion, barrier, autocall, participation or redemption
contract authority.

### 3.6 Gap classification

Direct post-UMI08 audit therefore establishes:

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-09 CONTRACT DELTA REQUIRED`

## 4. Candidate contract families

UMI-09 adds only:

- local terms/feature/evidence IDs;
- canonical local role and code values;
- a dedicated structured contractual level carrier;
- contractual observation cadence;
- direct component binding over exact UMI-02 relationship material;
- capital-protection feature;
- conversion/exchange feature;
- barrier feature;
- autocall feature;
- participation/inverse feature;
- redemption feature;
- one top-level structured/hybrid/synthetic terms aggregate.

No provider/account/market-observation/valuation/execution/settlement authority is added.

## 5. Local IDs and evidence

`StructuredTermsId`, `StructuredFeatureId` and `StructuredEvidenceRef` are local exact UUID-backed
values supplied explicitly by the caller.

They are not `EconomicIdentityId`. No implicit `uuid4()` exists.

## 6. Direct component binding

`StructuredComponentBinding` retains:

- root `EconomicIdentityId`;
- exact UMI-02 `IdentityRelationship`;
- UMI-09 local component/payoff role;
- UMI-09 evidence reference.

The relationship source must equal the root identity. The component identity is the relationship
target.

UMI-09 does not copy source/target/effective interval/ordinal fields into a shadow graph.

The local UMI-09 role does not overwrite the UMI-02 relationship code.

### 6.1 Component collection canonicalization

Top-level UMI-09 components are a set-like collection of explicit graph bindings for the
minimum stage. Their deterministic collection order is canonicalized only by stable
`relationship_id`.

Any optional relationship ordinal remains embedded in each relationship's own logical material.
It neither changes top-level order nor creates a UMI-09 validation rule.

Mixed ordinal/non-ordinal relationships are therefore representable.
Non-contiguous ordinals are representable.
Same numeric ordinal in different UMI-02 scopes is representable.

This does **not** assert that an arbitrary set of relationships is valid under the full UMI-02
graph. Governed composition must still validate UMI-02 graph-level invariants where that claim
is required.

### 6.2 Relationship revisions

Distinct relationship IDs are retained even when target identity and UMI-09 local role coincide.
This prevents silent loss of effective-dated relationship revisions.

UMI-09 does not choose which revision is current/as-of. The inherited UMI-02 cross-revision
resolver obligation remains open.

## 7. Primary payoff identity versus contractual level reference

Every feature has one primary payoff identity:

- capital protection -> protected identity;
- conversion -> conversion target;
- barrier -> reference identity;
- autocall -> reference identity;
- participation -> reference identity;
- redemption -> redemption identity.

Every primary payoff identity must be a direct component target.

A nested `StructuredContractLevel.reference_identity_id` is contractual quotation/reference
context. It is not automatically a component identity.

Frozen law:

```text
PRIMARY PAYOFF IDENTITY -> DIRECT COMPONENT TARGET
LEVEL REFERENCE / QUOTATION CONTEXT != AUTOMATIC COMPONENT
```

Barrier and autocall levels are structurally about their primary reference, so their level
reference must match that primary reference.

A conversion level may legitimately use a distinct quotation/reference identity; UMI-09 must
not invent a fake UMI-02 component edge solely because that level context exists.

## 8. Structured contractual level

`StructuredContractLevel` retains:

- finite exact `Decimal`;
- PRICE / RATE / YIELD / SPREAD / LEVEL semantic kind;
- exact reference `EconomicIdentityId`;
- explicit unit/quotation code.

There is no universal positivity constraint because valid rates/spreads/levels can be zero or
negative. Decimal zero is an explicitly tested acceptance path and canonicalizes to `"0"`.

This type is deliberately not UMI-05 `DerivativeStrike`.

```text
SAME NUMERIC SHAPE != SAME BUSINESS SEMANTIC
```

## 9. Contractual observation cadence

`StructuredObservationTerms` distinguishes CONTINUOUS and DISCRETE contractual observation.

CONTINUOUS carries neither dates nor a schedule code.

DISCRETE requires exactly one of:

- non-empty immutable exact `date` tuple; or
- typed externally governed schedule code.

Explicit dates are unique and canonicalized chronologically. `datetime` laundering into a
date-only role fails closed.

A schedule code grants no D06 scheduler/calendar authority.

## 10. Higher-order features

### Capital protection

Retains protected component identity, positive exact protected-principal ratio and evidence.
No artificial upper cap is imposed. It does not prove issuer/guarantor solvency, payment or
finality.

### Conversion / exchange

Retains target component identity, positive units-per-source-unit ratio, optional dedicated
structured contractual level and evidence. It performs no exercise/conversion/transfer.

### Barrier

Retains reference component identity, extensible barrier-kind code, above/below direction,
typed contractual level, contractual observation cadence and evidence. It detects no event.

### Autocall

Retains reference component identity, typed trigger level, contractual observation cadence,
positive redemption ratio and evidence. It creates no lifecycle event or redemption mutation.

### Participation / inverse

Retains reference component identity, POSITIVE/INVERSE contractual direction, positive
participation ratio and evidence. It does not calculate current leverage, margin, exposure or
risk.

### Redemption

Retains redemption component identity, positive redemption ratio, optional exact contractual
`date` and evidence. It performs no cash/position settlement mutation.

## 11. Top-level terms

`StructuredHybridSyntheticTerms` requires:

- local terms ID;
- root economic identity;
- non-empty immutable component tuple;
- non-empty immutable certified UMI-09 feature tuple;
- evidence.

Rules:

- every component root equals the top-level instrument identity;
- relationship IDs are unique;
- components canonicalize by relationship ID only;
- UMI-02 ordinal material is preserved but never reinterpreted;
- feature IDs are unique;
- features canonicalize by feature ID;
- every primary payoff identity is a direct component target;
- nested `logical_values()` is deterministic.

## 12. UMI-05 laundering prevention

A UMI-05 `DerivativeCompositionTerms` object is not a certified UMI-09 feature. A pure
LONG/SHORT/ratio derivative composition therefore cannot acquire UMI-09 status by wrapping.

## 13. No executable payoff DSL

Candidate source contains no:

- formula/expression payload;
- Python callback/callable;
- AST;
- `eval`/`exec`;
- script;
- generic mutable parameter dictionary;
- hidden payoff interpreter.

Declarative typed contractual material is the full scope.

## 14. Determinism and fail-closed guarantees

All UMI-09 dataclasses are frozen and slotted.

The candidate uses explicit IDs, immutable tuples, strict date-only validation, finite Decimal
values, positive ratios only where universally required, canonical Decimal representation,
deterministic relationship-ID component order, deterministic feature-ID order and complete
nested logical material.

No `datetime.now()`, `date.today()`, `uuid4()`, random, mutable global state, hidden retry,
sleep, thread or scheduler is introduced.

## 15. Mandatory PRE-CHK matrix

`PRE-CHK-UMI09-00 — SECOND IDENTITY GRAPH`  
No parallel component graph; exact UMI-02 relationship retained.

`PRE-CHK-UMI09-01 — UMI-05 DUPLICATION`  
Pure derivative composition is not UMI-09.

`PRE-CHK-UMI09-02 — CORPORATE ACTION / EMBEDDED RIGHT COLLAPSE`  
UMI-06 rights distribution remains distinct.

`PRE-CHK-UMI09-03 — TRIGGER SPEC / OBSERVED EVENT COLLAPSE`  
Barrier/autocall specification does not detect an event.

`PRE-CHK-UMI09-04 — PAYOFF TERMS / VALUATION ENGINE`  
No valuation/pricing/evaluation engine.

`PRE-CHK-UMI09-05 — CAPITAL PROTECTION / GUARANTEED VALUE CLAIM`  
Contractual protection does not prove economic outcome.

`PRE-CHK-UMI09-06 — CONVERSION TERMS / CONVERSION EXECUTION`  
No exercise/conversion/transfer authority.

`PRE-CHK-UMI09-07 — LEVERAGED-INVERSE / CURRENT RISK CLAIM`  
Participation transform is contractual only.

`PRE-CHK-UMI09-08 — BASKET / UNIVERSAL VALUATION`  
Composition does not produce current value.

`PRE-CHK-UMI09-09 — OPAQUE RELATIONSHIP ID`  
Exact relationship object is required where endpoint/effective material matters.

`PRE-CHK-UMI09-10 — REVERSED DIRECT EDGE`  
Component relationship source must equal root.

`PRE-CHK-UMI09-11 — EFFECTIVE-DATED OBJECT / CURRENT REVISION CLAIM`  
No relationship-currentness claim.

`PRE-CHK-UMI09-12 — LINEAR COMPOSITION LAUNDERING`  
UMI-05 composition cannot satisfy UMI-09 feature type.

`PRE-CHK-UMI09-13 — EXECUTABLE PAYOFF PAYLOAD`  
No executable DSL.

`PRE-CHK-UMI09-14 — CONTRACT LEVEL / OPTION STRIKE COLLAPSE`  
Dedicated structured level retained.

`PRE-CHK-UMI09-15 — LOCAL ROLE / UMI-02 RELATIONSHIP ROLE COLLAPSE`  
Local payoff role does not replace UMI-02 relationship meaning.

`PRE-CHK-UMI09-16 — CAPITAL PROTECTION / CREDIT FINALITY`  
No creditworthiness/payment-finality state.

`PRE-CHK-UMI09-17 — AUTOCALL / LIFECYCLE EVENT`  
Autocall specification is not lifecycle evidence.

`PRE-CHK-UMI09-18 — CONVERTIBLE / RIGHTS DISTRIBUTION`  
Embedded conversion is not corporate-action rights distribution.

`PRE-CHK-UMI09-19 — SYNTHETIC IDENTITY / SYNTHETIC PAYOFF`  
UMI-02 SYNTHETIC classification does not define payoff semantics.

`PRE-CHK-UMI09-20 — EVIDENCE REF / ECONOMIC TRUTH`  
Opaque evidence reference is not self-attestation.

`PRE-CHK-UMI09-21 — LEVEL REFERENCE / PAYOFF COMPONENT COLLAPSE`  
Primary payoff identities require component binding; level quotation context does not create a
fake component.

`PRE-CHK-UMI09-22 — UMI-02 ORDINAL / UMI-09 GLOBAL ORDER COLLAPSE`  
UMI-09 must preserve owner ordinal material without imposing all-present, global uniqueness,
contiguity or sort-by-ordinal rules. Component collection canonical order is relationship ID.

## 16. Required ordinal adversarial oracles

Independent review must verify at least:

1. mixed `ordinal` / `None` relationships remain representable;
2. non-contiguous UMI-02 ordinal values remain representable;
3. same numeric ordinal in distinct UMI-02 scopes remains representable;
4. caller tuple order does not alter UMI-09 logical material;
5. UMI-09 orders component collection by relationship ID, not ordinal;
6. the ordinal remains intact inside each retained relationship logical value;
7. UMI-09 does not claim graph-level validity/currentness merely because terms construct.

## 17. Non-claims

A favorable UMI-09 certification does not establish:

- a specific structured product;
- issuer or guarantor credit quality;
- provider/platform support;
- current valuation or fair value;
- barrier hit;
- autocall event;
- conversion/exercise;
- cash/position settlement;
- current leverage/risk;
- UMI-02 graph-level relationship set certification;
- cross-revision currentness resolution;
- Production readiness;
- real-capital authorization.

## 18. Carry-forwards

Remain open/HOLD:

- `GAP-FND04-TIME-01` / #333 — OPEN / HIGH;
- `GAP-FND07-RES-01` / #332 — OPEN / HIGH;
- PR #298 — HOLD;
- `GAP-EXEC` — OPEN / HIGH;
- `GAP-ANALYSIS-PRODUCER` — OPEN / HIGH;
- `GAP-LIN-001` — OPEN / HIGH;
- UMI-02 cross-revision effective-interval resolver obligation — OPEN.

## 19. Gate discipline

`CERTIFIED BASELINE -> AUDIT -> MINIMUM ARCHITECTURE -> IMPLEMENTATION -> ADVERSARIAL TESTS
-> DIFF AUDIT -> DRAFT PR -> EXACT-HEAD CI -> FREEZE -> INDEPENDENT CLAUDE REVIEW ->
INTEGRATION GATE -> EXPECTED-HEAD MERGE -> POST-MERGE VERIFICATION -> BASELINE FREEZE ->
UMI-09 CLOSED`

`CI GREEN != ENGINEERING APPROVAL`

`NO INDEPENDENT REVIEW -> NO READY -> NO MERGE`

`MERGED != CERTIFIED`
