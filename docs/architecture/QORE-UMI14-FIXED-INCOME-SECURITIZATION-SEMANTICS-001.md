# QORE-UMI14-FIXED-INCOME-SECURITIZATION-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 CORRECTION — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Target: `UMI13-UNR-003`  
Family: `fixed-income-credit`  
Implementation baseline: `0d341cb886994b8bbabbabed3c38f3c3ce3a5053`  
Owner foundation: `src/qore/infrastructure/fixed_income_economics.py`  
Owner foundation blob at implementation baseline: `166a1b9896c2f7c3fc833bdd8eb20827f93ad12c`

This document describes a static, provider-neutral correction candidate for securitization deal/pool/tranche, contractual priority/allocation, performance-condition, prepayment, defeasance, and yield-maintenance semantics. It does not close UNR-003 and does not establish operational support.

## 1. Boundary and ownership

The correction adds a dedicated fixed-income-credit sub-owner:

`src/qore/infrastructure/fixed_income_securitization_semantics.py`

The existing UMI-03 owner remains authoritative for reusable fixed-income primitives. This candidate does not modify `fixed_income_economics.py` and does not turn generic fixed-income terms or cash-flow schedules into securitization contracts.

```text
DEAL != POOL != TRANCHE
POOL IDENTITY != POOL MEMBERSHIP != CURRENT POOL STATE
PRIORITY != PRINCIPAL ALLOCATION
STATIC CONTRACT SEMANTICS != WATERFALL EXECUTION
PREPAYMENT CONTRACT != PREPAYMENT FORECAST MODEL
YIELD-MAINTENANCE FORMULA CONTRACT != VALUATION ENGINE
```

## 2. Exact existing-type reuse

The candidate reuses the already-certified UMI-03 / universal identity contracts where their semantics are exact:

- `EconomicIdentityId` for economic/reference identities;
- `FaceAmount` for tranche original face/principal only;
- `FixedIncomeEvidenceRef` for opaque retained-evidence references;
- `FixedCouponTerms`, `FloatingCouponTerms`, `ZeroCouponTerms` through the existing `FixedIncomeCouponTerms` semantic union;
- `FixedIncomeBenchmarkReference`;
- `FixedIncomeSpread`;
- `DayCountConventionCode`;
- `CompoundingConventionCode`;
- `FinancialTenor`.

It deliberately does **not** reuse:

- `FixedIncomeInstrumentTerms` as securitization deal/pool/tranche terms;
- `FixedIncomeCashFlowSchedule` as a waterfall;
- `CouponRate` as the loan contractual rate inside yield-maintenance Formula B.

## 3. Identity model

Owner-local immutable UUID-backed identifiers are used for:

- deal;
- pool;
- tranche;
- priority regime;
- allocation regime;
- contractual condition;
- metric definition;
- prepayment phase;
- defeasance qualification/notice reference.

No implicit UUID generation is permitted. Deal, pool and tranche economic identities are separately bound through `EconomicIdentityId`; the candidate rejects deal/pool/tranche identity conflation while allowing a shared denomination currency identity.

## 4. Deal / pool / tranche model

`SecuritizationDeal` binds:

- deal identity;
- pools;
- tranches;
- one authoritative contractual condition set;
- one priority-regime set;
- distinct scheduled and unscheduled principal-allocation regime sets;
- retained evidence reference.

Pools bind the parent deal, economic identity, membership contract, original contractual balance, denomination, collateral type, contractual prepayment terms and evidence.

Tranches bind the parent deal and pool, economic identity, original `FaceAmount`, denomination, existing fixed-income coupon terms and evidence.

Pool and tranche caller order is non-semantic and canonicalized by owner-local ID. Priority ranking and sequential principal-allocation order remain semantic and are preserved.

## 5. Pool membership

Three exact membership shapes are represented:

```text
EXPLICIT_CONSTITUENT_MEMBERSHIP
EXTERNAL_POOL_REFERENCE
COMBINED
```

Explicit member tuples are non-empty, unique and canonicalized by `EconomicIdentityId`. Combined membership retains both external reference and explicit members but makes no equivalence assertion and performs no runtime resolution.

