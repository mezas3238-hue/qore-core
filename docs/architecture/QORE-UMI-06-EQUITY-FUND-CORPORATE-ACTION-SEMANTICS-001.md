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
benchmark relationships, and bounded corporate-action terms.

It does **not** implement provider feeds, NAV calculation, benchmark calculation,
position adjustment, cash movement, settlement, execution, tax, borrow/locate
state, or production support.

```text
EQUITY / FUND CONTRACT TERMS
!=
ECONOMIC / LISTING IDENTITY AUTHORITY
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
ECONOMIC IDENTITY / LISTING / GENERIC LIFECYCLE -> UMI-02
EQUITY/FUND TERMS ID != ECONOMIC IDENTITY
CORPORATE ACTION ID != INSTRUMENT IDENTITY
LISTING IDENTITY != EQUITY TERMS
PROVIDER SYMBOL != EQUITY/FUND IDENTITY
ISSUER REFERENCE != PROVIDER FACT
COMMON != PREFERRED
DEPOSITARY RECEIPT != UNDERLYING SHARE
DEPOSITARY RECEIPT RATIO != POSITION QUANTITY
FUND VEHICLE CLASSIFICATION != DEBT / PAYOFF ENGINE
NAV BASIS != NAV OBSERVATION
NAV BASIS != NAV CALCULATION ENGINE
FUND BENCHMARK RELATIONSHIP != BENCHMARK VALUE
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

## 2.1 UMI-02 already owns identity, listings and generic lifecycle

Directly inspected at certified baseline:

`src/qore/infrastructure/universal_instrument_identity.py`

UMI-02 already provides:

- `EconomicIdentityId`;
- `ListingIdentityId`;
- `EconomicIdentity`;
- `ListingIdentity`;
- `IdentityRelationship`;
- `IdentityLifecycleEvent`;
- effective-dated provider/venue mapping;
- retained evidence references.

Therefore UMI-06 MUST NOT add:

- a second equity/fund economic identity;
- a second listing/venue identity;
- a provider symbol as canonical identity;
- a duplicate generic lifecycle graph.

UMI-06 terms bind existing `EconomicIdentityId` values.

```text
TERMS BIND IDENTITY
TERMS DO NOT CREATE IDENTITY AUTHORITY
```

Issuer, underlying, fund, benchmark, currency, unit and rights identities are
typed references. Their family/kind correctness remains a governed UMI-02 graph
composition obligation when material.

## 2.2 Existing “equity” usage is not equity-security semantics

Repository discovery finds existing `equity` terminology primarily in account
financial state and research performance/equity series. Those values represent
account equity, not common/preferred stock or fund-security semantics.

```text
ACCOUNT EQUITY != EQUITY SECURITY
```

UMI-06 does not reuse account-equity types as security contracts.

## 2.3 Existing money contracts are bounded

`proprietary_accounts.MoneyAmount` is an account-financial-state value with a
three-letter `CurrencyCode`.

`fixed_income_economics.FixedIncomeCashAmount` is fixed-income scoped and binds
currency separately in its containing fixed-income contracts.

Neither type is promoted silently to universal corporate-action authority.

UMI-06 therefore adds a narrow `CorporateActionCashAmount` containing:

- positive finite exact Decimal amount;
- explicit `EconomicIdentityId` currency identity.

This amount describes declared contractual cash material only.

```text
CORPORATE ACTION CASH AMOUNT != CASH BALANCE MUTATION
```

## 2.4 Market observations remain outside UMI-06

`market_observation.py` owns retained market-price/OHLC evidence and source
provenance. It does not define fund NAV or corporate-action terms.

UMI-10 remains the universal valuation-observation stage.

Therefore UMI-06 may retain a fund NAV **basis relationship**, but it MUST NOT
retain or compute an observed NAV value.

## 2.5 UMI-05 strike semantics are reusable for rights

UMI-05 already defines `DerivativeStrike` with explicit PRICE/RATE/YIELD/SPREAD/
LEVEL separation and PRICE quote-basis material.

A rights subscription price is PRICE strike material. UMI-06 therefore reuses
`DerivativeStrike` and requires `DerivativeStrikeBasis.PRICE` instead of creating
another strike/price semantic.

This reuse grants no exercise or execution authority.

## 2.6 Verified structural gap

At baseline `22241b770975083cd31bfa65a680339cec5a33ed`, the inspected canonical
foundations do not provide one provider-neutral immutable semantic layer that can
retain, without authority collapse:

- common versus preferred equity security terms;
- depositary receipt program + underlying ratio;
- fund/pooled vehicle family terms;
- structural NAV basis;
- fund-to-benchmark role + return basis;
- cash dividend terms;
- stock dividend ratios;
- split/reverse-split ratios;
- rights entitlement + subscription strike.

Classification:

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-06 CONTRACT DELTA REQUIRED`

