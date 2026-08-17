# QORE-UMI14 FX Static Contract Semantics

## Status

**PROGRAM D / UMI-14 LANE-4 PARALLEL CORRECTION CANDIDATE — INDEPENDENT CERTIFICATION REQUIRED**

Tracker: `#378`  
Target: `UMI13-UNR-006`  
Family: `fx`  
Parallel implementation baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`  
Starting tree: `380140cd55ba7d90dcbd9e5fbb4944bdec9368d2`

This artifact describes a bounded provider-neutral static FX semantic candidate.
It does not certify the candidate and grants no merge authority.

```text
PARALLEL CANDIDATE
!=
MERGE READY
```

Lane 3 / PR `#376` remains the upstream integration gate. After Lane 3 integrates,
this lane must synchronize to the then-current `main`, obtain a new exact head,
run new exact-head CI, receive independent review, pass Integration Gate and only
then become eligible for protected expected-head merge.

---

## 1. Purpose

The candidate closes the bounded D04 portion of `UMI13-UNR-006` by retaining
financially material FX contractual relationships that generic derivative terms
do not retain by themselves.

The owner distinguishes:

- one quoted currency pair from two unrelated currency identities;
- FX quotation direction from rate magnitude;
- contractual currency amounts and PAY/RECEIVE roles;
- spot FX from an outright FX forward;
- deliverable forward from NDF;
- an FX swap from two unrelated exchange legs;
- a generic option from an option explicitly bound to an FX pair and put/call
  currency amounts.

It implements no market-data, fixing-observation, pricing, execution, account,
risk, provider or settlement engine.

---

## 2. Evidence boundary

The implementation authority comes from tracker `#378`, which records the
Integration-Gate adjudication of the UMI-13 gap, the exact repository baseline
and primary FpML/BIS product evidence.

The candidate must still pass the normal QORE chain:

```text
IMPLEMENTATION
-> EXACT DIFF AUDIT
-> QUALITY GATE
-> EXACT-HEAD FREEZE
-> INDEPENDENT REVIEW
-> INTEGRATION GATE
```

A green CI result alone is not engineering approval.

---

## 3. Existing-owner audit

### 3.1 UMI-02 identity authority

`EconomicIdentityId` remains the sovereign identity attachment for economic
instruments and reference objects.

This lane does not create a second currency identity system and does not add a
`CURRENCY` member to `EconomicIdentityKind`.

```text
CURRENCY IDENTITY
!=
FX QUOTED PAIR
```

Local `FxTermsId`, `FxSwapLegId` and `FxEvidenceRef` identify semantic artifacts
or evidence references only.

```text
FX LOCAL ID
!=
ECONOMIC IDENTITY
```

### 3.2 UMI-05 derivative authority

UMI-05 remains authoritative for generic derivative structures including
`OptionContractTerms`, `DerivativeStrike`, exercise style, generic settlement
style, multiplier and notional.

The FX owner composes those types where their meaning is exact. It does not copy
the generic option system.

The inspected generic forward/swap structures do not retain a canonical
quoted-currency relationship, two FX currency flows, FX-specific NDF binding or
explicit near/far FX-swap reversal relationship. `OptionContractTerms` does not
retain FX put/call currency amounts.

Therefore an additive FX owner is required without changing UMI-02 or UMI-05.

---

## 4. Quoted-pair semantics

`FxQuotedCurrencyPair` retains:

- pair `EconomicIdentityId`;
- `currency1_identity_id`;
- `currency2_identity_id`;
- explicit `FxQuoteBasis`;
- evidence reference.

The two currency identities must differ. The pair identity must differ from both
currency identities.

`FxQuoteBasis` distinguishes:

- `currency1-per-currency2`;
- `currency2-per-currency1`.

Quotation direction is deterministic logical material.

```text
TWO CURRENCY IDS
!=
QUOTED FX PAIR

QUOTE DIRECTION
!=
RATE MAGNITUDE
```

Pair-relationship comparison uses pair identity, ordered currency identities and
quote basis. Evidence references are provenance and are deliberately excluded
from pair-relationship equality.

```text
SAME ECONOMIC PAIR RELATIONSHIP
!=
SAME EVIDENCE REFERENCE
```

---

## 5. Currency amount and flow semantics

`FxCurrencyAmount` retains a strictly positive finite exact `Decimal` and an
explicit currency `EconomicIdentityId`.

It is contractual amount material only.

```text
FX CONTRACTUAL CURRENCY AMOUNT
!=
ACCOUNT CASH BALANCE
```

`FxCurrencyFlow` adds an explicit `PAY` or `RECEIVE` role.

Each bounded FX exchange requires exactly two immutable flows:

- exactly one `PAY`;
- exactly one `RECEIVE`;
- exactly the two currencies of the quoted pair.

