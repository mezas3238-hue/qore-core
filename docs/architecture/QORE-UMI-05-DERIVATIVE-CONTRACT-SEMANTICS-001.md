# QORE-UMI-05-DERIVATIVE-CONTRACT-SEMANTICS-001

## Status

**PROGRAM D / UMI-05 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #324  
Master roadmap: Issue #303  
Universal Markets / Instruments program: Issue #301  
Certified starting baseline: `c1b18750782a3a16bfb037f2f100dedcf2b1f238`  
Predecessor: UMI-04 / #322 / PR #323 — CLOSED

This artifact defines the minimum provider-neutral derivative contractual semantic
foundation required by UMI-05 after the exact-baseline repository audit recorded
on #324.

It covers bounded contractual semantics for:

- futures;
- options;
- forwards / NDF-style cash-settled forwards;
- swaps through explicit typed legs;
- derivative multi-leg composition referencing existing UMI-02 identities.

It does **not** implement valuation, pricing, payoff calculation, cash-flow
materialization, Greeks, implied volatility, volatility surfaces, curve
construction, provider adapters, execution, position mutation, settlement
mutation, margin, risk reservation, productive Cloud, or real-capital authority.

```text
DERIVATIVE CONTRACT TERMS
!=
DERIVATIVE PRICING ENGINE
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
CASH SETTLEMENT != PHYSICAL SETTLEMENT
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

UMI-05 does not close or promote any of them.

---

# 2. Exact-baseline audit

## 2.1 UMI-02 owns identity and generic lifecycle

The certified UMI-02 boundary already provides:

- `EconomicIdentityId`;
- `EconomicIdentityKind`;
- `IdentityConstructionKind`;
- `IdentityRelationship`;
- `IdentityLifecycleEvent`;
- `LifecycleEventCode`;
- evidence-bearing effective-dated identity relationships.

`IdentityConstructionKind` already distinguishes:

- `NATIVE`;
- `SYNTHETIC`;
- `COMPOSITE`;
- `CONTINUOUS_REFERENCE`.

A `CONTINUOUS_REFERENCE` is required by UMI-02 to be a `REFERENCE_OBJECT`.

Therefore UMI-05 MUST NOT invent:

- `DerivativeId` as another economic identity authority;
- `FuturesSeriesId` as a competing continuous-series identity;
- a second generic lifecycle-event graph.

UMI-05 terms bind existing `EconomicIdentityId` values.

Local `DerivativeTermsId` and `DerivativeLegId` identify immutable semantic
artifacts/components only.

```text
DERIVATIVE TERMS ID != DERIVATIVE ECONOMIC IDENTITY
DERIVATIVE LEG ID != DERIVATIVE ECONOMIC IDENTITY
```

### Contractual date versus lifecycle event

A futures expiry date or option expiry date in an immutable terms artifact is a
contract specification.

A UMI-02 `IdentityLifecycleEvent` is evidence that a lifecycle event was recorded
for an identity at an effective time.

They are not interchangeable authorities:

```text
CONTRACTUAL EXPIRY DATE
!=
OBSERVED / RECORDED EXPIRY LIFECYCLE EVENT
```

Composition/integration may require them to agree when both exist, but UMI-05 does
not rebuild UMI-02 lifecycle history.

## 2.2 Existing futures contracts are adapter/execution boundaries

The baseline futures adapter contracts retain:

- provider name;
- provider contract identifier;
- mapping to legacy `market_data.Instrument(symbol)`;
- market-data observations;
- paper/simulation execution requests and receipts.

The inspected canonical futures adapter boundary does not retain universal
contractual:

- contract month;
- expiry;
- multiplier;
- tick-value relationship;
- cash/physical settlement style;
- first-notice date;
- last-trade date;
- typed underlying/reference identity.

Provider-specific IBKR contract identifiers are explicitly provider-side.

Therefore:

```text
FUTURES PROVIDER CONTRACT ID + LEGACY SYMBOL
!=
CANONICAL FUTURES CONTRACT ECONOMICS
```

Existing futures modules remain valid bounded adapter/execution infrastructure and
are not modified by this stage.

## 2.3 FND-04 requires explicit economic dimensions

FND-04 previously certified:

```text
QUANTITY != NOTIONAL
CONTRACT COUNT != FACE VALUE != BASE UNITS != TOKEN UNITS
MULTIPLIER != QUANTITY
TICK SIZE != TICK VALUE
PRICE × QUANTITY != UNIVERSAL ECONOMIC VALUE
```

It also established that later family contracts must explicitly model, where
material:

- notional / face / par;
- contract unit / multiplier;
- tick-value economic relationship;
- denomination/reference identity.

This is direct positive evidence that UMI-05 cannot reuse execution
`OrderQuantity` or infer derivative economics from price and quantity.

## 2.4 UMI-03 reuse boundary

UMI-05 reuses UMI-03 only where the semantic is identical:

- `FinancialTenor`;
- `DayCountConventionCode`;
- `SettlementConvention` and its D06-governed calendar references;
- `FixedIncomeSpread` as a bounded spread magnitude;
- `YieldConvention` when a derivative strike is explicitly a yield strike.

It does NOT silently promote:

- `FaceAmount` to derivative notional;
- `CouponRate` to a generic derivative fixed rate;
- `FixedIncomeBenchmarkReference` to a universal derivative benchmark reference.

Those names and original scopes are not identical.

## 2.5 UMI-04 reuse boundary

UMI-05 reuses `RateCurveConvention` only for a strike whose semantic basis is
explicitly `RATE`.

UMI-05 does NOT reuse:

- `ZeroRate`;
- `ParRate`;
- `ForwardRate`

as contractual swap fixed rates.

Those are UMI-04 curve-node semantics, not immutable contract coupon/rate terms.

```text
CURVE RATE != CONTRACTUAL FIXED RATE
```

## 2.6 Verified structural gap

At certified baseline `c1b18750782a3a16bfb037f2f100dedcf2b1f238`, direct
inspection establishes the absence of one canonical provider-neutral derivative
terms layer capable of retaining the minimum semantics required by #301 while
respecting the above authority boundaries.

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

All are UUID-backed.

They are not economic identity and do not prove retained evidence content.

## 3.2 DerivativeNotional

`DerivativeNotional` retains:

- positive exact Decimal magnitude;
- explicit `EconomicIdentityId` for the notional unit/reference asset.

It is deliberately distinct from:

- `OrderQuantity`;
- futures contract count;
- `FaceAmount`;
- contract multiplier;
- cash balance;
- market price.

The type itself does not prove whether the referenced identity is a currency,
commodity unit, token, share-like unit, or another reference object. UMI-02 graph
composition must validate kind/relationship evidence where material.

## 3.3 DerivativeNotionalSchedule

Swaps may amortize or accrete.

A single scalar notional would incorrectly make such contracts impossible.

`DerivativeNotionalSchedule` therefore retains a non-empty immutable tuple of:

- effective date;
- typed notional.

Rules:

- dates are exact `date`, never `datetime`;
- dates unique;
- caller order canonicalized chronologically;
- all steps retain the same notional unit identity.

Within `SwapContractTerms`, rate/reference/protection leg schedules must start on
swap `effective_date`; later changes must precede termination.

This is retained contract structure only. No balance, exposure or risk reservation
is calculated.

## 3.4 Contract multiplier

`DerivativeContractMultiplier` is:

- positive Decimal;
- explicit unit/reference `EconomicIdentityId`.

It means per-contract multiplier semantics.

It is NOT an order quantity and is NOT a notional amount.

No automatic formula:

```text
quantity × multiplier × price
```

is authorized by this type.

## 3.5 Tick value

`DerivativeTickValue` retains:

- positive Decimal value;
- explicit economic value identity.

It is the contractual value of one minimum tick per contract where such a term is
meaningful.

It does NOT define market tick size or minimum price increment. Those remain
market/provider evidence concerns.

## 3.6 Contractual fixed rate

`DerivativeContractRate` is a finite Decimal, including negative values.

It is a derivative contractual fixed-rate magnitude.

It is not:

- UMI-04 zero rate;
- UMI-04 par rate;
- UMI-04 forward rate;
- UMI-03 yield;
- UMI-03 spread.

## 3.7 Derivative benchmark reference

`DerivativeBenchmarkReference` retains:

- reference `EconomicIdentityId`;
- typed semantic role code;
- optional `FinancialTenor`.

It does not contain curve nodes, discount factors, interpolation or fixing values.

`REFERENCE ATTACHMENT != REFERENCE / CURVE AUTHORITY`.

---

# 4. Strike semantics

A raw Decimal cannot preserve universal strike meaning.

UMI-05 therefore defines one typed `DerivativeStrike` with explicit basis:

- `PRICE`;
- `RATE`;
- `YIELD`;
- `SPREAD`;
- `LEVEL`.

All strike values must be finite Decimal.

No global positivity rule exists because rate strikes and some commodity/market
levels may legitimately require zero or negative domains.

## 4.1 PRICE

Requires:

- explicit quote/reference `EconomicIdentityId`;
- no rate/yield convention.

The option/forward underlying identity remains separately bound by the parent
contract.

## 4.2 RATE

Requires:

- UMI-04 `RateCurveConvention`;
- no quote identity.

The underlying/reference identity in the parent terms identifies the economic rate
or rate derivative referent.

## 4.3 YIELD

Requires:

- UMI-03 `YieldConvention`;
- no quote identity.

## 4.4 SPREAD / LEVEL

They carry neither rate/yield convention nor quote identity in this minimum
contract.

Their parent underlying/reference identity plus explicit strike basis retains the
semantic referent.

If later evidence proves a specialized spread-strike convention is required, it
must be added explicitly rather than laundering spread through a rate convention.

---

# 5. Futures contract terms

`FuturesContractTerms` retains:

- local terms ID;
- native derivative `EconomicIdentityId` attachment;
- reference/underlying `EconomicIdentityId`;
- settlement asset/reference `EconomicIdentityId`;
- structural `DerivativeContractMonth(year, month)`;
- contractual expiry date;
- contract multiplier;
- `CASH` or `PHYSICAL` settlement style;
- evidence;
- optional tick value;
- optional first-notice date;
- optional last-trade date.

Rules:

- instrument identity must differ from reference identity;
- instrument identity must differ from settlement identity;
- first-notice and last-trade dates, if supplied, cannot be after expiry;
- cash-settled futures cannot carry first-notice date;
- no universal ordering between first-notice and last-trade is invented because
  legitimate futures markets differ.

### Continuous futures rule

The terms object accepts an `EconomicIdentityId` shape but cannot prove that the
referenced identity is `NATIVE` versus `CONTINUOUS_REFERENCE` without graph state.

Composition MUST validate:

```text
FuturesContractTerms.instrument_identity_id
-> UMI-02 TRADABLE_INSTRUMENT / NATIVE where required
```

A continuous series remains a UMI-02 `CONTINUOUS_REFERENCE` reference object and
must not be passed off as the native expiring contract merely because the UUID
shape matches.

---

# 6. Option contract terms

`OptionContractTerms` retains:

- local terms ID;
- option economic identity;
- underlying economic identity;
- settlement asset/reference identity;
- `CALL` or `PUT`;
- typed strike;
- expiry date;
- exercise terms;
- `CASH` or `PHYSICAL` settlement style;
- evidence;
- optional listed contract multiplier;
- optional OTC notional.

At least one of multiplier/notional is required.

This permits:

- listed options with contract multiplier;
- OTC options with contractual notional;
- structures where both pieces of contract sizing are explicitly retained.

It does not infer order quantity or market position.

## 6.1 Exercise style

Closed minimum styles:

- EUROPEAN;
- AMERICAN;
- BERMUDAN.

European/American terms carry no explicit exercise-date tuple.

Bermudan terms require a non-empty unique immutable set of exercise dates,
canonicalized chronologically.

Every Bermudan exercise date must be on or before option expiry.

No business-calendar exercise-date generation occurs.

## 6.2 Non-claims

Option terms do NOT contain:

- delta;
- gamma;
- vega;
- theta;
- rho;
- implied volatility;
- model price;
- volatility surface;
- exercise decision engine.

Those are downstream valuation/analytics concerns.

---

# 7. Forward contract terms

`ForwardContractTerms` retains:

- local terms ID;
- derivative economic identity;
- underlying/reference identity;
- settlement identity;
- derivative notional;
- typed agreed strike;
- maturity date;
- CASH / PHYSICAL settlement style;
- evidence;
- optional fixing terms;
- optional UMI-03 `SettlementConvention` reference.

## 7.1 Fixing terms

`DerivativeFixingTerms` retains:

- typed derivative benchmark/reference;
- contractual fixing date;
- evidence reference.

It is not an observed fixing value.

```text
FIXING REFERENCE + FIXING DATE
!=
OBSERVED FIXING VALUE
```

## 7.2 Cash versus physical

Cash-settled forwards require explicit fixing terms because the retained contract
must identify the reference/fixing used for cash settlement.

For cash-settled forwards:

`fixing_date <= maturity_date`.

Physical forwards MAY carry fixing terms or omit them.

This is deliberate.

A classic deliverable FX forward normally has an agreed fixed exchange rate and no
future fixing. But a deliverable commodity/other forward may retain an explicit
reference/fixing as part of contractual price determination.

Therefore the following historical first-draft rule was rejected before review:

```text
PHYSICAL FORWARD -> fixing MUST be None
```

It is not universal.

### PRE-CHK-UMI05-01

Historical draft defect:
physical forwards with any fixing were rejected.

Required correction:

```text
CASH -> fixing REQUIRED
PHYSICAL -> fixing OPTIONAL
ANY fixing -> fixing_date <= maturity_date
```

This correction must be independently re-falsified at exact review head.

No fixing observation is produced and no settlement is executed.

---

# 8. Swap leg architecture

A swap is not modeled as one generic object containing a large set of nullable
fields.

UMI-05 defines explicit typed leg families.

All legs retain:

- local leg ID;
- explicit positive ordinal;
- PAY / RECEIVE direction;
- evidence.

## 8.1 FixedRateSwapLeg

Retains:

- notional schedule;
- `DerivativeContractRate`;
- day-count convention;
- payment tenor;
- D06-backed settlement convention reference.

No curve rate is substituted for the contractual rate.

## 8.2 FloatingRateSwapLeg

Retains:

- notional schedule;
- derivative benchmark reference;
- `FixedIncomeSpread` magnitude;
- day count;
- payment tenor;
- reset tenor;
- settlement convention.

The benchmark reference is not a curve engine and the spread is not a generic rate.

This supports minimum fixed/floating and basis-swap semantics without computing
fixings or cash flows.

## 8.3 ReferenceReturnSwapLeg

Retains:

- notional schedule;
- typed reference identity;
- payment tenor;
- settlement convention.

This is the minimum structural leg required for total-return / commodity-reference
style obligations.

It does not calculate total return or reference performance.

## 8.4 ExchangeSwapLeg

Retains:

- explicit amount/notional with unit identity;
- payment date;
- direction.

This supports principal exchanges and FX-swap near/far exchanges without generating
payment instructions.

## 8.5 ProtectionSwapLeg

Retains:

- notional schedule;
- typed reference;
- typed contingency role code;
- settlement convention.

This is the minimum structural protection leg for credit-derivative composition.

The contingency code is NOT a credit-event detection engine and does not claim
complete ISDA legal terms.

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

- termination must be after effective date;
- at least two legs;
- all leg IDs unique;
- all ordinals unique;
- ordinals contiguous from 1;
- caller tuple order canonicalized by ordinal;
- at least one PAY and one RECEIVE leg;
- rate/reference/protection leg notional schedules begin at swap effective date;
- subsequent notional changes occur before termination;
- exchange-leg payment dates must fall inside the inclusive swap term.

No universal rule requires exactly two legs.

Multi-leg basis, cross-currency and exchange structures can require more.

The explicit ordinal is retained sequence semantics, not a financial-time sort and
not a payoff-calculation order.

---

# 10. Derivative multi-leg composition

UMI-05 needs a narrow way to retain combinations such as:

- option spreads;
- calendar spreads;
- futures spreads;
- ratio combinations.

It must not create fake primitive instruments merely to encode each leg.

`DerivativeCompositionLeg` therefore references an existing component
`EconomicIdentityId` and retains:

- local leg ID;
- ordinal;
- LONG / SHORT side;
- positive ratio;
- evidence.

`DerivativeCompositionTerms` binds the composition's own UMI-02 economic identity
to at least two component legs.

Rules:

- no self-reference;
- component identities unique in canonical form; repeated same-component exposure
  should be aggregated into one ratio rather than duplicated;
- unique leg IDs;
- unique contiguous ordinals;
- deterministic order independent of caller tuple order.

This is intentionally narrower than UMI-09.

UMI-09 retains authority for structured/hybrid/synthetic products involving
higher-order wrappers, capital protection, embedded non-derivative components,
custom payoff transformation or other cross-family product architecture.

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
| Continuous futures reference identity | UMI-02 | never re-created in UMI-05 |
| Generic identity relationships/lifecycle events | UMI-02 | reused/deferred |
| Contractual derivative dates/terms | UMI-05 | retained as immutable contract specification |
| Financial tenor/day-count | UMI-03 | reused |
| Business calendar resolution | D06 | reference only; no resolution |
| Rate-curve convention | UMI-04 | reused only where strike basis is RATE |
| Curve construction | D07 / UMI-04 implementation work | not implemented here |
| Derivative contractual economics | UMI-05 | current scope |
| Commodity-specific delivery lifecycle/details | UMI-07 | deferred beyond generic PHYSICAL style |
| Structured/hybrid higher-order product architecture | UMI-09 | deferred |
| Prices, Greeks, IV, valuation observations | D07 / UMI-10 | not implemented |
| Market/provider observations | D05 | not implemented |
| Execution | D10 / D18 | not implemented |
| Position/settlement mutation | D11 | not implemented |
| Risk/margin/capacity reservation | D08 / D09 / D10 | not implemented |

---

# 12. Fail-closed and non-claim rules

A valid UMI-05 terms object proves only that the supplied immutable terms satisfy
this structural semantic contract.

It does NOT prove:

- UMI-02 identity kind/construction is the expected kind;
- provider supports the product;
- the evidence reference resolves to valid evidence;
- a fixing exists;
- a market price exists;
- the contract is currently live/tradable;
- the contract can be valued;
- the contract can be executed;
- settlement can be performed;
- risk capacity exists;
- margin can be calculated;
- regulatory/legal programmability is complete.

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

UMI-05 uses `date` for contractual calendar-date roles:

- expiry;
- first notice;
- last trade;
- Bermudan exercise date;
- maturity;
- fixing;
- swap effective/termination;
- notional schedule steps;
- exchange payment dates.

Exact `type(value) is date` validation rejects `datetime` laundering.

UMI-05 does not add a timezone-bearing datetime logical contract.

This does NOT close repository-wide `GAP-FND04-TIME-01`.

D06 retains calendar/session/date-resolution authority.

---

# 14. Security / evidence boundary

All local IDs and evidence refs are UUID-backed.

Semantic codes use bounded lowercase syntax.

No contract field accepts:

- credentials;
- tokens;
- passwords;
- secret values;
- provider auth material.

Evidence refs identify retained evidence but are not evidence content.

---

# 15. Compatibility / blast radius

This candidate is additive.

It does not modify:

- UMI-02 identity contracts;
- UMI-03 fixed-income contracts;
- UMI-04 rate/curve contracts;
- futures adapter contracts;
- any provider adapter;
- order/execution contracts;
- runtime;
- persistence;
- market data;
- risk;
- position/settlement;
- client/CEO surfaces.

Existing futures/provider contracts remain valid and may later project/map into
UMI-05 terms under explicit governed composition.

No provider fact is promoted automatically.

---

# 16. Mandatory adversarial test obligations

The exact-head test suite must falsify at minimum:

1. local UUID IDs reject raw/secret-like strings;
2. contract month rejects bool/invalid month;
3. notional/multiplier/tick value remain distinct types;
4. notional/multiplier/tick value reject zero/negative/non-finite values;
5. contractual fixed rate remains distinct from curve rate/yield/spread;
6. notional schedule is immutable, sorted, unique-date and unit-stable;
7. benchmark reference requires typed identity/role;
8. PRICE/RATE/YIELD/SPREAD/LEVEL strike semantics remain distinct;
9. RATE strike requires `RateCurveConvention`;
10. YIELD strike requires `YieldConvention`;
11. spread/level reject rate/yield/quote laundering;
12. strike allows legitimate non-positive domains;
13. Bermudan requires explicit unique dates and deterministic order;
14. non-Bermudan exercise rejects Bermudan dates;
15. date roles reject datetime subclass laundering;
16. futures retain month/expiry/multiplier/settlement/tick value;
17. cash futures reject first-notice date;
18. first-notice/last-trade cannot exceed expiry;
19. no invented universal first-notice-vs-last-trade ordering;
20. raw UUID cannot replace `EconomicIdentityId`;
21. option right/strike/exercise/settlement remain explicit;
22. listed multiplier and OTC notional paths both work;
23. option with neither multiplier nor notional fails;
24. Bermudan date after expiry fails;
25. cash forward requires fixing;
26. any fixing after maturity fails;
27. physical forward may omit fixing;
28. PRE-CHK-UMI05-01: physical forward may also retain a valid fixing;
29. fixed/floating/reference-return/exchange/protection legs remain distinct;
30. swap requires at least two typed legs;
31. swap requires PAY + RECEIVE;
32. swap leg IDs/ordinals unique;
33. swap ordinals contiguous and caller-order independent;
34. swap notional schedule starts at effective date;
35. later notional changes precede termination;
36. exchange date lies within swap term;
37. termination > effective;
38. composition references existing economic identities;
39. composition rejects self-reference;
40. composition rejects duplicate components in canonical form;
41. composition ratio strictly positive;
42. composition tuple immutable and at least two legs;
43. composition ordinals deterministic;
44. no pricing/Greeks/IV/margin/execution/settlement/curve-engine methods;
45. logical values deterministic and secret-free.

Passing tests do not self-certify the architecture.

---

# 17. Independent review requirements

Because ChatGPT / Integration Gate materially designed and implemented this
candidate:

`NO SELF-CERTIFICATION` applies.

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

---

# 18. Explicit non-goals / downstream boundaries

A favorable UMI-05 result does NOT mean:

- any futures provider supports canonical UMI-05 terms operationally;
- options provider support;
- OTC provider support;
- derivative pricing;
- Greeks;
- implied volatility;
- volatility surfaces;
- option exercise engine;
- swap fixing engine;
- swap cash-flow generation;
- curve bootstrapping/interpolation;
- discounting/PV;
- commodity delivery lifecycle certification;
- structured note/product certification;
- UMI-06/07/08/09/10 authorization;
- execution authority;
- settlement mutation authority;
- risk/margin/capacity reservation;
- productive QORE Cloud;
- production readiness;
- real-capital authority;
- `GAP-FND04-TIME-01` closure;
- `GAP-FND07-RES-01` closure;
- PR #298 promotion.

The candidate means only:

> QORE has a provider-neutral immutable semantic vocabulary for the minimum
> contractual economics of the derivative families covered by UMI-05, subject to
> exact-head independent review and Integration Gate certification.
