# QORE-UMI14-CFD-CONTRACT-QUALIFICATION-001

## 1. STATUS

PROGRAM D / UMI-14 LANE IMPLEMENTATION CANDIDATE
INDEPENDENT CERTIFICATION REQUIRED

## 2. MISSION / ISSUE

Issue #398
UMI13-UNR-015 bounded CFD qualification / rolling lifecycle semantics

## 3. EXACT BASELINE

SHA: 39e1598e91c912f473f9628c3aab30fe7b9cc034
TREE: 380140cd55ba7d90dcbd9e5fbb4944bdec9368d2

## 4. EVIDENCE BOUNDARY

Repository facts are Integration-Gate verified and supplied.
Not independently verified by DeepSeek.

## 5. FINANCIAL EXPERT R6 RESULT

- Bounded ISDA CFD price-return/opening-closing semantics proven.
- Dividend/income/distribution/gross-net return not proven universal.
- Financing leg not proven mandatory.
- ESMA rolling-spot specimen requires bounded:
  - spot reference
  - automatic contract rollover
  - party termination capability.

## 6. REPOSITORY CODER R5 RESULT

No universal standalone CFD owner required.
Standard fixed-maturity and swap-form economics can use existing UMI-05
forward/swap primitives.
Bounded rolling-lifecycle residual remains.

## 7. INTEGRATION-GATE FINAL CROSS-ADJUDICATION

No universal CFD owner.
Bounded qualification/composition over UMI-02 + UMI-05.

## 8. R1/R2/R3/R4 CORRECTION HISTORY

- R1: constructors/oracles/rolling semantics/type hardening corrected.
- R2: exact UMI-02/05 constructors, temporal rule, same-reference oracle corrected.
- R3: module docstring, exact logical-value oracles, non-UTC projection,
  field-surface and negative-space oracles corrected.
- R4: final static package.
- R5: full EconomicIdentity logical projection, collision regression,
  valid foreign negative oracles, exact optional narrowing, and finite
  negative-space field/method oracles added.

## 9. WHY NO UNIVERSAL CFD OWNER

UMI-02 already provides `IdentityFamilyCode` classification.
UMI-05 already provides forward/fixing/settlement/composition.
Only bounded binding and rolling lifecycle specialization are missing.

## 10. AUTHORITY MAP

- Economic identity/family: UMI-02
- Forward/fixing/settlement: UMI-05
- Price-determination binding: this module
- Rolling lifecycle qualification: this module
- FX pair/quotation: future certified Lane 4
- Current observation: D05
- Payoff/valuation: D07
- Margin/leverage: D08/D09
- Execution/close-out: D10
- Settlement mutation: D11
- Legal/regulatory: D22

## 11. EXACT REUSED UMI-02 TYPES

EconomicIdentity
EconomicIdentityId
IdentityFamilyCode
IdentityRelationship
IdentityRelationshipCode

## 12. EXACT REUSED UMI-05 TYPES

ForwardContractTerms
DerivativeFixingTerms
DerivativeBenchmarkReference
DerivativeSettlementStyle

## 13. TYPED CANONICAL CFD FAMILY CONSTANT

IdentityFamilyCode("contracts-for-difference")

## 14. TYPED PRICE-DETERMINATION RELATIONSHIP CONSTANT

IdentityRelationshipCode("price-determination-reference")

## 15. SAME-REFERENCE RULE

When economic reference equals fixing reference, no relationship is required.
Any supplied relationship fails closed.

## 16. DISTINCT-REFERENCE RULE

When economic reference differs from fixing reference, an explicit
price-determination reference relationship is mandatory.

## 17. UMI-02 SOURCE != TARGET RULE

UMI-02 rejects same-source-target relationships upstream.
Tests never construct a same-endpoint relationship for qualification.

## 18. COMPLETE UTC FIXING-DATE COVERAGE LAW

Exact date fixing has unknown intraday location.
Relationship must cover complete UTC civil date:
effective_from <= fixing_day_start
effective_until is None or effective_until >= next_day_start.

## 19. NON-UTC NORMALIZATION

