# QORE-UMI14 Specialized Commodity Static Semantics

Status: **GATE-B CURRENT-BASELINE RECERTIFICATION CANDIDATE — NOT GATE-C CERTIFIED**

Tracker: `#388`  
Preparatory audit: `#387`  
Historical preparatory PR: `#389`  
Target: `UMI13-UNR-009`  
Current sealed baseline: `bc4df616cec7a3b15e152c6797eba5ff8ef32925`  
Current sealed baseline tree: `6de9b0944e4ac9dbf37cf13ee1852fca3078db5c`  
Gate-B branch: `agent/qore-umi14-specialized-commodity-full-closure-009`

## 1. Currentness rule

The historical PR #389 was built from baseline
`39e1598e91c912f473f9628c3aab30fe7b9cc034` and is not current certification.
Its source and primary-test payloads may be reused only where the live repository proves
that direct productive dependencies remain compatible.

Current live reconstruction proves that the imported owners used by the historical source
remain byte-identical across the relevant drift:

- `commodity_contract_delivery_semantics.py` ->
  `e2e7b4e302996a351cd3044077f250234ec81b25`;
- `derivative_contract_semantics.py` ->
  `36e4d672459c489573eabc7ba5413bb5ef99c3a6`;
- `universal_instrument_identity.py` ->
  `c39a77c621f9a6a524751d4e2983e71c36400a0f`.

`HISTORICAL CERTIFICATION != CURRENT CERTIFICATION`

`OLD PR #389 != CURRENT GATE-C CANDIDATE`

`AUTHORIZATION NEVER PROPAGATES`

## 2. Exact bounded Gate-B file surface

Gate B is additive and limited to:

- `src/qore/infrastructure/specialized_commodity_semantics.py`;
- `tests/infrastructure/test_specialized_commodity_semantics.py`;
- `tests/infrastructure/test_specialized_commodity_semantics_logical_identity.py`;
- `docs/architecture/QORE-UMI14-SPECIALIZED-COMMODITY-SEMANTICS-001.md`.

The productive source and primary tests are reused byte-for-byte from historical PR #389:

- source blob: `f782826b500cb3cf46122cadb102eaea3e57aa49`;
- primary tests blob: `4a5264ca1cb6c52a2f9176854df72404b482d15d`.

The additional logical-identity oracle is a current Gate-B test-only hardening required by
the serial Full Closure oracle law. Its blob is:

- logical-identity oracle blob: `e8275c5b71422b566903cf714f2ae087c287d0a9`.

No existing certified owner is modified.

## 3. Purpose

This additive D04 owner addresses the bounded surviving `UMI13-UNR-009` specialized
commodity gaps after exact UMI-07 falsification:

- electricity / power delivery-profile semantics;
- freight static contract qualification;
- weather-index static contract definition;
- environmental-product and vintage-eligibility semantics.

It does not replace or duplicate generic commodity delivery.

## 4. Existing UMI-07 owner retained

UMI-07 already owns generic commodity reference and physical-delivery semantics:

- `CommodityReferenceTerms`;
- commodity class and measurement-unit identity;
- delivery grade;
- location identity;
- delivery method;
- delivery window;
- immutable physical-delivery alternatives;
- `CommodityFuturesContractTerms` composition over UMI-05 futures.

The specialized owner composes those types where exact.

`GENERIC COMMODITY DELIVERY != SPECIALIZED COMMODITY CONTRACT COMPLETENESS`

## 5. Electricity semantics

`ElectricityContractTerms` composes existing `CommodityReferenceTerms`, existing
`CommodityPhysicalDeliveryTerms`, a specialized `ElectricityDeliveryProfile`, and evidence.

`ElectricityLoadType` retains BASE, PEAK, OFF_PEAK, BLOCK_HOURS and CUSTOM.
`ElectricitySettlementPeriodCode` retains governed static profile codes without D06
calendar-resolution authority.

`ElectricityQuantityStep` retains explicit effective date, positive exact Decimal quantity
and measurement-unit identity. Steps are date-unique and canonicalized, use one unit, must
match the UMI-07 measurement-unit identity, and must fall inside an eligible delivery
window.

No dispatch, metering, current power observation or schedule generation is represented.

`DELIVERY WINDOW != SETTLEMENT-PERIOD SHAPE`

`GENERIC COMMODITY DELIVERY != ELECTRICITY LOAD PROFILE`

## 6. Freight semantics

The bounded owner distinguishes:

- WET VOYAGE CHARTER -> Worldscale points only;
- DRY VOYAGE CHARTER -> contract rate only;
- TIME CHARTER -> contract rate only.

`FreightTerms` retains explicit instrument identity, route identity, transaction kind,
calculation period, exactly the applicable Worldscale/contract-rate material, and evidence.

No current freight-index observation, provider route symbol, valuation or payment
calculation is represented.

`WORLDSCALE POINTS != CONTRACT RATE`

`FREIGHT CONTRACT != PHYSICAL COMMODITY DELIVERY BY IMPLICATION`

