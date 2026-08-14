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

The candidate deliberately composes the already-certified UMI-05
`FuturesContractTerms`; it does not create a second futures contract model.

It does not implement provider support, delivery-event observation, calendar
resolution, logistics, warehouse inventory, title transfer, physical settlement,
position/cash mutation, valuation, risk, execution, productive Cloud or real capital.

```text
COMMODITY CONTRACT QUALIFICATION
!= GENERIC FUTURES CONTRACT SEMANTICS
!= RECORDED LIFECYCLE EVENT
!= DELIVERY / LOGISTICS ENGINE
!= PHYSICAL SETTLEMENT MUTATION
!= PROVIDER SUPPORT
```

---

# 1. Governing invariants

```text
ECONOMIC / REFERENCE IDENTITY -> UMI-02
LOCAL COMMODITY TERMS ID != ECONOMIC IDENTITY
COMMODITY CLASS CODE != UMI-02 IdentityFamilyCode AUTHORITY
COMMODITY CLASS CODE != ECONOMIC IDENTITY
PROVIDER SYMBOL / VENUE PRODUCT CODE != COMMODITY IDENTITY

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
COMMODITY CLASS != GRADE
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
PHYSICAL DELIVERY TERMS != POSITION / CASH MUTATION

CALLER ALTERNATIVE ORDER != ECONOMIC SEMANTIC
EVIDENCE REF != EVIDENCE CONTENT
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

Carry-forwards remain binding:

- `GAP-FND04-TIME-01` — OPEN / HIGH;
- `GAP-FND07-RES-01` — OPEN / HIGH;
- PR #298 — HOLD;
- `GAP-EXEC` — OPEN / HIGH;
- `GAP-ANALYSIS-PRODUCER` — OPEN / HIGH;
- `GAP-LIN-001` — OPEN / HIGH.

---

# 2. Exact-baseline audit

## 2.1 UMI-02 already owns identity and lifecycle

Direct inspection of
`src/qore/infrastructure/universal_instrument_identity.py` at the certified baseline
confirms UMI-02 owns:

- `EconomicIdentityId` / `EconomicIdentity`;
- `IdentityFamilyCode` as generic identity-family classification;
- `IdentityRelationship`;
- `IdentityLifecycleEvent`;
- `LifecycleEventCode`;
- evidence-bearing `effective_at` and `recorded_at` lifecycle facts.

UMI-02 explicitly permits reference-object identities for physical/reference
concepts and explicitly cites first notice, last trade and expiry as examples of
future-family lifecycle events.

UMI-07 therefore MUST NOT create:

- another economic commodity identity;
- another listing identity;
- another generic identity-family authority;
- another relationship graph;
- another lifecycle-event history.

```text
UMI-07 TERMS ATTACH TO UMI-02 IDENTITY
!= UMI-07 BECOMES IDENTITY AUTHORITY
```

## 2.2 PRE-CHK-UMI07-00 — identity-family authority duplication

An internal pre-falsification candidate originally used a type named
`CommodityFamilyCode`.

That name was too close to UMI-02 `IdentityFamilyCode` and could suggest a second
family authority capable of disagreeing with the canonical identity graph.

The candidate was corrected before exact-head freeze:

```text
CommodityClassCode
```

`CommodityClassCode` is a bounded family-economic qualifier such as `energy`,
`metals`, `agriculture`, `livestock` or `softs`.

It is NOT:

- `IdentityFamilyCode`;
- proof of an identity's UMI-02 family;
- economic identity;
- provider or venue classification authority.

Governed composition remains responsible for checking the referenced UMI-02
identity graph when identity kind/family proof is material.

```text
COMMODITY CLASSIFICATION MATERIAL
!= CANONICAL IDENTITY-FAMILY AUTHORITY
```

Independent review must attack this boundary explicitly.

## 2.3 UMI-05 already owns generic futures economics

Direct inspection of
`src/qore/infrastructure/derivative_contract_semantics.py` confirms UMI-05 owns:

- `DerivativeContractMonth`;
- `DerivativeContractMultiplier`;
- `DerivativeTickValue`;
- `DerivativeSettlementStyle` (`CASH`, `PHYSICAL`);
- `FuturesContractTerms`.

`FuturesContractTerms` already retains:

- instrument/reference/settlement identities;
- contract month;
- expiry date;
- multiplier;
- CASH/PHYSICAL settlement style;
- evidence;
- optional tick value;
- optional first-notice date;
- optional last-trade date.

It already validates the generic futures chronology and obvious identity rules.

UMI-07 therefore MUST NOT add parallel fields for those semantics.

```text
UMI-07 COMMODITY FUTURES TERMS
-> EMBED UMI-05 FuturesContractTerms
-> DO NOT COPY FUTURES FIELDS
```

## 2.4 UMI-05 leaves physical commodity delivery specification open

UMI-05's `PHYSICAL` settlement style says the contract settles physically.
It does not retain every eligible:

- deliverable grade/specification;
- delivery location;
- physical delivery method;
- contractual delivery window.

Nor does it execute settlement.

```text
PHYSICAL SETTLEMENT STYLE
!= PHYSICAL DELIVERY SPECIFICATION
!= PHYSICAL SETTLEMENT EXECUTION
```

This is the bounded UMI-07 gap.

## 2.5 FND-04 prevents quantity/unit flattening

FND-04 freezes:

```text
QUANTITY != NOTIONAL
CONTRACT COUNT != BASE UNITS
MULTIPLIER != QUANTITY
PRICE × QUANTITY != UNIVERSAL ECONOMIC VALUE
NUMERIC REPRESENTATION != ECONOMIC SEMANTIC
```

UMI-07 therefore does not introduce another Decimal quantity that duplicates the
UMI-05 contract multiplier.

Instead:

- UMI-05 multiplier already retains the per-contract magnitude and unit identity;
- UMI-07 commodity reference retains its measurement-unit identity;
- composition requires those unit identities to match.

No unit-conversion engine is added.

## 2.6 Existing settlement/calendar types are not commodity delivery authority

UMI-03 types such as `BusinessCalendarRef` and `SettlementConvention` remain bounded
structural fixed-income/calendar semantics. They do not identify a commodity grade,
delivery point, warehouse/pipeline mechanism or allowed delivery combination.

D06 remains calendar/date-resolution authority.

## 2.7 Verified structural gap

At baseline `b44529c8e3caf5badf6ff49da2f0246f3f985219`, direct inspection
establishes:

1. UMI-02 already owns generic identity/lifecycle;
2. UMI-05 already owns generic futures economics;
3. PHYSICAL style alone does not preserve grade/location/method/window alternatives;
4. no inspected canonical contract composes those commodity delivery semantics over
   UMI-05 futures terms;
5. no bounded existing type may be promoted to that role without reinterpretation.

Classification:

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-07 CONTRACT DELTA REQUIRED`

