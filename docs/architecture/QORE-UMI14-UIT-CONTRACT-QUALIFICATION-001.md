# QORE-UMI14-UIT-CONTRACT-QUALIFICATION-001

## 1. STATUS

PROGRAM D / UMI-14 LANE IMPLEMENTATION CANDIDATE
INDEPENDENT CERTIFICATION REQUIRED

## 2. MISSION / ISSUE

Issue #400
UMI13-UNR-016 — unit investment trusts / funds-pooled-vehicles

## 3. EXACT BASELINE

SHA: 39e1598e91c912f473f9628c3aab30fe7b9cc034
TREE: 380140cd55ba7d90dcbd9e5fbb4944bdec9368d2

## 4. EXACT BOUNDED PURPOSE

This module provides a bounded identity-rooted Unit Investment Trust
qualification over complete UMI-02 EconomicIdentity.

It does not create a sovereign UIT fund owner, a generic fund taxonomy, a
parallel FundVehicleTerms owner, or a NAV value/calculation authority.

## 5. FINANCIAL EVIDENCE SCOPE

The implementation follows the authoritative US-style bounded UIT scope.

It does not create a universal global legal ontology.

## 6. ETF + UIT COEXISTENCE

ETF and UIT are not mutually exclusive.

QORE retains ETF form through UMI-06 FundVehicleTerms(vehicle_kind=ETF)
and UIT structure through this qualifier on the same economic identity.

## 7. NON-ETF UIT REPRESENTABILITY

The UIT qualifier is rooted directly on EconomicIdentity.

It does not require FundVehicleTerms or any existing FundVehicleKind member.
Therefore a non-ETF UIT can be qualified without falsely assigning:
ETF, LISTED_TRUST, MUTUAL_FUND, CLOSED_END_FUND, MONEY_MARKET_FUND, or REIT.

## 8. WHY FundVehicleTerms IS NOT REQUIRED

FundVehicleTerms enforces one mutually-exclusive FundVehicleKind.

Non-ETF UIT has no truthful current FundVehicleKind value.

Forcing FundVehicleTerms would reintroduce the exact R2 contradiction:
a valid non-ETF UIT could not be constructed without a false vehicle kind.

## 9. WHY FundVehicleKind IS NOT EXTENDED

Adding UNIT_INVESTMENT_TRUST to the same closed enum would allow
FundVehicleTerms(vehicle_kind=UNIT_INVESTMENT_TRUST) without the
mandatory bounded UIT qualification.

It would also be unable to represent ETF + UIT simultaneously.

## 10. WHY GENERIC FUND TAXONOMY IS NOT REWRITTEN

No repository evidence proves a generic orthogonal fund vehicle structure
decomposition beyond UIT.

A bounded qualifier solves UNR-016 with smaller blast radius.

## 11. COMPLETE ECONOMIC IDENTITY ROOT

The root field is:

fund_identity: EconomicIdentity

NOT EconomicIdentityId.

Complete identity material includes identity ID, kind, family, construction,
and identity evidence.

Lossy projection of only ID + family is prohibited.

## 12. FUNDS-POOLED-VEHICLES FAMILY GUARD

The root fund EconomicIdentity must be:

family == IdentityFamilyCode("funds-pooled-vehicles")

## 13. TRADABLE INSTRUMENT GUARD

The root and each specified security must have:

kind == EconomicIdentityKind.TRADABLE_INSTRUMENT

## 14. REDEEMABLE-SECURITY TYPE-ENCODED SEMANTIC

A completed UnitInvestmentTrustQualification means redeemable-security.

No configurable `redeemable: bool` exists because `False` would be an
invalid bounded state.

## 15. UNDIVIDED-INTEREST TYPE-ENCODED SEMANTIC

A completed UnitInvestmentTrustQualification means undivided-interest.

No configurable `undivided_interest: bool` exists.

## 16. SPECIFIED-SECURITY LOCAL CARRIER

UnitInvestmentTrustSpecifiedSecurity is local to UIT semantics.

It represents one contractually specified security identity.

It is not:
- current holding
- portfolio quantity
- portfolio weight
- allocation
- market value
- derivative payoff leg
- UMI-09 structured component binding

