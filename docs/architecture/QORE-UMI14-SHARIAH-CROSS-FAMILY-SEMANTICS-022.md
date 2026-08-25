# QORE UMI-14 — Shari'ah cross-family semantics 022

## 1. Scope

This bounded Program-D component closes `UMI13-UNR-022` for the exact retained
cross-family qualification surface. It represents static contractual structure
only.

It does **not** determine present religious or legal compliance and it does not
replace the existing economics owned by loans, Sukuk, derivatives, rates or FX.

## 2. Retained external-reference scope

UMI-13 retains three distinct surfaces:

1. `EXT-IIFM-ISLAMIC-LIQUIDITY-01`
   - Murabahah;
   - Wakalah / agency liquidity;
   - collateralized Murabahah financing/liquidity.
2. `EXT-IIFM-ISLAMIC-HEDGING-01`
   - profit-rate hedging;
   - cross-currency hedging;
   - Islamic FX-forward structures.
3. `EXT-IIFM-SYNDICATED-2026-01`
   - standardized Ijarah / Murabahah syndicated-financing suite.

These retained references do not authorize a universal taxonomy of Islamic
finance.

## 3. Non-conflation laws

```text
SHARI'AH CROSS-FAMILY QUALIFICATION
!= ECONOMIC IDENTITY
!= CONVENTIONAL LOAN ECONOMICS
!= SUKUK STRUCTURAL QUALIFICATION
!= GENERIC DERIVATIVE ECONOMICS
!= CURRENT RATE / FIXING
!= VALUATION
!= RELIGIOUS / LEGAL DETERMINATION
!= PROVIDER SUPPORT
!= EXECUTION
!= SETTLEMENT
```

The component adds only the missing cross-family contractual qualification.

## 4. Top-level contract

`ShariahCrossFamilyQualification` retains:

- caller-supplied `ShariahCrossFamilyQualificationId`;
- exact `ShariahCrossFamilyCategory`;
- one exact typed terms variant;
- explicit effective date and optional end date;
- extensible `ShariahFrameworkCode`;
- opaque `ShariahEvidenceRef`.

The three exact categories are:

- `FINANCING_LIQUIDITY`;
- `HEDGING`;
- `SYNDICATED_FINANCING`.

Category and terms variant must match exactly.

## 5. Financing / liquidity

`ShariahFinancingLiquidityTerms` retains:

- exact retained structure:
  - Murabahah;
  - Wakalah / agency;
  - collateralized Murabahah;
- one primary `EconomicIdentity`;
- non-empty contract-local participant bindings;
- optional canonical related `EconomicIdentityId` links;
- explicit start/end dates;
- evidence.

The primary identity may be qualified only when its family is one of the
cross-family financing/liquidity families retained by the reconstructed scope:

- `cash-money-market`;
- `fixed-income-credit`;
- `structured-hybrid-products`;
- `loans-credit-facilities`.

This does not convert every such identity into Shari'ah-compliant financing; it
only constrains which already-existing economic family may be qualified by this
contract.

No principal, margin, profit rate, amortization, current collateral state or
cash movement is copied or calculated here.

## 6. Hedging

`ShariahHedgingQualificationTerms` retains:

- profit-rate hedging;
- cross-currency hedging;
- Islamic FX-forward qualification;
- the complete existing economic identity being qualified;
- optional canonical related economic-identity references;
- evidence.

The primary qualified instrument must belong to `forwards-swaps-otc` because
this contract qualifies existing hedging economics rather than redefining FX,
rate or derivative terms.

Notional, benchmark, rate, currency pair, legs and flows remain owned by their
existing contracts.

## 7. Syndicated financing

`ShariahSyndicatedFinancingTerms` retains:

- Ijarah or Murabahah structure;
- a complete primary `EconomicIdentity` in `loans-credit-facilities`;
- declarative participants and roles;
- evidence.

It represents no current participant position, commitment balance, allocation,
cash movement or legal/religious determination.

## 8. Participant semantics

`ShariahParticipantBinding` is contract-local. It is not KYC or universal legal
identity.

Each binding retains:

- caller-supplied binding UUID;
- caller-supplied contract-local party UUID;
- extensible canonical role code;
- evidence reference.

Participant collections are exact non-empty tuples, binding IDs are unique and
an identical party+role pair cannot be duplicated. One party may hold distinct
contractual roles when the contract explicitly retains those roles.

Caller order is non-semantic and is canonicalized deterministically.

## 9. Economic identity validation

Whenever family is material, the full imported `EconomicIdentity` is required.
The component independently revalidates:

- exact `EconomicIdentity` runtime type;
- exact `EconomicIdentityId` and inner UUID;
- exact `EconomicIdentityKind`;
- exact `IdentityFamilyCode` and canonical code text;
- exact `IdentityConstructionKind`;
- exact `IdentityEvidenceRef` and inner UUID;
- `CONTINUOUS_REFERENCE -> REFERENCE_OBJECT`.

This is intentionally stronger than relying on the older imported constructor
checks alone.

Where family is not material, only canonical `EconomicIdentityId` links are
retained, again with exact wrapper and inner UUID revalidation.

## 10. Determinism and immutable logical state

All value objects are frozen/slotted dataclasses where applicable.

Logical output:

- revalidates recursively on every call;
- uses explicit caller-supplied UUIDs only;
- uses explicit dates only;
- has no implicit clock;
- canonicalizes non-contractual participant and identity-reference order;
- rejects duplicate canonical identity links;
- remains provider-neutral.

## 11. Runtime validation laws

The contract rejects at least:

- category/terms mismatch;
- raw or subclass-laundered wrappers, UUIDs, strings, dates and enums;
- unsupported primary economic families;
- invalid nested economic identity state;
- continuous-reference identities paired with a non-reference kind;
- non-tuple participant or related-identity collections;
- duplicate participant binding IDs;
- duplicate party+role participant semantics;
- duplicate related economic identities;
- end dates preceding start/effective dates;
- corrupted nested state when logical values are requested.

## 12. Explicit exclusions

This component does not:

- calculate price, PV, margin, profit, yield or current rate/fixing;
- determine Shari'ah compliance or issue legal/scholarly conclusions;
- create KYC or legal-entity identity;
- duplicate loan principal/amortization;
- duplicate derivative/FX/rate economics;
- calculate collateral state or participant positions;
- move cash or assets;
- query providers;
- execute or settle transactions;
- mutate Risk or accounts;
- authorize Production or real capital.

## 13. Closure boundary

Closing `UMI13-UNR-022` means the exact retained cross-family qualification is
representable without conflating it with generic economic contracts or
operational authority.

It does not mean:

```text
UNR-022 CLOSED
== UNIVERSAL ISLAMIC-FINANCE TAXONOMY
== RELIGIOUS / LEGAL CERTIFICATION
== PROVIDER SUPPORT
== PRODUCTION READINESS
```
