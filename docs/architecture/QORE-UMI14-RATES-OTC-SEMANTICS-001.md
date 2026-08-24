# QORE-UMI14 Rates / OTC Static Semantics

Status: **GATE-B CURRENT-BASELINE RECERTIFICATION CANDIDATE — NOT GATE-C CERTIFIED**

Tracker: `#385`  
Historical preparatory audit: `#381`  
Historical preparatory PR: `#386` — CLOSED / SUPERSEDED / UNMERGED  
Target: `UMI13-UNR-008`  
Current sealed Gate-B baseline: `772c17b6d17702515fe4643df1275aa3f9aae085`  
Current sealed baseline tree: `8644143e5f36ca88655726cda7ac0257aea5bcf5`  
Gate-B branch: `agent/qore-umi14-rates-otc-full-closure-008`

## 1. Currentness rule

This document supersedes the historical baseline metadata carried by the old preparatory
candidate. PR #386 was reviewed against old main `b848f018146b4860664021e3715201509449cf75`
and its SHA-bound CI/reviews are historical evidence only.

The current Gate-B reconstruction starts from sealed main
`772c17b6d17702515fe4643df1275aa3f9aae085` and reuses the historically audited
implementation/test blobs only where the current repository proves that their reused
contract dependencies remain compatible.

`HISTORICAL CERTIFICATION != CURRENT CERTIFICATION`

`OLD PR #386 != CURRENT GATE-C CANDIDATE`

`AUTHORIZATION NEVER PROPAGATES`

## 2. Exact bounded file surface

Gate B is limited to these four additive paths:

- `src/qore/infrastructure/rates_otc_semantics.py`;
- `tests/infrastructure/test_rates_otc_semantics.py`;
- `tests/infrastructure/test_rates_otc_semantics_logical_identity.py`;
- `docs/architecture/QORE-UMI14-RATES-OTC-SEMANTICS-001.md`.

The source and test payloads are reused byte-for-byte from the historically hardened
candidate:

- source blob: `499adcca4229b6ff4ff6b2af2995225aa47aaaab`;
- primary tests blob: `5dd91af2091d2f9cb1985806b12e788542df5c53`;
- logical-identity tests blob: `2a6b820e6d7e137679a32a06b0cdf34de2033572`.

Only this architecture document is currentness-corrected for the new sealed baseline.
No certified existing owner is modified.

## 3. Purpose

This additive D04 owner addresses the bounded rates/OTC gaps retained by
`UMI13-UNR-008`:

- Forward Rate Agreement specialization;
- cap / floor / collar rate-strike schedule semantics;
- bounded vanilla fixed/floating swaption specialization.

It does not create a second generic swap, option, benchmark, curve, calendar,
execution, settlement or provider authority.

## 4. Existing owner reuse

The correction reuses current certified QORE primitives for:

- derivative terms and evidence IDs;
- contractual notional and notional schedules;
- contractual rates;
- benchmark references;
- floating-rate conventions;
- schedule conventions;
- fixed and floating swap legs;
- `SwapContractTerms`;
- option exercise terms;
- CASH / PHYSICAL settlement style;
- day-count, tenor, settlement, business-calendar and business-day conventions;
- `EconomicIdentityId`.

No reverse dependency from those existing owners into this specialized owner is added.

`EXISTING GENERIC OWNER != PRODUCT-SPECIFIC COMPLETENESS`

## 5. FRA bounded semantics

`FraTerms` retains the product material that a generic forward does not faithfully
establish:

- exact calculation-period start/end;
- payment date;
- contractual notional;
- fixed rate;
- floating benchmark reference;
- day-count convention;
- bounded `FraFixingDateOffset`;
- explicit static `FraDiscountingCode`;
- evidence.

The bounded owner requires exactly one benchmark tenor. Dual-tenor/interpolated FRA
remains outside this correction.

`FraFixingDateOffset` retains a signed exact business-day offset, explicit calendar
reference and business-day convention relative to calculation start. It resolves no
calendar and generates no date.

No current fixing, discount factor, settlement amount, present value or payment
mutation is calculated.

`FRA != GENERIC FORWARD BY IMPLICATION`

`FRA DISCOUNTING TERMS != DISCOUNT FACTOR`

## 6. Cap / floor / collar bounded semantics

`RateCapFloorTerms` retains:

- CAP / FLOOR / COLLAR product kind;
- effective and termination dates;
- contractual notional schedule;
- benchmark;
- optional constant spread;
- day count;
- payment/reset tenor;
- fixing convention;
- schedule/settlement convention;
- cap and/or floor strike schedules;
- evidence.

Required kind laws remain fail-closed:

- CAP requires cap strikes and forbids floor strikes;
- FLOOR requires floor strikes and forbids cap strikes;
- COLLAR requires both.

