# QORE-UMI14-SUKUK-SHARIAH-STRUCTURAL-SEMANTICS-019

## Status

**PROGRAM D / UMI-14 — UNR-019 CORRECTION CANDIDATE; INDEPENDENT REVIEW REQUIRED**

Tracking: Issue #442  
Parent audit: Issue #363  
Exact starting main: `25ed21be1ba427820be78dbb8958d441e5f27f9c`

This artifact defines the bounded provider-neutral correction for
`UMI13-UNR-019 — Sukuk / Shari'ah structural semantics`.

It does not self-certify the correction and does not close UMI-14.

## 1. Verified gap

The canonical UMI-13 ledger retains UNR-019 because Sukuk certificate structures
are not reducible to ordinary conventional debt by implication.

UMI-03 explicitly leaves Sukuk / Shari'ah structural qualification outside the
ordinary fixed-income foundation. UMI-09 supplies generic structured/hybrid
composition but does not identify a Sukuk certificate's interest, underlying
structural relationships, ordered contractual legs, distribution source or
external Shari'ah-framework evidence.

The canonical UMI-13 external ledger already records IIFM Sukuk standards. The
published IIFM Sukuk material distinguishes, among other documented forms:

- Sukuk Al-Ijarah templates with sale/purchase, lease, service-agency,
  undertaking and declaration-of-trust document roles; and
- Sukuk Al-Mudarabah Tier1 templates with Mudarabah and declaration-of-trust
  structural material.

Those references establish product/standard existence. They do not grant QORE
legal, religious, provider, execution or Production authority.

## 2. Governing laws

```text
SUKUK CERTIFICATE
!= CONVENTIONAL COUPON DEBT BY IMPLICATION

SUKUK STRUCTURE CODE
!= COMPLETE SUKUK STRUCTURE

CERTIFICATE INTEREST
+ UNDERLYING INTEREST BINDINGS
+ ORDERED STRUCTURAL LEGS
+ DISTRIBUTION SOURCE
+ EXTERNAL SHARIAH EVIDENCE
= BOUNDED STATIC STRUCTURAL QUALIFICATION

EXTERNAL SHARIAH EVIDENCE
!= QORE SHARIAH COMPLIANCE DETERMINATION
!= JURISPRUDENCE ENGINE
!= LEGAL OPINION

STRUCTURAL LEG
!= EXECUTED AGREEMENT
!= PAYMENT
!= SETTLEMENT MUTATION

DISTRIBUTION SOURCE
!= DISTRIBUTION AMOUNT
!= COUPON
!= CASH-FLOW CALCULATION

UNR-019 SUKUK CERTIFICATE QUALIFICATION
!= UNR-022 CROSS-FAMILY FINANCING / LIQUIDITY / HEDGING
```

## 3. Root identity boundary

`SukukStructuralQualification` reuses an existing exact UMI-02
`EconomicIdentity` as the certificate root.

The root must be:

- `TRADABLE_INSTRUMENT`; and
- already classified in `fixed-income-credit` or
  `structured-hybrid-products`.

No new identity family, issuer identity, trustee/legal-entity authority or
provider symbol is introduced.

The tradable-certificate requirement is also the principal UNR-019 / UNR-022
boundary. A standalone Murabahah financing, Ijarah financing, Wakalah liquidity
arrangement, Islamic hedge or syndicated-financing agreement cannot use this
contract merely because it is Shari'ah-compliant; it is not a Sukuk certificate
root by implication.

## 4. Static structural contract

The candidate retains:

1. `SukukQualificationId`;
2. exact UMI-02 certificate identity;
3. extensible `SukukStructureCode`;
4. explicit `SukukCertificateInterestCode`;
5. non-empty immutable underlying-interest bindings;
6. non-empty immutable ordered structural legs;
7. one explicit `SukukDistributionSource`;
8. one opaque `SukukExternalShariahEvidence` declaration;
9. exact issue date and optional maturity date;
10. opaque aggregate evidence reference.

