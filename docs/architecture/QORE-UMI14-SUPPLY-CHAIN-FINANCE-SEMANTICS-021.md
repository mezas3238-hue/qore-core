# QORE UMI-14 — Supply-Chain Finance Semantics 021

## 1. Status and scope

This document defines the bounded Program-D / D04 contract introduced for
`UMI13-UNR-021`.

The retained UMI-13 gap is:

```text
loans-credit-facilities
trade receivables / supply-chain finance
receivables purchase, factoring, forfaiting and advance-based techniques
are materially distinct
```

The retained external reference is `EXT-ICC-SCF-01`, qualified by UMI-13 as a
versioned reference to the ICC Standard Definitions for Techniques of Supply Chain
Finance, publication date 2017-01-09.

This contract closes only the semantic surface explicitly retained by that snapshot.
It does not claim that eight techniques are a complete present-day SCF taxonomy.
Payment-undertaking and later early-payment techniques discovered during the UMI-14
reconstruction remain separate qualification work for the final UMI-14 pass.

## 2. Responsibility boundary

The contract is an additive, provider-neutral, immutable qualification layer. It does
not modify the conventional loan/facility contract and does not reuse operational
QORE billing or profit-vault receivables.

The central separation is:

```text
RECEIVABLE / PAYMENT OBLIGATION
!= PURCHASE / ASSIGNMENT QUALIFICATION
!= LOAN / ADVANCE
!= DISCOUNT / PURCHASE PRICE
!= RECOURSE TERMS
!= SERVICING / COLLECTION
!= PAYMENT EXECUTION
!= CREDIT RISK
!= ACCOUNTING / ECL
```

Purchase-based SCF is not represented as conventional debt merely to reuse existing
loan structures. An advance-based SCF qualification may reference an already
represented credit leg through canonical UMI-02 `EconomicIdentityId`; it does not
import loan-local identifiers or duplicate loan economics.

## 3. Versioned technique set

`SupplyChainFinanceTechniqueKind` contains exactly the techniques retained for this
work item:

1. `RECEIVABLES_DISCOUNTING`
2. `FACTORING`
3. `FORFAITING`
4. `PAYABLES_FINANCE`
5. `LOAN_OR_ADVANCE_AGAINST_RECEIVABLES`
6. `DISTRIBUTOR_FINANCE`
7. `LOAN_OR_ADVANCE_AGAINST_INVENTORY`
8. `PRE_SHIPMENT_FINANCE`

The enum is deliberately versioned by the retained UMI-13/ICC-2017 scope. Newer
techniques must be represented only after explicit later qualification; they are not
silently coerced into these values.

## 4. Typed terms union

The top-level `SupplyChainFinanceQualification` stores one exact terms variant:

```text
ReceivablesPurchaseTerms | AdvanceBasedFinanceTerms
```

There is no independent mechanism field. The technique already determines which
variant is permitted, so a second discriminator would create redundant state that
could contradict the terms object.

Purchase techniques accept only `ReceivablesPurchaseTerms`. Advance techniques
accept only `AdvanceBasedFinanceTerms`. A mixed state such as forfaiting plus advance
terms is rejected.

## 5. Contract-local references

SCF uses caller-supplied opaque UUID references for:

- qualification identity;
- retained support reference;
- contractual parties;
- trade objects.

`ScfPartyReferenceId` does not establish legal identity, KYC status, registry identity,
account authority or provider identity.

`ScfTradeObjectReferenceId` does not establish title, current inventory state,
provider lookup identity or economic-instrument identity. When a trade object already
has canonical UMI-02 economic identity, an optional `EconomicIdentityId` may be linked
explicitly.

Every imported `EconomicIdentityId` is checked as an exact wrapper and its nested
UUID is checked as an exact `UUID` both at construction and when logical values are
emitted.

## 6. Contractual monetary values

`ScfContractualAmount` contains:

- a positive, finite, exact `Decimal`;
- an exact UMI-02 currency `EconomicIdentityId`.

It is a contractual amount, not current balance, utilization, availability, valuation
or accounting state.

Decimal serialization is context-independent and compact. The representation computes
whether fixed notation would be shorter before materializing a fixed string. Extreme
finite exponents therefore retain compact scientific notation instead of allocating a
large intermediate fixed representation.

## 7. Funding terms

`ScfFundingTerms` retains:

- an extensible canonical funding-rule code;
- an optional explicit fixed contractual amount.

A formula/rule-based arrangement is representable without inventing a fixed amount.
An explicit fixed amount can be retained when the contract supplies one. The model
performs no discount, present-value, eligibility, borrowing-base or ECL calculation.

## 8. Receivable/payment-obligation terms

`ReceivablePaymentObligationTerms` retains:

- local obligation reference;
- exact object kind: `receivable` or `payment-obligation`;
- creditor and debtor contract-local references;
- positive face amount and currency identity;
- exact due date;
- extensible obligation-form code;
- retained support reference;
- optional canonical economic identity if the right is already represented by UMI-02.

An invoice or documentary form may be expressed by the obligation-form code; purchase
terms do not redefine every document as a separate economic object kind.

No rule states that due date must follow purchase date. Purchasing or financing an
already-due receivable can be a valid contractual fact, so overdue status alone is not
a structural rejection condition.

## 9. Receivables purchase terms

`ReceivablesPurchaseTerms` retains:

- a non-empty exact tuple of receivable/payment-obligation terms;
- transferor and financier references;
- explicit assignment/transfer qualification;
- explicit recourse qualification;
- funding rule and optional fixed magnitude;
- purchase date;
- retained support reference.

Obligation references must be unique. Caller tuple order has no contractual authority,
so obligations are canonicalized deterministically.

The contract does not execute an assignment, transfer title, collect an invoice, move
cash or decide credit status.

For the retained forfaiting technique, the qualification must state
`without-recourse`. This is a technique-specific categorical condition retained by the
bounded definition rather than a universal law imposed on all purchases.

## 10. Advance-based terms

`AdvanceBasedFinanceTerms` retains:

- borrower and financier contract-local references;
- a non-empty exact tuple of typed trade-object bindings;
- funding rule and optional fixed magnitude;
- start date;
- optional maturity date;
- optional `credit_leg_identity_id: EconomicIdentityId`;
- retained support reference.

Trade objects are not receivable-only. They may represent receivables,
payment obligations, inventory, purchase orders, goods or other explicitly qualified
objects where the retained technique permits them.

The contract applies only categorical constraints justified by this work item:

- `LOAN_OR_ADVANCE_AGAINST_RECEIVABLES` accepts only `receivable` or
  `payment-obligation` trade objects;
- `LOAN_OR_ADVANCE_AGAINST_INVENTORY` accepts only `inventory` trade objects;
- distributor and pre-shipment finance remain capable of representing non-receivable
  objects without inventing a universal object rule not retained by UMI-13.

Trade-object references must be unique and caller tuple order is canonicalized because
no sequence role is defined by this contract.

## 11. Canonical credit-leg relationship

If an advance-based SCF arrangement corresponds to an economic loan/facility leg that
already exists, `credit_leg_identity_id` links to that leg through UMI-02
`EconomicIdentityId`.

This contract intentionally does not import `LoanContractId`, `LoanFacilityId`,
`LoanPartyReferenceId` or `LoanPrincipalAmount` for linkage. Those are local to the
conventional loan/facility representation and would create unnecessary internal
coupling or semantic distortion.

The optional relationship does not require every SCF advance to be represented as a
conventional loan. It only avoids duplicating an economic credit leg when one already
exists.

## 12. Runtime validation laws

The implementation follows the strongest current Program-D validation pattern:

- frozen/slotted dataclasses;
- exact runtime types at aggregate boundaries;
- exact `UUID` checks for local identifiers;
- exact plain `str` checks for extensible codes;
- exact finite `Decimal` checks;
- exact `date` checks, so `datetime` is rejected;
- exact `EconomicIdentityId` plus exact nested UUID checks;
- no caller-supplied list where an exact tuple is required;
- nested revalidation whenever `logical_values()` is emitted;
- deterministic caller-order canonicalization where order is not contractual;
- no implicit clock;
- no implicit UUID generation;
- no network/provider dependency.

State altered after construction is rechecked when logical values are requested. A
previously valid nested wrapper cannot be changed to an invalid UUID, code or identity
and then serialized silently.

## 13. Deterministic logical values

All public semantic values expose deterministic `logical_values()` material. Values
contain only canonical codes, explicit dates, UUID references, canonical Decimal text,
canonical identity references and nested immutable logical values.

No wall-clock value, random identifier, provider response or mutable process state is
part of the contract.

## 14. Explicit exclusions

UNR-021 does not:

- compute current receivables balance, dilution, utilization or availability;
- execute assignment or title transfer;
- collect invoices or move cash;
- approve credit or determine default;
- calculate discount, PV, ECL or accounting entries;
- create legal/KYC/account identity authority;
- determine current collateral eligibility;
- map provider capabilities;
- execute or settle a financial transaction;
- absorb `UMI13-UNR-022` Shari'ah financing/liquidity/hedging qualification;
- authorize Production or real capital.

## 15. Closure meaning

Closing `UMI13-UNR-021` means that the retained 2017 receivables-purchase and
advance-based SCF distinction has an explicit static D04 representation with typed
non-conflation.

It does **not** mean:

```text
UNR-021 CLOSED
= ALL PRESENT OR FUTURE SCF TECHNIQUES CERTIFIED
```

The final UMI-14 reconstruction must separately adjudicate later official SCF
techniques discovered after the retained UMI-13 snapshot.
