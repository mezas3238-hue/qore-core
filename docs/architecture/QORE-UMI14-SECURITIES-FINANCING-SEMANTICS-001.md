# QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — LANE 10 / UMI13-UNR-013 — PREPARATORY CORRECTION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracker: #394  
Parent audit: #363  
Starting certified baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`

This artifact closes only the bounded static D04 product-definition gap for repo,
securities lending and margin lending. It does not implement current SFT positions,
collateral valuation, margin calls, custody, settlement, execution, legal eligibility,
Production or real-capital authority.

## 1. Evidence boundary

Exact QORE baseline evidence:

- UMI-13 architecture blob: `ec51c900c2701f885053141601a7792cdf74856e`;
- cash/money-market source: `src/qore/infrastructure/cash_money_market_semantics.py`;
- cash/money-market source blob: `06315595819432a9da0fb2245262c4c12b9fd930`;
- UMI-05 generic derivative source blob:
  `36e4d672459c489573eabc7ba5413bb5ef99c3a6`.

UMI-13 retains:

`UMI13-UNR-013 — repo / securities lending / margin lending — distinct SFT forms; no dedicated owner`.

Exact-baseline repository searches did not identify another dedicated SFT owner. That
mechanical absence was not used alone as a financial defect claim.

Primary financial falsification used FpML 5.11/5.12 repo and security-lending product
schemas plus Financial Stability Board securities-financing standards/reporting
material. These sources distinguish repo, securities lending and margin lending and
preserve product-specific contractual terms.

## 2. Adjudication

`VERIFIED MATERIAL D04 GAP — BOUNDED CORRECTION REQUIRED`

Surviving collisions:

1. repo != term deposit or generic secured loan;
2. repo near transfer != contractual far repurchase transfer;
3. term repo != open/callable repo;
4. transferred repo security != current collateral valuation/state;
5. lent principal security != securities-lending collateral role;
6. securities-lending fee != cash-collateral rebate;
7. securities lending != repo;
8. margin-lending contractual limit != drawn balance or current availability;
9. bilateral != tri-party arrangement;
10. contractual haircut/initial margin != current margin calculation.

## 3. Candidate inventory

The candidate adds:

- `SftTermsId`, `SftEvidenceRef`, `SftPartyReferenceId`;
- `SftDayCountCode`, `SftCollateralEligibilityCode`;
- `SftDurationMode`, `SftRateKind`, `SftArrangementMode`;
- `SftCashAmount`, `SftSecurityQuantity`;
- `SftRateTerms`, `SftDurationTerms`, `SftArrangementTerms`;
- `SftMarginTerms`;
- `RepoFarLegTerms`, `RepoTerms`;
- `SecuritiesLendingCompensationTerms`, `SecuritiesLendingTerms`;
- `MarginLendingTerms`.

Only UMI-02 `EconomicIdentityId` is reused as cross-owner economic-identity material.
The SFT owner does not create or mutate identity records.

## 4. Contractual party references

`SftPartyReferenceId` is deliberately owner-local and opaque. Repo seller/buyer,
securities-lending lender/borrower and margin-lending lender/borrower must be distinct
within each contract.

This is not a party registry, legal-person identity system, KYC record or legal master
agreement. D22/legal systems retain those determinations.

## 5. Cash and security quantities

`SftCashAmount` preserves a positive finite amount and explicit economic identity for
the contractual currency.

`SftSecurityQuantity` preserves a positive finite quantity and explicit security
economic identity.

Neither object is a current account balance, inventory holding, custody record or
settlement instruction.

`SECURITY REFERENCE != SECURITY TRANSFER`

## 6. Financing-rate terms

`SftRateTerms` distinguishes fixed and floating financing terms:

- fixed rate: finite contractual rate; floating reference forbidden;
- floating rate: finite contractual spread/rate plus required reference economic
  identity;
- explicit day-count code in both cases.

Negative contractual rates/spreads are not universally forbidden. The owner performs
no accrual, compounding, benchmark observation or interest calculation.

## 7. Duration semantics

`SftDurationTerms` distinguishes:

- `TERM`: contractual termination date required, notice period forbidden;
- `OPEN`: no termination date may be invented; optional positive notice days allowed;
- `CALLABLE`: positive contractual notice days required; a contractual latest/end date
  may be present or absent.

These values do not resolve current notice, exercise, termination, recall or calendar
state.

## 8. Bilateral and tri-party arrangement

`SftArrangementTerms` distinguishes bilateral and tri-party structures. A bilateral
contract forbids a tri-party agent reference; tri-party requires one.

The agent reference is contractual metadata only. QORE does not communicate with,
control or certify a tri-party agent.

`TRI-PARTY TERMS != AGENT OPERATION`

## 9. Static margin / haircut material

`SftMarginTerms` may retain contractual initial-margin and/or haircut ratios. Values are
finite and non-negative.

The owner deliberately does **not** impose a universal `<= 1` bound. Contractual
initial-margin percentages can exceed 100%, and D04 must not invent a universal
normalization law.

No current collateral value, variation margin, margin call, exposure or liquidation is
calculated.

`CONTRACTUAL HAIRCUT != CURRENT MARGIN CALCULATION`

## 10. Repo semantics

`RepoTerms` retains:

- distinct repo instrument identity;
- seller and buyer references;
- duration terms, whose start date is the contractual near/purchase date;
- near-leg cash amount;
- non-empty transferred-security basket;
- financing-rate terms;
- bilateral/tri-party arrangement;
- optional static margin terms;
- evidence;
- contractual far-leg material where applicable.

A term repo requires a far leg whose repurchase date equals the contractual termination
date. Far-leg cash is optional because QORE must not calculate or fabricate a
repurchase cash amount from the repo rate when the supplied contract material does not
explicitly retain one.

An open repo forbids a far leg: the product definition must not invent the later close
date. A callable repo may retain a far leg only when a contractual termination date is
already present, and the dates must agree.

Transferred-security identities are unique within this bounded basket representation;
multiple quantities for the same identity must be presented upstream as one exact
contractual quantity rather than relying on hidden aggregation in D04.

The repo instrument identity must differ from the transferred security identities.

## 11. Securities-lending semantics

`SecuritiesLendingTerms` retains:

- distinct securities-lending instrument identity;
- lender and borrower references;
- duration terms;
- principal lent-security quantity/reference;
- fee/rebate compensation material;
- explicit collateral tuple;
- bilateral/tri-party arrangement;
- optional static margin terms;
- evidence.

`SecuritiesLendingCompensationTerms` keeps lending fee and cash-collateral rebate as
separate optional fields. At least one must be explicitly present. Lending fee is
non-negative; cash-collateral rebate may be negative and is therefore not silently
coerced into fee semantics.

Collateral may be cash and/or securities and may be an empty tuple when the contract
material supplied to this bounded owner does not enumerate collateral. The structural
role remains separate from the lent principal security even if a rare contract were to
reference the same economic identity in both roles; QORE does not invent a universal
identity-inequality rule where role distinction is sufficient.

No recall state, manufactured dividend/payment, current loan balance, collateral value,
substitution or return transfer is implemented.

## 12. Margin-lending semantics

`MarginLendingTerms` retains:

- distinct margin-lending facility/instrument identity;
- lender and borrower references;
- duration terms;
- positive contractual credit-limit cash amount;
- financing-rate terms;
- typed collateral-eligibility scheme code;
- optional exact tuple of eligible collateral economic identities;
- optional static margin/haircut terms;
- evidence.

The eligible-identity tuple may be empty because a scheme code can reference an
external contractual eligibility schedule. When identities are supplied they must be
typed and unique. The facility instrument itself cannot be listed as its own eligible
collateral identity.

No utilization, available credit, current borrowing balance, margin requirement,
liquidation threshold or collateral valuation is retained.

`MARGIN-LENDING LIMIT != CURRENT CREDIT AVAILABILITY`

## 13. Authority map

| Material | Authority |
|---|---|
| Economic/security identity and lifecycle | UMI-02 / D04 |
| Underlying security economics | existing D04 family owner |
| Repo / securities-lending / margin-lending static terms | this bounded D04 owner |
| Observed prices/collateral evidence | D05 |
| Current calendar/notice/time resolution | D06 |
| Collateral valuation/pricing | D07 |
| Current holdings, borrow/loan balances, collateral positions | D08 |
| Current margin/haircut/risk/exposure/capacity | D09 |
| Orders/execution/transfer instructions | D10 |
| Settlement, custody, collateral movement, recalls/returns | D11 |
| Legal/regulatory eligibility/master-agreement determinations | D22 |

## 14. Fail-closed invariants

- explicit UUID-backed owner IDs; no implicit identity generation;
- typed economic identities; raw UUID laundering rejected;
- canonical bounded lowercase codes;
- positive finite cash/security quantities;
- exact fixed/floating reference rules;
- strict positive-int notice semantics (`bool` rejected);
- term/open/callable duration combinations validated;
- bilateral/tri-party agent combinations validated;
- non-negative finite static margin/haircut ratios;
- term repo requires matching far date;
- open repo forbids far date;
- typed, non-empty repo transferred-security tuple with unique identities;
- securities-lending fee/rebate semantics remain distinct;
- collateral tuple retains cash/security role without current-state authority;
- margin-lending eligible collateral identities remain typed/unique;
- frozen/slotted deterministic values;
- deterministic `logical_values()`;
- no UUID generation, wall clock, provider/network/secret state.

## 15. Explicit exclusions

This candidate implements no:

- current repo/securities-loan/margin-loan position;
- collateral valuation or current margin calculation;
- margin call or liquidation;
- current shortability, locate or borrow availability;
- current utilization or available credit;
- manufactured payments/dividends;
- substitution/reuse/rehypothecation operation;
- recall/return operation;
- custody or settlement mutation;
- clearing/provider/execution integration;
- risk/exposure engine;
- legal master-agreement or eligibility engine;
- UMI-12 conformance-harness mutation;
- productive Cloud or real-capital authority.

## 16. Gate discipline

This candidate is preparatory because Lane 3 / PR #376 remains the integration-order
gate.

Required eventual sequence:

`PREPARATORY CANDIDATE -> EXACT-HEAD CI -> FREEZE -> WAIT FOR PRECEDING LANES -> SYNC TO NEW CERTIFIED MAIN -> NEW EXACT SHA -> FULL CI -> INDEPENDENT REVIEW -> INTEGRATION GATE -> EXPECTED-HEAD MERGE -> POST-MERGE CERTIFICATION`

`STATIC SFT TERMS != CURRENT SFT POSITION`

`CI GREEN != ENGINEERING APPROVAL`

`NO INDEPENDENT EXACT-HEAD REVIEW -> NO MERGE`

`NO LANE-ORDER BYPASS`