No current pool state, servicer state or provider catalog is owned by this contract.

## 6. Collateral and contractual balance

`SecuritizationPoolOriginalContractualBalance` is an owner-local finite positive `Decimal` value object. It is intentionally distinct from tranche `FaceAmount`.

`SecuritizationCollateralTypeCode` is a provider-neutral canonical code with maximum length 64 and lowercase syntax:

```text
[a-z0-9]+(?:[._-][a-z0-9]+)*
```

No provider-native symbol or resolver is embedded.

## 7. Contractual priority

`PriorityRegime` retains three distinct ordered rankings:

- interest-payment priority: senior to junior;
- principal-payment priority: senior to junior;
- loss allocation: first-loss to last-loss.

Each `PriorityRanking` is an ordered tuple of non-empty `PariPassuGroup` objects. Order between groups is semantic; order inside a pari-passu group is non-semantic and canonicalized.

`PriorityRegimeSet` contains one base regime and zero or more conditioned regimes. Conditioned regimes bind a condition and strict positive precedence ordinal. Lower ordinal represents higher contractual precedence; the collection is canonicalized by that ordinal. The contract does not select a currently active regime.

## 8. Principal allocation

Principal-allocation contracts remain distinct from priority:

- `SequentialPrincipalAllocation` preserves an ordered unique tranche sequence;
- `ParallelProRataPrincipalAllocation` is fail-closed to the fixed basis `OUTSTANDING_PRINCIPAL_BALANCE` and canonicalizes participants;
- `ParallelContractualSharesPrincipalAllocation` retains exact non-negative `Decimal` shares, one per tranche, summing exactly to one.

Scheduled and unscheduled principal-allocation regime sets are separate contracts, each with one base regime and conditioned regimes ordered by precedence. No current outstanding balance and no executable waterfall are represented.

## 9. Contractual conditions

Each deal owns exactly one `ContractualConditionSet` containing:

- event conditions;
- performance metric definitions;
- performance-test conditions;
- composite conditions.

Event kinds are exactly:

- payment default;
- issuer insolvency default;
- covenant / representation / warranty breach;
- acceleration event.

Composite operators are `ALL_OF` and `ANY_OF`; composites require at least two unique children and reject self-reference, orphan references and cycles. The condition set does not evaluate current condition state.

## 10. Static metric definitions

The candidate retains static formula semantics rather than only metric IDs.

### Cumulative realized loss ratio

```text
numerator = AGGREGATE_REALIZED_LOSSES_FROM_CUTOFF_THROUGH_MEASUREMENT_PERIOD
denominator = CUTOFF_DATE_POOL_BALANCE
window = CUMULATIVE_FROM_CUTOFF
aggregation = NONE_AGGREGATION
```

### 60+ delinquency ratio

```text
numerator = OUTSTANDING_PRINCIPAL_60_PLUS_DELINQUENT
qualification = INCLUDES_FORECLOSURE_BANKRUPTCY_REO
denominator = PERIOD_POOL_BALANCE
window = ROLLING_THREE_MONTHS
aggregation = ARITHMETIC_MEAN_OF_PERIOD_RATIOS
```

### Senior enhancement percentage

```text
gross = PRECEDING_DISTRIBUTION_DATE_MORTGAGE_LOAN_PRINCIPAL_BALANCE
subtracted = MOST_SENIOR_CERTIFICATE_CLASS_PRINCIPAL_BALANCE
subtracted temporal role = PRECEDING_MASTER_SERVICER_ADVANCE_DATE
denominator = PRECEDING_DISTRIBUTION_DATE_MORTGAGE_LOAN_PRINCIPAL_BALANCE
operation = GROSS_BALANCE_MINUS_SENIOR_CERTIFICATE_BALANCE_OVER_GROSS_BALANCE
```

Every fixed role is validated fail-closed and retained in `logical_values()`. Wrong role values are invalid definitions, not alternate valid metrics.

No current metric values are stored.

## 11. Performance tests and thresholds

Performance tests bind condition ID, metric definition ID, comparator, threshold contract, contractual measurement period and evidence.

Threshold right-hand sides are intentionally bounded:

- exact constant `Decimal`;
- exact non-negative multiple of another metric definition.

