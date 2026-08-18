# QORE-UMI14 Rates / OTC Static Semantics

Status: **PROGRAM D / UMI-14 LANE-6 CORRECTION CANDIDATE — INDEPENDENT CERTIFICATION REQUIRED**

Tracker: `#385`  
Preparatory audit: `#381`  
Target: `UMI13-UNR-008`  
Preparatory baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`  
Synchronized certification baseline: `b848f018146b4860664021e3715201509449cf75`

## 1. Purpose

This additive D04 owner addresses the bounded rates/OTC gaps that survived exact
repository falsification:

- Forward Rate Agreement specialization;
- cap / floor / collar rate-strike schedule semantics;
- vanilla fixed/floating swaption specialization.

It does not create a second generic swap, option, benchmark, curve, calendar,
execution, settlement or provider authority.

## 2. Evidence boundary

Integration Gate reconstructed exact UMI-05 mechanics on the preparatory baseline
and checked the product distinctions against primary FpML 5.12/5.13 Confirmation
semantics where cardinality and version-specific checks were material.

Integration Authority then synchronized this corrected candidate to certified
main `b848f018146b4860664021e3715201509449cf75` before exact-head qualification.

This document describes a correction candidate only.

`CANDIDATE != CERTIFICATION`

## 3. Existing UMI-05 reuse

The owner reuses certified UMI-05 primitives for:

- derivative terms and evidence IDs;
- contractual notional and notional schedules;
- contractual fixed rates;
- benchmark references;
- fixing conventions;
- schedule conventions;
- fixed and floating swap legs;
- `SwapContractTerms`;
- option exercise terms;
- CASH / PHYSICAL settlement style.

It also reuses UMI-03 fixed-income convention primitives where their semantics
are already identical: day count, tenor, settlement convention, business calendar
reference and business-day convention.

`EXISTING GENERIC OWNER != PRODUCT-SPECIFIC COMPLETENESS`

## 4. FRA gap and boundary

Generic `ForwardContractTerms` retains one maturity date and optional fixing, but
does not retain a distinct FRA calculation-period start/end pair or FRA
discounting qualification.

`FraTerms` therefore retains:

- exact calculation start;
- exact calculation end;
- payment date;
- contractual notional;
- fixed rate;
- floating benchmark reference;
- day count;
- bounded `FraFixingDateOffset`;
- explicit `FraDiscountingCode`;
- evidence.

The owner intentionally adds no payment-date chronology relative to the
calculation period beyond retaining the exact contractual date. A universal
payment-at-start or payment-at-end law is not invented without primary evidence.

No current fixing, discount factor, settlement amount or present value is
calculated.

## 5. Bounded FRA benchmark tenor

This bounded Confirmation-style FRA owner supports exactly one benchmark tenor.

`DerivativeBenchmarkReference.tenor` must not be `None`.

Dual-tenor / interpolated FRA is explicitly deferred and is not certified by this
owner.

`SINGLE BENCHMARK TENOR != UNIVERSAL FRA COMPLETENESS`

## 6. FRA fixing-date offset

`FraTerms` retains a bounded FRA-specific `FraFixingDateOffset`.

Semantics:

- offset is relative to the enclosing FRA calculation start/reset date;
- period unit is business days in this bounded owner;
- date-relative-to anchor is the enclosing `FraTerms.calculation_start_date`;
- no separate arbitrary anchor is accepted;
- offset direction is explicit through a signed integer;
- negative, zero and positive integer offsets are representable;
- `bool` is not an int;
- calendar reference is explicit;
- business-day convention is explicit.

`FraFixingDateOffset` retains:

- `business_days_offset`;
- `fixing_calendar_ref`;
- `business_day_convention`.

No date calculation, calendar resolution, adjusted date generation, lockout
semantics, observation-shift semantics or floating-rate calculation-engine
semantics occur.

## 7. FRA discounting qualification

`FraDiscountingCode` is an extensible canonical static code. It preserves a
contractual discounting qualification without embedding a discount-factor engine.

Discounting remains mandatory. An explicit governed code may represent a
no-discounting qualification; code presence does not itself assert economic
discounting.

`FRA DISCOUNTING TERMS != DISCOUNT FACTOR`

## 8. Cap / floor / collar gap

FpML represents cap/floor products through an interest-rate stream and retains
cap/floor strike schedules on floating-rate calculations.

A generic option and a generic swap leg do not by themselves establish this
product relationship.

`RateCapFloorTerms` retains:

- CAP / FLOOR / COLLAR product kind;
- effective and termination dates;
- notional schedule;
- benchmark;
- optional constant spread;
- day count;
- payment and reset tenor;
- fixing convention;
- schedule and settlement convention;
- cap and/or floor strike schedule;
- evidence.

### Spread optionality

`spread` is `FixedIncomeSpread | None`.

Absence is valid.

Explicit zero, negative and positive spreads remain governed solely by existing
`FixedIncomeSpread` semantics.

`None` and explicit zero are distinct logical material and are not normalized.

Only one constant spread is supported. Stepped or multiple spread schedules are
deferred.

`CAP/FLOOR SPREAD IS OPTIONAL AND NON-NORMALIZED`

## 9. Rate-strike schedules

`RateStrikeSchedule` contains:

- one initial contractual `DerivativeContractRate`;
- zero or more explicit dated changes.

Step dates are immutable, unique and canonicalized. The containing cap/floor
contract requires each change date to fall strictly inside its term.

The owner does not generate dates from tenor/calendar rules.

`STRIKE SCHEDULE != CURRENT RATE`

## 10. Cap / floor / collar invariants

- CAP requires cap strikes and forbids floor strikes.
- FLOOR requires floor strikes and forbids cap strikes.
- COLLAR requires both.
- termination must follow effective date.
- the notional schedule must begin at effective date.
- later notional changes must precede termination.
- benchmark identity cannot be the cap/floor instrument identity.

An isolated caplet/floorlet is not silently relabeled as a cap/floor by this
bounded owner. Further isolated-option specialization requires separate evidence
if final UMI-14 closure proves it necessary.

## 11. Swaption gap

`OptionContractTerms` is a generic CALL/PUT contract over an underlying identity.
That does not prove a swaption relationship to exact swap terms or preserve
payer/receiver fixed-leg economics.

`SwaptionTerms` therefore composes the existing exact `SwapContractTerms`
aggregate rather than duplicating swap economics.

`SWAPTION != GENERIC OPTION OVER AN UNBOUND IDENTITY`

## 12. Bounded vanilla swaption scope

The first bounded owner accepts exactly one fixed-rate leg and one floating-rate
leg in the underlying swap.

This is intentionally fail-closed.

It does not claim support for basis, cross-currency, multi-leg, non-standard or
structured swaptions merely because generic `SwapContractTerms` can contain
other leg forms.

## 13. Payer / receiver semantics

`SwaptionPosition` distinguishes PAYER and RECEIVER.

For the bounded vanilla underlying:

- PAYER requires fixed PAY / floating RECEIVE;
- RECEIVER requires fixed RECEIVE / floating PAY.

The position is not inferred from generic CALL/PUT and is retained directly in
logical material.

`PAYER SWAPTION != RECEIVER SWAPTION`

## 14. Exercise and chronology

The swaption retains existing `OptionExerciseTerms` and an explicit expiry date.

The candidate requires expiry not to follow the underlying swap effective date.
American-start and Bermudan exercise dates must not follow expiry.

This is static chronology only. No exercise decision or execution is performed.

## 15. Swaption settlement boundary

The owner reuses `DerivativeSettlementStyle`.

CASH may omit the explicit static `SwaptionCashSettlementMethodCode`.
CASH may retain an explicit static method.
PHYSICAL must not carry a cash method.

These are distinct logical states.

The method code identifies a governed contractual method only.

`STATIC CASH SETTLEMENT METHOD != CALCULATED CASH SETTLEMENT AMOUNT`

`SWAPTION TERMS != EXERCISE EXECUTION`

## 16. Premium non-claims

The bounded rates/OTC static product terms do not retain cap/floor option
premium or premium-payment economics.

Swaption static terms do not retain premium payment or premium economics.

No premium field exists in the bounded product types.

`PRODUCT CONTRACT != TRADE PAYMENT AUTHORITY`

## 17. D04 versus other authorities

D04 owns the static terms described here.

Outside this owner:

- current rate / fixing observations: D05;
- current calendar resolution and temporal authority: D06;
- curve construction, discount factors, PV, pricing and Greeks: D07;
- execution / exercise instruction: D10;
- payment / settlement mutation and finality: D11;
- provider product capability: D03.

## 18. FX and cross-currency boundary

Issue `#378` owns the bounded FX pair, FX forward/NDF, FX swap and FX option
currency-binding semantics.

