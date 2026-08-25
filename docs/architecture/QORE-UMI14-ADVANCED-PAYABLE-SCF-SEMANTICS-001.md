# QORE UMI-14 — Advanced Payable SCF Semantics — Correction 001

Status: **BOUNDED D04 CORRECTION / NO OPERATIONAL AUTHORITY**

Parent final audit: #363  
Correction tracker: #457  
Finding: `F-UMI14-ADV-PAYABLE-001`  
Starting exact main: `c5fc9fa17934d2559c65be3e79d22fcd64439916`

## 1. Why this correction exists

UNR-021 intentionally retained the 2017 Standard Definitions technique set as a versioned contract:

- Receivables Discounting
- Factoring
- Forfaiting
- Payables Finance
- Loan/Advance against Receivables
- Distributor Finance
- Loan/Advance against Inventory
- Pre-shipment Finance

That implementation remains valid for its declared historical scope and is not widened here.

The final UMI-14 reconstruction qualified later Global Supply Chain Finance Forum material that adds a third SCF sub-category, **Advanced Payable**, containing:

1. Corporate Payment Undertaking (CPU)
2. Dynamic Discounting (DD)
3. Bank Payment Undertaking (BPU)

Primary industry sources:

- https://supplychainfinanceforum.org/standard-definitions-to-include-description-of-corporate-payment-undertaking-cpu/
- https://supplychainfinanceforum.org/techniques/corporate-payment-undertaking/
- https://supplychainfinanceforum.org/techniques/dynamic-discounting/
- https://supplychainfinanceforum.org/techniques/enhancement-of-the-standard-definitions-for-techniques-of-supply-chain-finance/
- https://supplychainfinanceforum.org/techniques/

The new category cannot be represented faithfully by forcing every structure into the retained `ReceivablesPurchaseTerms | AdvanceBasedFinanceTerms` union.

## 2. Owner boundary

New owner:

`src/qore/infrastructure/advanced_payable_scf_semantics.py`

Logical schema tag:

`advanced-payable-scf.v1`

This module is additive. It reuses exact UNR-021 primitives only where the economics are identical:

- `ReceivablePaymentObligationTerms` as the static contractual payment-obligation envelope;
- `ScfPartyReferenceId` as opaque contract-local party reference;
- `ScfEvidenceRef` as opaque evidence reference.

It deliberately does **not** import:

- `ReceivablesPurchaseTerms`;
- `AdvanceBasedFinanceTerms`;
- `ScfFundingTerms`.

Therefore the later Advanced Payable category does not mutate or masquerade as the earlier purchase/advance categories.

## 3. Common approved-obligation binding

`AdvancedPayableApprovedObligation` composes an exact `ReceivablePaymentObligationTerms` plus independent approval evidence.

It requires the retained obligation kind to be exactly:

`payment-obligation`

not `receivable`.

This distinction prevents an approved payable from automatically becoming a purchased receivable. The nested obligation retains seller/creditor, buyer/debtor, contractual amount/currency, original due date, obligation form, evidence and optional economic identity.

## 4. Corporate Payment Undertaking

`CorporatePaymentUndertakingTerms` retains:

- exact approved payment obligation;
- finance-provider contract-local reference;
- opaque corporate undertaking reference;
- undertaking evidence.

The buyer is the debtor already bound by the approved payment obligation; the seller is its creditor. The finance provider must differ from both.

Structural law:

```text
CPU != PAYABLES FINANCE
CPU != RECEIVABLES PURCHASE
BUYER UNDERTAKING != BANK UNDERTAKING
FINANCE-PROVIDER EARLY-PAYMENT RELATIONSHIP != ASSIGNMENT/TITLE ENGINE
```

The module does not assert that receivable title moved, does not construct an RPA, does not settle cash and does not calculate the discounted early-payment amount.

## 5. Dynamic Discounting

`DynamicDiscountingTerms` retains:

- exact approved payment obligation;
- exact `DynamicDiscountConvention`;
- evidence.

Its logical material explicitly records:

`buyer-own-funds`

There is intentionally **no finance-provider field** in the terms. This structurally preserves the GSCFF distinction that the buyer uses its own cash rather than receiving financing from a bank/fund/alternative financier.

`DynamicDiscountConvention` retains only the static contractual dimensions needed by this bounded owner:

- rate setter: `buyer | seller`;
- timing basis: `days-before-original-due-date`;
- evidence.