Caller tuple order is non-semantic and is canonicalized. PAY/RECEIVE assignment
is semantic and remains visible in `logical_values()`.

No universal arithmetic equality between the two amounts and the retained rate
is imposed; that would introduce unapproved rounding/calculation rules.

---

## 6. Exchange-rate semantics

`FxExchangeRate` retains:

- positive finite exact `Decimal` magnitude;
- pair identity;
- `FxQuoteBasis`.

Every spot, forward and FX-swap leg validates that its contractual rate is bound
to the same pair identity and FX quote direction as the enclosing quoted pair.

```text
AGREED FX CONTRACT RATE
!=
CURRENT FX MARKET OBSERVATION
```

No rate inversion, reciprocal calculation, cross-rate calculation or market
lookup is performed.

---

## 7. UMI-05 PRICE quote basis versus FX quote direction

The corrected boundary deliberately separates two different authorities:

- `DerivativePriceQuoteBasisCode` from UMI-05 describes the generic semantic
  basis of a PRICE strike;
- `FxQuoteBasis` describes which currency of the FX pair is quoted per the other.

They are not interchangeable strings.

```text
DerivativePriceQuoteBasisCode
!=
FxQuoteBasis
```

For the bounded FX-option composition, the explicit bridge is:

- UMI-05 strike basis must be `PRICE`;
- UMI-05 `price_quote_basis` must be the generic code `currency-per-unit`;
- the UMI-05 strike quote identity must be the price currency selected by the
  FX `FxQuoteBasis`;
- the generic option underlying identity must equal the FX pair identity.

The earlier preparatory implementation compared the free-form
`DerivativePriceQuoteBasisCode.value` directly to `FxQuoteBasis.value`. That
collapsed two semantic authorities and was rejected by Integration Gate even
though the exact-head CI was green.

A direct oracle now proves that a generic PRICE quote code such as
`currency1-per-currency2` is rejected rather than mistaken for the FX quote
direction.

---

## 8. Value-date semantics

`FxValueDates` retains one contractual date for each pair currency role.

It represents both:

- common value dates, by equal dates;
- split currency value dates.

No universal T+2 rule, trade-date field, business-day calculation or calendar
resolution is introduced.

```text
CONTRACTUAL FX VALUE DATE
!=
D06 CALENDAR RESOLUTION
```

---

## 9. Spot semantics

`FxSpotTerms` binds:

- local terms ID;
- economic/instrument identity attachment;
- quoted pair;
- two currency flows;
- value dates;
- agreed exchange rate;
- evidence.

The corrected owner does **not** impose a universal requirement that
`instrument_identity_id` differ from `quoted_pair.pair_identity_id`.

That inequality was present in an earlier preparatory candidate but had no
verified universal financial basis for spot. Rejecting equality could make a
legitimate model in which the quoted pair itself is the spot economic attachment
unrepresentable.

The field remains available for an enclosing identity model that uses a distinct
spot instrument identity, but equality is also representable.

No provider symbol or trade-event envelope is introduced.

---

## 10. Deliverable forward and NDF

`FxForwardTerms` retains:

- derivative instrument identity attachment;
- quoted pair;
- two FX currency flows;
- value dates;
- agreed forward exchange rate;
- explicit `FxForwardDeliveryKind`;
- evidence;
- optional NDF settlement terms only when the delivery kind is non-deliverable.

The explicit delivery kinds are:

- `DELIVERABLE`;
- `NON_DELIVERABLE`.

A deliverable forward rejects NDF settlement terms. A non-deliverable forward
requires them.

```text
DELIVERABLE FX FORWARD
!=
NDF

GENERIC CASH SETTLEMENT
!=
NDF BY IMPLICATION
```

---

## 11. NDF fixing binding

`FxFixingTerms` is a static fixing **definition**, not an observed fixing value.
It retains:

- fixing date;
- FX pair identity;
- FX quote basis;
- fixing reference identity;
- evidence.

`FxNonDeliverableSettlementTerms` retains:

- explicit settlement currency identity;
- fixing definition;
- optional settlement date;
- evidence.

The enclosing non-deliverable `FxForwardTerms` now fails closed unless the fixing
pair identity and FX quote basis exactly match the forward's quoted pair.

This correction prevents an otherwise structurally valid NDF from carrying a
fixing definition for an unrelated FX pair or the opposite quotation direction.

```text
FIXING REFERENCE
!=
FIXING VALUE

NDF FIXING DEFINITION
MUST BIND TO
NDF QUOTED PAIR
```

No current/observed fixing value has a slot in these contracts.

The settlement currency is retained explicitly and is not restricted by an
invented universal rule requiring it to equal one of the two pair currencies.

---

## 12. FX swap semantics

`FxSwapLegTerms` retains one bounded FX exchange leg:

- local leg ID;
- quoted pair;
- two currency flows;
- value dates;
- agreed exchange rate;
- evidence.

