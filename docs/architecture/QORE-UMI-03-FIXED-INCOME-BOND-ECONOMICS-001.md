# QORE-UMI-03-FIXED-INCOME-BOND-ECONOMICS-001

## Status

**PROGRAM B / UMI-03 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #320  
Master roadmap: Issue #303  
Universal Markets / Instruments program: Issue #301  
Certified starting baseline: `ccf3755e42c51ee7a9d9d61ea3dd9cc756906bf1`  
Predecessor: STAGE-08 / FND-08 — CLOSED

This artifact defines the bounded provider-neutral fixed-income / bond economic
foundation required by UMI-03.

It is additive to UMI-02 identity/lifecycle and FND-04 economic-semantic law.
It does not create a second instrument identity authority, a curve engine, a
valuation engine, an execution path, a provider catalog, or a production support
claim.

```text
IDENTITY FOUNDATION
+
FIXED-INCOME ECONOMIC TERMS
!=
FIXED-INCOME OPERATIONAL SUPPORT
```

---

# 1. Governing invariants

```text
ECONOMIC IDENTITY != FIXED-INCOME ECONOMIC TERMS
FACE / PAR AMOUNT != GENERIC ORDER QUANTITY
CLEAN PRICE != DIRTY PRICE
FIXED-INCOME PRICE != MONEY AMOUNT
RATE != YIELD != SPREAD
NUMERIC EQUALITY != SEMANTIC INTERCHANGEABILITY
FINANCIAL TENOR != MARKET TIMEFRAME
FINANCIAL TENOR != FIXED SECONDS
DAY-COUNT CONVENTION != CALENDAR AUTHORITY
SETTLEMENT CONVENTION != SETTLEMENT EXECUTION
BENCHMARK REFERENCE != CURVE CONSTRUCTION AUTHORITY
CASH-FLOW IDENTITY != PAYMENT EXECUTION
CONTRACTUAL CASH FLOW != OBSERVED CASH MOVEMENT
PERIODIC YIELD COMPOUNDING -> EXPLICIT COMPOUNDING TENOR
ZERO-COUPON TERMS -> NO COUPON CASH FLOWS
COUPON CASH-FLOW DAY COUNT == COUPON TERMS DAY COUNT
PROFILE EXISTS != PROVIDER SUPPORT
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

The implementation follows FND-04/R1:

```text
PRICE != MONEY != VALUATION
RATE != YIELD != SPREAD
TENOR != MARKET TIMEFRAME
CLEAN PRICE != DIRTY PRICE
```

and reuses UMI-02 `EconomicIdentityId` as the sole canonical attachment point for
instrument/reference identity.

---

# 2. Starting evidence and authority boundary

The UMI-03 work order was derived from live Issue #301 after Program A closed.
Issue #301 assigns UMI-03 fixed-income / bond semantics for:

- cash flows;
- coupons;
- accrual;
- day-count;
- settlement;
- clean / dirty price;
- yield;
- curve / benchmark references.

UMI-02 already provides:

- `EconomicIdentityId`;
- tradable-instrument vs reference-object identity;
- effective-dated `IdentityRelationship`;
- denomination / settlement currency topology;
- benchmark/reference topology;
- lifecycle events including bond maturity where applicable;
- canonical timestamp semantics for its own timestamp-bearing logical material.

UMI-03 therefore does not create `BondId`, provider symbol identity, currency
identity, benchmark identity, issuer identity, listing identity, or a second
mapping authority.

FND-04/R1 already freezes these semantic boundaries:

- execution quantity is not face/par principal;
- money amount is not market/fixed-income price;
- clean price is not dirty price;
- rate is not yield and neither is spread;
- financial tenor is not fixed seconds or a market timeframe;
- business/contract dates retain explicit roles;
- provider-native facts remain evidence, not Core economic authority.

---

# 3. Scope freeze

## 3.1 Canonical identity attachment

Every fixed-income terms/profile contract binds an existing UMI-02
`EconomicIdentityId`.

Denomination currency and benchmark/reference targets are also represented by
UMI-02 economic identities.

An ID alone does not prove the referenced identity kind. Graph/domain composition
must validate retained identity kind/relationship evidence where that distinction
is material.

```text
ECONOMIC ID SHAPE != REFERENCE-OBJECT PROOF
REFERENCE ATTACHMENT != REFERENCE AUTHORITY
```

## 3.2 Face/par principal

`FaceAmount` is a positive finite exact `Decimal` magnitude. Its denomination is
bound separately by `FixedIncomeInstrumentTerms.denomination_currency_identity_id`.

This prevents `FaceAmount(1000)` from silently becoming:

- 1000 shares;
- 1000 contracts;
- 1000 provider lots;
- an unqualified money balance;
- a portfolio weight.

No generic `price × quantity` bond-value rule is introduced.

## 3.3 Coupon semantics

The family foundation distinguishes:

- `FixedCouponTerms`;
- `FloatingCouponTerms`;
- `ZeroCouponTerms`.

Fixed coupon retains a typed `CouponRate`, day-count convention and payment tenor.
Floating coupon retains a benchmark/reference attachment, typed spread, day-count,
payment tenor and reset tenor. Zero coupon is a separate semantic object rather
than `CouponRate(0)`.

A zero-coupon instrument requires maturity in this candidate. Fixed/floating
coupon debt may remain perpetual; no universal expiry is invented.

The composed `FixedIncomeEconomicProfile` additionally enforces:

```text
ZERO-COUPON TERMS -> NO COUPON CASH FLOWS
```

A contractual schedule that contradicts the declared coupon family is therefore
rejected rather than retained as internally inconsistent evidence.

For coupon-bearing profiles, each coupon cash-flow accrual period must use the
same day-count convention declared by the coupon terms:

```text
COUPON CASH-FLOW ACCRUAL DAY COUNT
==
FIXED/FLOATING COUPON TERMS DAY COUNT
```

This does not calculate accrual. It prevents one canonical profile from carrying
two contradictory conventions for the same coupon economics.

## 3.4 Rate / yield / spread separation

Distinct value objects retain distinct semantics:

- `CouponRate`;
- `FixedIncomeYield`;
- `FixedIncomeSpread`.

They use finite exact Decimal fractions and deterministic decimal serialization.
Equal numeric magnitudes do not make the runtime types interchangeable.

Negative rate/yield/spread magnitudes are not globally prohibited because the
sign domain is economically distinct from price/face/cash positivity and can be
valid for some rate/yield markets.

`FixedIncomeYield` is a typed magnitude only. It is not, by itself, a market
observation or valuation result. A later quantitative observation/calculation
must add source, methodology, time and retained evidence under the appropriate
valuation/market-data authority.

## 3.5 Financial tenor

`FinancialTenor(value, unit)` supports structural day/week/month/year horizons.
It intentionally exposes no fixed-second conversion and no market-bar identity.

This is sufficient for coupon payment/reset frequency and yield compounding
frequency while leaving curve-node/term-structure authority to UMI-04.

## 3.6 Accrual and day-count

`AccrualPeriod` retains:

- start date;
- end date;
- payment date;
- day-count convention.

It requires:

```text
end_date > start_date
payment_date >= end_date
```

`DayCountConventionCode` is extensible validated semantic material. UMI-03 does
not calculate year fractions, accrued interest or coupon amount.

## 3.7 Settlement convention

`SettlementConvention` retains:

- non-negative business-day lag;
- `BusinessCalendarRef`;
- `BusinessDayConventionCode`.

`BusinessCalendarRef` is only a typed reference to D06-governed semantics. It has
no holiday table, session schedule, timezone table, resolver or calendar mutation
authority.

```text
SETTLEMENT LAG + CALENDAR REF + CONVENTION
!=
RESOLVED SETTLEMENT DATE
```

## 3.8 Clean / dirty price

`FixedIncomePrice` retains:

- exact finite Decimal value;
- `FixedIncomePriceKind.CLEAN` or `.DIRTY`;
- explicit `FixedIncomePriceBasisCode`.

Clean and dirty price remain distinct even when numeric values are equal.

UMI-03 deliberately does not compute:

```text
dirty = clean + accrued interest
```

because that computation requires certified accrual economics, date/calendar
semantics, quote basis and possibly source/methodology evidence.

## 3.9 Yield convention

`YieldConvention` retains:

- extensible yield semantic code;
- day-count convention;
- compounding convention;
- optional structural compounding tenor in the general extensible model;
- optional benchmark/reference attachment.

One fail-closed rule is explicit now:

```text
compounding == periodic
-> compounding_tenor MUST be present
```

A periodic yield without frequency is not reproducible economic meaning and is
rejected. Other extensible compounding codes are not prematurely forced into a
closed universal taxonomy; later codes may add their own bounded invariants when
introduced.

No YTM/YTW solving, discounting, curve construction or pricing occurs here.

## 3.10 Benchmark / curve references

`FixedIncomeBenchmarkReference` retains exact `EconomicIdentityId`, an explicit
role and optional structural tenor.

```text
REFERENCE TO CURVE / BENCHMARK
!=
CURVE CONSTRUCTION
!=
CURVE NODE AUTHORITY
!=
BOOTSTRAPPING
!=
INTERPOLATION
```

All term-structure construction remains UMI-04.

## 3.11 Contractual cash flows

`FixedIncomeCashFlow` retains:

- stable cash-flow ID;
- exact instrument identity;
- coupon/principal/redemption kind;
- receivable/payable direction;
- positive exact amount;
- exact currency identity;
- payment date;
- retained evidence reference;
- accrual period when and only when the flow is a coupon.

`FixedIncomeCashFlowSchedule` requires:

- non-empty immutable tuple input;
- exact schedule/instrument binding;
- unique cash-flow IDs;
- deterministic canonical ordering by payment date then cash-flow ID.

The schedule is contractual economic evidence. It is not a payment instruction,
ledger movement, provider receipt, position mutation or D11 authority.

## 3.12 Instrument terms and economic profile

`FixedIncomeInstrumentTerms` composes:

- stable terms ID;
- instrument identity;
- denomination currency identity;
- face amount;
- issue date;
- optional maturity date;
- one coupon semantic family;
- settlement convention;
- yield convention;
- retained evidence reference;
- optional redemption amount.

`FixedIncomeEconomicProfile` composes terms with an optional retained cash-flow
schedule and verifies:

- exact instrument binding;
- no cash flow predates issue date;
- zero-coupon terms carry no coupon flow;
- coupon cash-flow day-count matches the declared coupon terms.

The schedule remains optional because terms can exist before complete schedule
materialization and perpetual instruments cannot be forced into one finite
universal schedule.

---

# 4. Runtime/type and determinism law

All new value/contracts are `@dataclass(frozen=True, slots=True)` or `StrEnum`.
Runtime boundaries validate concrete semantic types rather than trusting type
annotations alone.

Strict integer guards use `type(value) is int` where bool/int ambiguity matters.
Date roles use `type(value) is date`, preventing `datetime` from entering silently
through Python subclassing.

Decimal inputs must be actual finite `Decimal` objects. Face amount and cash-flow
amount must be strictly positive. Decimal logical material canonicalizes equivalent
exponent encodings.

Cash-flow collections are canonicalized independently of caller input order.
Opaque evidence references and UMI-03 local IDs are UUID-backed; credentials or
secret payloads are not accepted as evidence content.

This stage adds `date` roles, not timezone-bearing `datetime` logical material.
Therefore it creates no new TIME-01 offset-canonicalization site.

---

# 5. Explicit non-goals

This candidate does not implement or certify:

- yield-curve construction or curve-node authority;
- bootstrapping, interpolation or discount-factor surfaces;
- forward-rate surfaces;
- pricing engines or present-value calculation;
- accrued-interest calculation;
- YTM/YTW numerical solving/selection;
- option/call/put/convertible payoff economics;
- generic derivative legs/payoffs (UMI-05);
- issuer/legal-entity authority;
- credit ratings/default modeling;
- tax treatment;
- provider-native fixed-income catalogs;
- execution quantity conversion;
- positions, settlement mutation or payment execution;
- risk capacity reservation;
- productive Cloud;
- real capital;
- operational support for every fixed-income subtype.

---

# 6. Open inherited boundaries

## GAP-FND04-TIME-01

**OPEN / HIGH.** UMI-03 does not close the pre-existing repository-wide temporal
canonicalization obligation. No broad temporal-determinism claim is made.

## GAP-FND07-RES-01

**OPEN / HIGH.** UMI-03 economic semantics do not implement concurrent
risk-increasing capacity reservation and do not authorize productive concurrent
execution claims.

## PR #298

**HOLD.** No provider-native catalog is promoted by UMI-03.

---

# 7. Adversarial test obligations

`tests/infrastructure/test_fixed_income_economics.py` must prove at minimum:

1. canonical UMI-02 instrument/denomination attachment;
2. rate/yield/spread semantic separation at equal magnitude;
3. Decimal canonicalization and non-finite rejection;
4. clean/dirty price distinction;
5. face/cash amount positivity;
6. financial tenor has no fixed-seconds contract;
7. bool/int laundering is rejected where integers are required;
8. code/runtime type boundaries fail closed;
9. accrual chronology fails closed;
10. settlement convention remains reference-only, not calendar authority;
11. fixed/floating/zero coupon forms remain distinct;
12. floating coupon requires typed benchmark attachment;
13. benchmark reference exposes no curve engine;
14. periodic yield compounding without tenor is rejected;
15. coupon cash flows require accrual binding;
16. non-coupon flows reject accrual material;
17. schedule IDs are unique and exact instrument binding is enforced;
18. mutable/list schedule input is rejected;
19. schedule logical ordering is caller-order independent;
20. terms maturity/identity/redemption invariants fail closed;
21. foreign schedule and pre-issue flow are rejected by profile composition;
22. zero-coupon profile rejects coupon cash flows;
23. coupon accrual day-count mismatch is rejected;
24. perpetual coupon-bearing debt is not forced to maturity;
25. evidence/ID boundaries are UUID-only;
26. deterministic logical material remains free of credential-like payloads.

---

# 8. Compatibility and blast-radius law

The intended PR delta remains exactly:

- one new infrastructure contract module;
- one new focused test module;
- this architecture artifact.

No existing source contract is reinterpreted. No provider adapter, runtime,
execution path, database, storage backend or migration is changed.

Compatibility is additive:

```text
UMI-02 EconomicIdentityId
-> UMI-03 fixed-income economics
-> later UMI-04 / department / valuation consumers
```

not:

```text
replace every existing price / quantity / rate class
```

---

# 9. Certification discipline

This candidate was materially designed/implemented through the Integration Gate
workflow and therefore cannot self-certify.

Required sequence:

```text
IMPLEMENT
-> TEST
-> QORE QUALITY GATE
-> DIFF AUDIT
-> DRAFT PR
-> FREEZE EXACT HEAD
-> CLAUDE INDEPENDENT ADVERSARIAL REVIEW
-> INTEGRATION GATE FALSIFICATION
-> CORRECTION LOOP IF REQUIRED
-> EXPECTED-HEAD MERGE
-> VERIFY ACTUAL MERGE
-> VERIFY POST-MERGE MAIN
-> FREEZE NEW CERTIFIED BASELINE
-> CLOSE UMI-03
```

Until that sequence completes:

```text
IMPLEMENTED CANDIDATE != CERTIFIED UMI-03
CI GREEN != ENGINEERING APPROVAL
PR OPEN != PROGRAM CLOSURE
```