Search absence is not treated as exhaustive proof; the decision is based on the
directly inspected canonical boundaries above.

---

# 3. Contract inventory

## 3.1 Local identities / evidence

UMI-06 adds:

- `EquityFundTermsId`;
- `CorporateActionId`;
- `CorporateActionRevision`;
- `EquityFundEvidenceRef`.

These are immutable local artifact identities/revisions.

```text
LOCAL ARTIFACT ID != ECONOMIC IDENTITY
EVIDENCE REF != EVIDENCE CONTENT
```

No implicit UUID generation exists.

## 3.2 Extensible typed codes

UMI-06 adds:

- `EquityShareClassCode`;
- `DepositaryReceiptProgramCode`;
- `FundBenchmarkRoleCode`;
- `BenchmarkReturnBasisCode`;
- `FundNavBasisCode`.

Codes use deterministic canonical lowercase syntax and contain no provider
authority.

## 3.3 Equity security family

`EquitySecurityKind` distinguishes:

- `COMMON`;
- `PREFERRED`.

`EquitySecurityTerms` retains:

- local terms ID;
- economic instrument identity;
- issuer identity;
- security kind;
- optional share-class code;
- evidence ref.

Instrument and issuer identities must differ.

UMI-06 does not duplicate UMI-02 listing/venue material.

## 3.4 Depositary receipts

`DepositaryReceiptTerms` retains:

- local terms ID;
- receipt economic identity;
- underlying economic identity;
- typed program code such as ADR/GDR;
- exact positive underlying-units-per-receipt ratio;
- evidence ref.

Receipt identity and underlying identity must differ.

The ratio is not a position quantity and performs no conversion/mutation.

## 3.5 Fund / pooled vehicle terms

`FundVehicleKind` provides bounded classification for:

- ETF;
- mutual fund;
- closed-end fund;
- money-market fund;
- listed trust;
- REIT;
- ETN;
- index-linked product.

Classification is not a claim that all economics of every listed family are
implemented. In particular:

```text
ETN CLASSIFICATION != ETN DEBT ECONOMICS CERTIFIED
INDEX-LINKED CLASSIFICATION != STRUCTURED PAYOFF ENGINE
```

`FundVehicleTerms` retains:

- local terms ID;
- economic instrument identity;
- vehicle kind;
- optional share-class code;
- optional structural NAV basis;
- evidence ref.

## 3.6 NAV basis

`FundNavBasis` retains:

- NAV currency identity;
- NAV unit identity;
- typed basis code such as `per-share`;
- evidence ref.

Currency and unit identities must differ.

It contains no NAV value, timestamp, pricing source, methodology or calculation.

Those belong to UMI-10 / D07 when implemented.

## 3.7 Fund benchmark relationship

`FundBenchmarkRelationshipTerms` retains:

- local terms ID;
- fund identity;
- benchmark identity;
- relationship role;
- explicit benchmark return basis;
- evidence ref.

Fund and benchmark identities must differ.

Return-basis material prevents `price-return` and `total-return` semantics from
collapsing merely because a textual/index reference looks similar.

This contract contains no benchmark level and calculates no return.

---

# 4. Corporate-action model

Corporate-action terms are immutable revisions of semantic announcements/terms.
They do not apply the action.

`CorporateActionId` identifies the action.

`CorporateActionRevision` is an explicit positive integer. A later provider/D05
ingestion layer may retain revision history; UMI-06 does not create persistence
or current-state authority.

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

UMI-06 deliberately does **not** impose one universal ordering across declared,
ex, record and payable dates. Market conventions and special distributions can
differ. Exact role preservation is safer than a false universal chronology.

Each field is a strict `date`; `datetime` laundering is rejected.

The contract does not pay cash or alter a balance.

## 4.2 Stock dividend

`StockDividendTerms` retains:

- action ID + revision;
- subject identity;
- distribution identity;
- positive exact units-per-existing-unit ratio;
- ex / record / payable dates;
- evidence ref.

The distribution identity may equal the subject identity because a stock
dividend may distribute additional units of the same security.

The ratio does not mutate a position.

## 4.3 Split / reverse split

`SplitTerms` retains:

- action ID + revision;
- subject identity;
- exact positive new-units-per-old-unit ratio;
- effective date;
- evidence ref.

Ratios below 1 are valid and represent reverse-split semantics.

No position/cost-basis/P&L mutation is performed.

## 4.4 Rights distribution

`RightsDistributionTerms` retains:

- action ID + revision;
- source security identity;
- distinct rights instrument identity;
- positive entitlement-units-per-source-unit ratio;
- UMI-05 `DerivativeStrike` for subscription price;
- ex / record / expiration dates;
- evidence ref.

