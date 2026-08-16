# QORE-UMI14 FX Static Contract Semantics

## Status

**PROGRAM D / UMI-14 LANE-4 PARALLEL CORRECTION CANDIDATE — INDEPENDENT CERTIFICATION REQUIRED**

Tracker: `#378`  
Target: `UMI13-UNR-006`  
Parallel implementation baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`  
Starting tree: `380140cd55ba7d90dcbd9e5fbb4944bdec9368d2`

This candidate may be implemented and tested in parallel while Lane 3 remains blocked at its
independent correction-review gate. It has no authority to merge ahead of Lane 3.

```text
PARALLEL CANDIDATE GREEN
!=
MERGE READY
```

After Lane 3 integrates, Lane 4 must synchronize to the then-current `main`, obtain a new exact
head, run new exact-head CI, receive independent review, pass Integration Gate and only then be
eligible for protected expected-head merge.

---

## 1. Purpose

This boundary adds provider-neutral **static FX contractual semantics** required to correct the
bounded D04 portion of `UMI13-UNR-006`.

It retains the structural economics needed to distinguish:

- an FX quoted pair from two unrelated currency identities;
- quotation direction from rate magnitude;
- spot FX from an outright forward;
- deliverable forward from NDF;
- one FX swap from two unrelated exchange legs;
- a generic option from an option explicitly bound to FX put/call currency amounts and an
  FX-consistent strike quotation.

It does not implement market observations, valuation, execution, accounts, risk, provider
capability or settlement mutation.

---

## 2. Evidence boundary

The implementation is based on the Integration-Gate adjudication recorded in tracker `#378`.
That adjudication independently qualified the exact repository baseline and relevant UMI-02 /
UMI-05 owner blobs, plus primary FpML/BIS product semantics.

This document is not an independent certification artifact. The candidate remains subject to:

```text
IMPLEMENTATION
-> EXACT DIFF AUDIT
-> QUALITY GATE
-> EXACT-HEAD FREEZE
-> INDEPENDENT REVIEW
-> INTEGRATION GATE
```

No class, green local test or CI result self-certifies semantic sufficiency.

---

## 3. Existing-owner reconstruction

### 3.1 UMI-02

`EconomicIdentityId` remains the sovereign attachment for an economic instrument or reference
object.

This lane does not create a new currency identity system and does not add a `CURRENCY` member to
UMI-02 identity kind.

```text
CURRENCY IDENTITY
!=
FX QUOTED PAIR
```

### 3.2 UMI-05

UMI-05 already owns generic derivative primitives, including `OptionContractTerms` and
`DerivativeStrike`.

That owner is reused where its semantics are exact. It is not copied into this module.

The exact UMI-05 generic forward/swap structures do not themselves retain a canonical two-currency
FX pair, two FX currency flows, deliverable/NDF qualification or a typed near/far FX-swap reversal
relationship. `OptionContractTerms` also does not retain FX put/call currency amounts.

UMI-05 `DerivativeStrike` does retain a `PRICE` strike's quote/reference identity and a
`DerivativePriceQuoteBasisCode`. Those dimensions are reused and mechanically bound to this
owner's canonical FX pair rather than duplicated.

Therefore this correction is additive and compositional rather than a replacement of UMI-05.

---

## 4. Quoted pair and quotation semantics

`FxQuotedCurrencyPair` retains:

- one pair `EconomicIdentityId` attachment;
- `currency1_identity_id`;
- `currency2_identity_id`;
- explicit `FxQuoteBasis`;
- retained evidence reference.

The currencies must differ and the pair identity must not be laundered into either currency role.

`FxQuoteBasis` explicitly distinguishes:

- `currency1-per-currency2` — amount of currency 1 for one unit of currency 2;
- `currency2-per-currency1` — amount of currency 2 for one unit of currency 1.

```text
QUOTE BASIS
!=
RATE MAGNITUDE
```

Opposite quote bases therefore remain distinct deterministic logical material even when all other
identities and magnitudes are equal.