Search absence is locator evidence only. The decision is grounded in directly
inspected canonical boundaries.

---

# 3. Candidate contract inventory

The candidate adds only:

- `CommodityTermsId`;
- `CommodityEvidenceRef`;
- `CommodityClassCode`;
- `CommodityGradeCode`;
- `CommodityDeliveryMethodCode`;
- `CommodityDeliveryWindow`;
- `CommodityReferenceTerms`;
- `CommodityDeliveryAlternative`;
- `CommodityPhysicalDeliveryTerms`;
- `CommodityFuturesContractTerms`.

No new economic identity, identity-family type, listing, relationship, lifecycle
event, futures month, expiry, multiplier, tick-value or settlement-style type is
introduced.

---

# 4. Local IDs and evidence

`CommodityTermsId` is a UUID-backed local semantic artifact ID only.

`CommodityEvidenceRef` is an opaque UUID reference to retained evidence only.

```text
LOCAL UUID != ECONOMIC IDENTITY
EVIDENCE REF != EVIDENCE CONTENT
HASH / UUID != RETAINED SOURCE EVIDENCE
```

No implicit UUID generation exists.

---

# 5. Commodity reference semantics

`CommodityReferenceTerms` retains:

- `terms_id`;
- `reference_identity_id: EconomicIdentityId`;
- `commodity_class: CommodityClassCode`;
- `measurement_unit_identity_id: EconomicIdentityId`;
- `evidence_ref`.

The commodity reference and measurement-unit identities must differ.

