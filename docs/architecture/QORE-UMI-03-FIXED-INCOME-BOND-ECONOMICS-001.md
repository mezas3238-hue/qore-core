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

# 2. Live repository evidence before implementation

The UMI-03 work order was derived from live Issue #301 after Program A closed.

Issue #301 defines UMI-03 as the fixed-income / bonds family stage covering:

- cash flows;
- coupons;
- accrual;
- day-count;
- settlement;
- clean / dirty price;
- yield;
- curve / benchmark references.

The following existing contracts were directly inspected on starting baseline
`ccf3755e42c51ee7a9d9d61ea3dd9cc756906bf1`.

## 2.1 UMI-02 identity foundation

`src/qore/infrastructure/universal_instrument_identity.py`

provides:

- `EconomicIdentityId`;
- tradable-instrument vs reference-object identity;
- effective-dated `IdentityRelationship`;
- denomination / settlement currency reference topology;
- benchmark/reference topology;
- lifecycle events including bond maturity when applicable;
- canonical UTC logical timestamp serialization.

UMI-03 therefore does not create `BondId`, provider symbol identity, currency
identity, benchmark identity or listing identity.

## 2.2 FND-04 semantic freeze

`QORE-FND-04-UNIVERSAL-ECONOMIC-PRIMITIVES-AUDIT-001.md` and R1 establish:

- `OrderQuantity` is execution-scoped and cannot mean universal face amount;
- `MoneyAmount` is bounded money semantics and is not universal price/value identity;
- clean and dirty price are materially distinct;
- rate, yield and spread are distinct semantic classes;
- tenor is not a market timeframe or fixed seconds;
- business/contract dates are explicit roles;
- provider-native terms remain evidence, not Core economic authority.

FND-04 also explicitly used bonds as the adversarial case requiring face/par,
clean/dirty price, accrued/coupon semantics, yield, day-count, maturity and
currency separation.

---

# 3. Scope freeze

UMI-03 implements the minimum contracts needed to retain fixed-income meaning
without building neighboring stages.

## 3.1 Canonical attachment

Every fixed-income terms/profile contract binds an existing UMI-02
`EconomicIdentityId`.

Denomination currency, benchmark and curve/reference targets are also expressed
as UMI-02 economic identity references.

The fixed-income layer does not claim those referenced identities are valid
reference-object kinds by ID shape alone. Graph/domain composition remains
responsible for validating the referenced identity kind and relationship evidence.

## 3.2 Face/par principal

`FaceAmount` is a positive exact `Decimal` magnitude.

Its denomination is not encoded in the magnitude. The parent
`FixedIncomeInstrumentTerms` separately binds
`denomination_currency_identity_id`.

This prevents:

```text
FaceAmount(1000)
```

from silently meaning 1000 shares, 1000 contracts, 1000 provider lots or an
unqualified money balance.

## 3.3 Coupon semantics

Three bounded coupon forms are represented:

- `FixedCouponTerms`;
- `FloatingCouponTerms`;
- `ZeroCouponTerms`.

Fixed coupon retains:

- typed `CouponRate`;
- day-count convention;
- payment tenor.

Floating coupon retains:

- benchmark/reference identity;
- typed `FixedIncomeSpread`;
- day-count;
- payment tenor;
- reset tenor.

Zero coupon remains a distinct semantic object rather than `CouponRate(0)`.

A zero-coupon instrument requires an explicit maturity date in this candidate.
Fixed/floating coupon terms do not force a maturity date, preserving the ability
to represent perpetual coupon-bearing debt without inventing a universal expiry.

## 3.4 Rate / yield / spread separation

The candidate introduces distinct value objects:

- `CouponRate`;
- `FixedIncomeYield`;
- `FixedIncomeSpread`.

All hold finite exact `Decimal` magnitudes encoded as decimal fractions.
No maximum is silently imposed.

Equal numeric values remain distinct Python/runtime semantic types.