`FxSwapTerms` explicitly retains `near_leg` and `far_leg` and requires:

- distinct near/far leg IDs;
- the same economic quoted-pair relationship on both legs;
- opposite PAY/RECEIVE roles for each currency;
- each far value date strictly later than its comparable near value date.

It does **not** require equal near/far amounts or equal exchange rates.

```text
FX SWAP
!=
TWO UNRELATED EXCHANGE LEGS

FX SWAP
!=
CURRENCY SWAP
```

Periodic cross-currency interest-rate swap semantics remain outside this owner.

---

## 13. FX option binding

`FxOptionBinding` composes certified generic UMI-05 `OptionContractTerms` with:

- exact quoted FX pair;
- explicit put-currency amount;
- explicit call-currency amount;
- optional static premium terms;
- FX evidence.

The put and call amounts must use different currencies and together cover exactly
the two currencies of the quoted pair.

The generic option underlying must equal the quoted-pair economic identity.
The generic strike must satisfy the corrected UMI-05/FX bridge described in
Section 7.

Opposite put/call currency assignments therefore remain distinct logical
material.

```text
GENERIC CALL / PUT
!=
FX PUT / CALL CURRENCY AMOUNTS
```

Barrier, digital, Asian, lookback and other generic exotic payoff semantics are
not implemented here. They are handled by the separate `UMI13-UNR-007` lane and
may later compose with this FX-specific binding.

---

## 14. Premium boundary

`FxOptionPremiumTerms` retains only:

- contractual currency amount;
- contractual payment date;
- evidence reference.

It performs no payment or account mutation.

```text
OPTION PREMIUM TERMS
!=
PAYMENT EXECUTION
```

No universal restriction forces premium currency to one of the pair currencies.

---

## 15. Provider-neutrality

Canonical FX logical material contains no:

- provider symbol such as `EUR_USD`;
- venue-specific instrument code;
- provider SDK type;
- provider availability claim;
- credential;
- network endpoint.

```text
PROVIDER SYMBOL
!=
CANONICAL FX PAIR
```

Provider mapping/capability remains D03 authority.

---

## 16. D04 versus downstream authorities

This owner retains static product semantics only.

| Dimension | Authority |
|---|---|
| quoted pair / currency roles | D04 |
| agreed contractual rate | D04 |
| contractual value/fixing dates | D04 static terms |
| NDF fixing definition | D04 |
| current FX rate / current fixing value | D05 |
| calendar resolution | D06 |
| valuation / PnL / forward points | D07 |
| balances / positions | D08 |
| margin / exposure | D09 |
| order / exercise execution | D10 |
| payment / settlement mutation | D11 |
| provider symbol / availability | D03 |

No downstream capability gap is used to justify a false D04 authority.

---

## 17. Explicit exclusions

This lane does not implement:

- rolling/overnight financing;
- CFD financing;
- swap-point accrual;
- current rates or fixings;
- cross-rate calculation;
- pricing or valuation;
- PnL;
- Greeks;
- account balances;
- margin/risk;
- execution;
- payment/settlement mutation;
- provider capability;
- generic exotic option payoff machinery;
- currency-swap periodic interest legs.

Rolling financing remains outside this correction and may be classified under
CFD/provider/account/valuation authorities as separately adjudicated.

---

## 18. Determinism and security

The owner uses:

- frozen/slotted dataclasses;
- caller-supplied UUID-backed local IDs;
- exact finite `Decimal` financial magnitudes;
- exact `date` contractual dates;
- immutable tuples;
- deterministic canonical ordering where caller order is non-semantic;
- deterministic `logical_values()`;
- typed validation errors.

It contains no implicit UUID generation, wall clock, random source, mutable global
state, network, database, scheduler, thread, provider SDK or secret material.

---

## 19. Integration-Gate correction ledger

The exact preparatory head `d53bc63cae2ee32439cf44a28e6ea39b3916d516`
passed QORE CI #1145 but was not accepted as a frozen engineering candidate.
Integration Gate identified three post-CI semantic defects/overconstraints:

### FX-IG-001 — generic PRICE quote-basis authority collapse

The candidate required
`DerivativePriceQuoteBasisCode.value == FxQuoteBasis.value`.

Consequence: two distinct semantic authorities were conflated through string
coincidence.

Correction: explicit generic UMI-05 `currency-per-unit` PRICE basis plus a
separate FX direction/quote-identity binding.

### FX-IG-002 — NDF fixing pair/direction not mechanically bound

The candidate retained fixing date/reference but did not prove that the fixing
was for the same FX pair and quotation direction as the NDF.

Consequence: an unrelated-pair fixing definition could be attached to an
otherwise valid NDF.

Correction: `FxFixingTerms` now retains pair identity + `FxQuoteBasis`, and the
NDF parent validates both.