`CommodityClassCode` may preserve bounded semantic classes such as:

- `energy`;
- `metals`;
- `agriculture`;
- `livestock`;
- `softs`.

It remains extensible rather than a closed world enum.

It does not prove the UMI-02 identity kind or family.

```text
COMMODITY CLASS CODE != IdentityFamilyCode
COMMODITY CLASS CODE != ECONOMIC IDENTITY
```

---

# 6. Grade, delivery location and delivery method

## 6.1 Grade

`CommodityGradeCode` retains a contractual grade/specification code.

It does not:

- inspect physical quality;
- certify exchange compliance;
- calculate quality differentials;
- create identity authority.

## 6.2 Location

`CommodityDeliveryAlternative.location_identity_id` uses an existing UMI-02
`EconomicIdentityId` reference.

This avoids turning a provider warehouse string or venue code into canonical
location authority.

The UMI-02 graph must prove the referenced identity is an appropriate reference
object when that proof is material.

Within the local composition, a delivery-location identity cannot equal:

- the futures contract identity;
- the commodity reference identity;
- the measurement-unit identity.

Those are locally decidable cross-role collisions and fail closed.

## 6.3 Delivery method

`CommodityDeliveryMethodCode` retains a contractual mechanism such as
`warehouse-receipt` or `pipeline-transfer`.

It is not a logistics or settlement engine.

```text
DELIVERY METHOD CODE != METHOD EXECUTION
```

---

# 7. Delivery window

`CommodityDeliveryWindow` retains exact date-only:

- `start_date`;
- `end_date`.

Rules:

- exact `date`; `datetime` is rejected;
- `end_date >= start_date`;
- same-day window is valid.

UMI-07 intentionally does NOT impose one universal order between the delivery
window and:

- first notice;
- last trade;
- expiry;
- an observed UMI-02 lifecycle event.

Exchange/product rulebooks vary. Retaining exact roles is safer than inventing a
false chronology.

```text
DELIVERY WINDOW ROLE RETENTION
!= UNIVERSAL EXCHANGE CHRONOLOGY
```

---

# 8. Delivery alternatives

A physical contract can allow multiple specific combinations of grade, location,
method and window.

UMI-07 retains each valid combination as one
`CommodityDeliveryAlternative` rather than independent sets whose cartesian product
would invent combinations not actually allowed.

`CommodityPhysicalDeliveryTerms` requires:

- an actual immutable tuple;
- at least one alternative;
- only `CommodityDeliveryAlternative` members;
- no exact duplicates;
- deterministic canonical sorting by complete logical material.

Caller tuple order is not economic semantic.

```text
GRADE A @ LOCATION X
+
GRADE B @ LOCATION Y
!= {A,B} × {X,Y}
```

No delivery-selection engine exists.

---

# 9. Composition over UMI-05 futures

`CommodityFuturesContractTerms` retains:

- local UMI-07 terms ID;
- exact embedded UMI-05 `FuturesContractTerms`;
- UMI-07 `CommodityReferenceTerms`;
- UMI-07 evidence ref;
- optional `CommodityPhysicalDeliveryTerms`.

The complete UMI-05 futures logical values are retained inside the UMI-07 logical
material. UMI-07 does not selectively copy generic futures fields.

## 9.1 Reference binding

```text
futures.reference_identity_id
== commodity_reference.reference_identity_id
```

A mismatch fails closed.

This proves local referential consistency only. It does not prove UMI-02 kind/family
without governed graph composition.

## 9.2 Measurement-unit binding

```text
futures.multiplier.unit_identity_id
== commodity_reference.measurement_unit_identity_id
```

A mismatch fails closed.

This prevents a futures multiplier denominated in one physical/reference unit from
being silently qualified as commodity terms measured in another unit.

No conversion is attempted.

## 9.3 CASH / PHYSICAL coherence

Closed rules:

```text
PHYSICAL -> physical_delivery REQUIRED
CASH -> physical_delivery MUST BE None
```

A cash-settled commodity contract can still retain commodity reference semantics.
It simply carries no physical delivery alternatives.

```text
COMMODITY REFERENCE != PHYSICAL DELIVERY
```

---

# 10. Lifecycle authority boundary