The pair's evidence reference is provenance material. It is not itself the economic pair
relationship. Pair-relationship comparison uses pair identity, both ordered currency identities and
quote basis; independent evidence references may legitimately differ across enclosing artifacts.

```text
SAME FX PAIR RELATIONSHIP
!=
SAME EVIDENCE REFERENCE
```

---

## 5. Currency amount and exchange-flow semantics

`FxCurrencyAmount` retains a positive finite exact `Decimal` plus explicit currency
`EconomicIdentityId`.

`FxCurrencyFlow` qualifies that amount as `PAY` or `RECEIVE`.

A bounded FX exchange requires exactly two immutable flows:

- one `PAY`;
- one `RECEIVE`;
- exactly the two currencies declared by the quoted pair.

Caller tuple ordering is non-semantic and is canonicalized. Pay/receive role assignment is
semantic and is retained.

```text
FLOW ORDER
!=
PAY / RECEIVE ROLE
```

The module does not require the two currency amounts to be exactly derivable from the retained rate.
Doing so would introduce unapproved rounding or calculation rules into a static D04 contract.

---

## 6. Exchange-rate semantics

`FxExchangeRate` retains:

- a positive finite exact `Decimal`;
- the pair identity to which the rate belongs;
- the explicit quote basis.

Every enclosing spot, forward and swap leg verifies that both pair identity and quote basis match
its `FxQuotedCurrencyPair`.

This is an agreed contractual rate, not a D05 market observation.

```text
AGREED FX RATE
!=
CURRENT FX RATE OBSERVATION
```

---

## 7. Value-date semantics

`FxValueDates` retains a date for each currency role.

It deliberately supports:

- one common value date represented by equal dates;
- split currency value dates.

No `trade_date`, spot-lag rule, holiday calendar calculation or automatic T+2 assumption is added.
Those would require separate event/time authority.

---

## 8. Spot semantics

`FxSpotTerms` binds:

- local terms ID;
- FX instrument identity attachment;
- exact quoted pair;
- two canonicalized currency flows;
- currency-specific value dates;
- agreed exchange rate bound to that pair and quote basis;
- evidence.

The FX instrument identity must differ from the pair identity under this bounded owner. This is an
implementation qualification, not a claim about provider symbols or trade identifiers.

```text
SPOT FX
!=
OUTRIGHT FX FORWARD
```

The distinction is structural through separate types and deterministic logical prefixes; no
calendar heuristic decides the family.

---

## 9. Forward and NDF semantics

`FxForwardTerms` retains the same bounded FX exchange material plus explicit
`FxForwardDeliveryKind`:

- `DELIVERABLE`;
- `NON_DELIVERABLE`.

A deliverable forward must not carry NDF settlement terms.

A non-deliverable forward must carry `FxNonDeliverableSettlementTerms`, which retain:

- settlement currency identity;
- `FxFixingTerms`;
- optional settlement date;
- evidence.

`FxFixingTerms` retains only:

- fixing date;
- fixing-reference identity;
- evidence.

It contains no current or observed fixing value.

Where an explicit NDF settlement date is retained, fixing may not occur after settlement.

```text
FX FIXING TERMS
!=
CURRENT FX FIXING VALUE
```

No forward-points, discounting or settlement-amount calculation exists.

---

## 10. FX swap semantics

`FxSwapLegTerms` is the bounded FX exchange-leg structure reused by `FxSwapTerms`.

`FxSwapTerms` requires:

- explicit `near_leg` and `far_leg`;
- distinct leg IDs;
- the same canonical **quoted-pair relationship** on both legs;
- the same pair identity, ordered currencies and quote basis;
- the same two pair currencies on both legs;
- exact reversal of `PAY`/`RECEIVE` roles per currency;
- `far` currency-1 value date strictly after `near` currency-1 value date;
- `far` currency-2 value date strictly after `near` currency-2 value date.

