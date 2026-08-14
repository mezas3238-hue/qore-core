# QORE-UMI-07-COMMODITY-CONTRACT-DELIVERY-SEMANTICS-001

## Status

**PROGRAM D / UMI-07 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #328  
Master roadmap: Issue #303  
Universal Markets / Instruments program: Issue #301  
Certified starting baseline: `b44529c8e3caf5badf6ff49da2f0246f3f985219`  
Predecessor: UMI-06 / Issue #326 / PR #327 — CLOSED

This artifact defines the minimum provider-neutral immutable commodity reference and
physical-delivery contractual semantics that remain missing after UMI-02 and UMI-05.

The candidate deliberately **composes** the already-certified UMI-05
`FuturesContractTerms`. It does not create a second futures contract model.

It does **not** implement exchange/provider support, delivery notice ingestion,
calendar resolution, logistics, warehouse inventory, title transfer, physical
settlement, position/cash mutation, pricing, basis/storage/carry calculation,
risk, execution, productive Cloud or real-capital authority.

```text
COMMODITY CONTRACT QUALIFICATION
!=
GENERIC FUTURES CONTRACT SEMANTICS
!=
RECORDED LIFECYCLE EVENT
!=
DELIVERY / LOGISTICS ENGINE
!=
PHYSICAL SETTLEMENT MUTATION
!=
PROVIDER SUPPORT
```

---

# 1. Governing invariants

