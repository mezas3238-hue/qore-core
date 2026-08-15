# QORE-UMI-09-STRUCTURED-HYBRID-SYNTHETIC-COMPOSITION-001

## Status

**PROGRAM D / UMI-09 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #352  
Master roadmap: #303  
Universal Markets / Instruments: #301  
Certified starting baseline: `78142031c1a857d9d5f1c54d5d6b7873d1b0de23`  
Predecessor UMI-08 / #330 / PR #331: CERTIFIED/CLOSED.

## 1. Constitutional boundary

```text
ECONOMIC IDENTITY / COMPONENT GRAPH -> UMI-02 / D04
SYNTHETIC / COMPOSITE IDENTITY CLASS -> UMI-02 / D04
IDENTITY RELATIONSHIP ENDPOINTS / EFFECTIVE MATERIAL -> UMI-02 / D04

GENERIC DERIVATIVE MULTI-LEG COMPOSITION -> UMI-05
CORPORATE-ACTION RIGHTS DISTRIBUTION -> UMI-06
CRYPTO / PERPETUAL CONTRACTUAL QUALIFICATION -> UMI-08

STRUCTURED / HYBRID / SYNTHETIC HIGHER-ORDER PAYOFF QUALIFICATION -> UMI-09

CURRENT PRICE / RATE / YIELD / NAV / IV / MARK OBSERVATION -> UMI-10 / D07
PAYOFF VALUATION / PRICING / TRIGGER EVALUATION -> D07
CALENDAR / SCHEDULE RESOLUTION -> D06
EXERCISE / CONVERSION / CASH / POSITION / SETTLEMENT MUTATION -> D11
ORDER / EXECUTION AUTHORITY -> D10 / D18

RELATIONSHIP ID != CURRENT EFFECTIVE RELATIONSHIP
RELATIONSHIP OBJECT != CROSS-REVISION RESOLVER
CONTRACTUAL TRIGGER != OBSERVED TRIGGER EVENT
AUTOCALL TERMS != AUTOCALL EXECUTED
CONVERSION TERMS != CONVERSION EXECUTED
CAPITAL PROTECTION TERM != ISSUER CREDIT / PAYMENT FINALITY
PARTICIPATION RATIO != CURRENT LEVERAGE / RISK
CONTRACTUAL LEVEL != OBSERVED VALUE
STRUCTURED LEVEL != OPTION STRIKE
EVIDENCE REF != ECONOMIC TRUTH
```

UMI-09 is a declarative semantic layer only. It contains no provider adapter, market-data
read, valuation engine, event detector, execution path, settlement mutation, wallet/custody,
wall clock, implicit identity generation or executable payoff DSL.

## 2. Exact-baseline audit

### 2.1 UMI-02 remains the only economic identity and relationship graph authority

At the certified baseline, UMI-02 already owns:

- `EconomicIdentityId`;
- `IdentityConstructionKind.SYNTHETIC`;
- `IdentityConstructionKind.COMPOSITE`;
- `IdentityRelationship`;
- exact source/target identities;
- effective-from/effective-until material;
- relationship evidence and optional ordinal.

UMI-09 therefore does not create a second economic identity, a second component graph or
shadow copies of relationship endpoints/effective intervals.

A structured component retains the exact immutable UMI-02 `IdentityRelationship` object.

```text
STRUCTURED COMPONENT
= UMI-02 RELATIONSHIP
+ UMI-09 LOCAL PAYOFF ROLE QUALIFICATION
+ UMI-09 EVIDENCE REF
```

The UMI-09 local role does not replace or mutate the UMI-02 relationship code.

### 2.2 UMI-05 already owns narrow derivative composition

UMI-05 already provides `DerivativeCompositionLeg` and `DerivativeCompositionTerms` with
LONG/SHORT/ratio semantics.

Its certified architecture explicitly states that this composition is intentionally narrower
than UMI-09 and reserves higher-order structured/hybrid/synthetic products, capital
protection, embedded non-derivative components and custom payoff transformation to UMI-09.

Therefore:

```text
DERIVATIVE LONG/SHORT/RATIO COMPOSITION
!=
STRUCTURED PRODUCT PAYOFF QUALIFICATION
```

UMI-09 does not import, wrap or relabel `DerivativeCompositionTerms` as a structured feature.