Threshold contracts are static or scheduled. `ContractualMeasurementYearMonth` uses strict positive year and month 1–12. `ExactFraction` canonicalizes by GCD; for example `2/24` and `3/36` are retained as `1/12`, without floating point.

A ramp uses a typed threshold RHS plus an exact `ExactFractionOf` increment; it does not pre-expand fractional steps to rounded decimal values.

## 12. Exact retained Impac schedule specimen

The cumulative-loss threshold specimen retains the contractual schedule exactly:

| Contractual period | Base | Exact increment |
|---|---:|---:|
| 2007-12 through 2008-11 | 0.005 | 1/12 × 0.005 |
| 2008-12 through 2009-11 | 0.010 | 1/12 × 0.005 |
| 2009-12 through 2010-11 | 0.015 | 1/12 × 0.005 |
| 2010-12 through 2011-11 | 0.020 | 1/12 × 0.0025 |
| 2011-12 onward | 0.0225 | constant |

The schedule contract validates deterministic chronological order, non-overlap and terminal-only open-ended segments. This retained specimen is static contract evidence, not a trigger evaluator.

## 13. Prepayment boundaries and phases

The exact boundary union is:

- origination;
- exact contractual date;
- payment count from origination;
- payment count before maturity.

Payment counts are strict positive integers with `bool` rejected. Mixed boundary kinds may coexist because source ordinal is the authoritative contractual sequence. No D06 calendar resolution or universal chronology is inferred across incomparable boundary kinds.

`CollateralPrepaymentTerms` requires non-empty unique phases ordered by strict positive ordinal, begins at origination, and rejects duplicate IDs, ordinals and canonical boundaries.

## 14. Voluntary prepayment and defeasance

Voluntary prepayment is either prohibited or permitted with one of:

- no charge;
- fixed percentage premium;
- yield-maintenance charge;
- greater-of fixed premium and yield maintenance.

Fixed premium bases are prepaid principal amount or outstanding principal amount.

`PrepaymentFixedPremiumRate` is a strict finite `Decimal` with **no additional sign restriction** in this owner. The contract does not invent positivity policy that the financial design did not authorize.

Defeasance retains:

- substitution collateral type;
- optional owner-local qualification/notice reference;
- evidence reference.

The qualification/notice reference is semantically distinct from `FixedIncomeEvidenceRef`. No trustee, settlement or operational workflow is implemented.

## 15. Yield maintenance

The candidate represents two intentionally distinct static formula contracts.

### Formula A

`PV_REMAINING_PRINCIPAL_AND_INTEREST_MINUS_PRINCIPAL` requires:

- remaining contractual payments;
- outstanding-principal subtraction basis;
- contractual horizon;
- fixed-income benchmark reference;
- benchmark selection;
- discount-rate conversion;
- compounding convention;
- payment frequency;
- optional fixed-income spread;
- partial-prepayment scaling (`NONE` or `PREPAID_PRINCIPAL_OVER_OUTSTANDING_PRINCIPAL`);
- evidence.

### Formula B

`PV_INTEREST_DIFFERENTIAL` requires:

- prepaid-principal base;
- owner-local finite `YieldMaintenanceLoanContractualRate`;
- reinvestment benchmark;
- positive-part contractual-rate-minus-reinvestment-rate differential semantic;
- frequency;
- maturity/open-prepayment-date horizon;
- reinvestment-benchmark-rate discount basis;
- closest-maturity or linear-interpolation benchmark selection;
- compounding conversion;
- evidence.

Fixed discriminants fail closed. Formula contracts do not fetch rates, calculate present value, select current benchmarks, or assume D07 valuation authority.

## 16. Deterministic logical material

All public semantic dataclasses are immutable `frozen=True, slots=True` values and expose deterministic `logical_values()`.

Canonicalized non-semantic collections include deal pools/tranches, explicit members, pari-passu members, pro-rata participants, contractual shares, condition-set collections, composite children and conditioned collections by their explicit ordinal/ID coordinates.

The candidate does not canonicalize away semantic ordering such as priority groups, sequential principal allocation or prepayment phase ordinals.