```text
ECONOMIC / REFERENCE IDENTITY -> UMI-02
LOCAL COMMODITY TERMS ID != ECONOMIC IDENTITY
COMMODITY FAMILY CODE != ECONOMIC IDENTITY
PROVIDER SYMBOL != COMMODITY IDENTITY
VENUE PRODUCT CODE != COMMODITY IDENTITY

CONTRACT MONTH -> UMI-05
CONTRACT EXPIRY -> UMI-05
CONTRACT MULTIPLIER -> UMI-05
CONTRACTUAL TICK VALUE -> UMI-05
CASH / PHYSICAL SETTLEMENT STYLE -> UMI-05
FIRST NOTICE DATE -> UMI-05
LAST TRADE DATE -> UMI-05

RECORDED LIFECYCLE FACT -> UMI-02 IdentityLifecycleEvent
CONTRACTUAL DELIVERY WINDOW != RECORDED LIFECYCLE FACT

COMMODITY REFERENCE IDENTITY != MEASUREMENT-UNIT IDENTITY
COMMODITY FAMILY != GRADE
GRADE != DELIVERY LOCATION
DELIVERY LOCATION != MARKET VENUE
DELIVERY METHOD CODE != SETTLEMENT ENGINE
CONTRACT MULTIPLIER != ORDER / POSITION QUANTITY
MEASUREMENT UNIT IDENTITY != EXECUTION QUANTITY

PHYSICAL FUTURES -> EXPLICIT PHYSICAL DELIVERY TERMS
CASH FUTURES -> NO PHYSICAL DELIVERY TERMS

PHYSICAL DELIVERY TERMS != DELIVERY SELECTION ENGINE
PHYSICAL DELIVERY TERMS != WAREHOUSE INVENTORY
PHYSICAL DELIVERY TERMS != TITLE TRANSFER
PHYSICAL DELIVERY TERMS != POSITION MUTATION
PHYSICAL DELIVERY TERMS != CASH MUTATION

CALLER ALTERNATIVE ORDER != ECONOMIC SEMANTIC
EVIDENCE REF != EVIDENCE CONTENT
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

Repository-wide carry-forwards remain binding:

- `GAP-FND04-TIME-01` — OPEN / HIGH;
- `GAP-FND07-RES-01` — OPEN / HIGH;
- PR #298 — HOLD;
- `GAP-EXEC` — OPEN / HIGH;
- `GAP-ANALYSIS-PRODUCER` — OPEN / HIGH;
- `GAP-LIN-001` — OPEN / HIGH.

UMI-07 does not close, promote or reclassify any of them.

---

# 2. Exact-baseline audit

## 2.1 UMI-02 already owns generic identity and lifecycle

Direct inspection of
`src/qore/infrastructure/universal_instrument_identity.py` at the certified
starting baseline confirms UMI-02 owns:

- `EconomicIdentityId`;
- `EconomicIdentity`;
- `IdentityRelationship`;
- `IdentityLifecycleEvent`;
- `LifecycleEventCode`;
- evidence-bearing effective/recorded times.

`EconomicIdentity` distinguishes tradable instruments from reference objects.
Reference objects explicitly include physical/reference concepts that instruments
may reference without those objects themselves becoming orderable instruments.

`IdentityLifecycleEvent` retains:

- explicit event ID;
- canonical subject;
- extensible event code;
- `effective_at`;
- `recorded_at`;
- evidence reference.

UMI-02 explicitly cites future-family examples such as first notice, last trade
and expiry.

Therefore UMI-07 MUST NOT create:

- a second economic commodity identity;
- a second listing identity;
- a second identity relationship graph;
- a second lifecycle-event history;
- one global commodity lifecycle enum.

```text
COMMODITY TERMS ATTACH TO UMI-02 IDENTITY
!=
COMMODITY TERMS BECOME IDENTITY AUTHORITY
```

## 2.2 UMI-05 already owns generic futures economics

Direct inspection of
`src/qore/infrastructure/derivative_contract_semantics.py` confirms UMI-05 owns:

- `DerivativeContractMonth`;
- `DerivativeContractMultiplier`;
- `DerivativeTickValue`;
- `DerivativeSettlementStyle` (`CASH`, `PHYSICAL`);
- `FuturesContractTerms`.

`FuturesContractTerms` already retains:

- derivative terms ID;
- instrument economic identity;
- reference identity;
- settlement identity;
- contract month;
- expiry date;
- multiplier;
- settlement style;
- evidence;
- optional tick value;
- optional first-notice date;
- optional last-trade date.

It already validates:

- instrument identity differs from reference identity;
- instrument identity differs from settlement identity;
- first notice cannot be after expiry;
- CASH futures cannot carry first-notice date;
- last-trade date cannot be after expiry;
- no false universal first-notice-vs-last-trade ordering.

UMI-07 therefore MUST NOT add parallel fields for any of those semantics.

```text
UMI-07 COMMODITY FUTURES TERMS
-> COMPOSE UMI-05 FuturesContractTerms
-> DO NOT COPY FUTURES FIELDS
```

## 2.3 UMI-05 deliberately leaves commodity delivery completion open

The certified UMI-05 architecture explicitly makes no claim that commodity
delivery lifecycle certification exists.

UMI-05's `PHYSICAL` settlement style establishes only the contractual style. It
does not specify every eligible deliverable grade/location/window/method and it
does not perform settlement.

```text
PHYSICAL SETTLEMENT STYLE
!=
PHYSICAL DELIVERY SPECIFICATION
!=
PHYSICAL SETTLEMENT EXECUTION
```

That gap is the bounded UMI-07 responsibility.

## 2.4 FND-04 forbids numeric/unit flattening

FND-04 freezes:

```text
QUANTITY != NOTIONAL
CONTRACT COUNT != BASE UNITS
MULTIPLIER != QUANTITY
PRICE × QUANTITY != UNIVERSAL ECONOMIC VALUE
NUMERIC REPRESENTATION != ECONOMIC SEMANTIC
```

It also establishes that account-scoped `CurrencyCode` is not a universal
commodity-unit identity.

UMI-07 therefore does not create a generic Decimal `CommodityQuantity` merely to
repeat the quantity implied by a futures multiplier.

Instead:

- UMI-05 multiplier retains the exact per-contract magnitude;
- its `unit_identity_id` identifies the measurement unit/reference;
- UMI-07 `CommodityReferenceTerms` explicitly binds the same measurement-unit
  identity;
- composition requires those identities to match.

```text
CONTRACT MULTIPLIER VALUE + UNIT IDENTITY
IS REUSED
NOT REDECLARED
```

## 2.5 Existing settlement/calendar primitives remain bounded

UMI-03 defines reusable structural calendar conventions such as
`BusinessCalendarRef` and `SettlementConvention`.

Those values do not identify a commodity delivery point, quality grade, warehouse,
pipeline, load-out method or delivery alternative.

UMI-07 therefore does not silently reinterpret a fixed-income settlement type as
a physical commodity delivery specification.

D06 retains calendar/date-resolution authority.

## 2.6 Verified structural gap

At certified baseline `b44529c8e3caf5badf6ff49da2f0246f3f985219`, direct
inspection establishes all of the following simultaneously:

1. generic identity/lifecycle already exists in UMI-02;
2. generic futures economics already exists in UMI-05;
3. physical settlement style alone does not retain deliverable
   grade/location/method/window alternatives;
4. no inspected canonical boundary composes those missing commodity-delivery
   semantics over the existing UMI-05 futures terms;
5. no inspected boundary may safely be promoted into that authority without
   semantic reinterpretation.

Classification:

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-07 CONTRACT DELTA REQUIRED`