Leg and aggregate pair evidence references may differ. Provenance-reference equality is not used as
a substitute for economic-pair equality.

No equal-notional rule is invented. Unequal near/far amounts remain representable.

```text
FX SWAP
!=
TWO UNRELATED FX EXCHANGE LEGS
```

A cross-currency interest-rate swap is not owned by this boundary merely because it references two
currencies.

```text
FX SWAP
!=
CURRENCY SWAP
```

Rates/OTC specialization remains outside this owner.

---

## 11. FX option binding

`FxOptionBinding` composes the certified UMI-05 `OptionContractTerms` rather than recreating generic
option right, exercise, strike, expiry, settlement style or sizing semantics.

It adds the missing FX-specific static material:

- exact quoted pair;
- put-currency amount;
- call-currency amount;
- optional static premium terms;
- evidence.

The generic option underlying identity must equal the `FxQuotedCurrencyPair.pair_identity_id`.
This provides a mechanical cross-owner binding instead of relying on caller convention.

The generic option strike is also mechanically bound to the same FX quotation:

- strike basis must be UMI-05 `PRICE`;
- for `currency1-per-currency2`, UMI-05 `quote_identity_id` must be currency 1;
- for `currency2-per-currency1`, UMI-05 `quote_identity_id` must be currency 2;
- UMI-05 `DerivativePriceQuoteBasisCode.value` must equal the canonical `FxQuoteBasis.value`.

This retains UMI-05 authority for strike magnitude and price-quote semantics while preventing an FX
option from binding a pair to a strike denominated or quoted under an unrelated relationship.

```text
FX OPTION UNDERLYING MATCH
!=
FX OPTION STRIKE MATCH
```

Both are independently validated.

Put and call currencies must differ and must cover exactly the two quoted-pair currencies.
Reversing put/call currency roles changes deterministic logical material.

```text
GENERIC CALL / PUT
!=
FX PUT / CALL CURRENCY AMOUNTS
```

No attempt is made to infer FX put/call direction solely from UMI-05 `OptionRight`.
No amount-to-strike arithmetic consistency rule is invented; this static owner performs no rounding
or valuation calculation.

---

## 12. Premium static boundary

`FxOptionPremiumTerms` retains only:

- positive contractual premium amount and currency identity;
- payment date;
- evidence.

The premium currency is not artificially constrained to the two quoted-pair currencies by this
minimum owner.

```text
FX PREMIUM TERMS
!=
PAYMENT MUTATION
```

D11 retains settlement/payment execution authority.

---

## 13. UNR-006 / UNR-007 boundary

This lane does not implement generic exotic-option payoff machinery.

Excluded here and owned by the later options qualification include:

- barrier payoff composition;
- digital/binary payoff semantics;
- Asian averaging semantics;
- lookback semantics;
- generic path-dependent event evaluation.

A later cross-family composition may bind generic exotic features to the FX pair/currency semantics
provided here. That does not move generic option-feature authority into UNR-006.

---

## 14. Rolling-financing exclusion

Rolling financing is explicitly outside this correction.

No owner is introduced for:

- rollover financing;
- CFD financing;
- swap-point accrual;
- account debit/credit financing;
- margin financing;
- PnL accrual.

Those concerns remain with their proper product/account/valuation/provider authorities.

---

## 15. D04 versus other authorities

| Dimension | Authority |
|---|---|
| quoted pair / quotation direction | D04 static semantics |
| contractual currency amount / exchange role | D04 static semantics |
| contractual value dates | D04 static semantics |
| agreed spot/forward/swap-leg rate | D04 static semantics |
| NDF fixing definition/reference | D04 static semantics |
| FX-option pair/strike quotation binding | D04 static semantics |
| current observed FX rate/fixing | D05 |
| business-calendar resolution | D06 |
| forward points / PV / valuation / PnL | D07 |
| account balance / position / financing | D08 |
| exposure / margin / risk | D09 |
| order / exercise / routing | D10 |
| cash/payment mutation and finality | D11 |
| provider product/symbol support | D03 |