## 7. Weather-index semantics

`WeatherIndexTerms` retains instrument identity, station/reference identity, weather-index
code, calculation period, contractual reference level and unit, settlement-level code,
notional per index unit, and evidence.

It does not ingest weather observations and does not compute HDD, CDD, CPD, cumulative
weather values, payoff or valuation.

`WEATHER INDEX TERMS != WEATHER OBSERVATION`

`WEATHER INDEX DEFINITION != CALCULATED WEATHER INDEX`

## 8. Environmental-product semantics

`EnvironmentalProductTerms` reuses `CommodityReferenceTerms` and, for PHYSICAL settlement,
existing `CommodityPhysicalDeliveryTerms`.

It retains product type, explicit vintage eligibility, optional compliance period,
applicable-law code, tracking-system code, settlement style and evidence.

`EnvironmentalVintageEligibility` distinguishes:

- `EXACT_SET`;
- `CONTRACT_YEAR_AND_PRIOR`.

Exact vintage sets are immutable, unique and canonicalized. PHYSICAL requires physical
delivery terms; CASH forbids them.

No allowance registry account, surrender operation, compliance inventory or transfer is
created by this owner.

`ENVIRONMENTAL PRODUCT IDENTITY != VINTAGE ELIGIBILITY RULE`

`SPECIFIC VINTAGE != CONTRACT-YEAR-PLUS-PRIOR-VINTAGES`

`ENVIRONMENTAL TRACKING SYSTEM REFERENCE != REGISTRY MUTATION`

## 9. Chronology / type discipline

The owner remains fail-closed for:

- strict `date != datetime`;
- strict `bool != int` for year material;
- finite Decimal material;
- positive electricity quantity and weather notional where required;
- freight calculation chronology;
- weather calculation chronology;
- environmental compliance chronology;
- canonical lower-case codes;
- immutable tuples and deterministic ordering.

## 10. Independent logical-projection oracle

The current Gate-B oracle independently reconstructs expected logical tuples from raw typed
fields. Expected-side helpers do not call SUT `logical_values()`, production serializers,
sort/fingerprint helpers, or actual output reused as expected.

The oracle covers populated top-level projections for:

- electricity;
- wet-voyage freight;
- contract-rate freight;
- weather index;
- PHYSICAL environmental product with exact vintages and optional qualifications;
- CASH environmental product with contract-year-and-prior and absent optional material.

It also asserts exact `dataclasses.fields()` surfaces for every specialized dataclass so an
added runtime/current/PV/provider/settlement-mutation field or omitted contractual field
cannot silently survive.

`GUARD EXISTS != REGRESSION ORACLE EXISTS`

## 11. Determinism / security / provider neutrality

All additive values are frozen/slotted dataclasses or bounded enums/codes. IDs, dates and
quantities are caller supplied. Logical material is deterministic.

No implicit UUID, wall clock, randomness, network/provider SDK, database, filesystem
runtime, scheduler, thread, sleep, secret material, current observation, valuation,
execution or settlement mutation is introduced.

## 12. Authority boundaries / non-claims

Outside this D04 owner:

- current power/weather/freight/emissions observations -> D05;
- calendar/time resolution -> D06;
- index calculation, payoff, PV and valuation -> D07;
- account/compliance inventory and exposure -> D08/D09 as applicable;
- execution -> D10;
- physical/cash settlement or registry mutation -> D11 / governed external boundary;
- provider capability -> D03;
- event-contract outcome resolution -> UNR-014;
- benchmark methodology/governance -> UNR-005 where applicable.

Also not claimed:

- complete natural-gas pipeline-cycle specialization;
- oil terminal/pipeline nomination semantics;
- coal composition/property schedules;
- commodity basket options;
- commodity Asian/digital options;
- freight-index methodology;
- weather data-source production;
- emissions compliance workflow;
- provider support;
- Production or real capital.

`SPECIALIZED COMMODITY TERMS != CURRENT MARKET DATA`

`SPECIALIZED COMMODITY TERMS != INDEX CALCULATION / VALUATION`

`SPECIALIZED COMMODITY TERMS != EXECUTION / SETTLEMENT MUTATION`

## 13. Gate-B disposition

This branch is a current-baseline Gate-B correction only.

Historical PR #389 and QORE CI #1154 remain provenance only. Fresh Gate C must freeze the
new exact head/tree/blobs/diff/synthetic, run the exact quality gate and obtain fresh
SHA-bound independent audits.

This Gate-B artifact does not authorize:

- Draft PR creation under Gate C;
- READY transition;
- merge;
- Gate F seal;
- `UNR-009` closure;
- UMI14 PASS;
- Program-D PASS;
- Production or real capital.

`GATE B CORRECTION != GATE C AUTHORIZATION`

## 14. Mandatory UMI-12 follow-up

Before final UMI14 closure, the cross-asset conformance harness and architecture material
must be re-evaluated for every newly certified owner. This bounded correction does not
mutate UMI-12.
