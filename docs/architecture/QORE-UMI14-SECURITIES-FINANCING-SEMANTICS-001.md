# QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — UNR-013 R3 FULL-CLOSURE CORRECTION CANDIDATE — NOT CERTIFIED**

Tracker: #394  
Parent final audit: #363  
PR: #437  
Target: `UMI13-UNR-013` — `securities-financing`  
Certified starting baseline: `db83b106f3a5e7f30a788567dfa970a38b7a379a`  
Starting tree: `5b9c218a4fe3609b10e34b1cf8523cade0d10bbe`  
Current branch: `agent/qore-umi14-securities-financing-full-closure-013`

R1 and R2 are historical audit rounds. R1 failed on securities-lending compensation
completeness and security quantity basis. R2 closed quantity basis but failed on two
remaining D04 collisions: ambiguous securities-lending collateralization and ambiguous
compensation payment/reset timing. IA accepted both R2 defects in PR #437 comment
`5387855870`. The first R3 mutation invalidates all R2 SHA-bound evidence and requires a
new freeze, exact synthetic CI and serial Gate-C chain beginning again with DeepSeek
Expert.

This owner remains bounded to static D04 securities-financing product semantics. It does
not calculate, observe, execute, settle, value, schedule, custody, authorize Production or
operate real capital.

---

## 1. Gate-A authority

UMI-13 retained:

`UMI13-UNR-013 — securities-financing — repo/securities lending/margin lending — distinct SFT forms; no dedicated owner`.

Cash/money-market, generic derivative and loan/facility owners do not preserve the
specific bilateral security-transfer, repo, securities-lending and margin-lending static
contract structure required here.

**Adjudication:** `VERIFIED MATERIAL D04 GAP — BOUNDED CORRECTION REQUIRED`.

---

## 2. Additive surface

Exactly three files remain additive relative to the certified baseline:

1. `src/qore/infrastructure/securities_financing_semantics.py`
2. `tests/infrastructure/test_securities_financing_semantics.py`
3. `docs/architecture/QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001.md`

No certified pre-existing file is modified.

---

## 3. Reused authority

The owner reuses exact certified primitives only where their semantics match:

- `EconomicIdentityId` — canonical economic/security/currency/reference identity;
- `DayCountConventionCode` — contractual day-count qualification;
- `FinancialTenor` / `FinancialTenorUnit` — static financial tenor without fixed-seconds
  interpretation.

Imported instances are revalidated at the consuming boundary:

- exact imported type;
- exact nested UUID/code/int/enum material;
- no hostile subclass trust;
- no malformed exact-object trust.

There is no existing certified generic schedule-reference primitive in the current
baseline. R3 therefore introduces an owner-local opaque `SftScheduleReferenceId` backed by
an explicit exact UUID. It identifies retained external static schedule/terms material but
does not resolve or generate calendar dates.

`SCHEDULE REFERENCE != SCHEDULE ENGINE`

---

## 4. Owner-local value surface

R3 retains the R2 surface and adds:

- `SftScheduleReferenceId`;
- `SftCollateralizationMode`;
- `SftCompensationPaymentMode`;
- `SftCompensationResetMode`.

Existing owner-local values remain:

- `SftTermsId`;
- `SftEvidenceRef`;
- `SftPartyReferenceId`;
- `SftCollateralEligibilityCode`;
- `SftSecurityQuantityBasisCode`;
- `SftCompensationAccrualBasisCode`;
- `SftDurationMode`;
- `SftRateKind`;
- `SftArrangementMode`;
- `SftCashAmount`;
- `SftSecurityQuantity`;
- `SftRateTerms`;
- `SftDurationTerms`;
- `SftArrangementTerms`;
- `SftMarginTerms`;
- `RepoFarLegTerms`;
- `SecuritiesLendingCompensationLegTerms`;
- `SecuritiesLendingCompensationTerms`;
- `RepoTerms`;
- `SecuritiesLendingTerms`;
- `MarginLendingTerms`.

All semantic values remain frozen/slotted and deterministic. No implicit UUID, wall clock,
random value or external side effect is introduced.

---

## 5. Security quantity — R1/R2 closure retained

`SftSecurityQuantity` retains:

- security `EconomicIdentityId`;
- positive finite exact Decimal quantity;
- `SftSecurityQuantityBasisCode`.

Thus the same security and numeric magnitude remain distinguishable for contractual
`units` versus `nominal-amount` or another explicit provider-neutral basis code.

`DS-EXPERT-UNR013-R1-02` remains closed by R2/R3 unless a later auditor demonstrates a
new material collision.

---

## 6. Compensation rate material

`SftRateTerms` retains:

- fixed vs floating kind;
- contractual outright rate or spread;
- day-count convention;
- floating reference identity when required.

The owner does not observe the reference, calculate accrual, compound, price or resolve
reset dates.

---

## 7. Compensation payment timing — R3 correction

R2 used `payment_tenor: FinancialTenor | None`. `None` could not distinguish payment at
termination from payment governed by external static schedule material.

R3 adds explicit `SftCompensationPaymentMode`:

- `PERIODIC = "periodic"`;
- `AT_TERMINATION = "at-termination"`;
- `EXTERNAL_SCHEDULE = "external-schedule"`.

`SecuritiesLendingCompensationLegTerms` retains:

- `payment_mode`;
- optional `payment_tenor`;
- optional `payment_schedule_reference`.

Invariants:

### PERIODIC

- exact positive `FinancialTenor` required;
- schedule reference forbidden.

### AT_TERMINATION

- tenor forbidden;
- schedule reference forbidden.

### EXTERNAL_SCHEDULE

- exact `SftScheduleReferenceId` required;
- tenor forbidden.

Logical identity contains the mode, tenor if periodic, and external schedule reference if
external. Therefore periodic, at-termination and external-schedule contracts cannot
collapse merely because no generated dates are owned here.

`CONTRACTUAL PAYMENT MODE != GENERATED PAYMENT CALENDAR`

---

## 8. Floating compensation reset timing — R3 correction

R2 used optional `reset_tenor` and could not distinguish different static meanings of
absence. R3 adds `SftCompensationResetMode`:

- `PERIODIC = "periodic"`;
- `AT_PAYMENT = "at-payment"`;
- `EXTERNAL_SCHEDULE = "external-schedule"`;
- `REFERENCE_CONVENTION = "reference-convention"`.

Floating compensation requires one exact reset mode.

### PERIODIC

- exact positive reset tenor required;
- external schedule reference forbidden.

### AT_PAYMENT

- tenor and external schedule reference forbidden.

### EXTERNAL_SCHEDULE

- exact external schedule reference required;
- tenor forbidden.

### REFERENCE_CONVENTION

- means the retained floating reference's contractual convention is authoritative for
  reset timing;
- separate tenor and schedule reference are forbidden.

Fixed compensation must not carry any reset mode, tenor or reset schedule reference.

This is static qualification only. No reference observation or calendar resolution is
performed.

---

## 9. Securities-lending collateralization — R3 correction

R2 allowed `collateral=()` without a semantic discriminator. That allowed a genuinely
uncollateralized contract and an externally governed collateralized contract to share the
same D04 material.

R3 adds `SftCollateralizationMode`:

- `UNCOLLATERALIZED = "uncollateralized"`;
- `EXPLICIT = "explicit"`;
- `EXTERNAL_SCHEDULE = "external-schedule"`.

`SecuritiesLendingTerms` now retains:

- `collateralization_mode`;
- explicit collateral tuple;
- optional `collateral_schedule_reference`.

Invariants:

### UNCOLLATERALIZED

- explicit collateral tuple must be empty;
- external schedule reference forbidden.

### EXPLICIT

- explicit collateral tuple must be non-empty;
- external schedule reference forbidden.

### EXTERNAL_SCHEDULE

- exact `SftScheduleReferenceId` required;
- explicit collateral tuple may be empty or may additionally retain explicitly supplied
  static items;
- the external reference remains part of logical identity either way.

Therefore:

`UNCOLLATERALIZED != EXPLICIT COLLATERAL != EXTERNAL COLLATERAL SCHEDULE`

The mode/reference qualifies the static contract only. It does not own current collateral
positions, valuation, substitutions, custody or settlement movement.

---

## 10. Repo semantics

R3 preserves the R2 repo model:

- seller/buyer references;
- term/open/callable duration;
- near cash amount/currency;
- canonical non-empty transferred-security basket with quantity basis;
- financing rate;
- bilateral/tri-party arrangement;
- optional static margin/haircut material;
- contractual far-leg date and optional supplied far cash.

Term repo requires the far leg. Open repo forbids an invented far leg. Callable repo may
retain a far leg only when a contractual termination date exists and matches. Supplied far
cash currency must match near cash currency. No repurchase amount is calculated.

---

## 11. Margin-lending semantics

R3 preserves:

- lender/borrower;
- duration;
- positive contractual credit limit;
- financing rate;
- collateral eligibility code;
- canonical optional explicit eligible-collateral identity set;
- arrangement;
- optional static margin/haircut material.

No utilization, live balance, available credit, current collateral value, margin call or
liquidation authority is added.

---

## 12. Logical identity

Every top-level product begins with its product discriminant:

- `repo`;
- `securities-lending`;
- `margin-lending`.

R3 securities-lending logical material now includes:

- fee/rebate role;
- rate kind/value/day-count/floating reference;
- compensation currency;
- accrual basis;
- payment mode + tenor/reference;
- reset mode + tenor/reference when floating;
- collateralization mode + external schedule reference when applicable;
- explicit collateral items with quantity basis.

Required non-collapse witnesses include:

- periodic payment vs at-termination payment;
- periodic payment vs external schedule payment;
- periodic reset vs at-payment reset;
- periodic reset vs external schedule reset;
- reference-convention reset vs explicit reset modes;
- uncollateralized vs external-schedule collateralization with empty explicit tuple;
- explicit collateral vs external-schedule collateralization;
- units vs nominal-amount quantity basis.

Caller order remains non-economic and is canonicalized for repo security baskets,
securities-lending explicit collateral and margin-lending eligible identities.

