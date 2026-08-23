# QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — UNR-013 R2 FULL-CLOSURE CORRECTION CANDIDATE — NOT CERTIFIED**

Tracker: #394  
Parent final audit: #363  
PR: #437  
Target: `UMI13-UNR-013` — `securities-financing`  
Certified starting baseline: `db83b106f3a5e7f30a788567dfa970a38b7a379a`  
Starting tree: `5b9c218a4fe3609b10e34b1cf8523cade0d10bbe`  
Current branch: `agent/qore-umi14-securities-financing-full-closure-013`

The historical preparatory branch
`agent/qore-umi14-securities-financing-semantics-013` remains provenance only. Its
implementation is not integration authority. The first current-baseline Gate-C candidate
was frozen as R1, reviewed by DeepSeek Expert, failed financial-semantic falsification,
and was invalidated when the accepted defects were corrected. R2 is therefore a new
candidate and requires a completely new freeze, exact synthetic CI, and serial review
chain beginning again with DeepSeek Expert.

This owner remains bounded to static D04 product-definition semantics for repo,
securities lending and margin lending. It does not authorize current SFT positions,
collateral valuation, margin calls, custody, settlement, execution, legal eligibility,
provider support, Production or real capital.

---

## 1. Gate-A reconstruction

UMI-13 retained:

`UMI13-UNR-013 — securities-financing — repo/securities lending/margin lending — distinct SFT forms; no dedicated owner`.

Cash/money-market semantics do not preserve bilateral security transfer and repurchase
roles. Generic derivative contracts are not a substitute for securities-financing
contracts. Commercial loan/facility semantics own credit-facility structure, not repo or
securities-lending economics.

**Adjudication:** `VERIFIED MATERIAL D04 GAP — BOUNDED CORRECTION REQUIRED`.

---

## 2. Financial non-conflation

The bounded owner preserves these distinctions:

1. repo != term deposit or generic secured loan;
2. repo near transfer != far repurchase transfer;
3. term repo != open/callable repo;
4. transferred repo security != current collateral valuation/state;
5. security quantity in units != security nominal/face amount;
6. securities-lending principal security != collateral role;
7. securities-lending fee != cash-collateral rebate;
8. compensation rate != compensation accrual/payment convention;
9. securities lending != repo;
10. margin-lending contractual credit limit != current drawn balance or availability;
11. bilateral != tri-party arrangement;
12. contractual haircut/initial margin != current margin calculation.

FpML securities-financing structures are evidence for retaining quantity basis and
contractual compensation conventions. They do not grant provider, valuation, execution,
settlement or legal authority.

---

## 3. Additive surface

Exactly three files are added relative to the certified baseline:

1. `src/qore/infrastructure/securities_financing_semantics.py`
2. `tests/infrastructure/test_securities_financing_semantics.py`
3. `docs/architecture/QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001.md`

No certified pre-existing source, test or architecture file is modified.

---

## 4. Reused authority

The owner reuses certified primitives only where their semantics are exact:

- `EconomicIdentityId` from UMI-02 for economic/security/currency/reference identity;
- `DayCountConventionCode` from UMI-03 for contractual day-count qualification;
- `FinancialTenor` / `FinancialTenorUnit` from UMI-03 for provider-neutral static
  payment/reset tenor qualification.

Imported instances are not trusted merely because `isinstance` would succeed. The
consumer requires exact imported types and revalidates the nested primitive state used
by this owner:

- `EconomicIdentityId.value` must be exact `UUID`;
- `DayCountConventionCode.value` must be canonical exact `str`;
- `FinancialTenor.value` must be positive exact `int`;
- `FinancialTenor.unit` must be exact `FinancialTenorUnit`.

`IMPORTED CERTIFIED TYPE != AUTOMATIC TRUST OF MALFORMED INSTANCE`

The owner does not reuse account-balance money, risk margin, settlement instructions,
provider-native identifiers or current observations.

