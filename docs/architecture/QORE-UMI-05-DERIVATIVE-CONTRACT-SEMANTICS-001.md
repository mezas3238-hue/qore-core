# QORE-UMI-05-DERIVATIVE-CONTRACT-SEMANTICS-001

## Status

**PROGRAM D / UMI-05 — FULL CLOSURE RECERTIFICATION RECORD; FINAL CLOSURE STATUS GOVERNED BY #301**

Tracking: Issue #324  
Master roadmap: Issue #303  
Universal Markets / Instruments program: Issue #301  
Historical certified starting baseline: `c1b18750782a3a16bfb037f2f100dedcf2b1f238`  
Full Closure reconstruction baseline: `54a71480b45b83c40cfac5a7629c1ea3685ac511`  
Full Closure reconstruction tree: `022ee2c28d268f3f9d312c156bfa37dbb9b4d99e`  
Predecessor: UMI-04 / #322 / PR #420 — FULL-CLOSURE RECERTIFIED / SEALED / CLOSED at the reconstruction baseline

Sections 1-18 preserve the historical UMI-05 implementation and certification
record. Section 19 is the current Full Closure recertification addendum and is
authoritative for current certification sequencing, evidence reconciliation,
ownership, carry-forward disposition and final closure status. This document does
not self-certify final closure; durable final disposition remains governed by the
serial Full Closure protocol and authorized #301 evidence.

This artifact defines the minimum provider-neutral derivative contractual semantic
foundation required by UMI-05 after the exact-baseline audit recorded on #324.

The candidate covers bounded contractual semantics for:

- futures;
- options;
- forwards / NDF-style cash-settled forwards;
- swaps through explicit typed legs;
- narrow derivative multi-leg composition referencing existing UMI-02 identities.

It does **not** implement valuation, pricing, payoff calculation, cash-flow or
payment-schedule materialization, observed fixings, auction processing,
credit-event detection, option-exercise execution, Greeks, implied volatility,
volatility surfaces, curve construction, provider adapters, execution, position
mutation, settlement mutation, margin, risk reservation, productive Cloud, or
real-capital authority.

```text
DERIVATIVE CONTRACT TERMS
!=
DERIVATIVE PRICING ENGINE
!=
DERIVATIVE SCHEDULE ENGINE
!=
DERIVATIVE SETTLEMENT ENGINE
!=
DERIVATIVE EXECUTION AUTHORITY
!=
PROVIDER SUPPORT
```

---

# 1. Governing invariants

