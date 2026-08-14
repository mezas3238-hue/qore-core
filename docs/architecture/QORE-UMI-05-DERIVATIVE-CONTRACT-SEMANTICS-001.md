# QORE-UMI-05-DERIVATIVE-CONTRACT-SEMANTICS-001

## Status

**PROGRAM D / UMI-05 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #324  
Master roadmap: Issue #303  
Universal Markets / Instruments program: Issue #301  
Certified starting baseline: `c1b18750782a3a16bfb037f2f100dedcf2b1f238`  
Predecessor: UMI-04 / #322 / PR #323 — CLOSED

This artifact defines the minimum provider-neutral derivative contractual semantic
foundation required by UMI-05 after the exact-baseline audit recorded on #324.

The candidate covers bounded contractual semantics for:

- futures;
- options;
- forwards / NDF-style cash-settled forwards;
- swaps through explicit typed legs;
- narrow derivative multi-leg composition referencing existing UMI-02 identities.

It does **not** implement valuation, pricing, payoff calculation, cash-flow
materialization, observed fixings, auction processing, credit-event detection,
Greeks, implied volatility, volatility surfaces, curve construction, provider
adapters, execution, position mutation, settlement mutation, margin, risk
reservation, productive Cloud, or real-capital authority.

```text
DERIVATIVE CONTRACT TERMS
!=
DERIVATIVE PRICING ENGINE
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
STRIKE != GENERIC DECIMAL
PRICE STRIKE != RATE STRIKE != YIELD STRIKE != SPREAD STRIKE != LEVEL STRIKE
CONTRACTUAL FIXED RATE != CURVE ZERO/PAR/FORWARD RATE
TERM FIXING != COMPOUNDED OVERNIGHT FIXING
FIXING-CONVENTION CODE != FIXING ENGINE
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

A futures or option expiry date in immutable terms is a contractual specification.

A UMI-02 `IdentityLifecycleEvent` is evidence that a lifecycle event was recorded
for an identity.

```text
CONTRACTUAL EXPIRY DATE
!=
OBSERVED / RECORDED EXPIRY LIFECYCLE EVENT
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
```

It also established that later family contracts must explicitly model notional,
contract unit/multiplier and tick-value economic relationships where material.

UMI-05 therefore does not reuse execution `OrderQuantity`, infer notional from
price/quantity, or promote UMI-03 `FaceAmount` to derivative notional.

## 2.4 UMI-03 reuse boundary

UMI-05 reuses UMI-03 only where semantics are identical:

- `FinancialTenor`;
- `DayCountConventionCode`;
- `BusinessCalendarRef` as a D06-owned calendar reference;
- `SettlementConvention` as structural settlement/calendar semantics;
- `FixedIncomeSpread` as a bounded spread magnitude;
- `YieldConvention` for an explicitly YIELD-based strike.

It does not silently promote:

- `FaceAmount` to derivative notional;
- `CouponRate` to a universal derivative fixed rate;
- `FixedIncomeBenchmarkReference` to a universal derivative benchmark authority.

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

Requires an explicit quote/reference `EconomicIdentityId` and no rate/yield
convention.

## 4.2 RATE

Requires UMI-04 `RateCurveConvention` and no quote identity.

## 4.3 YIELD

Requires UMI-03 `YieldConvention` and no quote identity.

## 4.4 SPREAD / LEVEL

Carry neither rate/yield convention nor quote identity in this minimum contract.
Their parent underlying/reference identity plus explicit strike basis retains the
semantic referent.

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

## 6.1 Exercise style

Closed minimum styles:

- EUROPEAN;
- AMERICAN;
- BERMUDAN.

Bermudan terms require a non-empty, unique, immutable exercise-date tuple,
canonicalized chronologically. Every Bermudan exercise date must be on or before
expiry.

No business-calendar exercise-date generator exists.

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

## 8.1 FixedRateSwapLeg

Retains:

- notional schedule;
- `DerivativeContractRate`;
- day count;
- payment tenor;
- settlement convention.

No curve node is substituted for contractual fixed rate.

## 8.2 FloatingRateSwapLeg

Retains:

- notional schedule;
- derivative benchmark reference;
- `FixedIncomeSpread`;
- day count;
- payment tenor;
- reset tenor;
- **explicit `DerivativeFloatingRateConvention`**;
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

## 8.3 ReferenceReturnSwapLeg

Retains:

- notional schedule;
- typed reference identity and role;
- payment tenor;
- settlement convention.

The reference role code is responsible for distinguishing the contractual return
referent, for example total-return versus another certified reference-return role.

The leg does not calculate return performance.

## 8.4 ExchangeSwapLeg

Retains explicit amount/notional unit, payment date and PAY/RECEIVE direction.

This supports principal exchanges and FX-swap near/far exchanges without generating
payment instructions.

## 8.5 ProtectionSwapLeg

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

No cash-flow generation or discounting occurs.

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
- Bermudan exercise;
- maturity;
- fixing;
- swap effective/termination;
- notional schedule steps;
- exchange payment dates.

Exact `type(value) is date` validation rejects `datetime` laundering.

The stage adds no timezone-bearing datetime logical contract and makes no claim to
close repository-wide `GAP-FND04-TIME-01`.

D06 retains calendar/session/date-resolution authority.

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
9. RATE strike requires `RateCurveConvention`;
10. YIELD strike requires `YieldConvention`;
11. spread/level reject rate/yield/quote laundering;
12. legitimate non-positive strike/rate domains remain possible;
13. Bermudan requires explicit unique dates and deterministic order;
14. non-Bermudan exercise rejects Bermudan date tuples;
15. date roles reject datetime subclass laundering;
16. futures retain month/expiry/multiplier/settlement/tick value;
17. CASH futures reject first-notice date;
18. notice/last-trade dates cannot exceed expiry;
19. no invented universal notice-vs-last-trade ordering;
20. raw UUID cannot replace `EconomicIdentityId`;
21. option right/strike/exercise/settlement remain explicit;
22. listed multiplier and OTC notional sizing paths both work;
23. option with neither multiplier nor notional fails;
24. Bermudan date after expiry fails;
25. CASH forward requires fixing;
26. any fixing after maturity fails;
27. PHYSICAL forward may omit fixing;
28. PRE-CHK-UMI05-01: PHYSICAL forward may also retain a valid fixing;
29. floating fixing convention retains calculation/calendar/lag/lockout/shift;
30. floating fixing convention rejects raw/bool/int laundering;
31. floating leg requires typed fixing convention;
32. PRE-CHK-UMI05-02: term-rate vs compounded-in-arrears do not collapse;
33. fixed/floating/reference-return/exchange/protection legs remain distinct;
34. PRE-CHK-UMI05-03: CASH vs PHYSICAL protection do not collapse;
35. PRE-CHK-UMI05-04: auction vs fixed-recovery CASH protection do not collapse;
36. fixed-recovery requires CASH plus explicit `[0,1]` recovery rate;
37. auction and physical-delivery style coherence fails closed;
38. non-fixed-recovery method rejects recovery-rate laundering;
39. swap requires at least two typed legs;
40. swap requires PAY + RECEIVE;
41. swap leg IDs/ordinals unique;
42. swap ordinals contiguous and caller-order independent;
43. swap notional schedule starts at effective date;
44. later notional changes precede termination;
45. exchange date lies within swap term;
46. termination > effective;
47. composition references existing economic identities;
48. composition rejects self-reference and duplicate components;
49. composition ratio strictly positive;
50. composition tuple immutable with deterministic ordinals;
51. no pricing/Greeks/IV/margin/execution/settlement/curve-engine methods;
52. logical values deterministic and secret-free.

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
- `PRE-CHK-UMI05-04` protection auction/fixed-recovery collapse.

---

# 18. Explicit non-goals / downstream boundaries

A favorable UMI-05 result does NOT mean:

- any futures/options/OTC provider supports UMI-05 operationally;
- complete exchange or ISDA legal terms are certified;
- CDS auction/recovery or deliverable-obligation engines exist;
- derivative pricing or payoff generation exists;
- Greeks, IV or volatility surfaces exist;
- option exercise engine exists;
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