---

## 5. Owner-local values

The R2 candidate defines:

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

All semantic values are frozen and slotted. No UUID, timestamp, current observation or
random value is created implicitly.

---

## 6. Exact-type and malformed-object boundary

Every composition edge uses exact-type validation.

Exact type alone is insufficient because an exact frozen/slotted instance can be
manufactured using `object.__new__` and reflective slot assignment without constructor
validation. Every parent therefore revalidates the internal primitive state of each
local and imported child before accepting or projecting it.

R2 extends this rule to:

- `SftSecurityQuantityBasisCode` inside `SftSecurityQuantity`;
- `SftCompensationAccrualBasisCode` inside compensation legs;
- `SftRateTerms` inside compensation legs;
- `FinancialTenor` and nested `FinancialTenorUnit` inside compensation legs.

Tests construct malformed exact instances and hostile subclasses to falsify these
boundaries.

`TYPE MATCH != VALID LOCAL STATE`

---

## 7. Decimal determinism and resource scaling

All numeric contract material requires exact finite `Decimal`; Decimal subclasses are
rejected before behavior is trusted.

Logical identity uses an owner-local canonical Decimal representation that:

- maps signed zero to `"0"`;
- removes coefficient trailing zeroes;
- is independent of ambient Decimal precision/context;
- round-trips exactly;
- keeps extreme exponents compact instead of expanding fixed-point strings in
  proportion to exponent magnitude.

Regression examples include `1E+1000000` and `1E-1000000`.

No `Decimal.normalize()` result is used for logical identity.

---

## 8. Security quantity and quantity basis — R2 correction

`SftSecurityQuantity` retains:

- exact `EconomicIdentityId` for the security;
- positive exact finite Decimal quantity;
- exact `SftSecurityQuantityBasisCode`.

The quantity basis is provider-neutral canonical code material such as `units` or
`nominal-amount`. It does not encode provider lot size or execution quantity.

R1 stored only `(security identity, quantity)`. That permitted contracts containing the
same security and numeric magnitude but different contractual denomination bases to
collapse into one logical identity. DeepSeek Expert finding
`DS-EXPERT-UNR013-R1-02` demonstrated the missing dimension. IA accepted the defect with
one refinement: the valid collision is not that one EconomicIdentityId magically changes
instrument family; the material distinction is number of units versus nominal/face
amount for the same referenced security.

R2 projects the quantity basis as part of every security quantity and therefore makes:

`SAME SECURITY + SAME NUMBER + UNITS != SAME SECURITY + SAME NUMBER + NOMINAL-AMOUNT`

The basis is revalidated again at every parent boundary. Repo baskets and
securities-lending collateral remain canonicalized, and duplicate security identity
entries remain rejected rather than silently aggregating or accepting mixed duplicate
representations.

---

## 9. Financing-rate semantics

`SftRateTerms` retains:

- fixed vs floating discriminant;
- finite contractual outright rate or spread;
- certified day-count convention;
- required floating reference identity only for floating terms.

Negative financing rates or floating spreads are not universally forbidden.

This object does not observe a benchmark, calculate accrual, compound interest,
materialize a schedule or price a contract.

R2 reuses this same hardened rate contract inside each securities-lending compensation
leg so day-count and fixed/floating reference semantics are not duplicated or lost.

---

## 10. Securities-lending compensation convention — R2 correction

R1 `SecuritiesLendingCompensationTerms` retained only two optional Decimal values:
lending-fee rate and cash-collateral rebate rate. That was insufficient static D04
material. DeepSeek Expert finding `DS-EXPERT-UNR013-R1-01` demonstrated that contracts
with identical numeric rates but different day-count, accrual base, payment frequency,
currency or floating reference could collapse.

IA accepted the finding as a HIGH production semantic defect and test/oracle gap.

R2 replaces bare rate fields with explicit optional compensation legs:

`SecuritiesLendingCompensationLegTerms`

Each leg retains:

- `rate: SftRateTerms`;
- `currency_identity_id: EconomicIdentityId`;
- `accrual_basis: SftCompensationAccrualBasisCode`;
- optional `payment_tenor: FinancialTenor`;
- optional `reset_tenor: FinancialTenor`.

The rate child supplies:

- fixed vs floating kind;
- outright fixed rate or floating spread;
- day-count convention;
- floating reference identity when required.

The compensation-leg fields add the contractual denomination and accrual/payment
qualification that R1 omitted.

The two roles remain separate:

- `lending_fee`;
- `cash_collateral_rebate`.

At least one leg must exist. A fixed lending-fee outright rate is non-negative. Rebate
material may be negative. A fixed compensation rate cannot carry a reset tenor; a
floating leg may carry a reset tenor. Payment and reset tenors are static terms only and
do not generate dated schedules.

The owner intentionally does not calculate fee cashflows, observe current collateral
value, resolve calendars, generate payment dates, settle cash, or determine current
accrual state.

`STATIC COMPENSATION CONVENTION != CALCULATED COMPENSATION CASHFLOW`

`PAYMENT/RESET TENOR != GENERATED CALENDAR SCHEDULE`

---

## 11. Duration semantics

`SftDurationTerms` distinguishes:

- `TERM`: explicit termination date required; notice period absent;
- `OPEN`: no termination date may be invented; optional positive notice days allowed;
- `CALLABLE`: positive contractual notice days required; contractual latest/end date may
  be present or absent.

All dates are exact `date` values. `bool` is not accepted as an integer notice period.
No current notice, termination, recall or calendar resolution occurs in D04.

---

## 12. Arrangement and static margin terms

`SftArrangementTerms` distinguishes bilateral from tri-party contracts.

- bilateral forbids a tri-party agent reference;
- tri-party requires an exact opaque contractual party reference.

`SftMarginTerms` retains optional contractual initial-margin and/or haircut ratios. They
are finite and non-negative. No universal `<= 1` rule is invented because initial
margin may exceed 100%.

These are static terms only.

`CONTRACTUAL HAIRCUT != CURRENT MARGIN CALCULATION`

---

## 13. Repo semantics

`RepoTerms` retains:

- terms and evidence identity;
- distinct repo instrument identity;
- seller and buyer references;
- term/open/callable duration;
- positive near cash amount and currency identity;
- non-empty transferred-security basket, now with explicit quantity basis per item;
- financing-rate terms;
- bilateral/tri-party arrangement;
- optional static margin terms;
- contractual far-leg material where applicable.

Term repo requires a far leg whose date equals the contractual termination date. Open
repo forbids an invented far leg. Callable repo may retain a far leg only when a
contractual termination date already exists and the dates agree.

If far-leg cash is explicitly supplied, its currency must equal the near-leg cash
currency. The owner never calculates a repurchase amount.

Transferred-security identities are unique. Caller tuple order is not declared
financial semantics and is canonicalized. The repo instrument identity must differ from
the transferred security identities.

---

## 14. Securities-lending semantics

`SecuritiesLendingTerms` retains:

- terms/evidence identity;
- distinct securities-lending instrument identity;
- lender and borrower references;
- duration;
- principal lent-security quantity/reference with explicit quantity basis;
- fee/rebate compensation legs with static rate/currency/accrual/tenor convention;
- explicit collateral tuple;
- bilateral/tri-party arrangement;
- optional static margin terms.

Collateral may contain cash and/or security quantities and may be empty when the static
contract supplied to this owner does not enumerate collateral. Empty explicit collateral
is not treated as proof of an unsecured loan, nor does generic `evidence_ref` grant
collateral-schedule, valuation or current-state authority. This remains an explicit
falsification target for Gate C rather than an invented universal rule.