UMI-07 adds no lifecycle event/history type.

The following remain distinct:

```text
UMI-05 expiry_date
UMI-05 first_notice_date
UMI-05 last_trade_date
UMI-07 CommodityDeliveryWindow
UMI-02 IdentityLifecycleEvent
```

UMI-05 and UMI-07 dates are contractual terms.

UMI-02 lifecycle events are evidence that an event was effective/recorded.

```text
CONTRACT SAYS DATE X
!= EVENT X WAS OBSERVED / RECORDED
```

---

# 11. Authority map

| Material | Authority |
|---|---|
| Economic/reference identity + generic family | UMI-02 / D04 |
| Generic identity relationships + lifecycle events | UMI-02 / D04 |
| Futures month/expiry/multiplier/tick/style/notice/trade | UMI-05 |
| Commodity class/reference qualification | UMI-07 |
| Grade/location/method/window alternatives | UMI-07 |
| Provider/observed commodity/delivery evidence | D05 |
| Calendar/business-day resolution | D06 |
| Price/basis/storage/carry/valuation | D07 / UMI-10 |
| Account/collateral/risk/margin/capacity | D08 / D09 |
| Order/execution | D10 / D18 |
| Position/inventory/title/cash/settlement/reconciliation | D11 |
| Structured commodity payoff/composition | UMI-09 |

No UMI-07 type grants another department's operational authority.

---

# 12. Determinism and fail-closed discipline

All candidate dataclasses use:

`@dataclass(frozen=True, slots=True)`

The candidate requires:

- explicit caller-supplied UUID-backed local IDs;
- UMI-02 `EconomicIdentityId` references;
- typed code wrappers;
- canonical lowercase code syntax;
- exact `date`, never `datetime`;
- immutable non-empty alternative tuples;
- duplicate-alternative rejection;
- caller-order-independent canonical alternative sorting;
- UMI-05 reference consistency;
- UMI-05 multiplier-unit consistency;
- CASH/PHYSICAL coherence;
- deterministic `logical_values()`.

Candidate source contains no implicit:

- `datetime.now()`;
- `date.today()`;
- `uuid4()`;
- randomness;
- retry/sleep/thread/scheduler;
- global mutable state.

---

# 13. Internal pre-falsification matrix

## PRE-CHK-UMI07-00 — identity-family authority duplication

Historical candidate:
`CommodityFamilyCode`.

Correction:
`CommodityClassCode`, explicitly non-sovereign versus UMI-02 `IdentityFamilyCode`.

Required independent attack:
prove whether UMI-07 can make identity-family claims or only retain bounded commodity
class material.

## PRE-CHK-UMI07-01 — generic futures duplication

Attack:
find parallel UMI-07 contract month, expiry, multiplier, tick value, first notice,
last trade or settlement style.

Expected:
NOT FOUND. Candidate embeds `FuturesContractTerms`.

## PRE-CHK-UMI07-02 — CASH / PHYSICAL collapse

Attack:
- PHYSICAL without delivery terms;
- CASH with delivery terms.

Expected:
both fail.

## PRE-CHK-UMI07-03 — reference/unit mismatch

Attack:
attach commodity reference A to futures reference B, or measurement unit U to
multiplier unit V.

Expected:
both fail.

## PRE-CHK-UMI07-04 — alternative combination/order loss

Attack:
- duplicate alternatives;
- mutable list instead of tuple;
- reverse caller order;
- grade/location combination collapse.

Expected:
duplicates/mutable list fail; caller order canonicalizes; each combination remains
explicit.

## PRE-CHK-UMI07-05 — lifecycle authority duplication

Attack:
find UMI-07 lifecycle event/history, recorded/effective event producer or a claim
that delivery-window dates prove observed lifecycle events.

Expected:
NOT FOUND.

---

# 14. Required test obligations

Exact-head tests must demonstrate at minimum:

1. local IDs/evidence refs are not economic identity;
2. UUID wrappers reject raw text;
3. raw UUID cannot enter UMI-02 identity fields;
4. commodity class, grade and delivery method are distinct typed semantics;
5. typed fields reject raw-string laundering;
6. noncanonical/credential-like code material fails;
7. delivery-window date roles are retained;
8. reverse window chronology fails;
9. datetime laundering fails for both window dates;
10. grade/location/method/window all survive logical values;
11. raw UUID cannot masquerade as delivery-location identity;
12. delivery alternatives require non-empty immutable tuple;
13. duplicates fail;
14. caller ordering does not alter logical values;
15. exact UMI-05 futures object is reused;
16. reference mismatch fails;
17. multiplier-unit mismatch fails;
18. PHYSICAL missing delivery terms fails;
19. CASH carrying delivery terms fails;
20. CASH commodity futures remain representable without physical delivery;
21. obvious location-role identity collisions fail;
22. no false delivery-window-vs-expiry/notice chronology is imposed;
23. terms are frozen;
24. no lifecycle/calendar/logistics/settlement/execution/risk/provider engine exists;
25. logical values are repeatable and secret-free.

Coverage percentage is not a substitute for these semantic attacks.

---

# 15. Semantic non-collision matrix

```text
CommodityClassCode != IdentityFamilyCode
CommodityClassCode != CommodityGradeCode
CommodityGradeCode != delivery location identity
commodity reference identity != measurement-unit identity
commodity reference identity != futures instrument identity by inherited UMI-05 rules
commodity reference != delivery location
measurement unit != delivery location
contract multiplier != order/position quantity
PHYSICAL != CASH
physical delivery specification != settlement mutation
delivery window != lifecycle event
evidence ref != evidence content
```

---

# 16. Blast radius

Expected exact candidate delta is additive and limited to:

- `src/qore/infrastructure/commodity_contract_delivery_semantics.py`;
- `tests/infrastructure/test_commodity_contract_delivery_semantics.py`;
- this architecture document.

No certified UMI-02/03/04/05/06, provider, runtime, persistence, execution, risk,
account, position, settlement or client/CEO file may change.

Any unexpected additional diff requires a new blast-radius decision.

---

# 17. Explicit non-goals

UMI-07 does NOT implement or certify:

- full physical commodity ontology;
- exchange/provider product catalogs or adapters;
- provider/venue product-code authority;
- delivery notice ingestion;
- warehouse receipt ingestion;
- warehouse/inventory state;
- logistics, transport or freight;
- title transfer;
- delivery election/selection;
- calendar/business-day date generation;
- storage costs or carry;
- convenience yield;
- commodity basis calculation;
- quality/location differential valuation;
- spot/forward/option pricing;
- valuation observations;
- margin/risk/capacity reservation;
- order/execution;
- position/inventory/cash/settlement mutation;
- structured commodity payoff products;
- productive Cloud;
- production readiness;
- real capital.

---

# 18. Carry-forwards

A favorable UMI-07 review does NOT close or alter:

- `GAP-FND04-TIME-01` — OPEN / HIGH;
- `GAP-FND07-RES-01` — OPEN / HIGH;
- PR #298 — HOLD;
- `GAP-EXEC` — OPEN / HIGH;
- `GAP-ANALYSIS-PRODUCER` — OPEN / HIGH;
- `GAP-LIN-001` — OPEN / HIGH.

---

# 19. Certification gate

UMI-07 may be integrated only through:

```text
CERTIFIED BASELINE
-> IMPLEMENTATION
-> INTERNAL FALSIFICATION
-> FULL QUALITY GATE
-> DIFF AUDIT
-> EXACT-HEAD FREEZE
-> FULL CLAUDE INDEPENDENT REVIEW
-> INTEGRATION GATE
-> EXPECTED-HEAD PROTECTED MERGE
-> ACTUAL MERGE VERIFICATION
-> POST-MERGE MAIN VERIFICATION
-> BASELINE FREEZE
```

Any candidate SHA mutation after freeze invalidates the prior independent review.

`CI GREEN != ENGINEERING APPROVAL`

`READY FOR INTEGRATION GATE != MERGED`

`MERGED != CERTIFIED UNTIL POST-MERGE VERIFICATION`

---

# 20. Final non-claims

Even if independently certified, UMI-07 establishes only a bounded
provider-neutral commodity reference + contract-delivery semantic layer composed
over UMI-02 and UMI-05.

It does not establish provider support, operational physical delivery, settlement,
commodity valuation, logistics, production readiness or real-capital authority.
