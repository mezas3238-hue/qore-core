# QORE-UMI14 Specialized Commodity Static Semantics

Status: **PROGRAM D / UMI-14 LANE-7 CORRECTION CANDIDATE — INDEPENDENT CERTIFICATION REQUIRED**

Tracker: `#388`  
Preparatory audit: `#387`  
Target: `UMI13-UNR-009`  
Starting baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`

## 1. Purpose

This additive D04 candidate covers only the specialized commodity semantics that remain unrepresented after exact UMI-07 falsification:

- electricity delivery profile;
- freight contract qualification;
- weather-index contract definition;
- environmental-product and vintage eligibility.

It does not replace generic commodity delivery.

## 2. Corrected evidence boundary

The exact baseline UMI-07 owner is:

`src/qore/infrastructure/commodity_contract_delivery_semantics.py`

Exact blob:

`e2e7b4e302996a351cd3044077f250234ec81b25`

Any earlier preparatory blob identifier is superseded.

Primary financial/product evidence used by Integration Gate includes FpML commodity schemas for electricity, freight, weather and environmental products plus official exchange environmental contract specifications.

External standards prove product semantics, not QORE implementation or provider support.

## 3. Existing UMI-07 owner retained

UMI-07 already owns:

- `CommodityReferenceTerms`;
- commodity class;
- measurement-unit identity;
- delivery grade;
- location identity;
- delivery method;
- delivery window;
- immutable physical-delivery alternatives;
- `CommodityFuturesContractTerms` composition over UMI-05 futures.

Lane 7 reuses those types where semantics are exact.

`GENERIC COMMODITY DELIVERY != SPECIALIZED COMMODITY CONTRACT COMPLETENESS`

## 4. Electricity gap

FpML electricity physical terms retain settlement-period profiles, load types and shaped quantities. A generic date window does not distinguish Base, Peak, Off-Peak, Block Hours or Custom delivery shapes.

`ElectricityContractTerms` composes existing `CommodityReferenceTerms`, existing `CommodityPhysicalDeliveryTerms`, a specialized `ElectricityDeliveryProfile`, and evidence.

No generic grade/location/window ownership is duplicated.

## 5. Electricity load and settlement periods

`ElectricityLoadType` retains the bounded categories BASE, PEAK, OFF_PEAK, BLOCK_HOURS and CUSTOM.

`ElectricitySettlementPeriodCode` is an externally governed canonical profile code. It identifies static settlement-period material without granting D06 schedule resolution.

At least one settlement-period code is required and duplicates are rejected.

`DELIVERY WINDOW != SETTLEMENT-PERIOD SHAPE`

## 6. Shaped electricity quantity

`ElectricityQuantityStep` retains an effective date, positive exact Decimal quantity and unit `EconomicIdentityId`.

Steps are date-unique and canonicalized. All steps must use one unit identity. The enclosing electricity contract requires that unit to equal the existing UMI-07 commodity measurement-unit identity and that every step fall in an eligible physical-delivery window.

No dispatch, metering or current load is represented.

## 7. Freight gap

FpML distinguishes freight contractual economics that generic physical commodity delivery does not retain.

The bounded owner distinguishes WET VOYAGE CHARTER with Worldscale points, DRY VOYAGE CHARTER with contract rate, and TIME CHARTER with contract rate.

It retains an explicit freight route/reference identity and calculation period.

`WORLDSCALE POINTS != CONTRACT RATE`

## 8. Freight boundary

`FreightTerms` is a static contract definition only. It contains no observed freight index, current Worldscale data, provider route symbol, valuation, payment calculation or execution.

Freight route identity is canonical QORE identity material, not a provider ticker.

## 9. Weather-index gap

A weather derivative is not a physical commodity-delivery contract.

`WeatherIndexTerms` retains instrument identity, weather-station/reference identity, weather index code, calculation period, contractual reference level and level unit, settlement-level method code, contractual notional per index unit, and evidence.

`WEATHER INDEX TERMS != WEATHER OBSERVATION`

## 10. Weather calculation boundary

The owner retains definition only. It does not calculate HDD, CDD, CPD, cumulative temperature, precipitation, weather settlement index, payoff or value.

Observed weather belongs to market/current-state evidence. Calculation/valuation belongs outside this D04 owner.

## 11. Environmental-product gap

FpML EnvironmentalProduct retains first-class product terms including product type, compliance period, vintages, applicable law and tracking system.

Generic commodity grade/location/window cannot safely encode all of those dimensions without caller convention.

`EnvironmentalProductTerms` reuses `CommodityReferenceTerms` and, when physically settled, `CommodityPhysicalDeliveryTerms`.

## 12. Vintage eligibility

`EnvironmentalVintageEligibility` explicitly distinguishes `EXACT_SET` from `CONTRACT_YEAR_AND_PRIOR`.

The distinction is material. Official exchange specifications demonstrate contracts that accept only one specific vintage versus standard contracts that accept a contract-year vintage and qualifying prior vintages.

Exact vintage sets are immutable, unique and canonicalized.

`SPECIFIC VINTAGE != CONTRACT-YEAR-PLUS-PRIOR-VINTAGES`

## 13. Compliance, law and tracking system

The owner may retain `EnvironmentalCompliancePeriod`, `EnvironmentalApplicableLawCode`, and `EnvironmentalTrackingSystemCode`.

Those are static references/qualifications.

`TRACKING SYSTEM REFERENCE != REGISTRY MUTATION`

No allowance registry account, surrender operation, compliance inventory or transfer is created by this owner.

## 14. Settlement boundary

Environmental contracts reuse `DerivativeSettlementStyle`.

PHYSICAL requires existing UMI-07 physical-delivery terms. CASH forbids physical-delivery terms.

This is static qualification only.

`STATIC SETTLEMENT TERMS != SETTLEMENT EXECUTION`

## 15. D04 versus other authorities

D04 owns the static contract definitions in this module.

Outside this owner:

- current power/weather/freight/emissions observations: D05;
- calendar/time resolution: D06;
- index calculation, payoff, PV and valuation: D07;
- account/compliance inventory and exposure: D08/D09 as applicable;
- execution: D10;
- delivery/payment/registry mutation and finality: D11 or governed external boundary;
- provider support: D03;
- event-contract outcome resolution: UNR-014;
- benchmark methodology/governance: UNR-005 where applicable.

## 16. Determinism and security

All new values are frozen/slotted dataclasses or bounded enums. Decimal magnitudes are exact and canonically serialized. Codes use canonical lowercase syntax. Dates and identities are caller supplied.

There is no implicit UUID, wall clock, randomness, network/provider SDK, database, filesystem runtime, thread/scheduler, secret material, valuation, current observation, execution or settlement mutation.

## 17. Test-oracle matrix

The dedicated tests directly falsify Base/Peak/Off-Peak distinctness; settlement-period presence, uniqueness and canonicalization; shaped quantity positivity, unit binding and delivery-window chronology; Wet Voyage Charter Worldscale-only semantics; Dry/Time Charter contract-rate-only semantics; Worldscale vs contract-rate collision; freight route retention; freight chronology; weather index/station/period/reference/notional retention; weather station/instrument collision; weather notional positivity; weather chronology; exact-vintage vs year-and-prior distinctness; vintage uniqueness and canonicalization; vintage-mode guards; compliance-period chronology; PHYSICAL environmental delivery requirement; CASH delivery exclusion; applicable-law/tracking-system retention; canonical code validation; strict date typing; frozen/slotted values; and absence of operational methods.

`GUARD EXISTS != REGRESSION ORACLE EXISTS`

## 18. Explicit deferred material

This candidate does not claim complete specialization for natural-gas pipeline cycles, oil terminal/pipeline nomination, coal composition/property schedules, commodity basket options, commodity Asian/digital options, event contracts, benchmark methodology, freight-index methodology, weather data-source production or emissions compliance workflow.

Further evidence is required before any such scope is added.

## 19. Integration order

Protected merge order:

`LANE 3 / PR #376 -> LANE 4 / PR #382 -> LANE 5 / PR #384 -> LANE 6 / PR #386 -> LANE 7 / #388`

This candidate is preparatory until upstream lanes integrate.

Final Lane-7 certification requires synchronization to then-current main, a new exact head, exact-head CI, diff audit, independent review and Integration-Gate adjudication.

## 20. Non-claims

`SPECIALIZED COMMODITY STATIC SEMANTICS != CURRENT MARKET DATA`

`SPECIALIZED COMMODITY STATIC SEMANTICS != INDEX CALCULATION`

`SPECIALIZED COMMODITY STATIC SEMANTICS != VALUATION`

`SPECIALIZED COMMODITY STATIC SEMANTICS != EXECUTION`

`SPECIALIZED COMMODITY STATIC SEMANTICS != SETTLEMENT / REGISTRY MUTATION`

`SPECIALIZED COMMODITY STATIC SEMANTICS != PROVIDER SUPPORT`

`LANE-7 CANDIDATE != UNR-009 CLOSURE`

`UNR-009 CLOSURE != UMI-14 PASS`

## 21. Mandatory UMI-12 follow-up

Before final UMI-14 closure, the cross-asset conformance harness and architecture documentation must be re-evaluated for all newly certified family owners.

This bounded candidate does not mutate UMI-12.
