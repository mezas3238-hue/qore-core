# QORE-UMI-14-CASH-MONEY-MARKET-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 CORRECTION — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #363  
Master roadmap: Issue #303  
Frozen starting baseline: `c7b901d9c4ba5d542860559ee78aa7717f611dea`  
Frozen starting tree: `9743cf8188d29cda682c229e1baeb5a77a28a623`

This artifact documents the bounded D04 correction for `UMI13-UNR-001` and
`UMI13-UNR-002`. It adds immutable provider-neutral semantics for term deposits,
dual-currency deposit features, commercial paper, and certificates of deposit.

```text
SEMANTIC REPRESENTABILITY
!= PROVIDER SUPPORT
!= EXECUTION SUPPORT
!= VALUATION METHODOLOGY
!= RISK AUTHORITY
!= SETTLEMENT AUTHORITY
!= PRODUCTION READINESS
```

Document existence does not close either UNR.

## Owner boundary

The owner is `src/qore/infrastructure/cash_money_market_semantics.py`.

It reuses only:

- UMI-02 `EconomicIdentityId`;
- UMI-03 `DayCountConventionCode`;
- UMI-03 `FinancialTenor`;
- UMI-05 `DerivativeStrike`, `DerivativeStrikeBasis`,
  `DerivativePriceQuoteBasisCode`.

`REUSE != AUTHORITY TRANSFER`.

There are no provider, account, risk, execution, settlement, valuation, or research
imports.

## Local identity, evidence, and numbers

`CashMoneyMarketTermsId` and `CashMoneyMarketEvidenceRef` are immutable UUID-backed
owner-local references. They are not economic identities and do not reuse
`IdentityEvidenceRef`.

Financial magnitudes use exact finite `Decimal` value objects. Deposit principal,
commercial-paper face amount, issue price, and the bounded floating multiplier are
positive. Contractual rates and floating spreads are signed; zero and negative rates
remain representable.

Canonical decimal material normalizes equivalent encodings and normalizes signed zero
to `"0"`.

## Term deposit

`TermDepositTerms` retains instrument, obligor, denomination currency, principal,
start/maturity dates, signed contractual rate, day count, evidence, and an optional
dual-currency feature.

Instrument, obligor, and currency identities must differ and:

```text
start_date < maturity_date
```

For this bounded simple contract, interest payment and principal redemption occur at
maturity. No bond coupon object or payment tenor is introduced.

## Dual-currency feature

`TermDepositDualCurrencyFeature` retains the two currencies, FX fixing identity,
fixing date, PRICE strike, quote orientation, comparator, payout mapping, and evidence.

Orientations:

```text
alternate-per-principal
principal-per-alternate
```

Comparators:

```text
less-than
less-than-or-equal
greater-than
greater-than-or-equal
```

The reused strike must satisfy:

```text
basis == PRICE
value > 0
convention is None
price_quote_basis == "currency-per-unit"
```

Orientation binds the strike quote identity. The feature base currency must equal the
parent term-deposit denomination, the two DCD currencies must differ, the FX fixing
identity must differ from both currencies, and the fixing date must lie inside the
term interval. TRUE/FALSE payout identities must be exactly the two distinct DCD
currencies.

No runtime FX observation, valuation, or settlement engine is introduced.

## Commercial paper

Commercial paper uses independent typed pricing and interest subcontracts.

Pricing:

```text
AT PAR
DISCOUNTED
```

Discounted issuance requires `0 < issue_price < face_amount`.

Interest:

```text
NONE
FIXED
FLOATING
```

Bounded combinations:

```text
NONE + DISCOUNTED
FIXED + AT PAR
FIXED + DISCOUNTED
FLOATING + AT PAR
FLOATING + DISCOUNTED
```

`NONE + AT PAR` is outside this bounded minimum without a universal impossibility
claim.

Fixed CP retains rate, day count, and exact payment dates. Floating CP retains
reference identity, optional financial-tenor index maturity, signed spread, positive
multiplier, reset dates, payment dates, and day count.

Neutral floating adjustments canonicalize as:

```text
omitted spread -> zero
omitted multiplier -> one
```

The frozen contractual formula ordering is `(base rate + spread) * multiplier`.
No current observed rate, fixing engine, scheduler, or valuation producer is added.

## Certificate of deposit

`CertificateOfDepositTerms` retains instrument, issuing institution, currency,
principal, issue/start and maturity dates, negotiability, one typed return subcontract,
and evidence.

Negotiability is exactly:

```text
negotiable
non-negotiable
```

Return subcontracts are:

```text
fixed-rate
reference-linked
preset-steps
```

Reference-linked terms retain reference identity, signed spread, exact reset dates,
and day count. Preset-step terms retain ordered effective-date/signed-rate steps and
day count. Higher-order structured/equity/index-linked CD payoffs are outside this
bounded owner.

## Chronology and determinism

Date schedules are immutable non-empty tuples of exact `date` values. Duplicates are
rejected and caller order is canonicalized ascending. Outer contracts verify that
retained dates lie inside their contractual intervals.

Reset chronology is not payment chronology. No maturity date is inserted
automatically. No business-day adjustment or schedule generation occurs here.

All public semantic contracts expose deterministic `logical_values()`. Provider
symbols and listings do not participate in canonical equality.

## Tests and non-claims

`tests/infrastructure/test_cash_money_market_semantics.py` covers signed rates, both
DCD orientations, all DCD comparators, PRICE-strike binding, supported CP
cross-products, neutral floating defaults, CD return forms, negotiability,
chronologies, fail-closed cross-field validation, deterministic logical material,
immutability, and absence of operational APIs.

This candidate does not establish provider capability, execution readiness, account or
risk support, valuation methodology, settlement support, production readiness,
real-capital authority, UMI-14 pass, or Program-D final pass.

`UNR-001` and `UNR-002` remain open until tests, exact-head CI, independent review,
Integration Gate, protected merge, post-merge verification, and the required UMI-14
re-audit complete successfully.