`FX SWAP != CROSS-CURRENCY INTEREST-RATE SWAP`

The present owner does not add an FX quotation system or claim complete
cross-currency-swap specialization.

## 19. Shari'ah boundary

Profit-rate swaps, Wa'ad structures, Murabahah-based hedges and other
Shari'ah-compliant hedging structures are not silently mapped to conventional
interest-rate products. They remain cross-family authority.

## 20. Determinism and security

All new values are frozen/slotted dataclasses or closed enums where the set is
bounded. Codes use canonical lowercase syntax. Dates and identities are
caller-supplied. Logical values are deterministic.

There is no implicit UUID, wall clock, randomness, network, provider SDK,
database, filesystem runtime, scheduler, thread, sleep, secret material,
valuation or execution method.

## 21. Adversarial oracle matrix

The dedicated test module falsifies at minimum:

- FRA calculation-period chronology;
- FRA payment-at-start representability;
- absence of invented FRA payment-date bounds relative to the period;
- strict date typing;
- mandatory explicit FRA discounting and discounting-code distinction;
- fixed-rate distinction;
- benchmark/instrument collision;
- bounded single-tenor FRA law;
- FRA fixing-date offset signing and exact integer typing;
- FRA fixing calendar and business-day convention typing;
- FRA fixing-date offset logical sensitivity;
- strike-step ordering and duplicate dates;
- CAP/FLOOR/COLLAR schedule laws;
- strike-step term boundaries;
- notional effective-date binding;
- optional constant spread and None/zero distinction;
- current-rate negative space;
- exact swap binding for swaptions;
- payer/receiver logical distinctness;
- payer/receiver fixed-leg direction mismatch;
- non-vanilla underlying fail-closed behavior;
- expiry/underlying chronology;
- CASH method optionality and PHYSICAL exclusion;
- absence of premium fields in bounded product terms;
- swaption/underlying identity collision;
- Bermudan chronology;
- canonical code validation;
- frozen/slotted behavior;
- absence of operational methods.