The subscription strike MUST use `DerivativeStrikeBasis.PRICE`.

Rights expiration must not precede record date.

This is a contractual/entitlement description only:

```text
RIGHTS TERMS != EXERCISE ENGINE
RIGHTS TERMS != ORDER AUTHORITY
RIGHTS TERMS != POSITION MUTATION
```

Warrant payoff/exercise architecture beyond these bounded rights-distribution
semantics remains UMI-05/UMI-09 work where applicable.

---

# 5. Determinism / validation

All UMI-06 dataclasses are:

`@dataclass(frozen=True, slots=True)`

Validation is fail-closed:

- UUID-backed local IDs;
- strict `EconomicIdentityId` references;
- strict enum/code types;
- strict `date` (`datetime` rejected);
- strict bool/int separation on revision (`bool` rejected);
- finite positive Decimal ratios/declared cash amount;
- canonical Decimal logical representation;
- explicit self-reference rejection where semantically invalid;
- deterministic `logical_values()`;
- no implicit `datetime.now()`;
- no implicit `uuid4()`;
- no global mutable state;
- no hidden retries/sleep/scheduler/threads.

---

# 6. Authority matrix

| Material | Authority |
|---|---|
| Economic identity / listing / generic lifecycle | UMI-02 / D04 |
| Equity/fund/corporate-action semantic terms | UMI-06 |
| Corporate-action/provider observations | D05 |
| Calendar/session/date resolution | D06 |
| NAV/price/benchmark valuation | D07 / UMI-10 |
| Account/cash/portfolio state | D08 |
| Risk/borrow constraints where authoritative | D09 + governed provider/evidence boundaries |
| Orders/execution | D10 / D18 |
| Position/cash/settlement mutation | D11 |
| Rights subscription strike semantic | UMI-05 |
| Higher-order warrant/structured payoff | UMI-09 where applicable |

No UMI-06 type grants another department's operational authority.

---

# 7. Semantic non-collisions

The candidate must preserve:

```text
COMMON != PREFERRED
RECEIPT != UNDERLYING SHARE
ADR PROGRAM != GDR PROGRAM
RECEIPT RATIO != POSITION QUANTITY
ETF != MUTUAL FUND != CLOSED-END FUND != REIT
NAV CURRENCY != NAV UNIT
NAV BASIS != NAV VALUE
FUND != BENCHMARK
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
- provider symbol/listing mapping beyond UMI-02;
- corporate-action feed ingestion;
- action revision persistence/current-state source;
- exchange calendar resolution;
- ex-date calculation;
- NAV observation or NAV calculation;
- benchmark/index level calculation;
- benchmark return calculation;
- market price calculation;
- dividend yield;
- withholding/tax;
- voting/capital-structure engines;
- borrow/locate/shortability availability;
- borrow rate;
- position adjustment;
- cost-basis adjustment;
- balance mutation;
- cash distribution;
- settlement/post-trade mutation;
- rights exercise;
- warrant exercise/payoff engine;
- general structured-product engine;
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
2. Raw UUID/string laundering into identity/code/enum fields fails.
3. Corporate-action revision rejects zero/negative/bool.
4. COMMON and PREFERRED remain distinct.
5. Instrument and issuer self-reference fails.
6. ADR/GDR program material remains distinct.
7. Receipt and underlying self-reference fails.
8. Unit ratios reject zero/negative/NaN/Infinity.
9. Decimal logical values normalize deterministically.
10. Fund NAV basis retains no value/calculation/observation method.
11. NAV currency and unit self-reference fails.
12. Fund benchmark fund/benchmark self-reference fails.
13. Price-return and total-return relationship material differs.
14. Benchmark relationship exposes no level/return engine.
15. Corporate-action cash amounts reject non-positive/non-finite values.
16. Corporate-action cash amount retains explicit currency identity.
17. Cash-dividend date roles accept unusual ordering rather than inventing one.
18. Date-only roles reject `datetime`.
19. Stock dividend retains distribution identity + exact ratio.
20. Reverse-split ratio below 1 remains valid.
21. Corporate-action terms expose no apply/settle/position mutation.
22. Rights source and rights identities must differ.
23. Rights subscription strike must be UMI-05 PRICE strike.
24. Rights expiration cannot precede record date.
25. Rights terms expose no exercise/execution engine.
26. All material logical values are repeatable and secret-free.

---

# 10. Compatibility / blast radius

The implementation is intentionally additive:

- one new infrastructure semantic module;
- one new adversarial test module;
- this architecture artifact.

No existing UMI-02, UMI-03, UMI-04, UMI-05, provider, market-data,
execution, account, risk, position/settlement, runtime, persistence or client
implementation needs modification for this bounded slice.

```text
ADDITIVE TERMS
!=
AUTOMATIC DOWNSTREAM ADOPTION
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