Their `logical_values()` canonicalize numerically equal Decimal encodings, so
`Decimal("0.0500")` and `Decimal("0.05")` do not produce different logical
material solely due to Decimal exponent representation.

## 3.5 Financial tenor

`FinancialTenor(value, unit)` supports structural:

- day;
- week;
- month;
- year.

It intentionally defines no conversion to seconds and has no market-bar code.

This is sufficient for bounded coupon/reset/compounding horizon semantics.
UMI-04 may reuse or extend the structural principle for curve-node semantics
without treating UMI-03 as curve authority.

## 3.6 Accrual and day-count

`AccrualPeriod` retains:

- accrual start date;
- accrual end date;
- payment date;
- day-count convention.

It requires:

```text
end_date > start_date
payment_date >= end_date
```

`DayCountConventionCode` is an extensible validated semantic code rather than a
premature closed list advertised as the entire fixed-income universe.

This candidate does not calculate year fractions. It preserves the exact
convention required for a later certified calculator to do so reproducibly.

## 3.7 Settlement convention

`SettlementConvention` retains:

- non-negative business-day lag;
- `BusinessCalendarRef`;
- `BusinessDayConventionCode`.

`BusinessCalendarRef` is explicitly a reference to D06-governed calendar
semantics. It does not contain holidays, sessions, timezone tables or calendar
mutation authority.

The contract therefore expresses T+n/business-day semantics without pretending
that an integer lag itself resolves a settlement date.

## 3.8 Clean / dirty price

`FixedIncomePrice` retains:

- exact Decimal value;
- `FixedIncomePriceKind.CLEAN` or `.DIRTY`;
- explicit `FixedIncomePriceBasisCode`.

Clean and dirty price remain distinct even when numeric values are equal.

The candidate deliberately does not compute:

```text
dirty = clean + accrued interest
```

because a universal computation requires certified quote basis, accrual economics,
date/calendar semantics and potentially family/source methodology. UMI-03 freezes
the semantic distinction rather than inserting an unsafe generic formula.

## 3.9 Yield semantic

`FixedIncomeYield` is a typed magnitude.

`YieldConvention` retains enough surrounding meaning for later use:

- extensible yield semantic code;
- day-count;
- compounding convention;
- optional compounding tenor;
- optional benchmark/reference attachment.

This establishes yield semantics without implementing valuation, market
observation provenance, YTM root solving, YTW selection, curve construction or
pricing.

A later quantitative observation/calculation must add its own source,
methodology, time and retained evidence under UMI-10/D07/D14.

## 3.10 Benchmark / curve references

`FixedIncomeBenchmarkReference` retains:

- exact `EconomicIdentityId`;
- explicit role;
- optional structural tenor.

It is deliberately only an attachment/reference object.

```text
REFERENCE TO CURVE / BENCHMARK
!=
CURVE CONSTRUCTION
!=
CURVE NODE AUTHORITY
!=
BOOTSTRAPPING
```

Those remain UMI-04.

## 3.11 Contractual cash flows

`FixedIncomeCashFlow` retains:

- stable cash-flow ID;
- exact instrument identity;
- explicit semantic kind;
- receivable/payable direction;
- positive exact amount;
- exact currency identity;
- payment date;
- retained evidence reference;
- accrual period when and only when it is a coupon flow.

`FixedIncomeCashFlowSchedule` requires:

- a non-empty immutable tuple;
- exact instrument binding;
- unique cash-flow IDs;
- deterministic canonical ordering by payment date then cash-flow ID.

The schedule is contractual economic evidence. It is not a payment instruction,
ledger movement, settlement receipt or D11 mutation authority.

## 3.12 Instrument terms and profile

`FixedIncomeInstrumentTerms` composes:

- stable terms ID;
- instrument identity;
- denomination currency identity;
- face amount;
- issue date;
- optional maturity date;
- one certified coupon semantic;
- settlement convention;
- yield convention;
- retained evidence reference;
- optional redemption amount.