It does not carry a computed discount, present payment amount, current early-payment date, liquidity availability or platform calculation result.

Structural law:

```text
DYNAMIC DISCOUNTING = BUYER-FUNDED
RATE-SETTER != FINANCE PROVIDER
TIMING BASIS != CURRENT DISCOUNT CALCULATION
CONTRACTUAL RULE != PAYMENT EVENT
```

## 6. Bank Payment Undertaking

`BankPaymentUndertakingTerms` retains:

- exact approved payment obligation;
- issuing-bank contract-local reference;
- beneficiary contract-local reference;
- opaque bank-undertaking reference;
- opaque matched-network reference;
- undertaking evidence.

The issuing bank must differ from buyer, seller and beneficiary. The beneficiary must differ from the buyer; it may be the seller or another bank/party represented by an opaque contract-local reference.

Logical material explicitly records:

`issuing-bank-primary-obligor`

The network reference does not contain protocol, SDK, provider, endpoint or DLT implementation authority. It represents only the static matched-network context required to identify the contract structure.

Structural law:

```text
BPU != CPU
ISSUING BANK != BUYER
NETWORK REFERENCE != NETWORK IMPLEMENTATION
BPU MAY SUPPORT FINANCING != BPU EXECUTES FINANCING
BANK PRIMARY-OBLIGOR SEMANTIC != PAYMENT SETTLEMENT
```

## 7. Versioned technique qualification

`AdvancedPayableTechniqueKind` contains exactly:

- `corporate-payment-undertaking`
- `dynamic-discounting`
- `bank-payment-undertaking`

`AdvancedPayableQualification` binds one exact technique to one exact corresponding terms class, qualification/evidence IDs and an explicit date interval.

Cross-laundering is fail-closed:

- CPU cannot carry DD or BPU terms;
- DD cannot carry CPU or BPU terms;
- BPU cannot carry CPU or DD terms.

The retained `SupplyChainFinanceTechniqueKind` remains exactly the original eight-technique versioned set. No backwards schema mutation is performed.

## 8. Determinism / immutability / runtime-type policy

All new value/terms objects use `@dataclass(frozen=True, slots=True)`.

Validation uses exact runtime types for wrappers, UUIDs, enums and `date`; `datetime` is not accepted as a contractual date by subclassing.

Every `logical_values()` path re-enters validation and recursively revalidates nested mutable-by-forced-corruption state. No implicit wall clock or random UUID is generated.

No global mutable state is introduced.

## 9. Explicit negative space

This owner does not provide or authorize:

- invoice approval workflow/current status;
- finance-provider availability;
- receivable purchase/assignment/title transfer;
- current discount calculation;
- current early-payment election;
- payment initiation/execution;
- cash settlement;
- balance-sheet/accounting mutation;
- credit decision/ECL;
- valuation;
- Risk/account limits;
- provider mapping/capability;
- network/DLT implementation;
- credentials/secrets;
- Production or real capital.

```text
STATIC CONTRACT SEMANTICS != OPERATIONAL AUTHORITY
OFFICIAL TECHNIQUE EXISTS != PROVIDER SUPPORT
TYPE EXISTS != PAYMENT PRODUCER
```

## 10. Adversarial certification expectations

`tests/infrastructure/test_advanced_payable_scf_semantics.py` must prove at least:

- exact new three-technique set;
- retained ICC-2017 eight-technique set unchanged;
- exact technique↔terms binding;
- approved payable cannot be laundered as a receivable;
- CPU provider distinct from buyer/seller;
- CPU source has no purchase/advance owner dependency;
- DD buyer-funded structure and absence of finance-provider field;
- DD exact timing/rate-setter enums;
- BPU bank/beneficiary role separation;
- BPU primary-obligor + opaque network material;
- exact UUID/date/runtime types;
- interval chronology;
- deterministic logical values;
- recursive corruption detection;
- source-level absence of implicit time/UUID, network clients, threads/sleep/subprocess and operational write authority.

## 11. Integration boundary

This correction can close only `F-UMI14-ADV-PAYABLE-001` after exact-head tests, serial external review, protected expected-head merge and post-merge verification.

After this correction:

`#380 UNR-007 residual -> #458 final UMI-12 recertification -> rerun #363`

remain mandatory before any final Program-D disposition.

No QORE Universal Market Ready, provider-ready, operational-ready, Production or real-capital claim follows from this module.