---

## 13. Historical audit findings

### R1

DeepSeek Expert package: `UNR013-GATEC-R1-DS-EXPERT-01`.

Accepted:

1. `DS-EXPERT-UNR013-R1-01` — compensation static convention incomplete.
2. `DS-EXPERT-UNR013-R1-02` — security quantity basis absent.

R2 closed finding 02 but not finding 01 completely.

### R2

DeepSeek Expert package: `UNR013-GATEC-R2-DS-EXPERT-01`.

Accepted by IA in comment `5387855870`:

1. `DS-EXPERT-UNR013-R2-01` — collateralization mode/external reference absent.
2. `DS-EXPERT-UNR013-R2-02` — compensation payment/reset timing ambiguity.

R3 is specifically designed to close both without importing D05-D11 authority.

R1/R2 review outcomes are historical evidence only. They do not certify R3.

---

## 14. Exact-type and malformed-object boundary

Every composed owner-local/imported child is revalidated at the parent edge. Exact type
alone is not accepted as proof of valid internal state.

R3 extends the malformed-object matrix to:

- `SftScheduleReferenceId`;
- payment/reset mode fields;
- payment/reset tenors;
- external payment/reset schedule references;
- collateralization mode;
- external collateral schedule reference.

Hostile subclasses and reflectively malformed exact values must fail closed before logical
projection.

---

## 15. Decimal determinism

Exact finite `Decimal` remains mandatory. Subclasses are rejected.

Logical Decimal representation remains:

- context independent;
- signed-zero canonical;
- trailing-zero canonical;
- exact round-trip;
- compact for extreme exponents such as `1E+1000000` and `1E-1000000`.

No `Decimal.normalize()`-based logical identity is used.

---

## 16. Local correction validation before GitHub CI

The R3 candidate was exercised in an isolated local harness with exact-shaped stubs for
its imported primitives.

Result:

- 14 tests passed;
- owner source statements: 607;
- owner missed statements: 0;
- owner statement coverage: 100%;
- Python compilation/AST parsing passed.

This is pre-CI engineering evidence only. The repository-wide authoritative quality gate
remains GitHub QORE CI on the final PR synthetic object.

---

## 17. Authority map

| Material | Authority |
|---|---|
| Economic/security/currency/reference identity | UMI-02 / D04 |
| Day-count and static financial tenor | UMI-03 / D04 |
| Static SFT product terms and opaque schedule references | this UNR-013 owner |
| Observed market/collateral evidence | D05 |
| Calendar/date/schedule resolution | D06 |
| Accrual, cashflow, valuation, pricing | D07 |
| Holdings/current borrow/loan/collateral positions | D08 |
| Margin/risk/exposure/capacity | D09 |
| Orders/execution/transfer instructions | D10 |
| Settlement/custody/collateral movement/recall-return mutation | D11 |
| Legal/regulatory/master-agreement determinations | D22 |

---

## 18. Negative space

R3 contains no:

- provider/network I/O;
- generated payment/reset schedule;
- current market/collateral observation;
- accrual or cashflow calculation;
- pricing or collateral valuation;
- current SFT position/balance;
- margin call or liquidation;
- borrow availability/locate state;
- current utilization or available credit;
- manufactured payment operation;
- collateral substitution/rehypothecation operation;
- recall/return operation;
- custody or settlement mutation;
- execution/order submission;
- legal eligibility engine;
- implicit wall clock;
- implicit UUID/random generation;
- secrets/productive credentials;
- Production;
- real-capital authority.

`STATIC SCHEDULE REFERENCE != GENERATED SCHEDULE`

`STATIC COLLATERALIZATION MODE != CURRENT COLLATERAL STATE`

`STATIC COMPENSATION TIMING != CALCULATED CASHFLOW`

---

## 19. Gate status

R3 is a correction candidate only.

Required sequence after final HEAD is established:

`R3 QUALITY -> DIFF AUDIT -> R3 FREEZE -> EXACT POST-FREEZE SYNTHETIC CI -> DEEPSEEK EXPERT R3 -> IA -> DEEPSEEK CODER R3 -> IA -> CLAUDE CODE R3 -> IA -> IA FINAL FALSIFICATION -> READY -> PROTECTED EXPECTED-HEAD MERGE -> POST-MERGE VERIFY -> #394 CLOSE -> UMI-14 CONTINUE`

Any HEAD mutation after the future R3 freeze invalidates all R3 SHA-bound evidence and
requires a new audit round from DeepSeek Expert.

Current state at this document update:

- R1 = HISTORICAL;
- R2 = HISTORICAL after accepted defects and correction;
- R3 candidate = PRESENT;
- R3 repository-wide quality = PENDING;
- R3 freeze = NOT ESTABLISHED;
- R3 exact post-freeze CI = NOT ESTABLISHED;
- Gate-C external reviewers = HOLD until freeze + exact CI;
- Ready = NO;
- merge = NO;
- #394 = OPEN;
- UNR-013 / UMI-14 / PROGRAM D = NOT CLOSED.

Production remains CLOSED. Real capital remains NOT AUTHORIZED.