`FixedIncomeEconomicProfile` composes the terms with an optional retained
cash-flow schedule and verifies exact instrument binding.

The schedule is optional because:

- terms may exist before all retained cash flows are materialized;
- perpetual instruments cannot be forced into a finite universal cash-flow list.

---

# 4. Explicit non-goals

This candidate does not implement or certify:

- yield-curve construction;
- curve-node identity/catalog;
- bootstrapping;
- interpolation;
- discount factors;
- forward-rate surfaces;
- pricing engines;
- present-value calculation;
- accrued-interest calculation;
- YTM/YTW numerical solving;
- option/call/put/convertible payoff economics;
- issuer/legal-entity identity;
- credit ratings/default modeling;
- tax treatment;
- provider-native bond catalogs;
- execution quantity conversion;
- positions or settlement mutation;
- risk capacity reservation;
- productive Cloud;
- real capital;
- every fixed-income product subtype.

These boundaries are intentional.

---

# 5. Open inherited gaps

## GAP-FND04-TIME-01

Remains OPEN / HIGH.

This candidate adds no timestamp-bearing deterministic contract; its contract
dates are `date` semantic roles and therefore do not create a new offset
canonicalization path.

No broad temporal-determinism claim is made.

## GAP-FND07-RES-01

Remains OPEN / HIGH.

UMI-03 economic semantics do not implement D08/D09/D10 capacity reservation and
do not authorize productive concurrent risk-increasing execution.

## PR #298

Remains HOLD.

No provider-native catalog is promoted by this stage.

---

# 6. Adversarial test obligations

`tests/infrastructure/test_fixed_income_economics.py` proves at minimum:

1. profile binds canonical UMI-02 identity and deterministic cash-flow schedule;
2. rate/yield/spread remain distinct at equal magnitude;
3. Decimal logical values are canonical across equivalent exponent encodings;
4. clean and dirty price remain distinct at equal magnitude;
5. non-finite values fail closed;
6. face/cash amounts reject non-positive values;
7. tenor rejects bool/int laundering and exposes no fixed-seconds contract;
8. convention codes are validated;
9. settlement lag rejects bool and negative values;
10. accrual chronology and runtime date types fail closed;
11. coupon families are explicit and cannot be replaced by raw identity/value material;
12. floating coupon requires a typed benchmark reference;
13. benchmark/yield references provide no curve engine;
14. coupon cash flows require exact accrual binding;
15. non-coupon cash flows reject accrual material;
16. schedules reject duplicate IDs, foreign instruments and mutable/list containers;
17. schedule logical order is independent of input order;
18. terms reject identity collision, invalid maturity chronology and untyped IDs;
19. profile rejects foreign schedules and pre-issue cash flows;
20. perpetual fixed-coupon terms are not forced to have maturity;
21. evidence/ID boundaries accept UUIDs only;
22. logical material remains free of credential-like payload strings.

---

# 7. Compatibility and blast radius

Intended production delta:

- one new infrastructure contract module;
- one new focused test module;
- this architecture artifact.

No existing source contract is modified.
No legacy order/market-data type is reinterpreted.
No provider adapter changes.
No runtime/trading behavior changes.
No database/storage change.
No migration.

Compatibility strategy is additive:

```text
UMI-02 EconomicIdentityId
-> UMI-03 fixed-income terms/profile
-> later UMI-04/U07/U10 consumers
```

not:

```text
replace every existing price/quantity/rate class
```

---

# 8. Certification discipline

This candidate is authored under the Integration Gate workflow and therefore
cannot self-certify.

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

Until that sequence is complete:

```text
IMPLEMENTED CANDIDATE != CERTIFIED UMI-03
CI GREEN != ENGINEERING APPROVAL
PR OPEN != PROGRAM CLOSURE
```