```text
ECONOMIC DERIVATIVE IDENTITY -> UMI-02
LOCAL TERMS ID != ECONOMIC IDENTITY
LOCAL LEG ID != ECONOMIC IDENTITY
SYMBOL TEXT != DERIVATIVE IDENTITY
PROVIDER CONTRACT ID != DERIVATIVE ECONOMIC IDENTITY
CONTINUOUS FUTURES SERIES != NATIVE EXPIRING FUTURES CONTRACT
CONTINUOUS FUTURES SERIES -> UMI-02 CONTINUOUS_REFERENCE
CONTRACTUAL EXPIRY TERM != OBSERVED LIFECYCLE EVENT
QUANTITY != NOTIONAL
CONTRACT COUNT != NOTIONAL
CONTRACT MULTIPLIER != QUANTITY
CONTRACT MULTIPLIER != NOTIONAL
FACE / PAR != DERIVATIVE NOTIONAL BY IMPLICATION
TICK SIZE != TICK VALUE
PRICE × QUANTITY != UNIVERSAL ECONOMIC VALUE
OPTION RIGHT != EXERCISE STYLE
AMERICAN EXERCISE STYLE != AMERICAN EXERCISE WINDOW
STRIKE != GENERIC DECIMAL
PRICE STRIKE != RATE STRIKE != YIELD STRIKE != SPREAD STRIKE != LEVEL STRIKE
PRICE STRIKE QUOTE IDENTITY != PRICE STRIKE QUOTE BASIS
CONTRACTUAL FIXED RATE != CURVE ZERO/PAR/FORWARD RATE
TERM FIXING != COMPOUNDED OVERNIGHT FIXING
FIXING-CONVENTION CODE != FIXING ENGINE
PAYMENT TENOR != PAYMENT SCHEDULE SEMANTICS
STUB / ROLL RULE != CALENDAR / SCHEDULE ENGINE
CASH SETTLEMENT != PHYSICAL SETTLEMENT
PROTECTION AUCTION != FIXED-RECOVERY != PHYSICAL DELIVERY
PROTECTION SETTLEMENT METHOD != SETTLEMENT ENGINE
SETTLEMENT SEMANTICS != SETTLEMENT MUTATION AUTHORITY
BENCHMARK REFERENCE != RATE-CURVE CONSTRUCTION AUTHORITY
DERIVATIVE TERMS != PRICING / GREEKS / IMPLIED VOLATILITY
DERIVATIVE CONTRACT != EXECUTION AUTHORITY
DERIVATIVE CONTRACT != PROVIDER SUPPORT
MULTI-LEG CONTRACT != FAKE PRIMITIVE INSTRUMENT
LEG ORDER != CALLER TUPLE ORDER
EVIDENCE REF != EVIDENCE CONTENT
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO REPRODUCIBILITY -> NO PROMOTION
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

Repository-wide carry-forwards remain binding:

- `GAP-FND04-TIME-01` — OPEN / HIGH;
- `GAP-FND07-RES-01` — OPEN / HIGH;
- PR #298 — HOLD.

UMI-05 does not claim to close or promote any of them.

---

# 2. Exact-baseline audit

## 2.1 UMI-02 owns economic identity and generic lifecycle

The certified UMI-02 boundary already provides:

- `EconomicIdentityId`;
- `EconomicIdentityKind`;
- `IdentityConstructionKind`;
- `IdentityRelationship`;
- `IdentityLifecycleEvent`;
- `LifecycleEventCode`;
- evidence-bearing effective-dated identity relationships.

`IdentityConstructionKind` already distinguishes `NATIVE`, `SYNTHETIC`,
`COMPOSITE` and `CONTINUOUS_REFERENCE`.

A `CONTINUOUS_REFERENCE` is constrained by UMI-02 to be a `REFERENCE_OBJECT`.

Therefore UMI-05 MUST NOT invent:

- another sovereign derivative economic ID;
- another continuous-futures-series identity;
- another generic lifecycle-event graph.

UMI-05 terms bind existing `EconomicIdentityId` values.

Local `DerivativeTermsId` and `DerivativeLegId` identify immutable semantic
artifacts/components only.

```text
DERIVATIVE TERMS ID != ECONOMIC IDENTITY
DERIVATIVE LEG ID != ECONOMIC IDENTITY
```

An `EconomicIdentityId` value alone does not prove kind or construction kind.
Graph/domain composition must verify identity evidence where a native derivative,
underlying, reference object, currency or continuous reference distinction is
material.

### Contractual date versus lifecycle event

A futures expiry, option expiry or American exercise-start date in immutable terms
is a contractual specification.

A UMI-02 `IdentityLifecycleEvent` is evidence that a lifecycle event was recorded
for an identity.

```text
CONTRACTUAL DATE
!=
OBSERVED / RECORDED LIFECYCLE EVENT
```

Where both are present, governed composition may require consistency. UMI-05 does
not rebuild UMI-02 lifecycle history.

## 2.2 Existing futures code is provider/execution infrastructure

The certified baseline futures adapter boundary retains provider contract IDs,
legacy symbol mapping, market observations and execution requests/receipts.

The inspected boundary does not establish canonical universal derivative terms for:

- contract month;
- expiry;
- multiplier;
- contractual tick value;
- cash/physical settlement style;
- first-notice date;
- last-trade date;
- typed underlying/reference identity.

Provider-specific contract IDs remain provider-side facts.

```text
PROVIDER CONTRACT ID + SYMBOL
!=
CANONICAL DERIVATIVE CONTRACT ECONOMICS
```

No existing futures/provider file is modified by UMI-05.

## 2.3 FND-04 requires explicit derivative economic dimensions

FND-04 previously certified:

```text
QUANTITY != NOTIONAL
CONTRACT COUNT != FACE VALUE != BASE UNITS != TOKEN UNITS
MULTIPLIER != QUANTITY
TICK SIZE != TICK VALUE
PRICE × QUANTITY != UNIVERSAL ECONOMIC VALUE
PRICE REQUIRES SEMANTIC KIND / QUOTE OR DENOMINATION CONTEXT WHERE MATERIAL
```

FND-04 also identifies for interest-rate swaps contractual `tenor/schedules` as
material family semantics and assigns UMI-05 the obligation to distinguish
contract count, notional, multiplier, underlying/reference, leg structure and
price/rate semantics.

UMI-05 therefore does not reuse execution `OrderQuantity`, infer notional from
price/quantity, promote UMI-03 `FaceAmount` to derivative notional, or treat a
quote-asset identity as sufficient proof of PRICE strike quote basis.

## 2.4 UMI-03 reuse boundary

UMI-05 reuses UMI-03 only where semantics are identical:

- `FinancialTenor`;
- `DayCountConventionCode`;
- `BusinessCalendarRef` as a D06-owned calendar reference;
- `BusinessDayConventionCode` as structural date-adjustment semantics;
- `SettlementConvention` as structural settlement/calendar semantics;
- `FixedIncomeSpread` as a bounded spread magnitude;
- `YieldConvention` for an explicitly YIELD-based strike.

It does not silently promote:

- `FaceAmount` to derivative notional;
- `CouponRate` to a universal derivative fixed rate;
- `FixedIncomeBenchmarkReference` to a universal derivative benchmark authority;
- `FixedIncomePriceBasisCode` to a universal derivative PRICE-strike basis.

The last item is intentionally separate: UMI-03's price-basis code is explicitly
fixed-income scoped. UMI-05 adds a derivative-scoped quote-basis code rather than
turning a bounded prior-stage type into universal authority.

## 2.5 UMI-04 reuse boundary

UMI-05 reuses `RateCurveConvention` only for a strike explicitly classified as
`RATE`.

It does not reuse `ZeroRate`, `ParRate` or `ForwardRate` as a swap contractual fixed
rate.

```text
CURVE RATE != CONTRACTUAL FIXED RATE
```

## 2.6 Verified structural gap

At certified baseline `c1b18750782a3a16bfb037f2f100dedcf2b1f238`, direct
inspection establishes the absence of one canonical provider-neutral derivative
terms layer capable of retaining the minimum semantics required by #301 while
preserving the above authority boundaries.

Classification:

`VERIFIED STRUCTURAL GAP — UMI-05 IMPLEMENTATION DELTA REQUIRED`

Code-search absence was not used as exhaustive proof.

---

# 3. Common derivative primitives

## 3.1 Local IDs and evidence refs

UMI-05 adds:

- `DerivativeTermsId`;
- `DerivativeLegId`;
- `DerivativeEvidenceRef`.

All are UUID-backed. They are not economic identity and they do not prove retained
evidence content.

## 3.2 DerivativeNotional

`DerivativeNotional` retains:

- positive exact Decimal magnitude;
- explicit `EconomicIdentityId` for the notional unit/reference asset.

It is deliberately distinct from `OrderQuantity`, futures contract count,
`FaceAmount`, contract multiplier, cash balance and market price.

The wrapper does not prove the referenced identity kind. UMI-02 graph composition
must do so when required.

## 3.3 DerivativeNotionalSchedule

Swaps may amortize or accrete. A single scalar notional is insufficient.

`DerivativeNotionalSchedule` therefore retains a non-empty immutable tuple of:

- effective date;
- typed notional.

Rules:

- exact `date`, never `datetime`;
- unique dates;
- caller order canonicalized chronologically;
- one stable notional-unit identity across steps.

Within `SwapContractTerms`, non-exchange leg notional schedules start on the swap
effective date and later changes occur before termination.

This is contract structure only. It calculates no exposure or risk capacity.

## 3.4 Contract multiplier and tick value

`DerivativeContractMultiplier` is a positive exact Decimal plus explicit unit
identity.

`DerivativeTickValue` is a positive exact Decimal plus explicit value identity.

Neither authorizes a universal formula involving price, quantity or tick size.

```text
MULTIPLIER != NOTIONAL
TICK VALUE != TICK SIZE
```

Market/provider tick-size evidence remains outside this contract.

## 3.5 Contractual fixed rate

`DerivativeContractRate` is a finite Decimal and permits negative rates.

It is a contractual fixed-rate magnitude, not a zero/par/forward curve node, yield
or spread.

## 3.6 Derivative benchmark reference

`DerivativeBenchmarkReference` retains:

- reference `EconomicIdentityId`;
- typed semantic role code;
- optional `FinancialTenor`.

It does not contain observations, curve nodes, interpolation or fixing values.

`REFERENCE ATTACHMENT != REFERENCE / CURVE AUTHORITY`.

---

# 4. Strike semantics

A raw Decimal cannot preserve universal strike meaning.

`DerivativeStrike` therefore retains an explicit basis:

- `PRICE`;
- `RATE`;
- `YIELD`;
- `SPREAD`;
- `LEVEL`.

All strike values are finite exact Decimal. No blanket positivity rule exists
because valid rate and market-level domains may be zero or negative.

## 4.1 PRICE

Requires:

- explicit quote/reference `EconomicIdentityId`;
- explicit `DerivativePriceQuoteBasisCode`;
- no rate/yield convention.

Examples of different quote-basis semantics include `currency-per-unit` and
`percent-of-par`. The code retains a contractual quote-basis semantic only; it
does not implement price conversion or valuation.

```text
QUOTE CURRENCY / REFERENCE IDENTITY
!=
QUOTE BASIS
```

### PRE-CHK-UMI05-05 — PRICE quote-basis collapse

A prior candidate retained PRICE magnitude and quote identity but not quote basis.
That allowed two economically distinct PRICE strikes with the same numeric value
and quote identity — for example currency-per-unit versus percent-of-par — to
collapse to identical logical material.

FND-04 explicitly requires price semantic/quote context where material, while
UMI-03 already proves quote basis cannot be inferred from magnitude.

Current correction requires a typed `DerivativePriceQuoteBasisCode` for every
PRICE strike and includes it in deterministic logical values.

Independent review must attempt to reproduce the collision under the exact head.

## 4.2 RATE

Requires UMI-04 `RateCurveConvention` and rejects PRICE quote identity/basis.

## 4.3 YIELD

Requires UMI-03 `YieldConvention` and rejects PRICE quote identity/basis.

## 4.4 SPREAD / LEVEL

Carry neither rate/yield convention nor PRICE quote identity/basis in this minimum
contract. Their parent underlying/reference identity plus explicit strike basis
retains the semantic referent.

If future evidence proves a specialized spread-strike convention is required, it
must be added explicitly rather than laundering spread through a rate convention.

---

# 5. Futures contract terms

`FuturesContractTerms` retains:

- local terms ID;
- native derivative economic identity attachment;
- reference/underlying identity;
- settlement identity;
- structural contract month;
- contractual expiry date;
- contract multiplier;
- CASH/PHYSICAL settlement style;
- evidence;
- optional contractual tick value;
- optional first-notice date;
- optional last-trade date.

Rules:

- instrument identity differs from reference identity;
- instrument identity differs from settlement identity;
- first-notice and last-trade dates cannot be after expiry;
- CASH futures cannot carry first-notice date;
- no universal first-notice-vs-last-trade ordering is invented.

### Continuous futures

The terms object validates typed identity shape but cannot prove UMI-02
construction kind.

Governed composition must prevent a UMI-02 `CONTINUOUS_REFERENCE` from being
laundered into the native expiring-contract role.

```text
CONTINUOUS SERIES REFERENCE != NATIVE FUTURES CONTRACT
```

---

# 6. Option contract terms

`OptionContractTerms` retains:

- local terms ID;
- option identity;
- underlying identity;
- settlement identity;
- CALL/PUT right;
- typed strike;
- expiry;
- exercise terms;
- CASH/PHYSICAL settlement style;
- evidence;
- optional listed multiplier;
- optional OTC notional.

At least one of multiplier/notional is required.

This allows listed sizing, OTC notional sizing or explicitly retained contracts
where both are meaningful. It never infers order quantity or position.

## 6.1 Exercise style and exercise window

Closed minimum styles:

- EUROPEAN;
- AMERICAN;
- BERMUDAN.

Rules:

- EUROPEAN carries no American/Bermudan date material in this minimum contract;
- AMERICAN requires an explicit contractual `american_start_date` and the parent
  option requires that date to be on or before expiry;
- BERMUDAN requires a non-empty, unique immutable exercise-date tuple,
  canonicalized chronologically, with every exercise date on or before expiry.

The American start date is a contractual term, not proof of a UMI-02 listing/start
lifecycle event. Governed composition may later require both facts to agree.

No business-calendar exercise-date generator or exercise-decision engine exists.

### PRE-CHK-UMI05-07 — American exercise-window collapse

A prior candidate retained only `AMERICAN` plus option expiry. Two contracts with
the same expiry but different contractual exercise commencement dates therefore
collapsed to the same logical material.

UMI-02 deliberately assigns right/exercise economics to UMI-05 and does not provide
one universal expiry/start field that UMI-05 may silently assume.

Current correction requires explicit `american_start_date`, validates it as exact
`date`, bounds it by parent expiry, and includes it in deterministic logical values.

Independent review must attempt to collapse two otherwise-equal American options
with different exercise starts.

## 6.2 Non-claims

Option terms contain no delta, gamma, vega, theta, rho, implied volatility, model
price, volatility surface or exercise-decision engine.

---

# 7. Forward contract terms

`ForwardContractTerms` retains:

- local terms ID;
- derivative identity;
- underlying/reference identity;
- settlement identity;
- derivative notional;
- typed agreed strike;
- maturity date;
- CASH/PHYSICAL settlement style;
- evidence;
- optional fixing terms;
- optional UMI-03 settlement convention.

`DerivativeFixingTerms` retains a typed benchmark/reference, fixing date and evidence
reference. It is not an observed fixing value.

```text
FIXING REFERENCE + FIXING DATE
!=
OBSERVED FIXING VALUE
```

## 7.1 PRE-CHK-UMI05-01 — physical-forward fixing overrestriction

Historical first draft incorrectly imposed:

```text
PHYSICAL FORWARD -> fixing MUST be None
```

That is not universal. A deliverable commodity or other physical forward may retain
an explicit contractual reference/fixing.

Correct exact rule:

```text
CASH -> fixing REQUIRED
PHYSICAL -> fixing OPTIONAL
ANY fixing -> fixing_date <= maturity_date
```

No fixing observation is produced and no settlement is executed.

This correction must be independently re-falsified at the exact review head.

---

# 8. Swap leg architecture

A swap is not represented as one generic nullable-field object.

UMI-05 defines explicit typed leg families. All legs retain local leg identity,
positive ordinal, PAY/RECEIVE direction and evidence.

## 8.1 DerivativeScheduleConvention

Periodic swap legs require both a tenor and structural schedule semantics.

`DerivativeScheduleConvention` retains:

- typed stub-rule code;
- typed roll-rule code;
- D06-owned `BusinessCalendarRef`;
- `BusinessDayConventionCode`.

This permits contracts such as `short-first` versus `short-last`, or an
end-of-month versus IMM-style roll rule, to remain distinct without generating
payment dates.

The codes do not implement schedule algorithms. D06 retains calendar resolution
and any future certified schedule engine.

```text
PAYMENT TENOR != PAYMENT SCHEDULE
STUB / ROLL CODE != SCHEDULE ENGINE
CALENDAR REF != CALENDAR AUTHORITY
```

### PRE-CHK-UMI05-06 — swap stub/roll schedule collapse

A prior candidate retained effective/termination dates, payment/reset tenors and
settlement convention but no stub/roll schedule semantics.

FND-04 explicitly requires `tenor/schedules` for interest-rate swaps. Two otherwise
equal swaps could therefore retain different `short-first` versus `short-last`
stub rules or different roll rules while producing identical logical material.

Current correction requires `DerivativeScheduleConvention` on fixed-rate,
floating-rate and reference-return periodic legs and includes it in logical values.
Exchange legs already retain exact payment date; protection legs represent
contingent settlement and do not become periodic premium legs by implication.

Independent review must attempt the same-term/same-tenor/different-stub and
different-roll collisions.

## 8.2 FixedRateSwapLeg

Retains:

- notional schedule;
- `DerivativeContractRate`;
- day count;
- payment tenor;
- schedule convention;
- settlement convention.

No curve node is substituted for contractual fixed rate.

## 8.3 FloatingRateSwapLeg

Retains:

- notional schedule;
- derivative benchmark reference;
- `FixedIncomeSpread`;
- day count;
- payment tenor;
- reset tenor;
- explicit `DerivativeFloatingRateConvention`;
- schedule convention;
- settlement convention.

### DerivativeFloatingRateConvention

Retains:

- `DerivativeFloatingRateCalculationCode`;
- D06-owned `BusinessCalendarRef` for fixing-date interpretation;
- non-negative fixing lag in business days;
- non-negative lockout business days;
- explicit observation-shift boolean.

The calculation code is an extensible semantic code. Examples include distinct
retained meanings such as:

- `term-rate`;
- `compounded-in-arrears`;
- future certified averaging/compounding methods.

The code does not implement an algorithm.

```text
CALCULATION CODE != FIXING ENGINE
CALENDAR REF != RESOLVED FIXING DATES
```

D06 retains calendar resolution. D05 retains observed fixing evidence. D07/UMI-10
retain downstream calculation/valuation outputs.

### PRE-CHK-UMI05-02 — floating fixing/calculation collapse

Historical candidate head could distinguish benchmark, reset tenor and day count
but could not distinguish a term-rate leg from an overnight-compounded leg using
the same benchmark/reference envelope.

That was a current UMI-05 contractual semantic defect because OIS / term-rate
transformation is part of the leg contract, not a valuation result.

Current correction requires `DerivativeFloatingRateConvention` on every floating
leg and includes it in deterministic logical material.

Independent review must attempt to collapse:

```text
TERM RATE
vs
COMPOUNDED IN ARREARS
```

under otherwise equal leg material.

## 8.4 ReferenceReturnSwapLeg

Retains:

- notional schedule;
- typed reference identity and role;
- payment tenor;
- schedule convention;
- settlement convention.

The reference role code is responsible for distinguishing the contractual return
referent, for example total-return versus another certified reference-return role.

The leg does not calculate return performance.

## 8.5 ExchangeSwapLeg

Retains explicit amount/notional unit, payment date and PAY/RECEIVE direction.

This supports principal exchanges and FX-swap near/far exchanges without generating
payment instructions.

## 8.6 ProtectionSwapLeg

Retains:

- notional schedule;
- typed credit/protection reference;
- typed contingency code;
- CASH/PHYSICAL settlement style;
- explicit protection settlement-method code;
- settlement asset/reference identity;
- settlement convention;
- optional fixed contractual recovery rate;
- evidence.

`DerivativeProtectionSettlementMethodCode` is a semantic code, not an auction or
settlement engine.

Current explicit method coherence includes:

```text
auction -> CASH
fixed-recovery -> CASH + DerivativeRecoveryRate REQUIRED
physical-delivery -> PHYSICAL
non-fixed-recovery -> fixed_recovery_rate MUST be None
```

`DerivativeRecoveryRate` is an exact finite Decimal constrained to `[0, 1]`.

### PRE-CHK-UMI05-03 — protection settlement-style collapse

Historical candidate retained contingency and a calendar/settlement convention but
could not distinguish CASH from PHYSICAL protection settlement.

Current correction requires settlement style and settlement identity in the
protection leg.

### PRE-CHK-UMI05-04 — protection settlement-method collapse

After PRE-CHK-UMI05-03, a second counterexample remained:

Two protection contracts could have equal reference, notional, contingency, CASH
style, settlement currency and calendar, yet one could settle via an auction and
the other via a contractually fixed recovery fraction.

That difference materially changes contractual economics and cannot be deferred as
mere D11 settlement execution.

Current correction therefore retains:

- protection settlement-method code;
- fixed recovery fraction when and only when the method is `fixed-recovery`.

This closes the structural collision without implementing:

- credit-event detection;
- auction mechanics;
- recovery observation;
- deliverable-obligation legal qualification;
- settlement mutation.

A favorable UMI-05 result therefore does **not** mean full ISDA legal programmability
or provider CDS support.

---

# 9. Swap contract terms

`SwapContractTerms` retains:

- local terms ID;
- swap economic identity;
- effective date;
- termination date;
- immutable typed leg tuple;
- evidence.

Rules:

- termination > effective date;
- at least two typed legs;
- unique leg IDs;
- unique ordinals;
- ordinals contiguous from 1;
- caller tuple order canonicalized by ordinal;
- at least one PAY and one RECEIVE leg;
- non-exchange leg notional schedules begin at swap effective date;
- later notional changes occur before termination;
- exchange-leg payment dates fall inside the inclusive swap term.

No universal exactly-two-leg rule exists. Basis, cross-currency and exchange
structures may require more.

Ordinal is retained sequence semantics, not financial-time ordering and not payoff
calculation order.

No cash-flow generation, schedule generation or discounting occurs.

---

# 10. Derivative multi-leg composition

UMI-05 needs a narrow way to retain combinations such as option spreads, calendar
spreads, futures spreads and ratio combinations without inventing fake primitive
component instruments.

`DerivativeCompositionLeg` references an existing component `EconomicIdentityId`
and retains:

- local leg ID;
- ordinal;
- LONG/SHORT side;
- positive ratio;
- evidence.

`DerivativeCompositionTerms` binds the composition's own UMI-02 economic identity
to at least two component legs.

Rules:

- no self-reference;
- component identities unique in canonical representation;
- unique leg IDs;
- unique contiguous ordinals;
- deterministic order independent of caller tuple order.

Repeated same-component exposure should be expressed through the ratio rather than
duplicated component entries.

This is intentionally narrower than UMI-09.

UMI-09 retains authority for higher-order structured/hybrid/synthetic products,
capital protection, embedded non-derivative components and custom payoff
transformation.

```text
DERIVATIVE COMPONENT COMPOSITION
!=
STRUCTURED PRODUCT ENGINE
```

---

# 11. Authority ownership matrix

| Concern | Authority | UMI-05 behavior |
|---|---|---|
| Economic derivative identity | UMI-02 | reuse `EconomicIdentityId` |
| Continuous futures reference | UMI-02 | never re-created in UMI-05 |
| Identity relationships/lifecycle events | UMI-02 | reused/deferred |
| Contractual derivative terms/dates | UMI-05 | immutable specification |
| Financial tenor/day count | UMI-03 | reused |
| Calendar identity/resolution | D06 | reference retained; resolution deferred |
| Schedule stub/roll semantics | UMI-05 contract / D06 resolution | retained; no date generation |
| Rate-curve convention | UMI-04 | reused only for RATE strike |
| Curve construction | D07 / later engine | not implemented |
| Derivative contract economics | UMI-05 | current scope |
| Observed market/fixing evidence | D05 | not produced here |
| Fixing calculation/valuation | D07 / UMI-10 | no engine here |
| Commodity delivery lifecycle/details | UMI-07 | beyond generic PHYSICAL style |
| Structured/hybrid products | UMI-09 | downstream |
| Prices, Greeks, IV, valuations | D07 / UMI-10 | downstream |
| Execution | D10 / D18 | downstream |
| Position/settlement mutation | D11 | downstream |
| Risk/margin/reservation | D08 / D09 / D10 | downstream |

---

# 12. Fail-closed and non-claim rules

A valid UMI-05 terms object proves only that supplied immutable values satisfy this
structural semantic contract.

It does not prove:

- UMI-02 identity kind/construction kind is correct;
- provider supports the product;
- evidence refs resolve to valid evidence;
- observed fixing exists;
- market price exists;
- contract is currently live/tradable;
- price quote-basis code has a conversion engine;
- schedule stub/roll code has a D06 resolver;
- floating calculation code has an implemented certified algorithm;
- protection settlement method has an implemented auction/settlement engine;
- complete ISDA or exchange legal terms are captured;
- contract is valuable, executable or settleable;
- risk capacity or margin exists.

```text
TERMS VALID
!=
IDENTITY KIND VERIFIED
!=
PROVIDER SUPPORTED
!=
VALUABLE
!=
EXECUTABLE
```

---

# 13. Temporal boundary

UMI-05 uses `date` for contractual date roles:

- expiry;
- first notice;
- last trade;
- American exercise start;
- Bermudan exercise;
- maturity;
- fixing;
- swap effective/termination;
- notional schedule steps;
- exchange payment dates.

Exact `type(value) is date` validation rejects `datetime` laundering.

The stage adds no timezone-bearing datetime logical contract and makes no claim to
close repository-wide `GAP-FND04-TIME-01`.

D06 retains calendar/session/date-resolution authority. `DerivativeScheduleConvention`
retains only structural rule codes and D06 references; it does not calculate dates.

---

# 14. Security / evidence boundary

Local IDs and evidence refs are UUID-backed. Semantic codes use bounded lowercase
syntax. No contract field accepts provider credentials, tokens or secret values.

Evidence refs identify retained evidence but are not evidence content.

---

# 15. Compatibility / blast radius

The candidate is additive.

It does not modify UMI-02, UMI-03, UMI-04, futures adapters, provider adapters,
order/execution, runtime, persistence, market data, risk, position/settlement or
client/CEO surfaces.

Existing futures/provider contracts remain bounded and may later map into UMI-05
only under explicit governed composition.

`PROVIDER FACT != CANONICAL AUTHORITY` remains binding.

---

# 16. Mandatory adversarial test obligations

The exact-head test suite and independent reviewer must attack at minimum:

1. UUID-backed local IDs/evidence reject raw/secret-like strings;
2. contract month and leg ordinal reject bool/invalid integers;
3. notional/multiplier/tick value remain distinct semantic types;
4. notional/multiplier/tick value reject zero/negative/non-finite values;
5. contractual fixed rate remains distinct from curve rate/yield/spread;
6. notional schedule is immutable, sorted, unique-date and unit-stable;
7. benchmark reference requires typed identity/role;
8. PRICE/RATE/YIELD/SPREAD/LEVEL strike semantics remain distinct;
9. PRE-CHK-UMI05-05: PRICE strike requires typed quote basis;
10. same PRICE value/quote identity under different quote bases stays distinct;
11. RATE strike requires `RateCurveConvention` and rejects PRICE material;
12. YIELD strike requires `YieldConvention` and rejects PRICE material;
13. spread/level reject rate/yield/PRICE laundering;
14. legitimate non-positive strike/rate domains remain possible;
15. Bermudan requires explicit unique dates and deterministic order;
16. European rejects American/Bermudan date material;
17. PRE-CHK-UMI05-07: American requires explicit exercise start;
18. American exercise start after expiry fails;
19. different American starts produce different logical material;
20. date roles reject datetime subclass laundering;
21. futures retain month/expiry/multiplier/settlement/tick value;
22. CASH futures reject first-notice date;
23. notice/last-trade dates cannot exceed expiry;
24. no invented universal notice-vs-last-trade ordering;
25. raw UUID cannot replace `EconomicIdentityId`;
26. option right/strike/exercise/settlement remain explicit;
27. listed multiplier and OTC notional sizing paths both work;
28. option with neither multiplier nor notional fails;
29. Bermudan date after expiry fails;
30. CASH forward requires fixing;
31. any fixing after maturity fails;
32. PHYSICAL forward may omit fixing;
33. PRE-CHK-UMI05-01: PHYSICAL forward may also retain a valid fixing;
34. floating fixing convention retains calculation/calendar/lag/lockout/shift;
35. floating fixing convention rejects raw/bool/int laundering;
36. floating leg requires typed fixing convention;
37. PRE-CHK-UMI05-02: term-rate vs compounded-in-arrears do not collapse;
38. schedule convention retains typed stub/roll/calendar/BDC;
39. schedule convention rejects raw-type laundering;
40. fixed/floating/reference-return periodic legs require schedule convention;
41. PRE-CHK-UMI05-06: short-first vs short-last do not collapse;
42. PRE-CHK-UMI05-06: different roll rules do not collapse;
43. fixed/floating/reference-return/exchange/protection legs remain distinct;
44. PRE-CHK-UMI05-03: CASH vs PHYSICAL protection do not collapse;
45. PRE-CHK-UMI05-04: auction vs fixed-recovery CASH protection do not collapse;
46. fixed-recovery requires CASH plus explicit `[0,1]` recovery rate;
47. auction and physical-delivery style coherence fails closed;
48. non-fixed-recovery method rejects recovery-rate laundering;
49. swap requires at least two typed legs;
50. swap requires PAY + RECEIVE;
51. swap leg IDs/ordinals unique;
52. swap ordinals contiguous and caller-order independent;
53. swap notional schedule starts at effective date;
54. later notional changes precede termination;
55. exchange date lies within swap term;
56. termination > effective;
57. composition references existing economic identities;
58. composition rejects self-reference and duplicate components;
59. composition ratio strictly positive;
60. composition tuple immutable with deterministic ordinals;
61. no pricing/Greeks/IV/margin/execution/settlement/curve/schedule-engine methods;
62. logical values deterministic and secret-free.

Passing tests do not self-certify architecture.

---

# 17. Independent review requirements

Because ChatGPT / Integration Gate materially designed and implemented the
candidate, `NO SELF-CERTIFICATION` applies.

Required sequence:

```text
IMPLEMENTATION
-> EXACT-HEAD QORE CI
-> INTERNAL PRE-FALSIFICATION
-> EXACT-HEAD FREEZE
-> CLAUDE INDEPENDENT ADVERSARIAL REVIEW
-> INTEGRATION GATE INDEPENDENT FALSIFICATION
-> CORRECTION + FULL RE-REVIEW IF REQUIRED
-> PROTECTED EXPECTED-HEAD MERGE
-> ACTUAL MERGE VERIFICATION
-> POST-MERGE MAIN 0/0
-> NEW CERTIFIED BASELINE
```

Any mutation after review freeze invalidates that review.

The independent review must explicitly re-falsify:

- `PRE-CHK-UMI05-01` physical-forward fixing overrestriction;
- `PRE-CHK-UMI05-02` floating term/OIS calculation collapse;
- `PRE-CHK-UMI05-03` protection CASH/PHYSICAL collapse;
- `PRE-CHK-UMI05-04` protection auction/fixed-recovery collapse;
- `PRE-CHK-UMI05-05` PRICE quote-basis collapse;
- `PRE-CHK-UMI05-06` swap stub/roll schedule collapse;
- `PRE-CHK-UMI05-07` American exercise-window collapse.

---

# 18. Explicit non-goals / downstream boundaries

A favorable UMI-05 result does NOT mean:

- any futures/options/OTC provider supports UMI-05 operationally;
- complete exchange or ISDA legal terms are certified;
- CDS auction/recovery or deliverable-obligation engines exist;
- derivative pricing or payoff generation exists;
- Greeks, IV or volatility surfaces exist;
- option exercise engine exists;
- payment schedule/calendar generation exists;
- fixing observation or floating-rate calculation engine exists;
- swap cash-flow generation exists;
- curve bootstrapping/interpolation exists;
- discounting/PV exists;
- commodity delivery lifecycle certification exists;
- structured/hybrid product certification exists;
- UMI-06/07/08/09/10 is authorized;
- execution authority exists;
- settlement mutation authority exists;
- risk/margin/capacity reservation exists;
- productive QORE Cloud / production readiness / real capital is authorized;
- `GAP-FND04-TIME-01` is closed;
- `GAP-FND07-RES-01` is closed;
- PR #298 is promoted.

The candidate means only:

> QORE has a provider-neutral immutable semantic vocabulary for the minimum
> contractual economics of the derivative families covered by UMI-05, subject to
> exact-head independent review and Integration Gate certification.

---

# 19. Full Closure recertification addendum

## 19.1 Full Closure reconstruction baseline

The UMI-05 Full Closure read-only reconstruction began from exact current `main`:

- SHA: `54a71480b45b83c40cfac5a7629c1ea3685ac511`;
- tree: `022ee2c28d268f3f9d312c156bfa37dbb9b4d99e`;
- merge commit signature: verified / valid;
- current `main` is the verified UMI-04 Full Closure merge baseline;
- QORE CI #1231 / run `32305110042` completed successfully on that exact SHA.

The repository state, exact Git objects and current owner blobs are authoritative.
Historical PR bodies, issue prose, branch names, prior CI or review verdicts do not
replace current verification.

```text
NO VERIFICATION -> NO APPROVAL
NO EVIDENCE -> NO CLAIM
CI GREEN ALONE != ENGINEERING APPROVAL
HISTORICAL HEAD != CURRENT AUTHORITY
HISTORICAL CERTIFICATION != FULL CLOSURE RECERTIFICATION
```

## 19.2 Historical PR #325 certification ledger

UMI-05's original implementation remains historical certification evidence:

- tracking issue: #324;
- PR: #325 — `QORE-UMI-05 — Derivatives Contract Semantics`;
- certified starting base: `c1b18750782a3a16bfb037f2f100dedcf2b1f238`;
- final reviewed candidate head: `127e5a4f01deed550eb2f6eb4e2c2f82ffbab9ef`;
- candidate / merge tree: `aa0100af3ee3079bdcc321c0aca4726b0f95607b`;
- synthetic PR merge used by historical CI: `03449841fbe1fcf4ff82f98c1db889825ae0d74a`;
- authoritative historical QORE CI: #1042 / run `31828749791` / SUCCESS;
- Ruff PASS;
- Mypy PASS on 574 source files;
- Pytest 2497 passed with six inherited warnings;
- global statement coverage 84%;
- `derivative_contract_semantics.py` statement coverage 90%;
- original implementation delta: three additive files, `+3904/-0`;
- actual merge: `22241b770975083cd31bfa65a680339cec5a33ed`;
- actual merge parents:
  - `c1b18750782a3a16bfb037f2f100dedcf2b1f238`;
  - `127e5a4f01deed550eb2f6eb4e2c2f82ffbab9ef`;
- actual merge tree: `aa0100af3ee3079bdcc321c0aca4726b0f95607b`;
- actual merge signature: verified / valid.

Earlier candidate heads and their review/CI evidence remain historical only. The
final reviewed head above is the only historical #325 candidate authority retained
for the original certification ledger.

## 19.3 Later owner-local hardening — UMI05-LI-01

A later logical-identity/oracle audit established an owner-local test-oracle
completeness gap. It did not establish a production defect.

Durable ledger:

- retrospective tracker: #405 / `UMI05-LI-01`;
- classification: TEST-ONLY ORACLE GAP / MEDIUM;
- PR: #412 — `QORE-UMI05-LI-01 — complete derivative projection oracles`;
- base: `c9e7467bcd65f7cd4afdc8f7cd3ab7b5f7f5564a`;
- corrected final head: `11b464a40003028530dd9f403217c8562de2bcbe`;
- corrected final tree: `155ae9e52d1605542da258e6dd3b514deced2cb8`;
- corrected final test blob: `251848e39a3e634836d43f789d11fc5e44d27aa7`;
- production source blob remained unchanged:
  `36e4d672459c489573eabc7ba5413bb5ef99c3a6`;
- exact corrected synthetic PR merge:
  `323eefa39bfab6c44b0ce604b1db4c55c3142e05`;
- authoritative corrected QORE CI: #1212 / run `32205103878` / SUCCESS;
- Ruff PASS;
- Mypy PASS on 612 source files;
- Pytest 3237 passed with six historical warnings;
- total statement coverage 86%;
- derivative owner statement coverage 90%;
- actual merge: `0ea5ee2774b860acffc51bea773bb9e7c462c9dc`;
- merge parents:
  - `c9e7467bcd65f7cd4afdc8f7cd3ab7b5f7f5564a`;
  - `11b464a40003028530dd9f403217c8562de2bcbe`;
- merge tree: `155ae9e52d1605542da258e6dd3b514deced2cb8`;
- merge signature: verified / valid.

The rejected intermediate
`cc59501c540f5fda6ee6e0bf4c20b38c5f7c87a8` introduced unauthorized full-file
reconstruction drift and has zero qualification value. CI #1211 attached to that
rejected intermediate is likewise not qualification evidence for the corrected
R8 head.

The final hardening supplies independent expected-side complete-projection oracles
and explicit optional-presence witnesses for the targeted Futures, Option, Forward
and Protection logical-material contracts. Historical reviews of earlier R5/R6/R7
heads do not qualify the corrected R8 head.

Disposition:

`UMI05-LI-01 = CLOSED`

## 19.4 Full Closure Gate-A findings and correction disposition

Gate-A reconstruction found five material UMI-05-owned recertification findings
and no surviving production or test-oracle defect.

### FC05-01 — stale implementation-candidate status / historical ledger

Classification: `UMI_INTERNAL_NONCODE`.

The live artifact still described UMI-05 as an implementation candidate and did
not durably retain the final #325 Git-object certification ledger as current
recertification evidence.

Resolution in this addendum:

- the top status now records Full Closure recertification posture;
- #325 final base/head/tree/CI/merge/signature evidence is retained;
- historical heads remain historical only;
- exact Git objects, not narrative snapshots, govern recertification.

`FC05-01 -> RESOLVED IN CANDIDATE`

### FC05-02 — missing UMI05-LI-01 durable evidence

Classification: `UMI_INTERNAL_NONCODE`.

The architecture artifact predated the later owner-local oracle correction and did
not record the final corrected R8 chain.

Resolution in this addendum:

- #405 / PR #412 / exact corrected head/tree/blobs / CI #1212 / merge are retained;
- the TEST-ONLY classification is preserved;
- the rejected intermediate and its failed CI remain explicit historical
  non-authority;
- no false production-defect claim is introduced.

`FC05-02 -> RESOLVED IN CANDIDATE`

### FC05-03 — current-main authority and downstream reconciliation

Classification: `UMI_INTERNAL_NONCODE`.

The historical artifact correctly bounded generic derivative authority but could
not encode later Program-D specialized owners and current cross-owner state.

Resolution is defined in sections 19.5-19.7.

`FC05-03 -> RESOLVED IN CANDIDATE`

### FC05-04 — historical certification procedure is not definitive Full Closure

Classification: `UMI_INTERNAL_NONCODE`.

Historical UMI-05 certification predates the mandatory final whole-UMI audit,
correction/re-audit loop, IA final falsification and authorized #301 final evidence
law.

Resolution is defined in section 19.10.

`FC05-04 -> RESOLVED IN CANDIDATE`

### FC05-05 — stale current TIME-01 carry-forward disposition

Classification: `UMI_INTERNAL_NONCODE`.

Sections 1-18 correctly preserve the historical UMI-05 fact that
`GAP-FND04-TIME-01` was OPEN/HIGH during original certification. Current GitHub
state is different: authoritative tracker #333 is CLOSED after its independently
governed downstream remediation.

Current disposition:

- historical OPEN/HIGH statements remain historical evidence;
- current Full Closure state is `CLOSED_DOWNSTREAM_VERIFIED`;
- downstream closure includes merged PR #408 and the verified post-merge baseline
  `a88aa34677ca3778275d8fcca972627ff6b2714a`;
- no UMI-05 production or test change is inferred from that downstream closure.

`FC05-05 -> RESOLVED IN CANDIDATE`

No additional material UMI-05-owned source/test defect was established by Gate A.
A later independent review finding, if valid, must be corrected inside UMI-05
before closure and cannot be exported solely because another owner is nearby.

## 19.5 Current UMI-05 authority

UMI-05 remains the bounded generic provider-neutral derivative contractual
primitive owner for:

- local derivative terms/leg/evidence artifact identities;
- derivative notional and notional schedules;
- contract multiplier and contractual tick-value semantics;
- typed strike basis and PRICE quote-basis qualification;
- dated futures month/expiry/multiplier/settlement/notice/trade-date semantics;
- generic vanilla option right/strike/expiry/exercise/settlement/sizing semantics;
- generic forward maturity/fixing/settlement semantics;
- generic fixed-rate, floating-rate, reference-return, exchange and protection swap
  leg primitives;
- generic swap aggregation with deterministic leg identity/order;
- structural derivative schedule/fixing conventions without a calendar or fixing
  engine;
- narrow derivative component composition with LONG/SHORT/ratio semantics;
- deterministic, immutable and secret-free logical material for those contracts.

This remains a generic primitive authority. Product specialization discovered by
later audit does not retroactively convert every specialized product gap into a
UMI-05 defect.

```text
GENERIC DERIVATIVE PRIMITIVE
!=
EVERY SPECIALIZED DERIVATIVE PRODUCT
```

## 19.6 Current downstream / cross-owner reconciliation

### UMI-02

Owns canonical economic/reference identity, identity construction, relationships
and generic lifecycle. UMI-05 consumes `EconomicIdentityId` and does not create a
second economic identity graph.

### UMI-03

Owns reusable financial-tenor, day-count, yield/spread and bounded fixed-income
semantic contracts that UMI-05 composes only where exact.

### UMI-04

Owns rate/curve term-structure and quotation-convention semantics. UMI-05 reuses
bounded rate convention material without becoming a curve-construction owner.

### D05

Owns acquired/observed market and fixing evidence. Static fixing terms in UMI-05
do not produce a current fixing.

### D06

Owns current calendar/time/date resolution. UMI-05 retains date and schedule-rule
semantics but does not resolve calendars or generate schedules.

### D07 / UMI-10

Owns pricing, valuation, Greeks, implied volatility, calculated observations and
valuation methodology execution. UMI-05 does not calculate them.

### UMI-07

Owns commodity-specific physical-delivery qualification. Generic UMI-05
CASH/PHYSICAL style does not replace commodity grade/location/method/window terms.

### UMI-08

Owns bounded perpetual/funding/network contractual specialization while reusing
UMI-05 derivative multiplier/tick primitives where exact.

### UMI-09

Owns higher-order structured/hybrid/synthetic composition and structured features.
UMI-05 retains only narrow derivative component composition.

### D08 / D09

Own account/capital/collateral/risk/exposure/capacity authority. Derivative
notional and valid contract terms do not reserve capacity.

### D10 / D18

Own execution and submission authority. UMI-05 terms do not authorize an order.

### D11

Own position, cash, payment and settlement mutation. Static settlement semantics do
not execute settlement.

### UMI-14 specialized derivative lanes

Current Program-D specialized work remains separate from the generic UMI-05 owner:

- FX lane / #378 / PR #382 adds FX pair, dual-currency-flow, NDF, near/far and
  FX-option bindings while reusing UMI-05 where exact;
- exotic-option lane / #380 / PR #384 adds bounded digital/touch/Asian and
  option-feature composition without recreating vanilla UMI-05 option terms;
- rates/OTC lane / #385 / PR #386 adds FRA, cap/floor/collar and swaption
  specialization while explicitly retaining the UMI-05 generic swap owner;
- volatility/variance/correlation lane / #392 / PR #393 adds specialized static
  tradeable-contract semantics while retaining UMI-05 as generic derivative
  primitive owner;
- CFD lane / #398 / PR #399 uses bounded qualification/composition over existing
  UMI-05 economic forms rather than creating a universal replacement or narrowing
  generic `ForwardContractTerms`.

These open/preparatory specialized PRs are not `main` and do not constitute
integrated support merely because a type or candidate exists.

```text
SPECIALIZED PRODUCT GAP != DEFECT IN GENERIC UMI05 OWNER
OPEN PR != MAIN
PREPARATORY CANDIDATE != INTEGRATED SUPPORT
```

If a future specialized review proves a collision inside the generic UMI-05
contract itself, that new evidence must be independently adjudicated rather than
being hidden under a cross-owner label.

## 19.7 Current carry-forward ledger

At this Full Closure reconstruction/correction baseline:

- `GAP-FND04-TIME-01` / #333:
  `CLOSED_DOWNSTREAM_VERIFIED` under FND-04 ownership after PR #408 and verified
  post-merge baseline `a88aa34677ca3778275d8fcca972627ff6b2714a`;
- `GAP-FND07-RES-01` / #332:
  `CROSS_OWNER_VERIFIED_OPEN / OPEN-HIGH` under D08/D09/D10 distributed-capacity
  ownership;
- PR #298:
  `CROSS_OWNER_VERIFIED_OPEN / OPEN-DRAFT-HOLD` under provider-instrument/runtime
  ownership;
- later UMI-14 specialized derivative PRs:
  cross-owner preparatory/open until individually integrated under their own gates.

A cross-owner disposition is not permission to export UMI-05 internal debt. Gate A
found no current evidence that #332, #298 or the specialized UMI-14 lanes are
required to satisfy the bounded generic UMI-05 contract itself.

## 19.8 Current owner blob / no-regression ledger

Gate-A current-main owner state before this documentation correction:

- production source:
  `src/qore/infrastructure/derivative_contract_semantics.py`;
- production source blob:
  `36e4d672459c489573eabc7ba5413bb5ef99c3a6`;
- primary/hardened test owner:
  `tests/infrastructure/test_derivative_contract_semantics.py`;
- test blob:
  `251848e39a3e634836d43f789d11fc5e44d27aa7`;
- pre-Full-Closure architecture artifact blob:
  `a61effb926048868671eb33d198009c7136d8e61`.

Gate A established:

```text
SURVIVING UMI05 PRODUCTION DEFECT = NONE VERIFIED
SURVIVING UMI05 TEST-ORACLE DEFECT = NONE VERIFIED
UMI05-LI-01 = CLOSED
```

The present correction is documentation/evidence/governance-only. It does not
modify production source or tests and must not manufacture an engineering change
merely to make Full Closure appear substantive.

## 19.9 Determinism, security, hidden-work and open-PR reconciliation

Gate-A direct owner audit found no current UMI-05-specific evidence of:

- implicit wall clock;
- implicit UUID generation in deterministic UMI-05 contracts;
- implicit randomness;
- mutable global authority;
- hidden provider/network/file/database I/O;
- hidden retry/sleep/thread/scheduler behavior;
- execution or corrective-trading side effects;
- credentials, tokens, passwords or productive secrets in contract material;
- UMI-05-owned material TODO/FIXME/HACK debt.

Open-PR file-surface review found no current open PR modifying any of the three
UMI-05 owner files listed in section 19.8. Specialized UMI-14 derivative PRs add
separate owner files and do not mutate the generic owner at the reconstruction
baseline.

This is current evidence, not a guarantee against future drift. The exact candidate
and integrated state must each be reconstructed again at their applicable gates.

## 19.10 Definitive Full Closure protocol

The historical sequence in section 17 remains evidence of the original UMI-05
certification procedure. It is not sufficient for current Full Closure.

UMI-05 may be declared `FULL-CLOSURE RECERTIFIED / SEALED / CLOSED` only through:

```text
COMPLETE UMI05 OWNER WORK
-> ZERO MATERIAL UMI05 INTERNAL PENDING WORK
-> EXACT-CANDIDATE QUALITY GATE
-> CLAUDE EXACT-CANDIDATE READ-ONLY AUDIT
-> IA CANDIDATE FALSIFICATION
-> COMPLETE CORRECTION OF EVERY VALID FINDING
-> NEW EXACT-HEAD CI + RE-AUDIT WHEN HEAD CHANGES MATERIALLY
-> CLAUDE CANDIDATE CLEAN
-> IA CANDIDATE PASS
-> EXPLICIT READY AUTHORIZATION
-> EXPLICIT EXPECTED-HEAD MERGE AUTHORIZATION
-> VERIFY ACTUAL MERGE SHA/TREE/PARENTS/SIGNATURE
-> VERIFY MAIN == MERGE
-> POST-MERGE QORE CI ON EXACT MERGE SHA
-> INTEGRATED OWNER SOURCE/TEST/ARTIFACT RECONSTRUCTION
-> INTEGRATED HIDDEN-WORK + OPEN-PR INTERFERENCE AUDIT
-> CLAUDE FINAL WHOLE-UMI05 AUDIT ON ACTUAL CURRENT MAIN
-> COMPLETE CORRECTION / RE-AUDIT OF EVERY VALID FINAL FINDING
-> CLAUDE FINAL CLEAN
-> IA FINAL FALSIFICATION
-> ZERO VERIFIED MATERIAL UMI05-OWNED PENDING WORK
-> EXPLICIT GATE F AUTHORIZATION
-> DURABLE FINAL #301 EVIDENCE
-> FREEZE FINAL SHA/TREE/OWNER BLOBS/EVIDENCE COMMENT ID
-> UMI05 FULL-CLOSURE RECERTIFIED / SEALED / CLOSED
-> ONLY THEN UMI06
```

Binding laws:

```text
PR MERGED != UMI CLOSED
CI GREEN != UMI CLOSED
CLAUDE PRE-INTEGRATION PASS != FINAL WHOLE-UMI PASS
HISTORICAL REVIEW != CURRENT-HEAD REVIEW
NO GREEN EXACT HEAD -> NO MERGE
NO POST-MERGE VERIFICATION -> NO NEXT STEP
NO FINAL WHOLE-UMI AUDIT -> NO #301 FINAL EVIDENCE
NO IA FINAL PASS -> NO #301 FINAL EVIDENCE
NO EXPLICIT GATE F -> NO #301 MUTATION
```

No authorization propagates from one gate to another.

## 19.11 Current Full Closure candidate posture / non-claims

This addendum resolves the five Gate-A owner-local non-code findings in the
candidate artifact. It does not self-certify that the candidate is clean; exact
post-write diff audit, exact-head QORE CI, independent exact-candidate Claude audit
and IA falsification remain mandatory.

Until that sequence is complete:

```text
DOCUMENTATION CORRECTED != FULL CLOSURE
CANDIDATE EXISTS != CERTIFIED CANDIDATE
ZERO PENDING CLAIM REQUIRES REVALIDATION
```

Nothing in UMI-05 Full Closure authorizes:

- provider operational support;
- pricing, valuation or Greeks;
- execution or exercise execution;
- settlement/payment/position mutation;
- account/risk/capacity authority;
- productive credentials;
- Production accounts;
- real capital;
- real-money trading;
- autonomous productive execution;
- promotion of PR #298;
- automatic integration of UMI-14 specialized candidates;
- UMI-06 Full Closure before UMI-05 is formally sealed.

`TEST/DEMO != PRODUCTION`

`SEMANTIC SUPPORT != PROVIDER SUPPORT != OPERATIONAL SUPPORT != PRODUCTION AUTHORITY`