Repository search was used only as locator evidence. The architecture conclusion
is grounded in the directly inspected canonical authorities above.

---

# 3. Contract inventory

UMI-07 adds only these local semantic contracts:

- `CommodityTermsId`;
- `CommodityEvidenceRef`;
- `CommodityFamilyCode`;
- `CommodityGradeCode`;
- `CommodityDeliveryMethodCode`;
- `CommodityDeliveryWindow`;
- `CommodityReferenceTerms`;
- `CommodityDeliveryAlternative`;
- `CommodityPhysicalDeliveryTerms`;
- `CommodityFuturesContractTerms`.

No new economic identity, listing, lifecycle event, futures month, expiry,
multiplier, tick-value or settlement-style type is introduced.

---

# 4. Local IDs and evidence

## 4.1 CommodityTermsId

`CommodityTermsId` is a UUID-backed identity for one immutable UMI-07 semantic
artifact.

It is not:

- `EconomicIdentityId`;
- a provider product code;
- a venue-native contract code;
- a lifecycle-event ID.

No implicit UUID generation exists.

## 4.2 CommodityEvidenceRef

`CommodityEvidenceRef` is an opaque UUID reference to retained evidence.

```text
EVIDENCE REF != EVIDENCE CONTENT
UUID != PROVENANCE BY ITSELF
```

The evidence system outside this contract must retain the actual source material.

---

# 5. Commodity reference terms

`CommodityReferenceTerms` retains:

- local terms ID;
- canonical UMI-02 commodity/reference identity;
- extensible commodity-family code;
- canonical UMI-02 measurement-unit/reference identity;
- evidence ref.

The commodity reference and measurement-unit identities must differ.

Example family codes may include concepts such as:

- `energy`;
- `metals`;
- `agriculture`;
- `livestock`;
- `softs`.

These examples do not create a closed universal enum. The family code is an
extensible semantic qualifier, not economic identity.

The UMI-02 graph remains responsible for proving the referenced identities have
the intended governed kinds/families where that proof is required.

```text
FAMILY CODE != IDENTITY KIND PROOF
REFERENCE ID != PROVIDER SYMBOL
```

---

# 6. Delivery grade, location and method

## 6.1 CommodityGradeCode

A physical delivery contract may require a defined grade/specification.

`CommodityGradeCode` retains a canonical provider-neutral contractual code.

It does not:

- inspect laboratory quality;
- certify compliance with an exchange rulebook;
- calculate quality differentials;
- create a commodity identity.

## 6.2 Delivery location

A delivery alternative binds `location_identity_id: EconomicIdentityId`.

This intentionally avoids:

- provider-specific warehouse strings as canonical authority;
- venue codes masquerading as physical delivery-point identity;
- an ad hoc second location-ID graph.

The referenced UMI-02 identity is an attachment. Governed composition remains
responsible for proving that the identity is an appropriate reference object.

A locally composed commodity futures contract rejects a delivery location that is
identical to:

- the futures contract identity;
- the commodity reference identity;
- the measurement-unit identity.

These obvious self/cross-role collisions are locally decidable and therefore
fail closed.

## 6.3 CommodityDeliveryMethodCode

The method code may retain contract semantics such as a warehouse-receipt,
pipeline-transfer or other defined physical mechanism.

It grants no authority to:

- select a warehouse;
- book freight;
- move inventory;
- transfer title;
- settle the contract.

```text
METHOD CODE != METHOD EXECUTION
```

---

# 7. Delivery window

`CommodityDeliveryWindow` retains exact `date` values:

- `start_date`;
- `end_date`.

Rules:

- both values must be exact `date`, not `datetime`;
- `end_date >= start_date`;
- same-day delivery windows are valid.

UMI-07 deliberately does **not** impose a universal ordering between the delivery
window and:

- first notice;
- last trade;
- expiry;
- a recorded UMI-02 lifecycle event.

Different exchange/product rulebooks can define those relationships differently.
A false universal chronology would be worse than retaining the exact contractual
roles.

```text
DELIVERY WINDOW ROLE RETENTION
!=
UNIVERSAL EXCHANGE CHRONOLOGY
```

D06 may later resolve business-day/calendar rules where required.

---

# 8. Physical delivery alternatives

A physically deliverable commodity contract may permit more than one eligible
combination of:

- grade;
- delivery location;
- delivery method;
- delivery window.

Flattening those into four independent unordered sets would incorrectly imply all
cross-products are valid.

UMI-07 therefore retains one explicit `CommodityDeliveryAlternative` per eligible
combination.

`CommodityPhysicalDeliveryTerms` retains a non-empty immutable tuple of those
alternatives.

Rules:

- input must be an actual tuple;
- tuple must be non-empty;
- every member must be `CommodityDeliveryAlternative`;
- exact duplicate alternatives are rejected;
- caller order is non-semantic;
- alternatives are canonicalized by deterministic logical material.

```text
GRADE A @ LOCATION X
+
GRADE B @ LOCATION Y
!=
{GRADE A, GRADE B} × {LOCATION X, LOCATION Y}
```

This retains allowed combinations without implementing a delivery-selection
engine.

---

# 9. Commodity futures composition

`CommodityFuturesContractTerms` composes:

- local UMI-07 terms ID;
- exact UMI-05 `FuturesContractTerms`;
- UMI-07 `CommodityReferenceTerms`;
- UMI-07 evidence ref;
- optional `CommodityPhysicalDeliveryTerms`.

The UMI-05 futures object is retained intact in logical material.

UMI-07 does not copy or reserialize isolated futures fields under a new model.

## 9.1 Reference identity binding

The UMI-05 futures `reference_identity_id` must equal the UMI-07 commodity
`reference_identity_id`.

Otherwise the composition would permit commodity semantics for one reference to
be attached to a futures contract referencing another.

```text
FUTURES REFERENCE ID
=
COMMODITY REFERENCE ID
```

This is reference consistency, not UMI-02 kind proof.

## 9.2 Measurement-unit binding

The UMI-05 futures multiplier already retains:

- positive exact multiplier value;
- multiplier `unit_identity_id`.

UMI-07 commodity reference terms retain an explicit measurement-unit identity.

These identities must match.

```text
FUTURES MULTIPLIER UNIT
=
COMMODITY MEASUREMENT UNIT
```

This prevents a contract expressed in one unit from being silently qualified as
a commodity reference measured in another unit.

No unit conversion engine exists.

If future evidence requires explicit unit conversion, that conversion must be a
separate provenance-bearing valuation/reference boundary rather than an implicit
UMI-07 default.

## 9.3 CASH versus PHYSICAL

The closed rule is:

```text
UMI-05 settlement_style == PHYSICAL
-> UMI-07 physical_delivery REQUIRED
```

and:

```text
UMI-05 settlement_style == CASH
-> UMI-07 physical_delivery MUST BE None
```

A cash-settled commodity futures contract may still carry commodity reference
semantics. It simply cannot pretend to have physical delivery alternatives.

This preserves:

```text
COMMODITY REFERENCE != PHYSICAL DELIVERY
CASH-SETTLED COMMODITY CONTRACT IS STILL A COMMODITY CONTRACT
```

---

# 10. Lifecycle boundary

UMI-07 adds no lifecycle event class.

The following are deliberately separate:

```text
UMI-05 expiry_date
UMI-05 first_notice_date
UMI-05 last_trade_date
UMI-07 CommodityDeliveryWindow
UMI-02 IdentityLifecycleEvent
```

The first four are immutable contractual terms.

`IdentityLifecycleEvent` is retained evidence that an event was recorded/effective.

Governed composition may later require consistency between contract terms and
observed lifecycle evidence, but UMI-07 does not manufacture that evidence.

```text
CONTRACT SAYS DATE X
!=
EVENT X WAS OBSERVED / RECORDED
```

---

# 11. Authority map

