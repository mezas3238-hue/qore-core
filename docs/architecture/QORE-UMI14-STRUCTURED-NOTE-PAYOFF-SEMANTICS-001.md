# QORE-UMI14-STRUCTURED-NOTE-PAYOFF-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — UNR-011 GATE-B ADDITIVE CORRECTION CANDIDATE**

Tracker: #434  
Parent final audit: #363  
Universal Markets / Instruments program: #301  
Target: `UMI13-UNR-011`  
Certified starting baseline: `4ba5ccfcad890350729e57783755391c33cdaa8a`  
Starting tree: `ee86de15976c1ee13a15e7bcb16275a853fa79d0`

This record defines the bounded D04 correction for product-specific structured-note conditional payoff qualification. It does not claim Gate C, certification, Ready, merge, UNR-011 closure, UMI14 closure, Program-D closure, Production, provider support, legal suitability, or real-capital authority.

---

## 1. Gate-A finding

The current UMI-13 unresolved ledger retains:

```text
UMI13-UNR-011
family = structured-hybrid-products
gap = product-specific note / securitized payoff variants
reason = composition framework != every legal/payoff contract
```

Current UMI-09 already provides the correct static feature owners for capital protection, conversion/exchange, barriers, autocall trigger/redemption, participation/inverse participation, redemption, exact UMI-02 component relationships, and deterministic `StructuredHybridSyntheticTerms`.

Those feature contracts are certified owner material and are reused byte-for-byte. They are not duplicated or weakened by this correction.

The remaining gap is a relation gap. `StructuredHybridSyntheticTerms` retains a canonical collection of independent features, but it does not state which static condition selects which static outcome, how multiple conditions combine, which branch has contractual precedence, or which outcome is the final fallback.

```text
FEATURE SET != CONDITIONAL PAYOFF MAP
BARRIER EXISTS != BARRIER SELECTS THIS OUTCOME
OUTCOME FEATURES EXIST != OUTCOME PRECEDENCE EXISTS
```

A consumer cannot infer those relations without introducing an out-of-band payoff interpreter. That is the semantic loss this bounded owner prevents.

---

## 2. Primary product evidence

Gate-A falsification used official SEC-filed structured-note pricing material.

Morgan Stanley Trigger PLUS material filed in 2026 retains separate maturity branches: an upside branch with principal plus leveraged upside; a principal branch above a downside threshold; and a downside performance branch below that threshold.

Evidence:
`https://www.sec.gov/Archives/edgar/data/0000895421/000183988226026348/ms15849_424b2-17307.htm`

A multi-underlier filing conditions results on all underliers clearing thresholds and otherwise uses the worst-performing underlier.

Evidence:
`https://www.sec.gov/Archives/edgar/data/895421/000183988226026019/ms16303_424b2-17159.htm`

SEC-filed reverse-convertible material also demonstrates a path/threshold condition that can change maturity delivery from cash principal to linked shares.

Evidence:
`https://www.sec.gov/Archives/edgar/data/19617/000089109209003364/e36383fwp.pdf`

These filings prove contract shape only. They are not QORE provider support, valuation authority, legal/suitability authority, or permission to execute.

---

## 3. Authority map

```text
ECONOMIC IDENTITY / RELATIONSHIPS                    -> UMI-02 / D04
FIXED / ORDINARY COUPON ECONOMICS                    -> UMI-03
GENERIC DERIVATIVE PRIMITIVES                         -> UMI-05
STRUCTURED FEATURES + COMPONENT BINDINGS              -> UMI-09
CONDITIONAL STRUCTURED-NOTE PAYOFF QUALIFICATION      -> THIS UNR-011 OWNER
OBSERVED MARKET / BARRIER STATE                       -> D05
CALENDAR / SCHEDULE RESOLUTION                        -> D06
CURRENT VALUE / PAYOFF METHODOLOGY / CALCULATION      -> UMI-10 / D07
POSITIONS / COLLATERAL / RISK                         -> D08 / D09
ORDER / EXECUTION                                     -> D10 / D18
REDEMPTION / CONVERSION / DELIVERY / SETTLEMENT       -> D11
LEGAL / COMPLIANCE / SUITABILITY                      -> D22
```