## 17. SPECIFIED-SECURITIES ORDER / DUPLICATES

The specified-securities tuple is non-empty.

Duplicate security identities are rejected based on security identity ID,
even if component evidence differs.

Order is not material and is canonicalized deterministically by identity ID.

## 18. NO UNIVERSAL QUANTITY/WEIGHT CLAIM

This implementation does not introduce quantity, weight, allocation, or
current portfolio state.

## 19. OPTIONAL CONTRACTUAL TERMINATION DATE

`contractual_termination_date` is an optional exact civil date.

It is not mandatory §80a-4(2) material.

It does not create scheduler, rollover, lifecycle event, liquidation, or
settlement behavior.

## 20. TERMINATION DATE != LIFECYCLE EVENT

UMI-02 IdentityLifecycleEvent is evidence-bearing event history.

It cannot substitute a contractual future termination date.

## 21. NAV AUTHORITY BOUNDARY

UMI-06 FundNavBasis remains the structural basis owner.
UMI-10 FundNavValue and FundNavMeasure remain observation/value carriers.

This module does not import or duplicate NAV authority.

## 22. CURRENT HOLDINGS BOUNDARY

This module contains no current holdings, current position, or portfolio
state.

## 23. UMI-09 STRUCTURED-COMPONENT NON-REUSE

UMI-09 StructuredComponentBinding is qualified for structured-product use.

It is not a fund contractual specified-security carrier.

This module uses a local UnitInvestmentTrustSpecifiedSecurity type.

## 24. LISTING != UIT STRUCTURE

ListingIdentity remains separate UMI-02 authority.

This module does not require FundVehicleKind.LISTED_TRUST.

## 25. LEGAL/GOVERNANCE EXCLUSION

Board absence, registration, voting-trust exclusion, trustee/custodian
regulatory status, and legal eligibility remain outside this D04 qualifier.

## 26. PROVIDER / EXECUTION / SETTLEMENT EXCLUSION

No provider symbol, provider capability, execution, settlement mutation,
redemption execution, cash distribution, or liquidation authority exists.

## 27. DETERMINISM

All values are frozen/slotted dataclasses.
Tuple-based deterministic logical_values material.
No unordered set/dict as retained material.
No wall clock, no UUID generation, no random identity, no I/O, no scheduler.

## 28. LOGICAL VALUES DESIGN

Qualifier logical material includes complete:
- qualification ID
- complete fund EconomicIdentity
- redeemable-security tag
- undivided-interest tag
- canonical specified securities
- optional termination date
- local evidence

Specified security logical material includes:
- complete security EconomicIdentity
- local evidence

## 29. NEGATIVE AUTHORITY SURFACE

No current NAV, NAV value/calculation, current holdings, redemption price,
request/execution, cash distribution, in-kind settlement, liquidation
execution, provider, legal/governance, order/trade/receipt, or settlement
mutation.

No operational methods.

## 30. TESTS / ORACLES

The test file contains direct oracles for:
- valid non-ETF UIT
- ETF + UIT coexistence
- wrong root family/kind
- exact-type and subclass laundering
- full root/component identity-evidence collision resistance
- specified-security component rules
- deterministic exact logical values
- exact field surfaces and frozen/slotted values
- forbidden authority/method negative space
- no FundVehicleTerms dependency
- no FundVehicleKind.UNIT_INVESTMENT_TRUST addition
- no lifecycle-event or structured-component substitution

## 31. INTEGRATION SEQUENCING

This candidate is preparatory only.

It does not merge around prior integration lanes.

After predecessor lanes integrate, this branch must be synchronized through
the approved process, producing a new SHA, CI, diff audit, independent
review, and Integration Gate adjudication.

## 32. REGISTRY / UMI-12 PROHIBITION

UMI-13 registry artifact is not modified.

UMI-12 conformance harness tests and architecture are not modified.

Registry and final conformance reconciliation occur only after bounded
semantic lanes are integrated/certified.

## 33. EXPLICIT NON-CLAIMS

NO CI PASS CLAIMED.
NO INDEPENDENT REVIEW CLAIMED.
NO MERGE AUTHORITY.
NO UNR-016 CLOSURE.
NO UMI-14 PASS.
NO PROGRAM-D PASS.