Downstream capability does not become D04 authority by implication.

---

## 16. Determinism and safety

The module uses:

- `@dataclass(frozen=True, slots=True)` for local value objects and contracts;
- caller-supplied UUID-backed local artifact IDs;
- caller-supplied `EconomicIdentityId` references;
- exact finite `Decimal` magnitudes;
- immutable tuples;
- deterministic tuple canonicalization where caller order is non-semantic;
- deterministic `logical_values()`;
- typed `InfrastructureError`-derived validation failure.

It uses no:

- implicit UUID generation;
- wall-clock reads;
- randomness;
- global mutable state;
- network/provider SDK;
- database/filesystem runtime;
- looped retry/sleep/scheduler/thread authority;
- execution or settlement mutation.

---

## 17. Direct adversarial oracle matrix

The bounded test suite directly discriminates:

- same-currency pair rejection;
- pair-identity/currency-identity collision rejection;
- opposite quote-basis distinction;
- positive finite Decimal enforcement;
- immutable tuple requirement for flows;
- one-PAY/one-RECEIVE enforcement;
- third-currency flow rejection;
- caller-order canonicalization;
- pay/receive currency-role distinction;
- common and split value dates;
- spot rate pair mismatch;
- spot rate quote-basis mismatch;
- spot instrument/pair identity collision;
- spot versus forward distinction;
- deliverable versus NDF distinction;
- deliverable/NDF illegal-combination guards;
- NDF fixing chronology when settlement date is explicit;
- absence of current-fixing-value fields;
- valid near/far FX swap;
- non-reversing swap-role rejection;
- duplicate swap-leg ID rejection;
- independent far-date guards for each currency;
- swap pair mismatch;
- same economic swap pair with different evidence references remains representable;
- valid FX-option binding using a real UMI-05 option object;
- generic option underlying/pair mismatch rejection;
- non-PRICE FX-option strike rejection;
- FX-option strike quote-identity mismatch rejection;
- FX-option strike quote-basis mismatch rejection;
- same/third put-call currency rejection;
- put/call role reversal distinction;
- static premium shape;
- absence of prohibited runtime side-effect markers.

```text
GUARD EXISTS
!=
REGRESSION ORACLE EXISTS
```

The suite therefore gives each material guard a discriminating failure path rather than relying on
one broad exception test to mask multiple invariants.

---

## 18. Non-claims

This candidate does **not** establish:

- provider support;
- provider symbol mapping;
- executable FX;
- current market data;
- current fixing values;
- FX valuation;
- PnL;
- margin or account capacity;
- payment/settlement execution;
- Production readiness;
- real-capital authority;
- `UMI13-UNR-006` closure;
- UMI-14 PASS;
- Program-D PASS;
- QORE Universal Market Ready.

---

## 19. Mandatory UMI-12 future follow-up

Before final UMI-14 closure, the mandatory UMI-12 cross-asset conformance follow-up must be
revisited for an FX representative specimen and owner-module boundary:

- `tests/infrastructure/test_universal_cross_asset_conformance.py`;
- `tests/infrastructure/test_universal_cross_asset_conformance_guards.py`;
- `docs/architecture/QORE-UMI-12-CROSS-ASSET-CONFORMANCE-HARNESS-001.md`.

This Lane-4 bounded correction does not mutate those files now.

---

## 20. Integration law

This candidate starts from the historical parallel baseline while Lane 3 remains unmerged.

Before any final Lane-4 certification:

```text
LANE 3 INTEGRATION
-> SYNCHRONIZE LANE 4 TO NEW MAIN
-> NEW EXACT HEAD
-> NEW EXACT-HEAD CI
-> DIFF AUDIT
-> INDEPENDENT REVIEW
-> INTEGRATION GATE
-> PROTECTED EXPECTED-HEAD MERGE
-> POST-MERGE BASELINE VERIFICATION
```

No preparatory result bypasses that sequence.
