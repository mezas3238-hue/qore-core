# QORE-UMI14-LOAN-CREDIT-FACILITY-SEMANTICS-001

Status: **PROGRAM D / UMI-14 LANE-3 CORRECTION CANDIDATE**

Tracking: #373  
Parent audit: #363  
Target unresolved ref: `UMI13-UNR-004`  
Starting correction baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`

---

## 1. Purpose

UMI-13 records `loans-credit-facilities` as `UNRESOLVED / NO_CERTIFIED_OWNER`
and records `UMI13-UNR-004 — loans/facilities` because the inspected Program-D
baseline had no dedicated certified semantic owner.

Lane 3 adds the minimum provider-neutral static semantic owner needed to distinguish:

```text
CREDIT AGREEMENT / DEAL
!= FACILITY / CREDIT LINE
!= LOAN CONTRACT / DRAWDOWN
```

It deliberately does not create operational lending, cash movement, current balance,
credit-risk, accounting, valuation, provider, settlement or execution authority.

---

## 2. Audit-first evidence

The exact starting tree at `39e1598e...` contains no production source path named
for a loan/facility semantic owner and no `LoanFacility` production contract.
Repository searches for `loan` / `facility` resolve materially to the UMI-13
unresolved ledger or to unrelated concepts such as research/account drawdown.

UMI-13 already freezes the material distinction:

```text
LOAN FACILITY != DRAWN LOAN
```

Official FpML loan architecture independently supports the same structural boundary.
FpML describes a credit agreement as a Deal, one or more Facilities within a Deal,
and Loan Contracts as actual borrowings/utilizations within a Facility. Facility
summary/commitment structures separately retain commitment limits and commitment
schedules. Loan contract structures separately retain loan principal and interest
period semantics.

FpML LoanContract schema material also makes `maturityDate` optional (`minOccurs=0`).
That is direct counterevidence against requiring every representable Loan Contract to
carry an explicit maturity date. QORE therefore retains Loan maturity only when it is
present in the contractual source material; absence is representable rather than
silently synthesized.

Primary references used for semantic qualification:

- FpML product/loan architecture:
  https://www.fpml.org/spec/fpml-4-5-5-tr-1/html/fpml-4-5-intro.html
- FpML facility summary schema documentation:
  https://www.fpml.org/spec/fpml-5-10-5-rec-1/html/confirmation/schemaDocumentation/schemas/fpml-loan-5-10_xsd/groups/FacilityDetails.model/facilitySummary.html
- FpML facility commitment model:
  https://www.fpml.org/spec/fpml-5-11-1-wd-1/html/confirmation/schemaDocumentation/schemas/fpml-loan-5-11_xsd/groups/FacilityCommitment.model.html
- FpML 5.13 loan schema overview:
  https://www.fpml.org/spec/fpml-5-13-2-wd-2/html/confirmation/schemaDocumentation/schemas/fpml-loan-5-13_xsd/schema-overview.html
- FpML LoanContract component documentation, where `maturityDate` is optional:
  https://www.fpml.org/spec/fpml-5-13-2-wd-2/html/confirmation/schemaDocumentation/schemas/fpml-loan-5-13_xsd/complexTypes/LoanContract.html

These sources prove market/standard semantics only. They do not prove QORE provider,
operational, valuation, risk, accounting, settlement or execution support.

Audit result:

`VERIFIED STRUCTURAL GAP — BOUNDED ADDITIVE D04 OWNER REQUIRED`

---

## 3. Owner boundary

New owner:

`qore.infrastructure.loan_credit_facility_semantics`

This owner is additive. It does not modify UMI-02, UMI-03, UMI-04, UMI-05, UMI-12
or UMI-13 production contracts.

Reused certified semantics where the economic meaning is already owned:

- UMI-02 `EconomicIdentityId` only for instruments/reference objects and currency/reference attachments;
- UMI-03 `DayCountConventionCode`;
- UMI-03 `FinancialTenor`;
- UMI-03 `FixedIncomeBenchmarkReference` as benchmark/reference attachment only;
- UMI-03 `FixedIncomeSpread` as spread magnitude distinct from rate/yield.

Important non-conflations:

```text
LOAN CONTRACTUAL RATE != BOND COUPON RATE
LEGAL/CONTRACTUAL PARTY REFERENCE != ECONOMIC INSTRUMENT IDENTITY
```

UMI-02 defines `EconomicIdentityId` for an economic instrument or reference object.
It is therefore not valid authority for borrower, lender or agent parties. QORE has
no inspected universal legal-entity identity owner in this correction baseline.

Lane 3 defines `LoanPartyReferenceId` as an opaque caller-supplied contractual party
reference. It grants no universal legal-entity identity, KYC, LEI, counterparty-risk,
authorization or account authority. This is intentionally narrower than inventing a
global party identity contract.

The owner also defines `LoanInterestRate` instead of laundering a loan rate through
`CouponRate`.

---

## 4. Deal / facility / loan-contract structure

### 4.1 Deal

`LoanCreditFacilityDeal` is the static contractual aggregate. It owns:

- `LoanDealId`;
- a canonical deal `EconomicIdentityId`;
- one or more `LoanFacilityTerms`;
- zero or more `LoanContractTerms`;
- zero or more bounded `LoanCovenantTerms`;
- zero or more facility-scoped `LoanSyndicationTerms`;
- an opaque `LoanEvidenceRef`.

A Deal may contain an undrawn Facility and therefore does not require a Loan Contract.

### 4.2 Facility

`LoanFacilityTerms` retains:

- `LoanFacilityId` and exact Deal binding;
- facility economic identity;
- one or more permitted `LoanPartyReferenceId` borrower references;
- commitment currency identity;
- one or more allowed draw currency identities;
- extensible `LoanFacilityTypeCode`;
- start date and optional maturity date;
- positive original commitment;
- optional `LoanCommitmentSchedule`;
- evidence reference.

`LoanFacilityTypeCode` is intentionally extensible rather than a frozen facility enum.
QORE must not pretend that one short enum exhausts every commercial-loan facility form.

A scheduled commitment amount may reduce to zero. The original facility commitment
must be positive.

### 4.3 Loan Contract / drawdown

`LoanContractTerms` is an actual contractual borrowing within one Facility. It retains:

- `LoanContractId`;
- Facility binding;
- loan economic identity;
- borrower contractual party reference;
- draw/loan denomination identity;
- positive original contractual principal;
- explicit start date;
- optional explicit maturity date;
- fixed or floating contractual interest terms;
- contractual amortization schedule;
- evidence reference.

No maturity date is synthesized when the contractual source omits it. If an explicit
Loan maturity is retained, it must be after Loan start. Top-level Deal validation
fails closed unless:

- the referenced Facility exists inside the Deal;
- the Loan borrower party reference is permitted by that Facility;
- the Loan denomination is one of the Facility's allowed draw currencies;
- Loan start is not before Facility start;
- when both Loan and Facility maturities are explicit, Loan maturity does not follow Facility maturity;
- when Facility maturity is explicit, no retained Loan principal repayment follows that Facility maturity even if Loan maturity itself is absent.

No current outstanding principal is retained or derived.

---

## 5. Commitment semantics

`LoanCommitmentAmount` is a non-negative contractual magnitude in a separately bound
commitment currency.

`LoanCommitmentSchedule` is an immutable chronological set of unique effective-date
commitment states. Caller ordering is non-semantic; the schedule canonicalizes by
`effective_date`.

It does not:

- calculate availability;
- subtract current utilization;
- reserve credit capacity;
- move cash;
- enforce live draw requests;
- decide lender funding.

```text
COMMITMENT LIMIT != CURRENT AVAILABLE CREDIT
```

---

## 6. Interest semantics

Two explicit contractual forms are supported:

### `FixedLoanInterestTerms`

- `LoanInterestRate`;
- `DayCountConventionCode`;
- payment `FinancialTenor`.

### `FloatingLoanInterestTerms`

- `FixedIncomeBenchmarkReference`;
- `FixedIncomeSpread`;
- `DayCountConventionCode`;
- payment `FinancialTenor`;
- reset `FinancialTenor`.

The benchmark object is a reference attachment only. It does not construct, select,
observe or resolve a current benchmark fixing.

The contract permits finite signed rates/spreads; it does not invent a universal
non-negative-rate law.

```text
CONTRACTUAL RATE TERMS != CURRENT RATE PERIOD
REFERENCE != FIXING
SPREAD != RATE != YIELD
```

---

## 7. Amortization semantics

`LoanPrincipalRepayment` retains:

- explicit positive ordinal;
- contractual due date;
- positive `LoanPrincipalAmount`.

`LoanAmortizationSchedule` canonicalizes by ordinal and rejects duplicate ordinals or
backward-moving due dates. Every retained repayment must be after Loan start. When an
explicit Loan maturity exists, every retained repayment must also be on/before that
Loan maturity. Independently, when the enclosing Facility has an explicit maturity,
top-level Deal validation rejects any retained repayment after Facility maturity.

This preserves fail-closed chronology without inventing a Loan maturity solely to
bound repayments.

The schedule deliberately does not require scheduled principal amounts to sum to the
original principal. That would falsely exclude structures with capitalization,
reborrowing or other contractual mechanics whose current balance is outside this
static D04 slice.

```text
AMORTIZATION SCHEDULE != CURRENT OUTSTANDING BALANCE
```

---

## 8. Covenant boundary

`LoanCovenantTerms` provides bounded static qualification only:

- covenant identity;
- Deal binding;
- `LoanCovenantKind`;
- extensible `LoanCovenantCode`;
- optional testing tenor;
- optional Facility scope;
- evidence reference.

Kinds are:

- financial;
- affirmative;
- negative;
- information.

This owner does not define or execute metric production, financial-statement
normalization, covenant testing, breach determination, waiver, cure or event logic.

```text
COVENANT DEFINITION / QUALIFICATION != COVENANT EVALUATION
```

Facility-scoped covenants must resolve to a Facility inside the Deal.

---

## 9. Syndication boundary

`LoanSyndicationTerms` retains bounded **original contractual** syndication material
for one Facility:

- syndication identity;
- Deal binding;
- Facility binding;
- agent contractual party reference;
- unique original lender contractual party references;
- exact original `LoanParticipationShare` values summing to one;
- evidence reference.

A bilateral/non-syndicated Deal may retain no syndication terms. For a syndicated
Deal, lender allocations are Facility-scoped because commitments can differ between
Facilities. At most one complete original syndication definition is retained per
Facility. Caller order of lender shares is non-semantic and canonicalizes by lender
party reference.

This is not current lender-position state and does not model loan-contract lender
positions, secondary loan trading, assignments, participations, settlement, lender
books or transfer consent.

```text
ORIGINAL SYNDICATION SHARES != CURRENT LENDER POSITION
```

---

## 10. Cross-reference fail-closed rules

The aggregate rejects:

- duplicate Facility IDs;
- Facility Deal-ID mismatch;
- duplicate Facility economic identities;
- Deal/Facility economic-identity conflation;
- duplicate Loan Contract IDs;
- duplicate Loan economic identities;
- Deal/Loan or Facility/Loan economic-identity conflation;
- Loan Contract -> foreign Facility references;
- Loan borrower not permitted by Facility;
- Loan draw currency not permitted by Facility;
- Loan start before Facility start;
- explicit Loan maturity after explicit Facility maturity;
- retained Loan repayment after explicit Facility maturity, including when Loan maturity is absent;
- duplicate covenant IDs;
- covenant Deal-ID mismatch;
- Facility-scoped covenant -> foreign Facility;
- duplicate syndication IDs or duplicate original syndication definitions for one Facility;
- syndication Deal-ID mismatch;
- syndication Facility reference outside the Deal;
- duplicate original syndication lenders;
- original lender shares not summing exactly to one.

All canonical public values are frozen/slotted dataclasses with deterministic logical
material and explicit type/date/Decimal/code validation.

---

## 11. Explicit exclusions / unresolved carry-forward

Lane 3 targets only `UMI13-UNR-004`.

It does **not** close:

### `UMI13-UNR-021`

Supply-chain finance remains separate, including:

- receivables discounting/purchase;
- factoring;
- forfaiting;
- payables finance;
- loan/advance against receivables;
- inventory finance;
- distributor/pre-shipment finance.

ICC's Standard Definitions demonstrate that SCF contains materially distinct
receivables-purchase and loan/advance-based techniques. A generic Loan Facility owner
must not erase those distinctions.

### `UMI13-UNR-022`

Shari'ah-compliant financing/liquidity/hedging structures remain separate
cross-family qualification, including Murabahah, Ijarah, Wakalah/agency and related
syndicated financing forms.

```text
CONVENTIONAL LOAN FACILITY OWNER != SHARI'AH FINANCING CERTIFICATION
```

---

## 12. Operational negative space

This module contains no:

- provider SDK or provider mapping;
- HTTP/network access;
- database/persistence;
- scheduler/thread/async runtime;
- implicit wall clock;
- random/implicit UUID generation;
- current outstanding balance;
- live utilization/availability calculation;
- lender-position observation;
- covenant evaluator;
- default/breach engine;
- pricing/PV/ECL/accounting engine;
- risk/credit scoring;
- payment/settlement/cash mutation;
- execution/order authority;
- automatic corrective action.

`STATIC LOAN REPRESENTABILITY != OPERATIONAL LENDING SUPPORT`

---

## 13. Determinism / security

- UUID identities are caller supplied;
- no `uuid4()`;
- dates are explicit `date` values when present;
- absent maturity remains explicit `None`, never inferred from wall clock or another field;
- Decimal values must be finite;
- booleans cannot launder into integer ordinals;
- canonical code fields require exact plain `str` and lowercase code syntax;
- nested local values require exact runtime classes at aggregate boundaries;
- economic-object identities and contractual party-reference collections are unique and canonicalized deterministically;
- schedules are immutable and canonicalized by explicit economic keys;
- evidence is opaque UUID reference material only;
- no credentials/secrets are retained as text.

---

## 14. Acceptance criteria

Before promotion the exact candidate must demonstrate:

1. Deal != Facility != Loan Contract in both typed IDs and economic identities;
2. undrawn Facility representability;
3. Loan Contract with absent maturity representability without synthesized dates;
4. foreign Facility rejection for Loan Contracts;
5. contractual party-reference and draw-currency Facility binding;
6. explicit Facility/Loan chronology guards plus Facility-bounded repayments for open-ended Loans;
7. commitment schedule canonicalization and zero terminal commitment acceptance;
8. fixed != floating interest and rate != spread;
9. amortization schedule chronology/ordinal guards;
10. covenant reference/scoping without evaluation authority;
11. facility-scoped original syndication shares and deterministic ordering;
12. duplicate-ID fail-closed behavior;
13. frozen/slotted deterministic values;
14. no provider/runtime/valuation/risk/settlement authority;
15. full QORE Ruff/Mypy/Pytest+coverage green on exact head;
16. independent exact-head adversarial review;
17. Integration Gate adjudication;
18. protected expected-head merge;
19. post-merge baseline/tree/CI verification.

---

## 15. Non-claims

This candidate does not establish:

- `UMI13-UNR-004` final UMI-14 closure before re-audit;
- `UMI13-UNR-021` closure;
- `UMI13-UNR-022` closure;
- provider support;
- universal legal-entity/party identity authority;
- current loan/facility state;
- lender-position support;
- credit approval;
- covenant compliance;
- valuation/accounting/risk completeness;
- payment/settlement/execution support;
- UMI-14 pass;
- Program-D pass;
- QORE Universal Market Ready;
- Production or real-capital authority.

`CI GREEN != ENGINEERING APPROVAL`

`IMPLEMENTED CANDIDATE != CERTIFIED`

`NO INDEPENDENT EXACT-HEAD REVIEW -> NO MERGE`