Hard distinctions:

```text
STRUCTURED-NOTE PAYOFF TERMS != PAYOFF CALCULATION
CONTRACTUAL CONDITION != OBSERVED CONDITION STATE
BARRIER SPECIFICATION != BARRIER EVENT DETECTION
FIRST-MATCH BRANCH ORDER != RUNTIME EVALUATION ENGINE
OUTCOME QUALIFICATION != CASH / SECURITY DELIVERY
CONVERSION OUTCOME != CONVERSION EXECUTION
REDEMPTION OUTCOME != PAYMENT FINALITY
PARTICIPATION TERMS != CURRENT VALUE / RETURN
STRUCTURED NOTE != LEGAL / SUITABILITY DETERMINATION
SEC FILING EXISTS != PROVIDER SUPPORT
```

---

## 4. Additive owner surface

The candidate introduces exactly one new production module:

`src/qore/infrastructure/structured_note_payoff_semantics.py`

It imports and composes exact UMI-09 owner types. Existing UMI-09, UMI-03, UMI-05, UMI-02 and registry source files remain unchanged.

### 4.1 Local IDs

`StructuredNotePayoffTermsId` and `StructuredNotePayoffBranchId` are explicit exact-UUID-backed local identities. They are not economic instrument identities, order IDs, event IDs or settlement IDs. No implicit UUID generation exists.

### 4.2 Condition combination

`StructuredNoteConditionMode` has exactly `ALL` and `ANY`.

A conditional branch carries a non-empty immutable set-like tuple of exact UMI-09 `StructuredFeatureId` values. At top-level validation, every condition ID must resolve to an actual `StructuredBarrierFeature` contained in the bound `StructuredHybridSyntheticTerms`.

The condition-ID collection is canonicalized by stable UUID text. This ordering is deterministic material only; it is not evaluation precedence.

An unconditional branch carries:

```text
condition_mode = None
condition_feature_ids = ()
```

and is the explicit fallback.

### 4.3 Bounded outcome forms

`StructuredNoteOutcomeKind` is deliberately finite:

- `REDEMPTION`;
- `REDEMPTION_WITH_PARTICIPATION`;
- `PARTICIPATION`;
- `CONVERSION`.

`StructuredNotePayoffOutcome` contains only the exact UMI-09 feature IDs required by its kind. Invalid combinations fail closed.

At top-level validation, redemption IDs must resolve to `StructuredRedemptionFeature`; participation IDs to `StructuredParticipationFeature`; and conversion IDs to `StructuredConversionFeature`.

The new owner therefore establishes the missing conditional relation without creating a second redemption, participation or conversion contract.

This bounded set preserves common maturity shapes such as:

```text
condition -> redemption
condition -> redemption + participation
condition -> participation
condition -> conversion
else      -> one bounded outcome
```

It is not an arbitrary mathematical expression language.

### 4.4 Ordered branches

Every `StructuredNotePayoffBranch` has an explicit strict positive `ordinal`. `bool` is rejected.

At top level:

- branch IDs are unique;
- branch ordinals are unique;
- ordinals are contiguous `1..N`;
- branches canonicalize by ordinal;
- conditional signatures are unique;
- exactly one fallback exists;
- fallback is last.

This represents contractual first-match precedence while performing no runtime condition evaluation.

```text
BRANCH ORDINAL = CONTRACTUAL PRECEDENCE MATERIAL
BRANCH ORDINAL != OBSERVED OUTCOME
```

### 4.5 Top-level terms

`StructuredNotePayoffTerms` binds a local payoff terms ID, the exact complete `StructuredHybridSyntheticTerms`, the ordered branch tuple, and an evidence reference.

The complete nested UMI-09 logical material is retained in the payoff terms logical identity. This prevents a payoff map from remaining logically identical if the exact underlying component/feature contract changes.

---

## 5. Product-shape examples

A trigger/threshold note can retain statically:

```text
1: initial-level barrier satisfied
   -> REDEMPTION_WITH_PARTICIPATION
2: downside-threshold barrier satisfied
   -> REDEMPTION
3: fallback
   -> PARTICIPATION
```

For multiple references, one branch may bind multiple barrier IDs with `ALL` or `ANY` without introducing a general Boolean expression language.

A bounded reverse-convertible maturity structure can retain:

```text
1: contractual barrier condition
   -> CONVERSION
2: fallback
   -> REDEMPTION
```

The branch map does not determine that the barrier actually occurred and does not perform share delivery. D05 supplies observed condition state; D11 owns conversion/delivery mutation.

UMI-09 `StructuredAutocallFeature` already couples contractual autocall trigger specification with a redemption ratio. This correction does not duplicate autocall semantics.

---

## 6. Coupon boundary

UMI-03 remains the fixed-income coupon owner. This candidate neither duplicates fixed/floating coupon terms nor turns a structured-note branch into a cash-flow scheduler.

```text
MATURITY OUTCOME BRANCH != COUPON SCHEDULE
```

Conditional-coupon extensions are not silently inferred by this bounded maturity-outcome owner and require separate evidence/governance if later material.

---

## 7. Determinism and fail-closed rules

All new dataclasses are frozen and slotted. The candidate uses explicit caller-supplied IDs, exact UUID local IDs, strict positive branch ordinals, immutable tuples, canonical condition-ID order, canonical branch order, explicit fallback, exact typed UMI-09 feature resolution, and deterministic nested logical material.

There is no `datetime.now()`, `date.today()`, `uuid4()`, random source, mutable global state, retry loop, sleep, thread, scheduler, network or database I/O.

---

## 8. No executable payoff DSL

The source contains no formula/expression payload, callback/callable, AST, `eval`, `exec`, script, mutable parameter dictionary, arbitrary arithmetic operator tree, price observation, trigger evaluator, or payoff calculator.

The finite outcome enum is a semantic taxonomy, not an interpreter.

---

## 9. Gate-B tests

Primary tests:
`tests/infrastructure/test_structured_note_payoff_semantics.py`

They cover trigger-note and reverse-convertible shapes, multi-reference condition material, local UUID guards, strict ordinal/type/collection guards, fallback invariants, outcome-kind feature-shape rules, branch identity/ordinal/signature rules, exact UMI-09 condition/outcome type resolution, and deterministic caller-order canonicalization.

Independent logical oracle:
`tests/infrastructure/test_structured_note_payoff_semantics_logical_identity.py`

Expected material is manually reconstructed from primitive fixture constants. The expected side does not call SUT `.logical_values()`, production sort helpers, production enum `.value`, or actual output.

It protects exact dataclass field surfaces; local ID material; all four outcome projections; conditional/fallback branch projection; condition-set/branch-order canonicalization; and complete nested UMI-09 + UNR-011 top-level logical material.

---

## 10. Negative space

This owner grants no authority for current price/index/level observation; barrier/trigger/event detection; payoff evaluation; return/P&L/NAV/valuation calculation; probability/scenario/risk calculation; provider/broker/exchange/chain APIs; account/position/collateral state; wallet/custody/signing; order submission/cancel; early-redemption execution; conversion/share delivery; cash/position/settlement mutation; legal/security/suitability determination; Production; or real capital.

---

## 11. Gate state

```text
GATE A = COMPLETE / CONSUMED
GATE B = AUTHORIZED / ACTIVE
GATE C = NOT AUTHORIZED
GATE D = NOT AUTHORIZED
GATE E = NOT AUTHORIZED
GATE F = NOT AUTHORIZED
TRACKER #434 = OPEN
PR = NOT CREATED
READY = NOT AUTHORIZED
MERGE = NOT AUTHORIZED
UNR-011 = NOT CLOSED
UMI14 = NOT CLOSED
PROGRAM D = NOT DECLARED CLOSED
PRODUCTION = CLOSED
REAL CAPITAL = NOT AUTHORIZED
```

`GATE B CORRECTION != GATE C AUTHORIZATION`

`AUTHORIZATION NEVER PROPAGATES`
