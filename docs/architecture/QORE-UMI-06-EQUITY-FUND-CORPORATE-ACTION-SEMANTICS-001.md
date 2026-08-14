# QORE-UMI-06-EQUITY-FUND-CORPORATE-ACTION-SEMANTICS-001

## Status

**PROGRAM D / UMI-06 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #326  
Master roadmap: Issue #303  
Universal Markets / Instruments program: Issue #301  
Certified starting baseline: `22241b770975083cd31bfa65a680339cec5a33ed`  
Predecessor: UMI-05 / Issue #324 / PR #325 — CLOSED

This artifact defines the minimum provider-neutral immutable semantics needed for
equity securities, depositary receipts, fund/pooled vehicles, structural NAV and
benchmark semantic qualification, and bounded corporate-action terms.

It does **not** implement provider feeds, NAV calculation, benchmark calculation,
position adjustment, cash movement, settlement, execution, tax, borrow/locate
state, structured-product payoffs, or production support.

```text
EQUITY / FUND CONTRACT TERMS
!=
ECONOMIC / LISTING / RELATIONSHIP AUTHORITY
!=
MARKET / CORPORATE-ACTION OBSERVATION
!=
VALUATION / NAV ENGINE
!=
POSITION / CASH / SETTLEMENT MUTATION
!=
EXECUTION AUTHORITY
!=
PROVIDER SUPPORT
```

---

# 1. Governing invariants

```text
ECONOMIC IDENTITY / LISTING / GENERIC RELATIONSHIP / LIFECYCLE -> UMI-02
EQUITY/FUND TERMS ID != ECONOMIC IDENTITY
CORPORATE ACTION ID != INSTRUMENT IDENTITY
LISTING IDENTITY != EQUITY TERMS
PROVIDER SYMBOL != EQUITY/FUND IDENTITY
ISSUER REFERENCE != PROVIDER FACT
COMMON != PREFERRED
DEPOSITARY RECEIPT != UNDERLYING SHARE
DEPOSITARY RECEIPT RATIO != POSITION QUANTITY
FUND VEHICLE != ETN BY CLASSIFICATION
FUND VEHICLE != STRUCTURED INDEX-LINKED PRODUCT BY CLASSIFICATION
NAV BASIS != NAV OBSERVATION
NAV BASIS != NAV CALCULATION ENGINE
FUND BENCHMARK SEMANTICS -> BIND EXISTING UMI-02 RELATIONSHIP ID
FUND BENCHMARK SEMANTICS != SECOND RELATIONSHIP AUTHORITY
PRICE-RETURN BENCHMARK != TOTAL-RETURN BENCHMARK WHERE MATERIAL
DIVIDEND DECLARATION / TERMS != CASH PAYMENT
STOCK DIVIDEND RATIO != POSITION MUTATION
SPLIT RATIO != POSITION MUTATION
RIGHTS ENTITLEMENT != EXECUTION AUTHORITY
RIGHTS SUBSCRIPTION PRICE -> UMI-05 PRICE STRIKE SEMANTICS
CONTRACTUAL CORPORATE-ACTION DATE != OBSERVED SETTLEMENT EVENT
BORROW / SHORTABILITY STATE != STATIC EQUITY TERMS
EVIDENCE REF != EVIDENCE CONTENT
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
```

Repository-wide carry-forwards remain binding:

- `GAP-FND04-TIME-01` — OPEN / HIGH;
- `GAP-FND07-RES-01` — OPEN / HIGH;
- PR #298 — HOLD;
- research lineage gaps remain open.

UMI-06 does not close, promote, or reclassify any of them.

---

# 2. Exact-baseline audit

## 2.1 UMI-02 already owns identity, listings, relationships and lifecycle

Direct baseline inspection of
`src/qore/infrastructure/universal_instrument_identity.py` confirms UMI-02 owns:

- `EconomicIdentityId`;
- `ListingIdentityId`;
- `IdentityRelationshipId`;
- `EconomicIdentity`;
- `ListingIdentity`;
- effective-dated `IdentityRelationship`;
- `IdentityLifecycleEvent`;
- external/provider identity mapping and evidence references.

UMI-06 therefore MUST NOT create:

- a second equity/fund economic identity;
- a second listing/venue identity;
- a provider symbol as canonical identity;
- a second generic relationship graph;
- a duplicate generic lifecycle graph.

Equity/fund terms bind existing `EconomicIdentityId` values where family economics
need direct typed references. Fund/benchmark semantic qualification binds an
existing `IdentityRelationshipId`; it does not own relationship endpoints,
effective dates or generic relationship truth.

```text
TERMS BIND / QUALIFY CANONICAL IDENTITY MATERIAL
TERMS DO NOT REPLACE UMI-02 AUTHORITY
```

Governed composition must verify the referenced identity/relationship kinds and
endpoints whenever those facts are material.

## 2.2 Existing “equity” usage is not equity-security semantics

Repository discovery shows existing `equity` terminology primarily in account
financial state and research equity/performance series.

```text
ACCOUNT EQUITY != EQUITY SECURITY
```

Those values are not reused as common/preferred stock semantics.

## 2.3 Existing money contracts remain bounded

`proprietary_accounts.MoneyAmount` is account-state scoped.

`fixed_income_economics.FixedIncomeCashAmount` is fixed-income scoped.

Neither gains universal corporate-action authority. UMI-06 adds a narrow
`CorporateActionCashAmount` with:

- positive finite exact Decimal amount;
- explicit UMI-02 `EconomicIdentityId` for currency identity.

```text
DECLARED CORPORATE-ACTION CASH AMOUNT != CASH BALANCE MUTATION
```

## 2.4 Market observations remain outside UMI-06

`market_observation.py` owns retained market price/OHLC evidence. It does not make
UMI-06 a NAV or benchmark observation layer.

UMI-10 / D07 remain the universal valuation-observation/computation authority.
UMI-06 may retain a structural NAV basis only.

## 2.5 UMI-05 strike semantics are reused for rights

UMI-05 already distinguishes PRICE/RATE/YIELD/SPREAD/LEVEL strike material and
requires explicit PRICE quote-basis semantics.

A rights subscription price therefore reuses `DerivativeStrike` and MUST have
`DerivativeStrikeBasis.PRICE`.

Reuse of strike material grants no exercise, order or execution authority.

## 2.6 Internal pre-falsification corrections

Two candidate defects were removed before exact-head freeze:

### PRE-CHK-UMI06-01 — ETN / structured product classification leakage

Initial candidate placed `ETN` and `INDEX_LINKED_PRODUCT` in `FundVehicleKind`.
That would imply fund-family semantics for debt/structured products and could
create a false support claim.

Final rule:

`FundVehicleKind` is limited to:

- ETF;
- mutual fund;
- closed-end fund;
- money-market fund;
- listed trust;
- REIT.

ETN debt economics and structured/index-linked payoff semantics remain outside
this bounded fund contract and must be handled by their proper later economics
(UMI-03/UMI-09 as applicable).

### PRE-CHK-UMI06-02 — benchmark relationship authority duplication

Initial candidate carried fund and benchmark endpoint identities directly in a
new `FundBenchmarkRelationshipTerms`, too close to creating a second relationship
source beside UMI-02.

Final rule:

`FundBenchmarkRelationshipTerms` binds:

- local terms ID;
- existing UMI-02 `IdentityRelationshipId`;
- UMI-06 benchmark role;
- UMI-06 return-basis semantic;
- evidence ref.

It does NOT own fund/benchmark endpoints, relationship effective dates or generic
relationship identity.

```text
UMI-02 IDENTITY RELATIONSHIP = CANONICAL RELATIONSHIP AUTHORITY
UMI-06 FUND BENCHMARK TERMS = SEMANTIC QUALIFICATION OF THAT RELATIONSHIP
```