`RateStrikeSchedule` preserves an initial contractual rate and immutable canonical
dated changes. The owner generates no dates and stores no current observed rate.

`None` spread and explicit zero spread remain distinct logical material.

`CAP != FLOOR`

`CAP/FLOOR STRIKE SCHEDULE != CURRENT RATE`

## 7. Swaption bounded semantics

`SwaptionTerms` composes exact existing `SwapContractTerms`; it does not duplicate the
swap.

The bounded first owner accepts one fixed-rate leg plus one floating-rate leg and
preserves payer/receiver economics explicitly:

- PAYER => fixed PAY / floating RECEIVE;
- RECEIVER => fixed RECEIVE / floating PAY.

Payer/receiver is not inferred from generic CALL/PUT.

Exercise terms and expiry are static contractual material. CASH settlement may omit
or retain an explicit governed cash-settlement method; PHYSICAL forbids a cash method.

No option exercise instruction, calculated cash settlement or premium/payment
mutation is represented.

`SWAPTION != GENERIC OPTION OVER AN UNBOUND IDENTITY`

`PAYER SWAPTION != RECEIVER SWAPTION`

`STATIC CASH SETTLEMENT METHOD != CALCULATED CASH SETTLEMENT AMOUNT`

## 8. Chronology and fail-closed boundaries

The owner preserves the hardened chronology/type laws already covered by the reused
test payload, including:

- strict `date != datetime` validation;
- FRA calculation start before end;
- explicit contractual payment date without invented universal payment-at-start/end
  chronology;
- strike-step uniqueness/order and containing-term boundaries;
- cap/floor notional schedule binding;
- swaption expiry not after underlying effective date;
- American/Bermudan exercise material not after expiry;
- exact type checks and canonical codes.

## 9. Logical-projection protection

The dedicated logical-identity oracle file preserves complete independent projections
for:

- `FraTerms`;
- `RateCapFloorTerms` with populated optional material;
- direct FLOOR strike-payload materiality;
- `SwaptionTerms` with CASH/PAYER/Bermudan material;
- direct `SwaptionTerms.position` tuple-position materiality.

Expected values are manually reconstructed. They must not be manufactured from SUT
`logical_values()`, productive serializer/sort/fingerprint helpers, or actual output
reused as expected.

`GUARD EXISTS != REGRESSION ORACLE EXISTS`

## 10. Determinism / security

All additive values are frozen/slotted dataclasses or bounded enums/codes where
appropriate. IDs and dates are caller-supplied. Logical material is deterministic.

No implicit UUID, wall clock, randomness, network, provider SDK, database, filesystem
runtime, scheduler, thread, sleep, secret material, valuation or execution authority is
introduced.

## 11. Authority boundaries / non-claims

Outside this D04 owner:

- current benchmark/fixing observations -> D05;
- current calendar resolution / temporal authority -> D06;
- curves, discount factors, PV, pricing, Greeks -> D07;
- execution / exercise instruction -> D10;
- payment / settlement mutation and finality -> D11;
- provider product capability -> D03.

Also not claimed:

- FX pair / FX forward / FX swap ownership;
- cross-currency swap completeness;
- Shari'ah-compliant profit-rate / Wa'ad / Murabahah structures;
- dual-tenor/interpolated FRA;
- stepped/multiple spread schedules;
- cap/floor or swaption premium economics;
- provider support;
- Production or real capital.

`RATES / OTC STATIC SEMANTICS != CURRENT FIXING`

`RATES / OTC STATIC SEMANTICS != CURVE CONSTRUCTION`

`RATES / OTC STATIC SEMANTICS != VALUATION / GREEKS`

`RATES / OTC STATIC SEMANTICS != EXECUTION`

`RATES / OTC STATIC SEMANTICS != SETTLEMENT MUTATION`

## 12. Gate-B disposition

This branch is a current-baseline Gate-B correction only.

Historical DeepSeek/Claude reviews and historical QORE CI remain useful provenance but
are not current SHA-bound certification after rebasing onto sealed main.

Fresh Gate C must independently freeze the new exact head/tree/blobs/diff/synthetic,
run exact-candidate quality validation and obtain fresh independent audits.

This Gate-B artifact does not authorize:

- Draft PR creation under Gate C;
- exact-candidate certification;
- READY transition;
- merge;
- Gate F seal;
- `UNR-008` closure;
- UMI14 PASS;
- Program-D PASS;
- Production or real capital.

`GATE B CORRECTION != GATE C AUTHORIZATION`

## 13. Mandatory UMI-12 follow-up

Before final UMI14 closure, the cross-asset conformance harness and architecture
material must be re-evaluated for every newly certified owner. This bounded correction
does not mutate UMI-12.