# QORE-UMI14-INSURANCE-LINKED-RISK-TRANSFER-SEMANTICS-020

## Estado

**PROGRAM D / UMI-14 — UMI13-UNR-020 CANDIDATE — NO CERTIFICADA**

Tracker: #447  
Parent audit: #363  
Target: `UMI13-UNR-020` — fixed-income / structured / forwards-swaps-otc qualification

Implementation baseline: `f4e3f10f8f24724b1e94981b5dd989bd5d0e1c7a`  
Baseline tree: `35d61177c6200624a619835fce2e6f37be4f1852`  
Baseline Quality Gate: QORE CI #1429 — Ruff / Mypy / Pytest SUCCESS  
Predecessor governance integration: PR #446 — protected merge verified

No earlier moving `main` is implicitly authoritative.

This owner is static D04 semantics only. It does not observe an insurance event,
resolve a trigger, adjust a claim, run catastrophe/actuarial models, calculate an
expected loss or price, execute/settle a contract, map a provider, authorize Risk,
or enable Production/real capital.

---

## 1. Material gap

UMI-13 retained:

`UMI13-UNR-020 — insurance-linked risk-transfer / trigger semantics`

The gap spans existing families:

- `fixed-income-credit`;
- `structured-hybrid-products`;
- `forwards-swaps-otc`.

Insurance-linked risk transfer cannot be represented faithfully by any one of:

- ordinary principal/coupon/cash-flow terms;
- generic derivative notional/payoff structure;
- generic structured barrier terms;
- generic event-contract criterion/outcome/resolution terms.

The missing D04 owner is the explicit qualification connecting one existing
tradable economic identity to transferred insurance risk, contractual trigger
semantics, and declarative economic effect.

`EVENT CONTRACT != INSURANCE-LINKED RISK TRANSFER`

`TRIGGER TERMS != OBSERVED TRIGGER`

`ECONOMIC EFFECT TERMS != EFFECT EXECUTION`

---

## 2. Evidence boundary

The UMI-13 registry already retains external evidence references for this lane:

- `EXT-SEC-ILS-01`;
- `EXT-NAIC-ILS-01`;
- `EXT-SEC-ILS-TRIGGERS-01`;
- `EXT-SEC-ILS-DERIVATIVE-01`.

Those sources support, at minimum:

- catastrophe/event-linked securities;
- mortality, longevity and medical-claim-cost risk transfer;
- indemnity, parametric, industry-loss and modeled-loss trigger bases;
- hybrid triggers;
- event-linked derivative/swap forms.

The Core module retains only opaque evidence UUIDs. It performs no network lookup
and does not embed provider payloads or external source text.

---

## 3. Identity authority

UMI-02 remains the only economic identity authority.

`InsuranceLinkedRiskTransferTerms.instrument_identity` must be an exact
`EconomicIdentity` with:

- `kind == TRADABLE_INSTRUMENT`;
- family exactly one of the three qualified UMI-13 families;
- a non-`CONTINUOUS_REFERENCE` construction;
- valid nested identity/evidence values.

The owner never creates a second instrument identity, provider symbol, insurer
identity, sponsor identity or legal counterparty authority.

The risk subject is an opaque `InsuranceLinkedRiskSubjectRef`, which can represent
contractual books/exposures without claiming legal identity.

`RISK SUBJECT REF != LEGAL ENTITY IDENTITY`

---

## 4. Extensible risk and transfer-form codes

Risk types are canonical extensible codes, not a closed universal enum. This allows
the currently evidenced dimensions such as:

- `catastrophe`;
- `mortality`;
- `longevity`;
- `medical-claim-cost`;

while leaving future product-qualified risk types possible without changing a false
global taxonomy.

A contract may carry more than one risk type. The tuple is validated as a semantic
set, rejects duplicates, and is canonicalized by code.

Transfer form is also an extensible canonical code, permitting examples such as:

- `catastrophe-bond`;
- `event-linked-security`;
- `mortality-swap`;
- `longevity-swap`;
- `event-linked-derivative`.

`RISK TYPE != INSTRUMENT FAMILY`

`TRANSFER FORM != PROVIDER PRODUCT CODE`

---

## 5. Trigger components

Each trigger component retains:

- stable component UUID;
- trigger-basis code;
- trigger metric code;
- opaque risk-measure reference UUID;
- trigger source code;
- trigger rule code;
- evidence UUID;
- optional exact threshold;
- optional mathematical comparator;
- optional sequence ordinal.

A threshold consists of an exact finite `Decimal` plus an explicit unit code.

A threshold and comparator are paired:

- threshold present => comparator required;
- threshold absent => comparator absent.

This permits fixed-threshold terms without forcing formulaic mortality/longevity or
other index structures into a fake threshold representation.

`TRIGGER RULE CODE != COMPUTED TRIGGER RESULT`

`MEASURE REFERENCE != DATA FETCH`

`SOURCE CODE != PROVIDER CALL`

---

## 6. Single and hybrid trigger structure

`InsuranceLinkedTriggerStructureKind` is intentionally closed to:

- `SINGLE`;
- `HYBRID`.

SINGLE requires exactly one component, no combination rule and no sequence ordinal.

HYBRID requires at least two semantically distinct components and an explicit
combination-rule code.

Hybrid component order is not taken from caller tuple position.

If sequence is not contractually material, no component carries a sequence ordinal
and the component set is canonicalized by semantic key.

If sequence is contractually material, every component carries a positive explicit
sequence ordinal; mixed sequenced/unsequenced state and duplicate ordinals fail
closed.

This represents both unordered multi-trigger structures and the sequential hybrid
forms observed in retained evidence without inventing one universal ordering law.

`CALLER ORDER != CONTRACTUAL ORDER`

`EXPLICIT SEQUENCE != COLLECTION POSITION`

---

## 7. Declarative economic effects

Each `InsuranceLinkedEconomicEffect` retains:

- stable effect UUID;
- target code;
- action code;
- effect-rule code;
- optional fixed magnitude with explicit unit;
- evidence UUID.

Targets/actions remain extensible and can qualify terms such as:

- principal reduction;
- interest reduction/suspension;
- notional reduction;
- contingent payment.

The effect set is caller-order independent and rejects semantic duplicates.

This owner does not change any principal, notional, cash-flow or account state.
Existing fixed-income/derivative owners remain authoritative for their own economic
terms.

`DECLARED PRINCIPAL REDUCTION != PRINCIPAL MUTATION`

`CONTINGENT PAYMENT TERM != CASH SETTLEMENT`

---

## 8. Effective dates

The aggregate may retain `effective_from` and `effective_until` as exact `date`
values.

When both exist, `effective_until` cannot precede `effective_from`.

The owner does not use wall-clock time, infer currentness, schedule evaluation, or
resolve UMI-02 cross-revision precedence.

---

## 9. Determinism and fail-closed

All local values are frozen/slotted.

Aggregate boundaries use exact runtime types and recursively revalidate nested state.

The owner rejects:

- `bool` laundering into positive integers;
- `str` subclasses on canonical codes;
- non-finite Decimal values;
- duplicate UUID identities where uniqueness is required;
- semantic duplicate trigger components/effects;
- malformed or fabricated nested objects;
- corrupted frozen state surfaced through `logical_values()`.

`logical_values()` revalidates before emission and uses compact context-independent
Decimal canonicalization.

Input tuple order is canonicalized only where order has no contractual authority.
Material sequence requires explicit ordinal.

---

## 10. Authority exclusions

The module contains no authority to:

- observe catastrophe/weather/loss/mortality/longevity/medical-cost data;
- decide whether a trigger occurred;
- resolve a disputed trigger;
- adjust or approve claims;
- calculate indemnity;
- execute catastrophe, mortality or longevity models;
- price/discount/value/estimate expected loss;
- mutate principal, interest, notional or cash;
- access broker/provider APIs;
- submit or cancel orders;
- map provider capability;
- manage accounts or Risk;
- authorize Production or real capital.

Any future producer/evaluator must be a separate authoritative boundary.

---

## 11. Required cross-family proofs

The test surface must demonstrate without provider logic:

1. fixed-income catastrophe bond qualification;
2. structured event-linked security qualification;
3. OTC mortality/longevity derivative qualification;
4. medical-claim-cost risk qualification;
5. indemnity/parametric/industry-loss/modeled-loss trigger forms;
6. hybrid unordered and explicit-sequence forms;
7. formulaic trigger components without fabricated thresholds;
8. deterministic multi-risk/multi-subject/effect sets;
9. root-family and reference-object rejection;
10. fabrication/subclass/Decimal/date adversarial failures.

---

## 12. Closure meaning

If this lane passes its full independent review and protected integration gate, it
closes only the D04 semantic gap represented by `UMI13-UNR-020`.

It does not establish:

- universal ILS provider support;
- actuarial methodology;
- catastrophe-model correctness;
- legal/reinsurance compliance;
- valuation capability;
- executable settlement;
- QORE Universal Market Ready;
- Production readiness.

`D04 ILS SEMANTIC OWNER PASS != OPERATIONAL ILS SUPPORT`
