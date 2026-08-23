# QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — UNR-013 CURRENT-BASELINE FULL-CLOSURE CANDIDATE — NOT CERTIFIED**

Tracker: #394  
Parent final audit: #363  
Target: `UMI13-UNR-013` — `securities-financing`  
Certified starting baseline: `db83b106f3a5e7f30a788567dfa970a38b7a379a`  
Starting tree: `5b9c218a4fe3609b10e34b1cf8523cade0d10bbe`  
Current branch: `agent/qore-umi14-securities-financing-full-closure-013`

The historical preparatory branch
`agent/qore-umi14-securities-financing-semantics-013` was created from
`39e1598e91c912f473f9628c3aab30fe7b9cc034`. It remains provenance only.
Its bounded financial findings are retained, but its implementation is not integration
authority because it predates later UMI-14 exact-type, malformed-object and Decimal
scalability hardening.

This candidate adds only static D04 product-definition semantics for repo, securities
lending and margin lending. It does not authorize current SFT positions, collateral
valuation, margin calls, custody, settlement, execution, legal eligibility, provider
support, Production or real capital.

---

## 1. Gate-A reconstruction

UMI-13 retained:

`UMI13-UNR-013 — securities-financing — repo/securities lending/margin lending — distinct SFT forms; no dedicated owner`.

Existing cash/money-market semantics do not preserve bilateral security transfer and
repurchase roles. Generic derivatives are not a substitute for securities-financing
contracts. Loan/facility semantics added earlier in UMI-14 own commercial credit
facility structure, not repo or securities lending.

The material D04 gap therefore survives on the current certified baseline.

**Adjudication:** `VERIFIED MATERIAL D04 GAP — BOUNDED CORRECTION REQUIRED`.

---

## 2. Financial non-conflation

The bounded owner preserves these distinctions:

1. repo != term deposit or generic secured loan;
2. repo near transfer != far repurchase transfer;
3. term repo != open/callable repo;
4. transferred repo security != current collateral valuation/state;
5. securities-lending principal security != collateral role;
6. securities-lending fee != cash-collateral rebate;
7. securities lending != repo;
8. margin-lending contractual credit limit != current drawn balance or availability;
9. bilateral != tri-party arrangement;
10. contractual haircut/initial margin != current margin calculation.

FpML repo and securities-lending structures and FSB securities-financing classifications
are financial evidence for those distinctions. They do not prove provider support,
valuation authority, execution capability or legal eligibility.

---

## 3. Additive surface

Exactly three files are added:

1. `src/qore/infrastructure/securities_financing_semantics.py`
2. `tests/infrastructure/test_securities_financing_semantics.py`
3. `docs/architecture/QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001.md`

No certified pre-existing source, test or architecture file is modified.

---

## 4. Reused authority

The owner reuses only certified material whose semantics are exact:

- `EconomicIdentityId` from UMI-02 for economic/security/currency/reference identity;
- `DayCountConventionCode` from UMI-03 for day-count qualification.

Imported values are not trusted merely because `isinstance` succeeds. The consumer
requires exact imported type and revalidates the nested primitive used by this owner.

`IMPORTED CERTIFIED TYPE != AUTOMATIC TRUST OF MALFORMED INSTANCE`

The owner does not reuse account-balance money, risk margin, settlement instructions or
provider-native identifiers.

---

## 5. Owner-local values

The candidate defines:

- `SftTermsId`;
- `SftEvidenceRef`;
- `SftPartyReferenceId`;
- `SftCollateralEligibilityCode`;
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
- `SecuritiesLendingCompensationTerms`;
- `RepoTerms`;
- `SecuritiesLendingTerms`;
- `MarginLendingTerms`.

All semantic values are frozen and slotted. No UUID, timestamp or random value is
created implicitly.

---

## 6. Exact-type and malformed-object boundary

Every composition edge uses exact-type validation.

Exact type alone is not enough: Python can manufacture an exact frozen/slotted object
without its constructor using `object.__new__` and reflective slot assignment.
Therefore every parent revalidates the primitive/internal state of each local child
before accepting it.

The same rule applies to imported values used here:

- `EconomicIdentityId` must be exact and contain an exact `UUID`;
- `DayCountConventionCode` must be exact and contain a canonical exact `str`.

The tests construct malformed exact children and hostile subclasses to falsify these
trust boundaries.

`TYPE MATCH != VALID LOCAL STATE`

---

## 7. Decimal determinism and resource scaling

All numeric contract material requires exact finite `Decimal`; Decimal subclasses are
rejected before behavior is trusted.

Logical identity uses an owner-local canonical Decimal representation that:

- maps signed zero to `"0"`;
- removes coefficient trailing zeros;
- is independent of ambient Decimal precision/context;
- round-trips exactly;
- keeps extreme exponents compact rather than expanding fixed-point strings
  proportional to exponent magnitude.

Examples retained by tests include `1E+1000000` and `1E-1000000`.

No `Decimal.normalize()` result is used for logical identity.

---

## 8. Duration semantics

`SftDurationTerms` distinguishes:

- `TERM`: explicit termination date required; notice period absent;
- `OPEN`: no termination date may be invented; optional positive notice days allowed;
- `CALLABLE`: positive contractual notice days required; contractual latest/end date
  may be present or absent.

All dates are exact `date` values. `bool` is not accepted as an integer notice period.

No current notice, termination, recall or calendar resolution occurs in D04.

---