Logical material contains typed IDs/canonical decimals and retained static semantics; it contains no raw credential material, provider-native symbol, current benchmark value, current metric value, current pool balance or trigger result.

## 17. Provider-neutrality and operational exclusions

The source contract is static and imports no provider/vendor, network, database, filesystem, scheduler/threading, execution runtime or valuation runtime.

It implements no method that:

- submits/cancels orders;
- executes a waterfall;
- forecasts prepayment;
- prices a tranche;
- computes present value;
- resolves current pool state;
- fetches current rates/benchmarks.

```text
STATIC REPRESENTABILITY != PROVIDER SUPPORT
STATIC REPRESENTABILITY != VALUATION SUPPORT
STATIC REPRESENTABILITY != PREPAYMENT MODEL SUPPORT
STATIC REPRESENTABILITY != EXECUTION SUPPORT
```

## 18. Evidence provenance retained by the financial-design track

The frozen financial-design/provenance track used retained SEC filing identities including:

- JPMCC Commercial Mortgage Securities Trust 2019-COR5 — accession `000153949719001068`, file `n1658-x18_424b2cor5.htm`, 424B2 Final Prospectus, document date 2019-06-13, SEC filing date 2019-06-27;
- COMM 2012-CCRE1 Mortgage Trust — accession `000153949712000253`, file `prospectus_supplement.htm`, 424B5 Prospectus Supplement, SEC filing date 2012-05-25;
- BANK5 2026-5YR21 — accession `000153949726000969`, file `n5750_x4-annexa1.htm`, FWP Annex A-1, SEC filing date 2026-03-20.

The runtime module does not perform EDGAR/network retrieval and does not embed source bytes. Product instances retain opaque `FixedIncomeEvidenceRef` values to externally retained evidence under the applicable evidence system.

## 19. Adversarial test intent

The dedicated test suite falsifies, among other things:

- type/identity laundering;
- deal/pool/tranche conflation;
- non-deterministic caller ordering;
- priority/allocation conflation;
- wrong fixed metric roles;
- orphan/cyclic conditions;
- rounded fraction substitution;
- malformed threshold schedules;
- prepayment-boundary conflation;
- premium-sign policy invention;
- defeasance/evidence conflation;
- Formula-A/Formula-B discriminant substitution;
- hidden provider/runtime/valuation authority.

Local pre-CI falsification is not certification. Exact-head repository CI and independent review remain mandatory.

## 20. Mandatory future UMI-12 conformance follow-up

This bounded Lane-2 candidate does not modify the existing UMI-12 cross-asset harness. Before final UMI-14 closure, the following must be revisited and updated as required so the new owner participates in universal conformance:

- `tests/infrastructure/test_universal_cross_asset_conformance.py`;
- `tests/infrastructure/test_universal_cross_asset_conformance_guards.py`;
- `docs/architecture/QORE-UMI-12-CROSS-ASSET-CONFORMANCE-HARNESS-001.md`.

This follow-up is mandatory for final UMI-14 adjudication, not optional technical debt.

## 21. Certification chain

This candidate is not self-certifying. Required sequence:

```text
BOUNDED IMPLEMENTATION
-> TARGETED TESTS
-> FULL RUFF / MYPY / PYTEST+COVERAGE
-> EXACT CANDIDATE HEAD FREEZE
-> EXACT-HEAD QORE CI
-> INDEPENDENT ARCHITECTURE / SECURITY / PRODUCT-QUALITY REVIEW
-> INTEGRATION GATE
-> EXPECTED-HEAD PROTECTED MERGE
-> POST-MERGE MAIN/TREE/CI VERIFICATION
-> NEW FROZEN PROGRAM-D BASELINE
-> FINAL UMI-14 RERUN LATER
```

## 22. Explicit non-claims

This candidate does **not** establish:

- `UMI13-UNR-003` closed;
- UMI-14 pass;
- Program-D pass;
- universal market readiness;
- provider support;
- valuation support;
- prepayment-model support;
- executable waterfall support;
- loan/credit-facility lane closure;
- Production readiness;
- real-capital authority.

`UNR-003` remains open until implementation is independently certified and, even after integration, final closure remains subject to the full UMI-14 rerun.