## 2.7 Verified structural gap

At baseline `22241b770975083cd31bfa65a680339cec5a33ed`, direct inspection of the
canonical foundations establishes no provider-neutral immutable semantic layer
retaining, without authority collapse:

- common versus preferred equity-security terms;
- depositary receipt program + underlying-unit ratio;
- bounded fund/pooled-vehicle family terms;
- structural NAV basis;
- benchmark role + return basis attached to an existing UMI-02 relationship;
- cash dividend terms;
- stock dividend ratios;
- split/reverse-split ratios;
- rights entitlement + subscription strike.

Classification:

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-06 CONTRACT DELTA REQUIRED`

Search absence is locator evidence only; the architecture decision is grounded in
directly inspected canonical boundaries.

---

# 3. Contract inventory

## 3.1 Local artifact identity / revision / evidence

UMI-06 adds:

- `EquityFundTermsId`;
- `CorporateActionId`;
- `CorporateActionRevision`;
- `EquityFundEvidenceRef`.

They are immutable local semantic artifacts, never economic identity.
No implicit UUID generation exists.

## 3.2 Extensible typed codes

UMI-06 adds:

- `EquityShareClassCode`;
- `DepositaryReceiptProgramCode`;
- `FundBenchmarkRoleCode`;
- `BenchmarkReturnBasisCode`;
- `FundNavBasisCode`.

Codes use canonical lowercase syntax and grant no provider authority.

## 3.3 Equity securities

`EquitySecurityKind` distinguishes only:

- `COMMON`;
- `PREFERRED`.

`EquitySecurityTerms` retains:

- local terms ID;
- economic security identity;
- issuer economic identity;
- security kind;
- optional share-class code;
- evidence ref.

Security and issuer identities must differ. UMI-02 remains responsible for
identity kind proof and generic relationships/listings.

## 3.4 Depositary receipts

`DepositaryReceiptTerms` retains:

- local terms ID;
- receipt economic identity;
- underlying economic identity;
- typed program code such as ADR/GDR;
- exact positive underlying-units-per-receipt ratio;
- evidence ref.

Receipt and underlying identities must differ.
The ratio is not position quantity and performs no conversion/mutation.

## 3.5 Fund / pooled vehicles

`FundVehicleKind` is intentionally bounded to genuine fund/pooled/trust families:

- ETF;
- mutual fund;
- closed-end fund;
- money-market fund;
- listed trust;
- REIT.

`FundVehicleTerms` retains:

- local terms ID;
- economic instrument identity;
- vehicle kind;
- optional share-class code;
- optional structural NAV basis;
- evidence ref.

It does not classify ETNs or generic index-linked structured products as funds.

## 3.6 NAV basis

`FundNavBasis` retains:

- NAV currency identity;
- NAV unit identity;
- typed basis code such as `per-share`;
- evidence ref.

Currency and unit identities must differ.

It retains no NAV value, observation timestamp, pricing source, methodology or
calculation engine.

## 3.7 Fund benchmark semantic qualification

`FundBenchmarkRelationshipTerms` retains:

- local terms ID;
- UMI-02 `IdentityRelationshipId`;
- benchmark semantic role;
- explicit benchmark return basis;
- evidence ref.

It deliberately does NOT retain independent fund/benchmark endpoint authority.
Governed composition resolves the referenced UMI-02 relationship and verifies
that its endpoints/kinds are appropriate.

Return basis prevents price-return and total-return semantics from collapsing.
No benchmark level or return is produced.

---

# 4. Corporate-action model

Corporate-action values are immutable revisions of contractual/declaration
semantics. They do not apply the action.

`CorporateActionId` identifies one action.
`CorporateActionRevision` is an explicit positive strict integer.

A later D05/provider boundary may retain revision history/current evidence.
UMI-06 does not create persistence or current-state authority.

## 4.1 Cash dividend

`CashDividendTerms` retains:

- action ID + revision;
- subject economic identity;
- positive exact cash amount + currency identity;
- declared date;
- ex date;
- record date;
- payable date;
- evidence ref.

UMI-06 deliberately does not impose one universal order across declared/ex/record/
payable dates. Exact role retention is safer than a false universal chronology.

All roles are strict `date`; `datetime` laundering is rejected.
No cash is paid and no balance is mutated.

## 4.2 Stock dividend

`StockDividendTerms` retains:

- action ID + revision;
- subject identity;
- distribution identity;
- positive exact units-per-existing-unit ratio;
- ex / record / payable dates;
- evidence ref.

Distribution identity may equal subject identity because additional units of the
same security may be distributed.
No position is mutated.

## 4.3 Split / reverse split

`SplitTerms` retains:

- action ID + revision;
- subject identity;
- exact positive new-units-per-old-unit ratio;
- effective date;
- evidence ref.

Ratios below 1 are valid reverse-split semantics.
No position, cost basis or P&L is mutated.

## 4.4 Rights distribution

`RightsDistributionTerms` retains:

- action ID + revision;
- source-security identity;
- distinct rights-instrument identity;
- positive entitlement-units-per-source-unit ratio;
- UMI-05 PRICE strike for subscription price;
- ex / record / expiration dates;
- evidence ref.

Expiration may not precede record date.

```text
RIGHTS TERMS != EXERCISE ENGINE
RIGHTS TERMS != ORDER AUTHORITY
RIGHTS TERMS != POSITION MUTATION
```

Warrant/structured payoff economics remain downstream where material.

---

# 5. Determinism / fail-closed validation

All candidate dataclasses use:

`@dataclass(frozen=True, slots=True)`

Validation includes:

- UUID-backed local IDs;
- strict UMI-02 identity/relationship references;
- strict enum/code types;
- strict `date` (`datetime` rejected);
- strict bool/int separation for revision;
- finite positive Decimal ratios/declared cash amount;
- canonical Decimal logical representation;
- self-reference rejection where locally decidable;
- deterministic `logical_values()`;
- no implicit `datetime.now()`;
- no implicit `uuid4()`;
- no global mutable state;
- no hidden retry/sleep/scheduler/thread.

---

# 6. Authority map

| Material | Authority |
|---|---|
| Economic identity / listing / generic relationship / lifecycle | UMI-02 / D04 |
| Equity/fund/corporate-action semantic terms | UMI-06 |
| Corporate-action/provider observations | D05 |
| Calendar/session/date resolution | D06 |
| NAV/price/benchmark valuation | D07 / UMI-10 |
| Account/cash/portfolio state | D08 |
| Risk/borrow state | D09 + governed evidence boundaries |
| Orders/execution | D10 / D18 |
| Position/cash/settlement mutation | D11 |
| Rights subscription strike semantic | UMI-05 |
| ETN debt economics | UMI-03 / later composition as applicable |
| Structured/index-linked/warrant higher-order payoff | UMI-09 as applicable |

No UMI-06 type grants another department's operational authority.

---

# 7. Required semantic non-collisions

```text
COMMON != PREFERRED
RECEIPT != UNDERLYING SHARE
ADR PROGRAM != GDR PROGRAM
RECEIPT RATIO != POSITION QUANTITY
ETF != MUTUAL FUND != CLOSED-END FUND != REIT
FUND VEHICLE != ETN
FUND VEHICLE != GENERIC STRUCTURED INDEX-LINKED PRODUCT
NAV CURRENCY != NAV UNIT
NAV BASIS != NAV VALUE
UMI-06 BENCHMARK QUALIFICATION != UMI-02 RELATIONSHIP AUTHORITY
PRICE-RETURN != TOTAL-RETURN WHERE MATERIAL
CASH DIVIDEND != CASH PAYMENT
STOCK DIVIDEND != SPLIT
SPLIT RATIO < 1 IS VALID
RIGHTS INSTRUMENT != SOURCE SECURITY
RIGHTS ENTITLEMENT RATIO != ORDER QUANTITY
RIGHTS SUBSCRIPTION STRIKE != EXECUTION
CORPORATE ACTION REVISION != OBSERVED SETTLEMENT
```

---

# 8. Explicit non-goals

UMI-06 does NOT implement or certify:

- provider equity/fund/corporate-action adapters;
- provider symbol/listing authority;
- corporate-action feed ingestion;
- action revision persistence/current-state source;
- exchange calendar resolution;
- ex-date calculation;
- NAV observation or NAV calculation;
- benchmark/index level or return calculation;
- market-price calculation;
- dividend yield;
- withholding/tax;
- voting/capital-structure engines;
- borrow/locate/shortability availability or borrow rate;
- ETN debt economics;
- generic structured/index-linked payoff economics;
- position adjustment;
- cost-basis adjustment;
- balance mutation;
- cash distribution;
- settlement/post-trade mutation;
- rights exercise;
- warrant exercise/payoff engine;
- order/execution;
- risk/capital reservation;
- provider support certification;
- productive Cloud;
- production readiness;
- real capital.

---

# 9. Adversarial test obligations

Tests must attack at minimum:

1. Local terms/action IDs cannot masquerade as economic identity.
2. Raw UUID/string laundering into typed identity/code/enum fields fails.
3. Corporate-action revision rejects zero/negative/bool.
4. COMMON and PREFERRED remain distinct.
5. Security/issuer self-reference fails.
6. ADR/GDR material remains distinct.
7. Receipt/underlying self-reference fails.
8. Unit ratios reject zero/negative/NaN/Infinity.
9. Decimal logical values normalize deterministically.
10. Fund kind does not admit ETN/index-linked structured product as a fund.
11. Fund NAV basis retains no value/calculation/observation engine.
12. NAV currency/unit self-reference fails.
13. Benchmark semantics require UMI-02 `IdentityRelationshipId`.
14. Raw UUID cannot masquerade as benchmark relationship authority.
15. Price-return and total-return semantic material differs.
16. Benchmark qualification exposes no endpoint/level/return engine authority.
17. Corporate-action cash amounts reject non-positive/non-finite values.
18. Corporate-action cash amount retains explicit currency identity.
19. Cash-dividend date roles accept unusual ordering rather than inventing one.
20. Date-only roles reject `datetime`.
21. Stock dividend retains distribution identity + exact ratio.
22. Reverse-split ratio below 1 remains valid.
23. Corporate-action terms expose no apply/settle/position mutation.
24. Rights source and rights identities must differ.
25. Rights subscription strike must be UMI-05 PRICE strike.
26. Rights expiration cannot precede record date.
27. Rights terms expose no exercise/execution engine.
28. Material logical values are repeatable and secret-free.

---

# 10. Compatibility / blast radius

The candidate is intentionally additive:

- one new infrastructure semantic module;
- one new adversarial test module;
- this architecture artifact.

No certified UMI-02/03/04/05, provider, market-data, execution, account, risk,
position/settlement, runtime, persistence or client implementation is modified.

```text
ADDITIVE TERMS != AUTOMATIC DOWNSTREAM ADOPTION
```

Later producers/adapters must explicitly map evidence into these contracts and
receive separate certification.

---

# 11. Stage exit

UMI-06 may close only after:

`IMPLEMENTATION`
`-> ADVERSARIAL TESTS`
`-> EXACT-HEAD QUALITY GATE`
`-> EXACT-HEAD FREEZE`
`-> CLAUDE INDEPENDENT ADVERSARIAL REVIEW`
`-> INTEGRATION GATE`
`-> EXPECTED-HEAD PROTECTED MERGE`
`-> VERIFY ACTUAL MERGE`
`-> VERIFY POST-MERGE MAIN`
`-> BASELINE FREEZE`
`-> ISSUE #326 CLOSED`

Until then:

`IMPLEMENTED CANDIDATE != CERTIFIED UMI-06`
