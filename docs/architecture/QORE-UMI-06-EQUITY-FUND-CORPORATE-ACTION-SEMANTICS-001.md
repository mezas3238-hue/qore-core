# QORE-UMI-06-EQUITY-FUND-CORPORATE-ACTION-SEMANTICS-001

## Status

**PROGRAM D / UMI-06 — FULL CLOSURE RECERTIFICATION CORRECTION CANDIDATE; NOT SEALED**

Tracking: Issue #326  
Master roadmap: Issue #303  
Universal Markets / Instruments program: Issue #301  
Historical certified starting baseline: `22241b770975083cd31bfa65a680339cec5a33ed`  
Historical implementation merge: `b44529c8e3caf5badf6ff49da2f0246f3f985219` / PR #327  
Full Closure starting baseline: `e355a14257073862c3e6767d44d3bc058fb9ad8c`  
Predecessor in the serial Full Closure sequence: UMI-05 — SEALED / CLOSED

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

Repository-wide carry-forwards are reconciled as of the Full Closure starting
baseline:

- `GAP-FND04-TIME-01` / #333 — CLOSED / completed downstream; it is not UMI-06-owned work;
- `GAP-FND07-RES-01` / #332 — OPEN / HIGH and remains cross-owner;
- PR #298 — OPEN / DRAFT / HOLD and remains cross-owner;
- research lineage / concrete methodology gaps remain outside UMI-06 ownership.

UMI-06 does not close, promote, or reclassify cross-owner work by implication.

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
29. `FundVehicleTerms` full parent projection covers every current bounded
    `FundVehicleKind` across the complete `share_class` present/absent ×
    `nav_basis` present/absent matrix, so sibling-guard or kind-conditioned
    projection contamination fails.

---

# 10. Compatibility / blast radius

The original implementation was intentionally additive:

- one infrastructure semantic module;
- one adversarial test module;
- this architecture artifact.

The Full Closure correction is also bounded:

- production source remains byte-identical;
- the historical owner test remains intact;
- one owner-local Full Closure oracle module is added;
- this architecture artifact is reconciled with durable repository evidence.

No certified UMI-02/03/04/05, provider, market-data, execution, account, risk,
position/settlement, runtime, persistence or client implementation is modified.

```text
ADDITIVE TERMS != AUTOMATIC DOWNSTREAM ADOPTION
```

Later producers/adapters must explicitly map evidence into these contracts and
receive separate certification.

---

# 11. Full Closure stage exit

Historical UMI-06 implementation already completed its original governed lifecycle:

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

The current serial recertification requires the stronger Full Closure sequence:

`GATE A / COMPLETE RECONSTRUCTION`
`-> IDENTIFY ALL UMI06-OWNED PENDING WORK`
`-> GATE B / OWNER CORRECTION`
`-> ZERO INTERNAL PENDING CANDIDATE`
`-> GATE C / CREATE DRAFT PR`
`-> EXACT-CANDIDATE SYNTHETIC-MERGE QUALITY GATE`
`-> CLAUDE EXACT-CANDIDATE READ-ONLY AUDIT`
`-> IA EXACT-CANDIDATE FALSIFICATION`
`-> GATE D / DRAFT -> READY`
`-> GATE E / EXPECTED-HEAD MERGE`
`-> VERIFY ACTUAL MERGE / MAIN`
`-> POST-MERGE CI ON ACTUAL MAIN`
`-> CLAUDE FINAL WHOLE-UMI06 AUDIT`
`-> IA FINAL FALSIFICATION`
`-> GATE F / FINAL #301 EVIDENCE`
`-> FREEZE / SEALED / CLOSED`

Until that entire sequence completes:

`HISTORICALLY CERTIFIED UMI-06 != FULL-CLOSURE SEALED UMI-06`

---

# 12. Full Closure reconstruction and correction ledger

## 12.1 Exact current baseline

Gate A and Gate B were bound to:

- `main`: `e355a14257073862c3e6767d44d3bc058fb9ad8c`;
- tree: `221297010c1019a0f7e89e39e091edac6f2040f2`;
- GitHub merge signature: verified / valid;
- source blob: `44ed79ad27ea7b95c28b6811376bbb62bf4a7b0e`;
- hardened historical test blob: `56f3e257b99aca7ebe77a5d6949c50e9d71aa7b2`;
- pre-Full-Closure architecture blob: `b78d679060e357e660c038ea97d7585de2175d58`.

No production-source drift was found between the historical UMI-06 implementation
and the Full Closure starting baseline.

## 12.2 Historical implementation ledger — PR #327

The durable original implementation evidence is:

- base: `22241b770975083cd31bfa65a680339cec5a33ed`;
- exact reviewed head: `e757c8a22cbed2905c9b37dc164f10681502662e`;
- candidate tree: `d4601aa043ddeb707a584b1ee49889c1f7197044`;
- exact-head QORE CI #1049 / run `31842589207` — SUCCESS;
- Ruff PASS;
- Mypy PASS — 576 source files at that historical baseline;
- Pytest PASS — 2532 passed / 6 inherited warnings;
- global coverage 84%;
- UMI-06 module 92%;
- actual protected merge: `b44529c8e3caf5badf6ff49da2f0246f3f985219`;
- merge tree: `d4601aa043ddeb707a584b1ee49889c1f7197044`;
- merge parents: historical base + exact reviewed head;
- GitHub merge signature: verified / valid;
- exact diff: three additive owner files, `+1916/-0`;
- source blob: `44ed79ad27ea7b95c28b6811376bbb62bf4a7b0e`;
- original test blob: `104ac7fdf856649b9c06c4c315bd65a2334a0039`;
- architecture blob: `b78d679060e357e660c038ea97d7585de2175d58`;
- #301 recorded UMI-06 certified and Issue #326 closed/completed.

Historical PRE-CHK corrections retained as permanent evidence:

- `PRE-CHK-UMI06-01` — ETN/index-linked leakage removed from `FundVehicleKind`;
- `PRE-CHK-UMI06-02` — benchmark qualification bound to existing UMI-02
  `IdentityRelationshipId` rather than creating second endpoint authority.

Claude's first review package encountered `FINDING-UMI06-01`, an evidence-access
blocker only. The package was corrected without candidate mutation and the same
exact head later received `READY FOR INTEGRATION GATE`. Historical findings
`FINDING-UMI06-02..06` were adjudicated as non-blocking hardening/informational
items and did not establish a production defect.

## 12.3 Logical-identity retrospective hardening — #405 / PR #414

The retrospective field-materiality audit later classified:

`UMI06-LI-01 = CONFIRMED ORACLE GAP / MEDIUM`

No production semantic/projection defect was established. Production source was
not reopened.

PR #414 added owner-local TEST-ONLY complete-projection guards. Its first reviewed
head `755b52c0df006590ce5cf3096b3377dc8ca4cdce` is historical only: IA found
`UMI06-LI-01-GATE-001`, a sibling-guard correlation in the equity
`security_kind × share_class` fixtures.

The corrected exact head was:

- head: `d21623e73bab33b8376e7b1fa1e8337cfcb0ac45`;
- head tree: `d881e97f979dcec7121e02b6e7a0b5b30d82bc33`;
- test blob: `56f3e257b99aca7ebe77a5d6949c50e9d71aa7b2`;
- production blob retained: `44ed79ad27ea7b95c28b6811376bbb62bf4a7b0e`;
- QORE CI #1215 / run `32212531241` — SUCCESS;
- Ruff PASS;
- Mypy PASS — 612 source files at that baseline;
- Pytest PASS — 3241 passed / 6 inherited warnings;
- total coverage 86%;
- UMI-06 module 93%;
- cumulative PR blast radius: one test file, `+185/-0`;
- production files touched: zero;
- actual merge: `120856305588154459af925196687ffad69424ea`;
- merge tree: `d881e97f979dcec7121e02b6e7a0b5b30d82bc33`;
- GitHub merge signature: verified / valid.

The corrected hardening supplied full reconstruction oracles for equity security,
depositary receipt, fund optional branches, benchmark qualification, cash
dividend, stock dividend, split and rights distribution material.

## 12.4 Full Closure Gate A / Gate B / Gate C findings

The current Full Closure reconstruction and same-branch IA falsification classified:

| Finding | Classification | Initial state | Current candidate disposition |
|---|---|---:|---:|
| `FC06-01` stale candidate status / missing #327 durable ledger | `UMI_INTERNAL_NONCODE` | OPEN | RESOLVED IN CANDIDATE |
| `FC06-02` missing #405/#414 hardening ledger | `UMI_INTERNAL_NONCODE` | OPEN | RESOLVED IN CANDIDATE |
| `FC06-03` missing current-main/blob/downstream reconciliation | `UMI_INTERNAL_NONCODE` | OPEN | RESOLVED IN CANDIDATE |
| `FC06-04` historical exit procedure predates serial Full Closure | `UMI_INTERNAL_NONCODE` | OPEN | RESOLVED IN CANDIDATE |
| `FC06-05` stale TIME-01 OPEN claim after #333 closure | `UMI_INTERNAL_NONCODE` | OPEN | RESOLVED IN CANDIDATE |
| `FC06-06` missing durable disposition of historical UMI06 findings | `UMI_INTERNAL_NONCODE` | OPEN | RESOLVED IN CANDIDATE |
| `FC06-07` `FundVehicleTerms` optional/kind projection oracle correlation | `UMI_INTERNAL_BLOCKER / TEST-ONLY ORACLE GAP / MEDIUM` | OPEN | CORRECTED IN CANDIDATE |
| `FC06-08` initial Gate B artifact ordered Gate C after exact-candidate audit | `UMI_INTERNAL_NONCODE / GOVERNANCE PROCEDURE ORDER` | OPEN ON INITIAL GATE-B HEAD | RESOLVED IN CANDIDATE |
| `FC06-09` Draft-PR exact-candidate CI failed Ruff import ordering | `UMI_INTERNAL_BLOCKER / CI-LINT` | OPEN DURING GATE-C QUALIFICATION | CORRECTED IN CURRENT CANDIDATE; REQUALIFICATION REQUIRED |