### 2.3 UMI-06 rights are corporate-action authority

UMI-06 `RightsDistributionTerms` describes a corporate action distributing a separate right
identity to holders of a source instrument.

That is not the same semantic as an embedded conversion/exchange right inside a convertible
or structured product.

```text
CORPORATE-ACTION RIGHT
!=
EMBEDDED STRUCTURED CONVERSION RIGHT
```

UMI-09 does not reuse `RightsDistributionTerms` for embedded conversion.

### 2.4 UMI-08 does not close structured-product semantics

UMI-08 adds bounded crypto/perpetual/funding/network contractual qualification only.
It adds no structured payoff, barrier, autocall, conversion or capital-protection authority.

### 2.5 Gap conclusion

Roadmap #301 requires:

`UMI-09 — Structured / hybrid / synthetic composition — Explicit component/payoff
relationships without flattening.`

The current certified baseline contains the identity graph and narrow derivative composition,
but no canonical higher-order structured feature layer closing capital protection,
conversion, barrier/autocall and participation/redemption distinctions without a payoff
engine.

Classification:

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-09 CONTRACT DELTA REQUIRED`

## 3. Candidate inventory

The candidate adds only:

- `StructuredTermsId`;
- `StructuredFeatureId`;
- `StructuredEvidenceRef`;
- `StructuredComponentRoleCode`;
- `StructuredBarrierKindCode`;
- `StructuredObservationScheduleCode`;
- `StructuredLevelUnitCode`;
- `StructuredContractLevelKind`;
- `StructuredBarrierDirection`;
- `StructuredObservationMode`;
- `StructuredParticipationDirection`;
- `StructuredPositiveRatio`;
- `StructuredContractLevel`;
- `StructuredObservationTerms`;
- `StructuredComponentBinding`;
- `StructuredCapitalProtectionFeature`;
- `StructuredConversionFeature`;
- `StructuredBarrierFeature`;
- `StructuredAutocallFeature`;
- `StructuredParticipationFeature`;
- `StructuredRedemptionFeature`;
- `StructuredHybridSyntheticTerms`.

No provider, account, execution, market observation, valuation or settlement type is added.

## 4. Local identities and evidence

`StructuredTermsId` identifies one immutable UMI-09 terms artifact.

`StructuredFeatureId` identifies one immutable higher-order structured feature.

`StructuredEvidenceRef` is an opaque reference to retained evidence.

None is an `EconomicIdentityId`. None generates UUIDs implicitly.

The candidate uses exact `UUID` objects supplied by the caller and fails closed on other
runtime types.

## 5. Direct component binding

`StructuredComponentBinding` retains:

- root `EconomicIdentityId`;
- exact UMI-02 `IdentityRelationship`;
- local `StructuredComponentRoleCode`;
- `StructuredEvidenceRef`.

The relationship source must equal the root identity.

The component economic identity is the relationship target.

The candidate does not copy:

- source identity;
- target identity;
- effective-from;
- effective-until;
- relationship ordinal.

Those values remain inside the exact UMI-02 relationship object.

### 5.1 Relationship ordering

If any component relationship uses `ordinal`, all must use it.

When ordinals are present:

- they must be unique;
- they must be contiguous from 1;
- component order is canonicalized by ordinal.

When all ordinals are absent:

- component order is canonicalized by stable relationship ID.

Mixed ordinal/no-ordinal material fails closed because its intended semantic ordering is
ambiguous.

### 5.2 Relationship revisions

Distinct relationship IDs are never silently deduplicated merely because target identity and
local structured role match.

That preserves evidence for separate effective-dated relationship revisions.

UMI-09 does **not** choose which revision is current or valid as-of an instant.

The inherited UMI-02 cross-revision resolver obligation remains open.

```text
RETAINED EFFECTIVE-DATED RELATIONSHIPS
!=
CURRENT RELATIONSHIP RESOLVED
```

## 6. Structured contractual levels

`StructuredContractLevel` is a dedicated UMI-09 carrier with:

- finite exact `Decimal`;
- explicit `StructuredContractLevelKind`;
- exact reference `EconomicIdentityId`;
- explicit `StructuredLevelUnitCode`.

Kinds are:

- PRICE;
- RATE;
- YIELD;
- SPREAD;
- LEVEL.

No blanket positivity rule is applied because legitimate rates/spreads/levels may be zero or
negative.

The unit/quotation code prevents magnitude-only interpretation.

This type is intentionally **not** `DerivativeStrike`.

```text
SAME DECIMAL CARRIER SHAPE
!=
SAME BUSINESS SEMANTIC
```

A structured barrier or conversion level must not become an option strike merely for reuse.

The level is contractual specification only; it is not a current market observation.

## 7. Observation cadence

Barrier/autocall terms may need contractual observation cadence without D06 leakage.

`StructuredObservationTerms` distinguishes:

- `CONTINUOUS`;
- `DISCRETE`.

CONTINUOUS carries no explicit dates and no schedule code.

DISCRETE requires exactly one mode:

- non-empty exact `date` tuple; or
- `StructuredObservationScheduleCode`.

Explicit dates are unique and canonicalized chronologically.

`datetime` is rejected for date-only roles.

A schedule code grants no calendar/scheduler authority.

```text
OBSERVATION SCHEDULE CODE != SCHEDULE RESOLVED
CONTRACTUAL OBSERVATION DATE != OBSERVED EVENT
```

## 8. Capital protection

`StructuredCapitalProtectionFeature` retains:

- feature ID;
- protected component identity;
- positive exact protected-principal ratio;
- evidence.

No artificial upper bound of 1 is imposed.

A contractual ratio above 1 remains representable if supported by actual product terms.

Presence of this feature does not prove:

- issuer solvency;
- guarantor solvency;
- current value;
- payment;
- settlement finality.

```text
CAPITAL PROTECTION TERM != GUARANTEED ECONOMIC OUTCOME
```

## 9. Conversion / exchange

`StructuredConversionFeature` retains:

- target component identity;
- positive exact units-per-source-unit ratio;
- optional dedicated structured contractual level;
- evidence.

It performs no conversion, exercise, asset transfer or corporate action.

The target identity must be present as a direct component target of the top-level structured
terms.

## 10. Barrier

`StructuredBarrierFeature` retains:

- reference component identity;
- extensible barrier-kind code;
- direction (`AT_OR_ABOVE` / `AT_OR_BELOW`);
- typed contractual level;
- contractual observation cadence;
- evidence.

The level reference identity must exactly match the barrier reference identity.

It detects no crossing, touch, knock-in or knock-out event.

## 11. Autocall

`StructuredAutocallFeature` retains:

- reference component identity;
- typed trigger level;
- contractual observation cadence;
- positive exact redemption ratio;
- evidence.

The trigger level reference must match the autocall reference identity.

The object does not evaluate market observations and does not create a lifecycle event,
redemption, cash transfer or position mutation.

## 12. Participation / inverse transformation

`StructuredParticipationFeature` retains:

- reference component identity;
- `POSITIVE` or `INVERSE` contractual direction;
- positive exact participation ratio;
- evidence.

This allows leveraged/inverse payoff qualification without making a current leverage, margin,
exposure or risk claim.

```text
CONTRACTUAL PARTICIPATION != CURRENT RISK STATE
```

## 13. Redemption

`StructuredRedemptionFeature` retains:

- redemption component identity;
- positive exact redemption ratio;
- optional exact contractual `date`;
- evidence.

The date is a contract term, not proof that redemption occurred.

The feature mutates no cash or positions.

## 14. Top-level terms

`StructuredHybridSyntheticTerms` requires:

- local terms ID;
- root economic identity;
- non-empty immutable component tuple;
- non-empty immutable UMI-09 feature tuple;
- evidence.

Every component root must equal the top-level instrument identity.

Duplicate UMI-02 relationship IDs fail closed.

Duplicate feature IDs fail closed.

Components and features are canonicalized independently of caller tuple order.

Every economic identity referenced by a UMI-09 feature must appear as a direct component
target.

This rule mechanically binds higher-order payoff qualification to the explicit UMI-02 graph
rather than allowing detached arbitrary identifiers.

## 15. UMI-05 laundering prevention

A pure UMI-05 `DerivativeCompositionTerms` object is not a valid UMI-09 feature.

UMI-09 requires at least one certified UMI-09 higher-order feature.

Therefore a LONG/SHORT/ratio basket does not acquire structured-product status by wrapping.

```text
UMI-05 COMPOSITION EXISTS
!=
UMI-09 STRUCTURED FEATURE EXISTS
```

## 16. No executable payoff DSL

The candidate contains no:

- expression string;
- Python code;
- callback;
- callable;
- AST;
- `eval`;
- `exec`;
- generic mutable parameter dictionary;
- script;
- formula interpreter.

The model is typed declarative contractual material only.

```text
PAYOFF SEMANTICS != EXECUTABLE PAYOFF PROGRAM
```

## 17. Determinism and safety

All candidate dataclasses use `frozen=True, slots=True`.

Required invariants include:

- explicit local UUIDs;
- exact typed economic identities;
- exact UMI-02 relationship objects;
- immutable tuples;
- strict date-only roles;
- finite Decimals;
- positive ratios only where the ratio semantic requires positivity;
- canonical Decimal representation;
- canonical component ordering;
- canonical feature ordering;
- deterministic nested `logical_values()`;
- no `datetime.now()`;
- no `date.today()`;
- no `uuid4()`;
- no random;
- no mutable global state;
- no hidden retry/sleep/thread/scheduler;
- no secret-bearing generic text.

## 18. Mandatory PRE-CHK matrix

### PRE-CHK-UMI09-00 — SECOND IDENTITY GRAPH

Attack copied component endpoints/effective dates or a UMI-09 graph.

PASS requires exact UMI-02 `IdentityRelationship` retention.

### PRE-CHK-UMI09-01 — UMI-05 DUPLICATION

Attack wrapping `DerivativeCompositionTerms` as UMI-09.

PASS requires rejection unless actual UMI-09 typed higher-order features exist.

### PRE-CHK-UMI09-02 — CORPORATE ACTION / EMBEDDED RIGHT COLLAPSE

Attack reuse of UMI-06 rights distribution as conversion authority.

PASS requires separate conversion semantics.

### PRE-CHK-UMI09-03 — TRIGGER SPEC / OBSERVED EVENT COLLAPSE

Attack barrier/autocall objects for event state or detector methods.

PASS requires contractual specification only.

### PRE-CHK-UMI09-04 — PAYOFF TERMS / VALUATION ENGINE

Attack calculate/price/evaluate methods or current quantitative observations.

PASS requires none.

### PRE-CHK-UMI09-05 — CAPITAL PROTECTION / GUARANTEED VALUE CLAIM

Attack contractual protection as issuer/guarantor solvency or payment proof.

PASS requires no credit/finality field.

### PRE-CHK-UMI09-06 — CONVERSION TERMS / CONVERSION EXECUTION

Attack convert/exercise/transfer methods.

PASS requires none.

### PRE-CHK-UMI09-07 — LEVERAGED-INVERSE / CURRENT RISK CLAIM

Attack participation ratio as margin/leverage/exposure state.

PASS requires contract ratio only.

### PRE-CHK-UMI09-08 — BASKET / UNIVERSAL VALUATION

Attack component set as automatically valued basket.

PASS requires no valuation.

### PRE-CHK-UMI09-09 — OPAQUE RELATIONSHIP ID

Attack relationship ID alone where endpoint/effective proof is required.

PASS requires exact `IdentityRelationship`.

### PRE-CHK-UMI09-10 — REVERSED DIRECT EDGE

Attack component relationship whose source is not the root.

PASS requires fail closed.

### PRE-CHK-UMI09-11 — EFFECTIVE-DATED OBJECT / CURRENT REVISION CLAIM

Attack presence of relationship revisions as proof of currentness.

PASS requires no resolver/current flag.

### PRE-CHK-UMI09-12 — LINEAR COMPOSITION LAUNDERING

Attack pure LONG/SHORT/ratio derivative composition.

PASS requires rejection as UMI-09 feature.

### PRE-CHK-UMI09-13 — EXECUTABLE PAYOFF PAYLOAD

Attack scripts/formulas/callbacks/AST/generic mutable dict.

PASS requires none.

### PRE-CHK-UMI09-14 — CONTRACT LEVEL / OPTION STRIKE COLLAPSE

Attack reuse of option strike business semantics.

PASS requires dedicated structured contractual level.

### PRE-CHK-UMI09-15 — LOCAL ROLE / UMI-02 RELATIONSHIP ROLE COLLAPSE

Attack local structured role as replacement for canonical relationship meaning.

PASS requires both exact relationship object and separate local role.

### PRE-CHK-UMI09-16 — CAPITAL PROTECTION / CREDIT FINALITY

Attack a protection feature for payment-capacity/finality claims.

PASS requires none.

### PRE-CHK-UMI09-17 — AUTOCALL / LIFECYCLE EVENT

Attack autocall terms for recorded lifecycle status.

PASS requires no lifecycle event.

### PRE-CHK-UMI09-18 — CONVERTIBLE / RIGHTS DISTRIBUTION

Attack UMI-06 distributed rights for embedded conversion.

PASS requires separate UMI-09 conversion feature.

### PRE-CHK-UMI09-19 — SYNTHETIC IDENTITY / SYNTHETIC PAYOFF

Attack UMI-02 `construction=SYNTHETIC` as complete payoff semantics.

PASS requires explicit UMI-09 components/features.

### PRE-CHK-UMI09-20 — EVIDENCE REF / ECONOMIC TRUTH

Attack evidence-ref presence as proof external terms are correct.

PASS requires only opaque reference semantics and no self-attestation.

## 19. Authority map

| Material | Authority |
|---|---|
| Economic identity / synthetic/composite classification | UMI-02 / D04 |
| Relationship endpoints/effective material | UMI-02 / D04 |
| Relationship cross-revision resolution | UMI-02 future governed resolver |
| Fixed-income economics | UMI-03 |
| Generic derivatives + narrow derivative composition | UMI-05 |
| Corporate-action rights | UMI-06 |
| Crypto/perpetual semantics | UMI-08 |
| Structured higher-order contractual qualification | UMI-09 |
| Calendar/schedule resolution | D06 |
| Observed values / valuation / trigger evaluation | UMI-10 / D07 |
| Account/collateral/risk | D08 / D09 |
| Execution | D10 / D18 |
| Exercise/conversion/settlement mutation | D11 |

## 20. Required adversarial tests

At minimum attack:

- local IDs masquerading as economic identity;
- wrong UUID wrapper types;
- malformed/credential-like canonical codes;
- reversed component edge;
- opaque relationship ID in place of exact relationship;
- mixed/duplicate/noncontiguous ordinals;
- caller-order dependence;
- duplicate relationship IDs;
- separate same-target/role relationship revisions being silently deduplicated;
- non-finite contractual levels;
- false positivity on rate-style levels;
- missing unit/quotation semantics;
- continuous observation with illegal date/schedule material;
- discrete observation with neither/both modes;
- duplicate dates;
- datetime laundering into date-only roles;
- barrier/autocall reference mismatch;
- detached feature identity not present in component graph;
- pure UMI-05 derivative composition laundering;
- duplicate feature IDs;
- executable/valuation/execution/settlement methods;
- mutation of frozen terms;
- nondeterministic nested logical values.

## 21. Non-claims

This stage does not certify:

- any specific structured product;
- any issuer;
- any guarantor;
- any exchange/provider/platform;
- valuation;
- fair value;
- barrier hit;
- autocall event;
- exercise/conversion;
- cash/position settlement;
- current leverage/risk;
- provider support;
- production readiness;
- real-capital authorization.

## 22. Carry-forwards

Remain unchanged:

- `GAP-FND04-TIME-01` / #333 — OPEN / HIGH;
- `GAP-FND07-RES-01` / #332 — OPEN / HIGH;
- PR #298 — HOLD;
- `GAP-EXEC` — OPEN / HIGH;
- `GAP-ANALYSIS-PRODUCER` — OPEN / HIGH;
- `GAP-LIN-001` — OPEN / HIGH;
- UMI-02 cross-revision effective-interval resolver obligation — OPEN.

## 23. Gate discipline

`CERTIFIED BASELINE -> AUDIT -> MINIMUM ARCHITECTURE -> IMPLEMENTATION ->
ADVERSARIAL TESTS -> DIFF AUDIT -> DRAFT PR -> EXACT-HEAD CI -> FREEZE ->
INDEPENDENT CLAUDE REVIEW -> INTEGRATION GATE -> EXPECTED-HEAD MERGE ->
POST-MERGE VERIFICATION -> BASELINE FREEZE -> UMI-09 CLOSED`

`CI GREEN != ENGINEERING APPROVAL`

`NO INDEPENDENT REVIEW -> NO READY -> NO MERGE`

`MERGED != CERTIFIED`