## 9. Financing-rate semantics

`SftRateTerms` retains:

- fixed vs floating discriminant;
- finite contractual rate or spread;
- certified day-count convention;
- required floating reference identity only for floating terms.

Negative contractual fixed rates or floating spreads are not universally forbidden.

This object does not observe a benchmark, calculate accrual, compound interest,
materialize a schedule or price a contract.

---

## 10. Arrangement and static margin terms

`SftArrangementTerms` distinguishes bilateral from tri-party contracts.

- bilateral forbids a tri-party agent reference;
- tri-party requires an exact opaque contractual party reference.

`SftMarginTerms` retains optional contractual initial-margin and/or haircut ratios.
They are finite and non-negative. No universal `<= 1` rule is invented because initial
margin may exceed 100%.

These are static terms only.

`CONTRACTUAL HAIRCUT != CURRENT MARGIN CALCULATION`

---

## 11. Repo semantics

`RepoTerms` retains:

- terms and evidence identity;
- distinct repo instrument identity;
- seller and buyer references;
- duration, whose start date is the contractual near/purchase date;
- positive near cash amount and currency identity;
- non-empty transferred-security basket;
- financing-rate terms;
- bilateral/tri-party arrangement;
- optional static margin terms;
- contractual far-leg material where applicable.

Term repo requires a far leg whose date equals the contractual termination date.
Open repo forbids an invented far leg. Callable repo may retain a far leg only when a
contractual termination date is already present and the dates agree.

If far-leg cash is explicitly supplied, its currency must equal near-leg cash currency.
The owner never calculates a repurchase amount.

Transferred-security identities are unique and canonicalized by economic identity so
caller tuple order does not create a different logical contract.

The repo instrument identity must differ from transferred security identities.

---

## 12. Securities-lending semantics

`SecuritiesLendingTerms` retains:

- terms/evidence identity;
- distinct securities-lending instrument identity;
- lender and borrower references;
- duration;
- principal lent-security quantity/reference;
- fee/rebate compensation;
- explicit collateral tuple;
- bilateral/tri-party arrangement;
- optional static margin terms.

Lending fee and cash-collateral rebate are separate optional fields. At least one must
exist. Lending fee is non-negative; rebate may be negative.

Collateral may contain cash and/or security quantities and may be empty when the static
contract supplied to this owner does not enumerate collateral.

Collateral entries are canonicalized by role/identity and duplicate role/identity
entries are rejected rather than relying on hidden aggregation.

The same security identity is not universally forbidden from appearing in a principal
and collateral role; role distinction is retained explicitly and no unsupported
universal inequality is invented.

No recall state, manufactured payment, current loan balance, collateral value,
substitution or return transfer is implemented.

---

## 13. Margin-lending semantics

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

The eligible identity tuple may be empty when the eligibility code points to an
external contractual schedule. Explicit identities must be exact, unique and are
canonicalized by identity. The facility instrument cannot be its own eligible
collateral.

No current utilization, available credit, current borrowing balance, margin
requirement, liquidation threshold or collateral valuation is retained.

`MARGIN-LENDING LIMIT != CURRENT CREDIT AVAILABILITY`

---

## 14. Logical identity

Each top-level product begins with an explicit product discriminant:

- `"repo"`;
- `"securities-lending"`;
- `"margin-lending"`.

All static material owned by the contract is projected deterministically.

Order that is not financial semantics is canonicalized:

- repo transferred-security basket;
- securities-lending collateral tuple;
- margin-lending explicit eligible-collateral identities.

Tests reconstruct complete expected top-level tuples from primitive constants rather
than using SUT `logical_values()` to manufacture the expected oracle.

---

## 15. Authority map

| Material | Authority |
|---|---|
| Economic/security/currency identity | UMI-02 / D04 |
| Day-count convention | UMI-03 / D04 |
| Repo / securities-lending / margin-lending static terms | this UNR-013 owner |
| Observed prices/collateral evidence | D05 |
| Current calendar/notice/time resolution | D06 |
| Collateral valuation/pricing | D07 |
| Current holdings, borrow/loan balances, collateral positions | D08 |
| Current margin/haircut/risk/exposure/capacity | D09 |
| Orders/execution/transfer instructions | D10 |
| Settlement, custody, collateral movement, recalls/returns | D11 |
| Legal/regulatory/master-agreement determinations | D22 |

Downstream consumers are not identity owners.

---

## 16. Negative space

This candidate contains no:

- provider/network I/O;
- current SFT position or balance;
- collateral valuation;
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

---

## 17. Gate status

This file is a candidate record, not self-certification.

Required sequence remains:

`IMPLEMENT -> FULL QUALITY GATE -> DIFF AUDIT -> FREEZE -> EXACT SYNTHETIC CI -> INDEPENDENT REVIEW CHAIN -> IA FINAL FALSIFICATION -> READY -> PROTECTED EXPECTED-HEAD MERGE -> POST-MERGE VERIFY -> #394 CLOSE -> UMI-14 CONTINUE`

Any HEAD mutation after freeze invalidates SHA-bound Gate-C evidence and requires a new
round.

`CI GREEN != ENGINEERING APPROVAL`

`PROGRAM-D SEMANTIC CLOSURE != QORE UNIVERSAL MARKET READY`

`PROGRAM-D SEMANTIC CLOSURE != PROVIDER/OPERATIONAL/PRODUCTION READY`

Production remains closed. Real capital remains unauthorized.