Extensible codes are structural identifiers, not a closed global taxonomy.
Ijarah and Mudarabah are useful adversarial examples because they exercise
materially different interests and leg structures, but the implementation does
not claim that those two codes exhaust Sukuk forms.

## 5. Underlying interests

Each `SukukUnderlyingInterestBinding` retains:

- stable local binding ID;
- one exact UMI-02 underlying/reference economic identity;
- explicit structural role;
- explicit interest semantic;
- opaque retained-evidence reference.

The certificate cannot be its own underlying.

Exact duplicate semantic bindings are rejected even when callers invent different
local binding IDs. The same underlying may remain more than once only when role or
interest semantics differ materially.

Caller input order is not semantic. Underlying bindings canonicalize by exact
identity/role/interest material plus stable binding ID.

## 6. Ordered structural legs

Each `SukukStructuralLeg` retains:

- stable local leg ID;
- positive exact integer `ordinal`;
- extensible leg-kind code;
- extensible structural-role code;
- optional reference to one declared underlying binding;
- opaque retained-evidence reference.

Leg IDs and ordinals are independently unique. The aggregate canonicalizes by
explicit ordinal, not caller tuple order.

Changing the ordinals changes logical identity because contractual sequencing can
be material. The contract does not execute, resolve or legally interpret a sale,
lease, service agency, undertaking, declaration of trust, partnership or other
leg code.

## 7. Distribution source

`SukukDistributionSource` declares the contractual source semantic and may point
to one declared underlying binding.

It stores no rate, amount, accrual factor, payment schedule, observed cash flow or
valuation result. In particular, a Sukuk distribution is not silently converted
into a UMI-03 coupon merely because both may produce periodic payments.

## 8. External Shari'ah evidence

`SukukExternalShariahEvidence` retains only:

- an extensible framework/standard code;
- opaque evidence reference;
- optional exact effective date.

No boolean `is_compliant`, approval decision, legal opinion, board decision,
religious ruling, source-document content or credential is stored.

```text
REFERENCE EXISTS
!= QORE HAS ADJUDICATED COMPLIANCE
```

## 9. Determinism and fail-closed composition

The UNR-019 composition boundary locally revalidates exact nested UMI-02 runtime
types because earlier family foundations use broader `isinstance` guards.

It rejects:

- `str`, UUID, date and int subclasses where exact primitive semantics matter;
- bool-as-int ordinals;
- mutable collections;
- empty underlying/leg sets;
- duplicate binding IDs;
- duplicate semantic underlying bindings;
- duplicate leg IDs or ordinals;
- self-underlying certificate identity;
- references to undeclared underlying bindings;
- reflective corruption detected on later `logical_values()` calls.

There is no implicit wall clock, UUID generation, mutable global registry or
provider lookup.

## 10. Explicit exclusions

UNR-019 does not implement or certify:

- Shari'ah jurisprudence or compliance determination;
- legal opinions or legal-entity/party authority;
- standalone Murabahah/Ijarah/Wakalah financing or liquidity structures;
- collateralized Murabahah;
- Islamic FX forwards;
- profit-rate or cross-currency hedging;
- syndicated financing;
- cash-flow, profit-share, rental or redemption calculation;
- coupon/accrual inference;
- market data or observed inputs;
- valuation methodology;
- provider/platform support;
- account/Risk authority;
- execution or payment instruction;
- settlement mutation;
- Production or real-capital authority.

The broader Shari'ah-compliant financing/liquidity/hedging inventory remains
explicitly open under `UMI13-UNR-022`.

## 11. Review gate

```text
IMPLEMENT
-> QORE CI
-> EXACT DIFF AUDIT
-> FREEZE BASE / HEAD / SYNTHETIC
-> DEEPSEEK EXPERT
-> IA ADJUDICATION
-> DEEPSEEK CODER
-> IA ADJUDICATION
-> CLAUDE CODE
-> IA ADJUDICATION
-> IA FINAL
-> EXPECTED-HEAD PROTECTED MERGE
-> VERIFY MERGE / MAIN
-> RECONCILE #363
```

No clean-pass claim exists before that sequence completes.
