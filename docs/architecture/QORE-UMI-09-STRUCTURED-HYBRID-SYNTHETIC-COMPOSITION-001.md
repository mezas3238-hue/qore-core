# QORE-UMI-09-STRUCTURED-HYBRID-SYNTHETIC-COMPOSITION-001

## Status

**PROGRAM D / UMI-09 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: #352  
Master roadmap: #303  
Universal Markets / Instruments: #301  
Certified starting baseline: `78142031c1a857d9d5f1c54d5d6b7873d1b0de23`  
Predecessor UMI-08 / #330 / PR #331: CERTIFIED/CLOSED.

## 1. Stage purpose

Roadmap #301 requires:

`UMI-09 — Structured / hybrid / synthetic composition — Explicit component/payoff relationships without flattening.`

UMI-09 closes only the missing higher-order **contractual qualification** layer. It does not
become a pricing engine, event detector, settlement engine, provider adapter or second
identity graph.

## 2. Constitutional boundary

```text
ECONOMIC IDENTITY / COMPONENT GRAPH -> UMI-02 / D04
SYNTHETIC / COMPOSITE IDENTITY CLASS -> UMI-02 / D04
IDENTITY RELATIONSHIP ENDPOINTS / EFFECTIVE MATERIAL -> UMI-02 / D04

FIXED-INCOME ECONOMICS -> UMI-03
GENERIC DERIVATIVE CONTRACTS / LONG-SHORT-RATIO COMPOSITION -> UMI-05
CORPORATE-ACTION RIGHTS DISTRIBUTION -> UMI-06
CRYPTO / PERPETUAL QUALIFICATION -> UMI-08

HIGHER-ORDER STRUCTURED / HYBRID / SYNTHETIC CONTRACT QUALIFICATION -> UMI-09

CALENDAR / SCHEDULE RESOLUTION -> D06
CURRENT VALUE OBSERVATION / PAYOFF VALUATION / TRIGGER EVALUATION -> UMI-10 / D07
ACCOUNT / COLLATERAL / CURRENT RISK -> D08 / D09
ORDER / EXECUTION AUTHORITY -> D10 / D18
EXERCISE / CONVERSION / CASH / POSITION / SETTLEMENT MUTATION -> D11
```

Hard distinctions:

```text
RELATIONSHIP ID != VERIFIED ENDPOINTS / EFFECTIVE MATERIAL
RELATIONSHIP OBJECT != CROSS-REVISION CURRENTNESS RESOLVER
CONTRACTUAL TRIGGER != OBSERVED TRIGGER EVENT
AUTOCALL TERMS != AUTOCALL EXECUTED
CONVERSION TERMS != CONVERSION EXECUTED
CAPITAL PROTECTION TERM != ISSUER CREDIT / PAYMENT FINALITY
PARTICIPATION RATIO != CURRENT LEVERAGE / RISK
CONTRACTUAL LEVEL != OBSERVED VALUE
STRUCTURED CONTRACT LEVEL != OPTION STRIKE
EVIDENCE REF != ECONOMIC TRUTH
```

## 3. Exact-baseline audit

### 3.1 UMI-02 owns identity and relationships

UMI-02 already owns:

- `EconomicIdentityId`;
- `IdentityConstructionKind.SYNTHETIC` / `COMPOSITE`;
- immutable `IdentityRelationship`;
- exact source and target identities;
- effective-from/effective-until material;
- evidence and optional ordinal.

UMI-09 therefore retains the exact UMI-02 relationship object for direct component edges. It
creates no second economic identity and no shadow relationship graph.

### 3.2 UMI-05 composition remains narrower

UMI-05 already provides `DerivativeCompositionLeg` / `DerivativeCompositionTerms` for
LONG/SHORT/ratio derivative composition. Its certified architecture explicitly states this is
narrower than UMI-09 and reserves higher-order structured/hybrid/synthetic products, capital
protection, embedded non-derivative components and custom payoff transformation to UMI-09.

```text
DERIVATIVE COMPONENT COMPOSITION != STRUCTURED PRODUCT PAYOFF QUALIFICATION
```

### 3.3 UMI-06 corporate-action rights remain separate

`RightsDistributionTerms` represents a corporate action distributing a right identity. An
embedded conversion/exchange right of a convertible or structured product is a different
contractual semantic and is not represented by relabeling a UMI-06 corporate action.