Collateral entries are canonicalized by role/identity and duplicate role/identity
entries are rejected rather than relying on hidden aggregation. Security collateral
retains its quantity basis.

The same security identity is not universally forbidden from appearing in both
principal and collateral roles; those roles are structurally distinct and no universal
identity inequality has been proven.

No recall state, manufactured payment, current loan balance, collateral value,
substitution or return transfer is implemented.

---

## 15. Margin-lending semantics

`MarginLendingTerms` retains:

- terms/evidence identity;
- distinct facility/instrument identity;
- lender and borrower references;
- duration;
- positive contractual credit-limit cash amount;
- financing-rate terms;
- typed collateral-eligibility code;
- optional explicit eligible-collateral identity tuple;
- bilateral/tri-party arrangement;
- optional static margin/haircut terms.

The eligible identity tuple may be empty when the eligibility code points to contractual
eligibility material outside the explicit list. Explicit identities must be exact,
unique and are canonicalized by identity. The facility instrument cannot be its own
eligible collateral.

No current utilization, available credit, current borrowing balance, margin
requirement, liquidation threshold or collateral valuation is retained.

`MARGIN-LENDING LIMIT != CURRENT CREDIT AVAILABILITY`

---

## 16. Logical identity

Each top-level product begins with an explicit product discriminant:

- `"repo"`;
- `"securities-lending"`;
- `"margin-lending"`.

All static material owned by the bounded contract is projected deterministically.

R2 specifically adds to logical identity:

- security quantity basis for every `SftSecurityQuantity`;
- compensation rate kind/value/day-count/floating reference;
- compensation currency identity;
- compensation accrual-basis code;
- optional payment tenor;
- optional reset tenor.

Tests independently reconstruct complete top-level expected tuples from primitive
constants rather than using nested SUT `logical_values()` results to manufacture the
expected oracle.

Regression collisions assert that these produce distinct logical identity:

- same security + same quantity + `units` vs `nominal-amount`;
- same compensation rate + different day-count;
- same compensation rate + different accrual basis;
- same compensation rate + different payment tenor;
- same compensation rate + different currency;
- same floating spread + different reference identity.

Order that is not financial semantics remains canonicalized for:

- repo transferred-security basket;
- securities-lending collateral tuple;
- margin-lending explicit eligible-collateral identities.

---

## 17. R1 Gate-C finding history

R1 immutable authority before correction:

- HEAD `ce1429370b6e15ce76fc180f9aac4107e4272ab0`;
- synthetic `b503777efc35d8bf46411405bee35e845c527324`;
- freeze comment `5387641820`;
- post-freeze evidence comment `5387654891`;
- DeepSeek Expert package `UNR013-GATEC-R1-DS-EXPERT-01`.

DeepSeek Expert returned `FAIL`.

Accepted findings:

1. `DS-EXPERT-UNR013-R1-01` — HIGH — production semantic defect: securities-lending
   compensation omitted material static convention and allowed distinct contracts to
   collapse.
2. `DS-EXPERT-UNR013-R1-02` — HIGH — production semantic defect: security quantity
   omitted denomination/basis. IA accepted the underlying defect while refining the
   concrete witness to unit count versus nominal/face amount for the same security.

IA adjudication is recorded in PR #437 comment `5387700845`.

The first corrective HEAD mutation invalidated R1. DeepSeek Coder R1, Claude Code R1
and IA Final R1 were not run. No R1 reviewer result carries forward as R2 authority.

`R1 FAIL + HEAD MUTATION -> R2 FROM DEEPSEEK EXPERT`

---

## 18. R2 test/oracle closure

R2 tests retain all previous exact-type, Decimal, duration, repo, collateral,
arrangement, logical-identity and negative-space checks and add:

- exact/canonical quantity-basis codes;
- units vs nominal-amount non-collapse;
- quantity-basis malformed exact-child rejection;
- complete compensation-leg logical identity;
- day-count non-collapse;
- accrual-basis non-collapse;
- payment-tenor non-collapse;
- compensation-currency non-collapse;
- floating-reference non-collapse;
- exact imported `FinancialTenor` rejection;
- malformed exact `FinancialTenor.value` rejection;
- malformed exact nested `FinancialTenorUnit` rejection;
- fixed-rate compensation reset-tenor rejection;
- malformed exact compensation-basis rejection;
- parent revalidation of malformed compensation legs;
- reflective revalidation after post-construction mutation.

Statement coverage is not certification. R2 must return the owner to 100% statement
coverage and pass the complete repository quality gate before any new freeze.

---

## 19. Authority map

| Material | Authority |
|---|---|
| Economic/security/currency/reference identity | UMI-02 / D04 |
| Day-count and static financial tenor | UMI-03 / D04 |
| Repo / securities-lending / margin-lending static terms | this UNR-013 owner |
| Observed prices/collateral evidence | D05 |
| Current calendar/time/notice/date resolution | D06 |
| Calculated accrual/cashflow/collateral valuation/pricing | D07 |
| Current holdings, borrow/loan balances, collateral positions | D08 |
| Current margin/haircut/risk/exposure/capacity | D09 |
| Orders/execution/transfer instructions | D10 |
| Settlement, custody, collateral movement, recalls/returns | D11 |
| Legal/regulatory/master-agreement determinations | D22 |

Downstream consumers are not identity or product-definition owners.

---

## 20. Negative space

This candidate contains no:

- provider/network I/O;
- current SFT position or balance;
- current collateral value;
- generated compensation cashflow or current accrual;
- generated payment/reset calendar;
- current margin calculation or margin call;
- liquidation;
- borrow availability/locate state;
- utilization/available-credit state;
- manufactured payments;
- substitution/rehypothecation operation;
- recall/return operation;
- custody or settlement mutation;
- execution/order submission;
- risk engine;
- legal eligibility engine;
- implicit wall clock;
- implicit UUID/random generation;
- secrets or productive credentials;
- Production or real-capital authority.

`STATIC SFT TERMS != CURRENT SFT POSITION`

`SECURITY REFERENCE != SECURITY TRANSFER`

`TRI-PARTY TERMS != AGENT OPERATION`

`STATIC COMPENSATION CONVENTION != CASHFLOW CALCULATION`

---

## 21. Gate status

This document records a correction candidate; it does not self-certify R2.

Required sequence:

`R2 QUALITY -> DIFF AUDIT -> R2 FREEZE -> EXACT POST-FREEZE SYNTHETIC CI -> DEEPSEEK EXPERT R2 -> IA -> DEEPSEEK CODER R2 -> IA -> CLAUDE CODE R2 -> IA -> IA FINAL FALSIFICATION -> READY -> PROTECTED EXPECTED-HEAD MERGE -> POST-MERGE VERIFY -> #394 CLOSE -> UMI-14 CONTINUE`

Any HEAD mutation after the future R2 freeze invalidates all SHA-bound R2 evidence and
requires a new round beginning again with DeepSeek Expert.

Current state at document update:

- R1 = HISTORICAL / INVALIDATED BY CORRECTION;
- R2 candidate = PRESENT;
- R2 freeze = NOT ESTABLISHED;
- R2 exact post-freeze CI = NOT ESTABLISHED;
- DeepSeek Expert R2 = HOLD until freeze + exact CI;
- Ready = NO;
- merge = NO;
- #394 = OPEN;
- UNR-013 / UMI-14 / PROGRAM D = NOT CLOSED.

`CI GREEN != ENGINEERING APPROVAL`

`PROGRAM-D SEMANTIC CLOSURE != QORE UNIVERSAL MARKET READY`

`PROGRAM-D SEMANTIC CLOSURE != PROVIDER/OPERATIONAL/PRODUCTION READY`

Production remains CLOSED. Real capital remains NOT AUTHORIZED.