| Material | Authority |
|---|---|
| Economic/reference identity | UMI-02 / D04 |
| Generic identity relationships | UMI-02 / D04 |
| Evidence-bearing lifecycle events | UMI-02 / D04 |
| Futures month/expiry/multiplier/tick/settlement style/notice/trade | UMI-05 |
| Commodity family/reference qualification | UMI-07 |
| Grade/location/method/window alternatives | UMI-07 |
| Provider/observed commodity and delivery evidence | D05 |
| Calendar/business-day resolution | D06 |
| Price/basis/storage/carry/valuation | D07 / UMI-10 |
| Account/collateral/risk/margin/capacity | D08 / D09 |
| Order/execution | D10 / D18 |
| Position/inventory/title/cash/settlement/reconciliation | D11 |
| Structured commodity payoff/composition | UMI-09 |

No UMI-07 type grants another department's operational authority.

---

# 12. Required semantic non-collisions

```text
COMMODITY TERMS ID != ECONOMIC IDENTITY
COMMODITY FAMILY != GRADE
COMMODITY REFERENCE != MEASUREMENT UNIT
COMMODITY REFERENCE != DELIVERY LOCATION
FUTURES CONTRACT IDENTITY != DELIVERY LOCATION
GRADE != LOCATION
LOCATION != VENUE
DELIVERY METHOD != SETTLEMENT ENGINE
DELIVERY WINDOW != LIFECYCLE EVENT
DELIVERY ALTERNATIVE != CROSS-PRODUCT OF INDEPENDENT SETS
MULTIPLIER UNIT != EXECUTION QUANTITY
CASH COMMODITY FUTURE != PHYSICAL COMMODITY FUTURE
PHYSICAL DELIVERY TERMS != D11 MUTATION
EVIDENCE REF != EVIDENCE CONTENT
```

---

# 13. Determinism and fail-closed rules

All UMI-07 candidate dataclasses use:

`@dataclass(frozen=True, slots=True)`

Validation includes:

- explicit caller-supplied UUID-backed local IDs;
- strict UMI-02 `EconomicIdentityId` references;
- typed code wrappers;
- canonical lowercase code syntax;
- exact `date`; `datetime` rejected;
- immutable non-empty alternative tuple;
- duplicate alternative rejection;
- deterministic caller-order-independent alternative sorting;
- reference identity consistency with UMI-05 futures;
- measurement-unit identity consistency with UMI-05 multiplier;
- CASH/PHYSICAL coherence;
- obvious location identity role collisions rejected;
- deterministic `logical_values()`;
- no implicit `datetime.now()`;
- no implicit `date.today()`;
- no implicit `uuid4()`;
- no randomness;
- no global mutable state;
- no retry/sleep/thread/scheduler.

---

# 14. Adversarial test obligations

Exact-head tests must attack at least:

1. local terms/evidence IDs are not economic identity;
2. raw text cannot enter UUID wrappers;
3. raw UUID cannot enter `EconomicIdentityId` fields;
4. family, grade and delivery method remain distinct typed semantics;
5. raw strings cannot bypass typed-code fields;
6. noncanonical/credential-like code material fails;
7. delivery-window start/end roles are retained;
8. reverse delivery-window chronology fails;
9. `datetime` cannot launder into start date;
10. `datetime` cannot launder into end date;
11. grade/location/method/window all survive logical values;
12. raw UUID cannot masquerade as delivery location identity;
13. physical-delivery alternatives require non-empty immutable tuple;
14. exact duplicate alternatives fail;
15. caller alternative order does not change logical material;
16. UMI-05 futures object is reused intact;
17. UMI-05 reference identity mismatch fails;
18. UMI-05 multiplier-unit mismatch fails;
19. PHYSICAL without delivery terms fails;
20. CASH with physical-delivery terms fails;
21. CASH commodity futures without physical delivery remains representable;
22. delivery location cannot equal contract/commodity/unit identity;
23. no false delivery-window-vs-expiry/notice chronology is invented;
24. terms are frozen;
25. no lifecycle/calendar/logistics/settlement/execution/risk/provider engine exists;
26. logical values are repeatable and secret-free.

Coverage percentage does not substitute for those semantic attacks.

---

# 15. Internal falsification targets

Before exact-head freeze, Integration Gate must specifically try to construct:

## PRE-CHK-UMI07-01 — generic futures duplication

Counterexample sought:
UMI-07 introduces its own contract month, expiry, multiplier, tick value,
first-notice, last-trade or settlement-style field and can drift from UMI-05.