### 3.4 UMI-08 does not close this gap

UMI-08 is crypto/perpetual/funding/network contractual qualification only. It introduces no
capital-protection, conversion, barrier, autocall or structured participation authority.

### 3.5 Gap classification

Direct post-UMI08 baseline audit therefore establishes:

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-09 CONTRACT DELTA REQUIRED`

## 4. Candidate contract families

Candidate source adds only local structured terms/feature/evidence IDs, canonical role/code
values, dedicated structured contractual levels, contractual observation cadence, direct
component binding, six typed higher-order features and one top-level terms aggregate.

No provider, account, market observation, valuation, execution or settlement authority is
introduced.

## 5. Local IDs

`StructuredTermsId`, `StructuredFeatureId` and `StructuredEvidenceRef` are exact UUID-backed
local identities/references.

They are not `EconomicIdentityId` and never generate identity implicitly.

## 6. Direct component graph binding

`StructuredComponentBinding` retains:

- root `EconomicIdentityId`;
- exact UMI-02 `IdentityRelationship`;
- UMI-09 local component/payoff role code;
- UMI-09 evidence ref.

The relationship source must equal the structured root identity. The component identity is the
relationship target.

UMI-09 does not copy source/target/effective fields; those stay in UMI-02 material.

### 6.1 Component ordering

If any retained relationship carries `ordinal`, all component relationships must carry one.
Ordinals must be unique and contiguous from 1; order canonicalizes by ordinal.

If all ordinals are absent, order canonicalizes by stable relationship ID.

Mixed ordinal/no-ordinal inputs fail closed.

### 6.2 Relationship revisions and currentness

Distinct relationship IDs are retained even if target identity and local role coincide. This
avoids silent destruction of effective-dated revision evidence.

UMI-09 does not decide which relationship revision is current/as-of. The inherited UMI-02
cross-revision effective-interval resolver obligation remains open.

## 7. Primary payoff identities versus level reference context

This distinction is mandatory and was explicitly re-falsified before exact-head freeze.

Each UMI-09 feature has a **primary payoff identity**:

- capital protection -> `protected_identity_id`;
- conversion -> `target_identity_id`;
- barrier -> `reference_identity_id`;
- autocall -> `reference_identity_id`;
- participation -> `reference_identity_id`;
- redemption -> `redemption_identity_id`.

Every primary payoff identity must be present as a direct component target.

A nested `StructuredContractLevel.reference_identity_id` is a contractual
reference/quotation context. It is not automatically a payoff component. Requiring every
level reference to become a direct component would create artificial UMI-02 graph edges.

```text
PRIMARY PAYOFF IDENTITY -> DIRECT COMPONENT TARGET
LEVEL REFERENCE / QUOTATION CONTEXT != AUTOMATIC COMPONENT
```

Barrier and autocall levels are structurally about their primary reference, so their level
reference must equal that feature reference.

Conversion is different: a conversion level may legitimately retain a distinct contractual
reference/quotation identity. UMI-09 therefore requires the conversion target itself to be a
direct component but does not invent a second component edge solely because the conversion
level has a distinct reference context.

This distinction is provider-neutral and prevents both detached payoff identities and false
graph inflation.

## 8. Structured contractual level

`StructuredContractLevel` contains:

- finite exact Decimal;
- explicit kind: PRICE / RATE / YIELD / SPREAD / LEVEL;
- exact reference `EconomicIdentityId`;
- explicit unit/quotation code.

No universal positivity rule applies because rates/spreads/levels may validly be zero or
negative.

The type is deliberately distinct from UMI-05 `DerivativeStrike`:

```text
REUSE NUMERIC SHAPE != REUSE BUSINESS MEANING
```

It contains no observed/current value authority.

## 9. Observation cadence

`StructuredObservationTerms` distinguishes CONTINUOUS from DISCRETE contractual observation.

CONTINUOUS carries no explicit dates and no schedule code.

DISCRETE requires exactly one of:

- non-empty immutable exact-date tuple; or
- typed schedule code.

Dates are unique and canonicalized chronologically; `datetime` laundering into date-only
roles fails closed.

The schedule code grants no D06 scheduler/calendar authority.

## 10. Higher-order feature families

### 10.1 Capital protection

Retains protected primary component identity, positive exact principal ratio and evidence.
Does not prove issuer/guarantor solvency, current value, payment or finality. Ratio is not
artificially capped at one.

### 10.2 Conversion / exchange

Retains target primary component identity, positive units-per-source-unit ratio, optional typed
structured contractual level and evidence. Performs no conversion/exercise/transfer.

### 10.3 Barrier

Retains primary reference component, barrier-kind code, above/below direction, typed level,
contractual observation cadence and evidence. The level reference must match the barrier
reference. No event detector exists.

### 10.4 Autocall

Retains primary reference component, typed trigger level, observation cadence, positive
redemption ratio and evidence. Trigger level reference must match primary reference. No
autocall evaluation or lifecycle event is produced.

### 10.5 Participation / inverse transformation

Retains primary reference component, POSITIVE/INVERSE contractual direction, positive exact
participation ratio and evidence. This is not current leverage, margin, exposure or risk.

### 10.6 Redemption

Retains primary redemption component, positive exact redemption ratio, optional exact
contractual date and evidence. It performs no cash/position settlement mutation.

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
- component ordering is canonical under section 6.1;
- feature IDs are unique;
- feature order canonicalizes by feature ID;
- every **primary payoff identity** from section 7 is a direct component target;
- nested logical material is deterministic.

## 12. UMI-05 laundering prevention

A UMI-05 `DerivativeCompositionTerms` object is not a certified UMI-09 feature and fails the
top-level feature-type guard.

A LONG/SHORT/ratio basket therefore does not become a structured product merely because a
wrapper calls it one.

## 13. No executable payoff DSL

Forbidden from candidate source:

- arbitrary formula strings;
- Python expressions;
- callbacks/callables;
- AST payloads;
- `eval` / `exec`;
- scripts;
- generic mutable parameter dictionaries;
- hidden computation engines.

Typed declarative contract material is the only scope.

## 14. Determinism / fail-closed law

All candidate dataclasses are frozen + slots.

Candidate requires explicit identities, immutable tuples, strict date-only roles, finite
Decimals, canonical Decimal serialization, typed enums/codes, deterministic component and
feature order, complete nested logical material, and no hidden clock/random/retry/thread/
scheduler state.

No `datetime.now()`, `date.today()`, `uuid4()` or global mutable registry is introduced.

## 15. Mandatory PRE-CHK matrix

`PRE-CHK-UMI09-00 — SECOND IDENTITY GRAPH`  
Exact UMI-02 relationship retained; no shadow graph.

`PRE-CHK-UMI09-01 — UMI05 DUPLICATION`  
Pure derivative composition is not UMI-09.

`PRE-CHK-UMI09-02 — CORPORATE ACTION / EMBEDDED RIGHT COLLAPSE`  
UMI-06 rights are not embedded conversion authority.

`PRE-CHK-UMI09-03 — TRIGGER SPEC / OBSERVED EVENT COLLAPSE`  
Barrier/autocall terms contain no observed event state.

`PRE-CHK-UMI09-04 — PAYOFF TERMS / VALUATION ENGINE`  
No pricing/calculation/evaluation engine.

`PRE-CHK-UMI09-05 — CAPITAL PROTECTION / GUARANTEED VALUE CLAIM`  
Contractual protection does not prove economic outcome.

`PRE-CHK-UMI09-06 — CONVERSION TERMS / CONVERSION EXECUTION`  
No exercise/convert/transfer authority.

`PRE-CHK-UMI09-07 — LEVERAGED-INVERSE / CURRENT RISK CLAIM`  
Participation is contractual only.

`PRE-CHK-UMI09-08 — BASKET / UNIVERSAL VALUATION`  
Component composition does not calculate value.

`PRE-CHK-UMI09-09 — OPAQUE RELATIONSHIP ID`  
Where endpoints/effective material matter, exact relationship object is required.

`PRE-CHK-UMI09-10 — REVERSED DIRECT EDGE`  
Component relationship source must equal root.

`PRE-CHK-UMI09-11 — EFFECTIVE-DATED OBJECT / CURRENT REVISION CLAIM`  
No as-of/current resolver claim.

`PRE-CHK-UMI09-12 — LINEAR COMPOSITION LAUNDERING`  
UMI-05 composition cannot satisfy UMI-09 feature type.

`PRE-CHK-UMI09-13 — EXECUTABLE PAYOFF PAYLOAD`  
No executable DSL.

`PRE-CHK-UMI09-14 — CONTRACT LEVEL / OPTION STRIKE COLLAPSE`  
Dedicated structured level type retained.

`PRE-CHK-UMI09-15 — LOCAL ROLE / UMI-02 RELATIONSHIP ROLE COLLAPSE`  
Local payoff role never overwrites UMI-02 relationship meaning.

`PRE-CHK-UMI09-16 — CAPITAL PROTECTION / CREDIT FINALITY`  
No creditworthiness/finality state.

`PRE-CHK-UMI09-17 — AUTOCALL / LIFECYCLE EVENT`  
Autocall specification is not recorded lifecycle state.

`PRE-CHK-UMI09-18 — CONVERTIBLE / RIGHTS DISTRIBUTION`  
Embedded conversion is not UMI-06 rights distribution.

`PRE-CHK-UMI09-19 — SYNTHETIC IDENTITY / SYNTHETIC PAYOFF`  
UMI-02 SYNTHETIC classification alone does not define payoff semantics.

`PRE-CHK-UMI09-20 — EVIDENCE REF / ECONOMIC TRUTH`  
Evidence reference is not self-attestation.

## 16. Additional graph-context attack

`PRE-CHK-UMI09-21 — LEVEL REFERENCE / PAYOFF COMPONENT COLLAPSE`

Attack both directions:

1. a primary payoff identity missing from direct components must fail closed;
2. a distinct conversion-level reference/quotation identity must **not** require an artificial
   component edge merely because it is level context.

This PRE-CHK was added during internal falsification before exact-head freeze.

## 17. Test obligations

Adversarial tests cover local-ID typing, code hygiene, exact UMI-02 relationship retention,
reversed edges, opaque relationship-ID laundering, structured level typing/unit semantics,
negative rate-style levels, non-finite values, ratio validation, observation mode/date
validation, barrier/autocall reference binding, graph/root/duplicate/ordinal rules,
relationship-revision retention, UMI-05 composition laundering, feature-ID uniqueness,
caller-order determinism, Decimal canonicalization, frozen state, negative-space authority and
PRE-CHK-UMI09-21 reference-context semantics.

## 18. Authority map

| Material | Authority |
|---|---|
| Economic identity / SYNTHETIC / COMPOSITE | UMI-02 / D04 |
| Relationship endpoints/effective material | UMI-02 / D04 |
| Cross-revision currentness | UMI-02 future governed resolver |
| Fixed-income base economics | UMI-03 |
| Generic derivatives / narrow derivative composition | UMI-05 |
| Corporate-action rights | UMI-06 |
| Crypto/perpetual contract semantics | UMI-08 |
| Higher-order structured contractual qualification | UMI-09 |
| Calendar/schedule resolution | D06 |
| Observed values / payoff valuation / trigger evaluation | UMI-10 / D07 |
| Account/collateral/risk | D08 / D09 |
| Execution | D10 / D18 |
| Exercise/conversion/settlement mutation | D11 |

## 19. Non-claims

A favorable UMI-09 certification does not establish a specific product, issuer or guarantor;
provider/platform support; valuation/fair value; barrier hit; autocall event; conversion or
exercise; cash/position settlement; current leverage/risk; Production readiness; or real
capital authorization.

## 20. Carry-forwards

Remain open/HOLD:

- `GAP-FND04-TIME-01` / #333 — OPEN / HIGH;
- `GAP-FND07-RES-01` / #332 — OPEN / HIGH;
- PR #298 — HOLD;
- `GAP-EXEC` — OPEN / HIGH;
- `GAP-ANALYSIS-PRODUCER` — OPEN / HIGH;
- `GAP-LIN-001` — OPEN / HIGH;
- UMI-02 cross-revision effective-interval resolver obligation — OPEN.

## 21. Gate discipline

`CERTIFIED BASELINE -> AUDIT -> MINIMUM ARCHITECTURE -> IMPLEMENTATION -> ADVERSARIAL TESTS
-> DIFF AUDIT -> DRAFT PR -> EXACT-HEAD CI -> FREEZE -> INDEPENDENT CLAUDE REVIEW ->
INTEGRATION GATE -> EXPECTED-HEAD MERGE -> POST-MERGE VERIFICATION -> BASELINE FREEZE ->
UMI-09 CLOSED`

`CI GREEN != ENGINEERING APPROVAL`

`NO INDEPENDENT REVIEW -> NO READY -> NO MERGE`

`MERGED != CERTIFIED`