`GUARD EXISTS != REGRESSION ORACLE EXISTS`

## 22. Integration order

The correction candidate has been synchronized to certified main
`b848f018146b4860664021e3715201509449cf75` before application.

Protected order:

`LANE 3 / PR #376 -> LANE 4 / PR #382 -> LANE 5 / PR #384 -> LANE 6 / #385`

Final Lane-6 certification still requires the resulting exact head, exact-head
CI, diff audit, independent review and Integration-Gate adjudication.

## 23. Non-claims

`RATES / OTC STATIC SEMANTICS != CURRENT FIXING`

`RATES / OTC STATIC SEMANTICS != CURVE CONSTRUCTION`

`RATES / OTC STATIC SEMANTICS != VALUATION / GREEKS`

`RATES / OTC STATIC SEMANTICS != EXERCISE EXECUTION`

`RATES / OTC STATIC SEMANTICS != SETTLEMENT MUTATION`

`RATES / OTC STATIC SEMANTICS != PROVIDER SUPPORT`

`BOUNDED FRA OWNER != DUAL-TENOR / INTERPOLATED FRA SUPPORT`

`BOUNDED CAP/FLOOR OWNER != STEPPED SPREAD-SCHEDULE SUPPORT`

`BOUNDED RATES/OTC STATIC PRODUCT TERMS != PREMIUM PAYMENT ECONOMICS`

`LANE-6 CANDIDATE != UNR-008 CLOSURE`

`UNR-008 CLOSURE != UMI-14 PASS`

## 24. Mandatory UMI-12 follow-up

Before final UMI-14 closure, the cross-asset conformance harness and its
architecture documentation must be re-evaluated for every newly certified owner.
This bounded candidate does not mutate UMI-12.