### FX-IG-003 — unsupported spot identity inequality

The candidate universally rejected
`FxSpotTerms.instrument_identity_id == quoted_pair.pair_identity_id`.

Consequence: a valid representation using the pair identity as the spot economic
attachment could be rejected without financial evidence.

Correction: the universal inequality was removed for spot only. Forward/swap
instrument identities retain their distinct derivative-instrument role.

```text
CI GREEN
!=
ENGINEERING APPROVAL
```

CI #1145 is therefore historical evidence only. The corrected head requires a
new exact-head quality gate.

---

## 20. Direct adversarial oracle matrix

The dedicated test suite directly exercises at least:

- same currency on both pair sides rejected;
- pair identity / currency identity collision rejected;
- opposite FX quote directions are distinct;
- non-positive / non-finite / non-Decimal amounts rejected;
- flow tuple immutability;
- exactly one PAY + one RECEIVE;
- third flow currency rejected;
- caller flow order canonicalized without losing role semantics;
- common and split value dates representable;
- `datetime` rejected where exact `date` is required;
- spot rate pair mismatch rejected;
- spot rate quote-direction mismatch rejected;
- spot pair identity usable as spot instrument attachment;
- spot versus forward remain distinct;
- deliverable versus NDF remain distinct;
- NDF settlement required only for NDF;
- fixing after explicit NDF settlement date rejected;
- NDF fixing pair mismatch rejected;
- NDF fixing FX quote-direction mismatch rejected;
- fixing terms expose no observed/current value slot;
- FX swap requires reverse roles;
- near/far IDs distinct;
- each far currency value date after near;
- FX swap pair mismatch rejected;
- same pair with independent evidence refs accepted;
- real `OptionContractTerms` used for option composition;
- option underlying/pair mismatch rejected;
- non-PRICE strike rejected;
- FX quote identity mismatch rejected;
- generic PRICE quote basis other than `currency-per-unit` rejected;
- an FX-direction code masquerading as generic PRICE quote basis rejected;
- reversed FX quote direction selects the opposite price currency while retaining
  generic `currency-per-unit` semantics;
- put/call currency duplication or foreign third currency rejected;
- reversing put/call roles changes logical material;
- premium remains static contractual material;
- prohibited runtime side-effect markers absent.

Each material correction has a discriminating regression oracle.

```text
GUARD EXISTS
!=
REGRESSION ORACLE EXISTS
```

---

## 21. UNR-006 / UNR-007 boundary

This lane owns FX-specific pair, currency-flow and settlement bindings.
It does not own generic barrier/digital/Asian/path-dependent payoff logic.

```text
FX-SPECIFIC CURRENCY BINDING
!=
GENERIC EXOTIC OPTION FEATURE
```

The separate options lane may later compose generic exotic features with this
FX owner without duplicating quoted-pair authority.

---

## 22. Mandatory UMI-12 carry-forward

Before final UMI-14 closure, the mandatory UMI-12 cross-asset conformance
follow-up remains required in:

- `tests/infrastructure/test_universal_cross_asset_conformance.py`;
- `tests/infrastructure/test_universal_cross_asset_conformance_guards.py`;
- `docs/architecture/QORE-UMI-12-CROSS-ASSET-CONFORMANCE-HARNESS-001.md`.

This lane does not mutate those files.

---

## 23. Integration order

The required sequence remains:

```text
LANE 3 / PR #376 INTEGRATES
-> VERIFY NEW MAIN
-> SYNC LANE 4 TO NEW MAIN
-> NEW LANE-4 SHA
-> NEW EXACT-HEAD CI
-> EXACT DIFF AUDIT
-> INDEPENDENT REVIEW
-> INTEGRATION GATE
-> EXPECTED-HEAD MERGE
-> POST-MERGE VERIFICATION
```

Any CI obtained before the upstream synchronization is preparatory evidence only.

---

## 24. Non-claims

```text
FX STATIC SEMANTICS
!=
PROVIDER SUPPORT

FX STATIC SEMANTICS
!=
CURRENT MARKET DATA / FIXING

FX STATIC SEMANTICS
!=
VALUATION / PNL

FX STATIC SEMANTICS
!=
RISK / MARGIN

FX STATIC SEMANTICS
!=
ACCOUNT BALANCE

FX STATIC SEMANTICS
!=
EXECUTION

FX STATIC SEMANTICS
!=
PAYMENT / SETTLEMENT MUTATION

FX STATIC SEMANTICS
!=
PRODUCTION READINESS

FX STATIC SEMANTICS
!=
REAL-CAPITAL AUTHORITY

LANE-4 CANDIDATE
!=
UNR-006 CLOSED

UNR-006 INTEGRATED
!=
UMI-14 PASS

UMI-14 PASS
!=
QORE UNIVERSAL MARKET READY
```