`FC06-07` did not establish a production defect. The production implementation
already projects `share_class` and `nav_basis` independently. The gap was that the
pre-existing test suite did not independently kill all sibling-guard and
vehicle-kind-conditioned omission mutations.

Gate B adds one owner-local Full Closure oracle module that covers:

- every current bounded `FundVehicleKind`;
- `share_class=None`, `nav_basis=None`;
- share-class present / NAV absent;
- share-class absent / NAV present;
- share-class present / NAV present;
- complete parent projection with independently reconstructed nested NAV material.

This forms the complete `6 × 2 × 2` witness basis for the current bounded enum and
optional-state space. A projection guarded incorrectly by either optional sibling
or by any one current vehicle kind must fail at least one full-parent oracle.

`FC06-08` was found by IA while falsifying initial Gate B head
`a2d9bb654826998fe15ea0caa04b975697909efb`. That head is historical only and
receives no qualification. The corrected procedure now places Gate C/Draft PR
before synthetic-merge CI and exact-candidate independent audit, consistent with
the serial Full Closure law.

`FC06-09` was exposed only after Gate C created Draft PR #422 and GitHub evaluated
the exact synthetic merge. QORE CI #1234 / run `32316182718` on head
`67c3021e503bd36c3544605e8a2df9dac778e778`, QORE CI #1235 / run `32316335818`
on head `305520eb65260e91cb9cbf222b8b9229fda7e104`, and QORE CI #1236 / run
`32316410139` on head `1aded7ce5b4438ba59bc4461eb890312510213e6` all failed exclusively at
Ruff `I001`; Mypy and Pytest were skipped. Those heads and runs have zero
qualification value. No suppression, `noqa`, strictness reduction or production
mutation was used. The current test-owner correction follows Ruff's mechanically
reported canonical import grouping and must obtain a fresh full quality gate.

## 12.5 Current owner / downstream boundary

UMI-06 continues to own only bounded equity, fund and corporate-action semantic
terms. It does not absorb downstream specialization merely because those products
reference UMI-06 material.

Current open/draft work inspected during Gate A — including UMI-14 UIT, CFD,
event-contract, securities-financing, volatility/variance, crypto staking/tokenization,
specialized commodity and rates/OTC lanes, plus PR #298 and the cTrader Demo probe —
does not modify the UMI-06 production owner or the historical UMI-06 test owner.

The UIT lane is a bounded downstream qualification and deliberately does not add
`FundVehicleKind.UNIT_INVESTMENT_TRUST` or rewrite `FundVehicleTerms`.

```text
DOWNSTREAM QUALIFICATION != UMI-06 OWNER DRIFT
OPEN DOWNSTREAM PR != MAIN
```

## 12.6 Full Closure qualification law

Gate C correction status remains candidate-only. It does not certify itself.

Before UMI-06 can be sealed, the unchanged exact candidate must still receive:

- fresh exact candidate / synthetic merge diff and blob audit;
- full authoritative QORE quality gate on the exact PR candidate;
- independent Claude exact-candidate read-only audit;
- IA exact-candidate falsification;
- explicit Gate D before Draft -> Ready;
- explicit Gate E before expected-head merge;
- actual merge/main verification;
- post-merge CI on actual `main`;
- independent Claude final whole-UMI06 audit;
- IA final falsification;
- explicit Gate F before final #301 evidence/freeze.

```text
FAILED HISTORICAL HEAD != QUALIFIED CANDIDATE
CORRECTION CANDIDATE != QUALIFIED CANDIDATE
CI GREEN != ENGINEERING APPROVAL
HISTORICAL PASS != CURRENT EXACT-HEAD PASS
NO FINAL #301 EVIDENCE -> NO FULL-CLOSURE SEAL
```