All datetimes canonicalize through UTC.
Tests prove non-UTC input yields exact UTC logical projection.

## 20. UPSTREAM NAIVE-DATETIME REJECTION

UMI-02 rejects naive datetime before CFD aggregation.

## 21. SUBCLASS-LAUNDERING BOUNDARY

Local exact-type checks reject:
IdentityFamilyCode subclass
IdentityRelationshipCode subclass
EconomicIdentityId subclass.

## 22. FORWARD-FORM CFD QUALIFICATION

Cash-settled bounded forward qualification binding fix reference to economic
reference.

## 23. ROLLING-SPOT LIFECYCLE QUALIFICATION

Bounded ESMA automatic rollover + party termination capability.

## 24. AUTOMATIC-ROLLOVER SEMANTIC

Type-encoded, no configurable False field.

## 25. PARTY-TERMINATION CAPABILITY

Type-encoded, no configurable False field.

## 26. ABSENCE OF FALSE-STATE BOOLEANS

Field surface excludes automatic_rollover/party_termination_capability bools.

## 27. FINANCIAL TENOR REUSE

FinancialTenor and FinancialTenorUnit reused exactly.

## 28. SCHEDULE-ROLL NEGATIVE BOUNDARY

Valid DerivativeScheduleConvention cannot substitute.

## 29. IDENTITY-LIFECYCLE-EVENT NEGATIVE BOUNDARY

Valid IdentityLifecycleEvent cannot substitute.

## 30. CRYPTO-PERPETUAL NEGATIVE BOUNDARY

CryptoPerpetualContractTerms cannot substitute.
Test is explicitly classified as TYPE-BOUNDARY evidence only.

## 31. SWAP/TRS NON-CLAIM

This module does not create total-return CFD completeness.
UMI-05 ReferenceReturnSwapLeg remains uncertified for full TRS CFD.

## 32. FINANCING NON-CLAIM

No universal CFD financing.

## 33. MARGIN-CLOSEOUT NON-CLAIM

D08/D09/D10/D22 authority remains outside this module.

## 34. SPREAD-BET NON-CLAIM

D22 legal qualification remains outside this module.

## 35. FUTURE LANE-4 / PR-382 FX COMPOSITION

PR #382 is unmerged and non-certified.
This module does not import fx_semantics.
After certification, rolling-spot composition must reuse certified FX pair/
quotation.

## 36. FIELD / AUTHORITY MATRIX

CfdForwardFormQualification: UMI-02 + UMI-05 + local binding.
CfdRollingSpotLifecycleQualification: UMI-02 + FinancialTenor + local lifecycle.

## 37. NEGATIVE-SPACE AUTHORITY MATRIX

No current price, observed fixing, PnL, payoff, margin, leverage, provider,
execution, settlement mutation, legal eligibility, or spread-bet status.

## 38. COMPLETE FORWARD TEST-ORACLE LEDGER

All required forward oracles are present in the R5 test file.

## 39. COMPLETE ROLLING TEST-ORACLE LEDGER

All required rolling oracles are present in the R5 test file.

## 40. DETERMINISM / TYPE / SECURITY LAW

Frozen/slotted dataclasses, exact runtime type checks, no Any, no type ignore,
deterministic logical_values(), secret-free.

## 41. REGISTRY PROHIBITION

UMI-13 registry artifact is not modified.

## 42. UMI-12 HARNESS PROHIBITION

UMI-12 tests and architecture are not modified.

## 43. INTEGRATION SEQUENCING

Candidate is preparatory only.
PR #376 remains prior integration gate.
This lane cannot merge around earlier lanes.
After predecessor certification, branch must be synced/rebased through approved
process, producing a new SHA/CI/diff audit/independent review.

## 44. EXPLICIT NON-CLAIMS

THIS MODULE QUALIFIES / COMPOSES EXISTING ECONOMIC AUTHORITY.
IT DOES NOT REPLACE UMI-05.
No UMI-14 pass. No Program-D pass. No production readiness. No provider support.
No valuation. No execution. No settlement mutation. No real-capital authority.