Required outcome:
NOT CONSTRUCTED. The candidate must embed `FuturesContractTerms` instead.

## PRE-CHK-UMI07-02 — cash/physical semantic collapse

Counterexample sought:
A CASH futures contract carries physical delivery alternatives, or a PHYSICAL
contract omits them.

Required outcome:
Both invalid states fail closed.

## PRE-CHK-UMI07-03 — unit/reference mismatch

Counterexample sought:
Commodity semantics for reference A or unit U can be attached to futures
referencing B or multiplier unit V.

Required outcome:
Both mismatches fail closed.

## PRE-CHK-UMI07-04 — delivery-alternative cross-product loss

Counterexample sought:
Multiple grade/location combinations collapse into unordered independent sets or
caller tuple order changes logical material.

Required outcome:
Each eligible combination remains one explicit alternative and tuple order is
canonicalized.

## PRE-CHK-UMI07-05 — lifecycle authority duplication

Counterexample sought:
UMI-07 contractual delivery dates are represented as observed lifecycle events or
a second lifecycle history appears.

Required outcome:
No UMI-07 lifecycle event/history type exists.

---

# 16. Blast radius

The intended candidate is additive and limited to:

- one new infrastructure semantic module;
- one adversarial test module;
- this architecture artifact.

It must not modify:

- UMI-02;
- UMI-03;
- UMI-04;
- UMI-05;
- UMI-06;
- provider adapters;
- market-data ingestion;
- execution;
- risk;
- accounts;
- positions;
- settlement;
- runtime/persistence;
- client/CEO surfaces.

Any unexpected modification outside the three additive artifacts requires a new
blast-radius analysis.

---

# 17. Explicit non-goals

UMI-07 does NOT implement or certify:

- full physical commodity ontology;
- exchange/provider product catalogs;
- provider commodity adapters;
- provider contract support;
- venue-native product-code authority;
- delivery notice ingestion;
- warehouse receipt ingestion;
- warehouse/inventory state;
- logistics/transport/freight;
- title transfer;
- delivery election/selection;
- calendar or business-day date generation;
- storage costs;
- carry;
- convenience yield;
- cash-and-carry basis;
- location/quality differential valuation;
- commodity spot pricing;
- commodity forward pricing;
- commodity option pricing;
- valuation observations;
- margin/risk/capital reservation;
- order/execution;
- position mutation;
- inventory mutation;
- cash mutation;
- settlement mutation;
- automatic reconciliation trading;
- structured commodity payoff products;
- productive Cloud;
- production readiness;
- real capital.

---

# 18. Carry-forwards

UMI-07 leaves unchanged:

- `GAP-FND04-TIME-01` — OPEN / HIGH;
- `GAP-FND07-RES-01` — OPEN / HIGH;
- PR #298 — HOLD;
- `GAP-EXEC` — OPEN / HIGH;
- `GAP-ANALYSIS-PRODUCER` — OPEN / HIGH;
- `GAP-LIN-001` — OPEN / HIGH.

No favorable UMI-07 review may be interpreted as closure of those obligations.

---

# 19. Certification gate

UMI-07 can be integrated only through:

```text
CERTIFIED BASELINE
-> EXACT IMPLEMENTATION
-> ADVERSARIAL TESTS
-> DIFF AUDIT
-> EXACT-HEAD CI
-> EXACT-HEAD FREEZE
-> FULL INDEPENDENT CLAUDE REVIEW
-> INTEGRATION GATE
-> EXPECTED-HEAD PROTECTED MERGE
-> ACTUAL MERGE VERIFICATION
-> POST-MERGE MAIN VERIFICATION
-> BASELINE FREEZE
```

Any candidate SHA mutation after freeze invalidates the previous review binding.

`CI GREEN != ENGINEERING APPROVAL`

`READY FOR INTEGRATION GATE != MERGED`

`MERGED != CERTIFIED UNTIL POST-MERGE BASELINE VERIFICATION`

---

# 20. Final non-claims

This candidate, even if independently certified, establishes only a bounded
provider-neutral commodity reference + contract-delivery semantic layer composed
over UMI-02 and UMI-05.

It does not establish provider support, operational physical delivery,
settlement, commodity valuation, logistics, production readiness or real-capital
authority.
