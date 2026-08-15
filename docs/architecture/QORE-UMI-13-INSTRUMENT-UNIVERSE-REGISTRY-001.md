# QORE-UMI-13-INSTRUMENT-UNIVERSE-REGISTRY-001

## Status

**PROGRAM D / UMI-13 — IMPLEMENTATION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #361  
Master roadmap: Issue #303  
Universal Markets / Instruments: Issue #301  
Certified starting baseline: `e429c8731f1fca4bb0aa7c1eaa8b8865cb0375f0`  
Registry candidate snapshot date: **2026-08-15**  
Structural-gap checkpoint: #361 comment `5302898505`

This artifact is a date-qualified D04 instrument-family evidence/inventory snapshot.
It is deliberately separate from provider/platform catalogs, execution universes,
asset-taxonomy authority, valuation methodology, risk authority and settlement.

```text
COMPLETE AS OF VERIFIED SNAPSHOT DATE
!= COMPLETE FOREVER

REGISTRY ENTRY
!= PROVIDER SUPPORT
!= PLATFORM SUPPORT
!= EXECUTION SUPPORT
!= ROUTING AUTHORITY
!= VALUATION AUTHORITY
!= RISK AUTHORITY
!= SETTLEMENT AUTHORITY

OFFICIAL SOURCE EXISTS
!= QORE IMPLEMENTATION EXISTS

IdentityFamilyCode
!= ECONOMIC IDENTITY
```

The candidate is not certified until the exact-head independent-review and
Integration Gate sequence completes. No row in this document is a production or
real-capital claim.

---

# 1. Exact-baseline evidence ledger

The live repository was reverified before implementation:

- `main = e429c8731f1fca4bb0aa7c1eaa8b8865cb0375f0`;
- tree `049a3c0c466fd862765a24b1d2f97dd8a1311ee8`;
- parent1 `d157f4e42b8f60699264661e89702743cbb8be12`;
- parent2 `6c648815c2d70c42fb34ce69a0cf271afa189c66`;
- GitHub signature `verified=true`, `reason=valid`;
- #361 remained open and required baseline audit before implementation.

Search was used only to locate candidates. Functional absence was not inferred from
file-name search failure.

---

# 2. Existing artifact inventory and authority classification

| Artifact | Classification | UMI-13 role |
|---|---|---|
| UMI-01 taxonomy audit | DOCUMENTATION / INVENTORY ONLY | discovery and collision evidence; not registry implementation |
| `universal_instrument_identity.py` | CANONICAL REUSABLE REGISTRY FOUNDATION | reuse `IdentityFamilyCode`; identity/listing/lifecycle authority remains UMI-02 |
| `universal_instrument_identity_graph.py` | CANONICAL REUSABLE REGISTRY FOUNDATION | immutable identity graph and deterministic ordering pattern; not family coverage registry |
| UMI-03 fixed-income economics | FAMILY SEMANTIC OWNER | owner evidence only for its bounded contract scope |
| UMI-04 rate term structure | FAMILY SEMANTIC OWNER + PROVENANCE PATTERN | owner evidence; explicit `as_of`/provenance methodology analog |
| UMI-05 derivative contract semantics | FAMILY SEMANTIC OWNER | futures/options/forwards/swaps/protection/multi-leg bounded terms |
| UMI-06 equity/fund/corporate action | FAMILY SEMANTIC OWNER | equity, DR, pooled vehicles, bounded benchmark/NAV/corporate-action semantics |
| UMI-07 commodity delivery | FAMILY SEMANTIC OWNER | commodity reference and physical-delivery qualification over UMI-05 futures |
| UMI-08 crypto/perpetual/funding/network | FAMILY SEMANTIC OWNER | bounded crypto/perpetual/funding/network semantics |
| UMI-09 structured/hybrid/synthetic | FAMILY SEMANTIC OWNER | higher-order composition/payoff qualification |
| UMI-10 valuation observation | FAMILY-NEUTRAL VALUATION OBSERVATION OWNER | observation semantics only; not valuation methodology |
| UMI-11 market topology | MARKET TOPOLOGY OWNER | venue/interaction topology, effective intervals, deterministic patterns |
| UMI-12 conformance harness | CONFORMANCE EVIDENCE | cross-asset contract conformance; not support registry |
| hosting/runtime/service registries | DUPLICATE / UNSAFE AUTHORITY FOR UMI-13 | must not be reused as D04 instrument universe |
| Issue #300 platform registry | PROVIDER / PLATFORM CATALOG ONLY | methodology analog for date-qualified discovery; no D04 authority |

Direct inspection established that no existing canonical structure combines all
UMI-13 requirements:

- explicit family snapshot date;
- family semantic coverage state;
- QORE owner/certification qualification;
- unresolved/deferred/excluded semantics;
- official evidence-source category;
- deterministic family inventory material.

Decision:

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-13 REGISTRY VALIDATION CONTRACT REQUIRED`

The implementation therefore reuses UMI-02 `IdentityFamilyCode` instead of adding
another taxonomy owner.

---

# 3. Date-qualification decision

The canonical snapshot clock is an explicit exact `date` supplied by the caller.

Rules:

- no wall clock;
- no `datetime.now()`;
- no hidden currentness inference;
- `datetime` is rejected where exact `date` is required;
- evidence verification date cannot postdate registry `as_of`;
- one family may occur at most once in one snapshot;
- a later snapshot is a new explicit fact, not mutation of historical truth.

```text
2026-08-15 SNAPSHOT
!= TIMELESS COMPLETENESS
```

The implementation retains a positive explicit revision plus deterministic logical
material. It intentionally does not hash evidence into a substitute for retained
source evidence.

---

# 4. Status and owner model

Coverage status is restricted to:

- `COVERED`;
- `PARTIAL`;
- `UNRESOLVED`;
- `EXCLUDED`;
- `DEFERRED`.

Owner qualification is separate:

- `CERTIFIED_CONTRACT`;
- `PARTIAL_CONTRACT`;
- `NO_CERTIFIED_OWNER`;
- `NOT_APPLICABLE`.

`SUPPORTED` is intentionally absent.

A `COVERED` row requires certified QORE contract evidence and no unresolved
semantics. A `PARTIAL` row requires a retained QORE owner plus explicit unresolved
semantics. `UNRESOLVED` and `DEFERRED` require `NO_CERTIFIED_OWNER`. `EXCLUDED`
requires `NOT_APPLICABLE` and governed reason/evidence.

External/provider evidence alone cannot establish `COVERED` or `PARTIAL`.
At least one referenced `QORE_REPOSITORY` evidence record is required for those
states.

---

# 5. Official evidence ledger — verified for discovery on 2026-08-15

These sources prove market/product existence or standards coverage only. They are
not QORE support claims.

| Ref | Category | Official source | Evidence relevance |
|---|---|---|---|
| EXT-FPML-01 | STANDARDS_INDUSTRY_BODY | https://www.fpml.org/about/product-summary/ | IRD caps/floors/FRA/swaps/swaptions; FX spot/forward/NDF/swaps/options/deposits; CDS/index/basket/loan/mortgage; variance/correlation; commodity derivatives |
| EXT-FPML-02 | STANDARDS_INDUSTRY_BODY | https://www.fpml.org/about/faqs/ | FpML additionally describes loans and deposits; derivative families and underlying assets |
| EXT-BIS-01 | CENTRAL_BANK_OFFICIAL_REFERENCE | https://www.bis.org/statistics/triennialrep/guidelines_cbanks.htm | FX plus interest-rate, equity, commodity, credit and other OTC derivative categories |
| EXT-TREASURY-01 | REGULATORY_OFFICIAL | https://www.treasurydirect.gov/marketable-securities/ | bills, notes, bonds, TIPS, FRNs and STRIPS distinctions |
| EXT-FSB-01 | REGULATORY_OFFICIAL | https://www.fsb.org/2018/03/securities-financing-transactions-reporting-guidelines/ | repo, securities lending and margin lending as SFT data categories |
| EXT-CFTC-EVENT-01 | REGULATORY_OFFICIAL | https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationProducts?Category=Event | current event/binary DCM product evidence |
| EXT-FCA-CFD-01 | REGULATORY_OFFICIAL | https://www.fca.org.uk/firms/contract-for-differences | CFDs, spread betting and rolling spot FX as a distinct regulated product sector |
| EXT-CBOE-VOL-01 | EXCHANGE_CLEARING_VENUE | https://www.cboe.com/tradable-products/vix | VIX benchmark is distinct from VIX options/futures; volatility products are not the benchmark itself |
| EXT-SEC-ABS-01 | REGULATORY_OFFICIAL | https://www.sec.gov/newsroom/press-releases/2014-177 | ABS securitization pools/tranches and asset-level distinctions |
| EXT-CME-01 | EXCHANGE_CLEARING_VENUE | https://www.cmegroup.com/markets.html | futures/options/OTC/cash across agriculture, energy, equity index, FX, rates, metals and other major market groups |
| EXT-COINBASE-01 | PROVIDER_PLATFORM_OFFICIAL | https://www.coinbase.com/international-exchange | spot and perpetual product existence; provider evidence only |

QORE repository owner evidence is retained separately from the external ledger.
External-source coverage cannot promote a row into QORE semantic certification.

---

# 6. Candidate family coverage matrix — snapshot 2026-08-15

`COVERED` below means only the bounded D04 semantic-contract dimension represented
by the certified QORE owner(s). It never means provider/execution/production
support.

| Family code | Coverage | QORE owner qualification | Principal retained owners | Unresolved semantic refs / qualifications |
|---|---|---|---|---|
| `cash-money-market` | PARTIAL | CERTIFIED_CONTRACT | UMI-02, UMI-03, UMI-04 | term/dual-currency deposits; commercial paper/CD; boundary to repo/SFT |
| `fixed-income-credit` | PARTIAL | CERTIFIED_CONTRACT | UMI-03, UMI-05 | ABS/MBS pool/tranche/prepayment; loan/facility economics; full securitized-credit taxonomy |
| `rates-term-structures` | PARTIAL | CERTIFIED_CONTRACT | UMI-04, UMI-05 | caps/floors/FRA/swaption specialization; benchmark construction remains separate |
| `equities` | PARTIAL | CERTIFIED_CONTRACT | UMI-06 | warrants/convertible cross-family qualification; borrow/shortability remains outside static terms |
| `funds-pooled-vehicles` | PARTIAL | CERTIFIED_CONTRACT | UMI-06 | UIT coverage; ETN is explicitly not a fund by classification |
| `indices-benchmarks` | PARTIAL | CERTIFIED_CONTRACT | UMI-02, UMI-06, UMI-10 | benchmark/index construction methodology and constituent governance not owned here |
| `fx` | PARTIAL | CERTIFIED_CONTRACT | UMI-02, UMI-05 | dedicated FX spot pair semantics; digital/barrier/average-rate options; rolling financing |
| `futures` | COVERED | CERTIFIED_CONTRACT | UMI-02, UMI-05, UMI-07 | bounded generic futures terms only; event-resolution semantics classified separately |
| `options` | PARTIAL | CERTIFIED_CONTRACT | UMI-05, UMI-09 | digital/barrier/Asian/exotic payoff semantics remain incomplete |
| `forwards-swaps-otc` | PARTIAL | CERTIFIED_CONTRACT | UMI-05 | cap/floor/FRA/swaption product qualification; complete ISDA legal programmability not claimed |
| `commodities` | PARTIAL | CERTIFIED_CONTRACT | UMI-05, UMI-07 | power/electricity, freight, weather, emissions and specialized OTC commodity semantics |
| `crypto-digital-assets` | PARTIAL | CERTIFIED_CONTRACT | UMI-02, UMI-05, UMI-08 | staking/yield-bearing products; tokenized-security cross-domain qualification |
| `structured-hybrid-products` | PARTIAL | CERTIFIED_CONTRACT | UMI-03, UMI-05, UMI-09 | product-specific structured-note and securitized payoff/legal variants |
| `volatility-variance-products` | PARTIAL | CERTIFIED_CONTRACT | UMI-05, UMI-10 | variance/correlation swap/future product semantics beyond generic derivative structure |
| `securities-financing` | UNRESOLVED | NO_CERTIFIED_OWNER | none | repo/reverse-repo, securities lending/borrowing, margin lending |
| `cross-asset-compositions` | PARTIAL | CERTIFIED_CONTRACT | UMI-05, UMI-09 | composition semantics exist; execution/routing of strategy legs is intentionally outside registry |
| `event-contracts` | UNRESOLVED | NO_CERTIFIED_OWNER | none | event definition, source-of-resolution, contingency/outcome and dispute semantics |
| `contracts-for-difference` | UNRESOLVED | NO_CERTIFIED_OWNER | none | CFD rolling financing, close-out/reference-price and spread-betting qualification |
| `loans-credit-facilities` | UNRESOLVED | NO_CERTIFIED_OWNER | none | principal/facility/drawdown/amortization/covenant and syndicated-loan semantics |

The final three rows are additions produced by the discovery challenge rather than
by blindly stopping at the original 16-family baseline.

---

# 7. Explicit unresolved-semantics ledger

| Ref | Family | Unresolved material | Why it remains open |
|---|---|---|---|
| UMI13-UNR-001 | cash-money-market | term and dual-currency deposits | FpML proves material product semantics; no inspected dedicated QORE owner |
| UMI13-UNR-002 | cash-money-market | commercial paper / certificates of deposit | discovery baseline requires explicit accounting; fixed-income owner cannot be promoted without proof |
| UMI13-UNR-003 | fixed-income-credit | ABS/MBS pools, tranches and prepayment | SEC evidence shows securitization economics not reducible to an ordinary bond row |
| UMI13-UNR-004 | loans-credit-facilities | loans/facilities | FpML explicitly covers loans; no inspected QORE family owner |
| UMI13-UNR-005 | indices-benchmarks | methodology / constituent governance | index level/reference identity != construction methodology |
| UMI13-UNR-006 | fx | dedicated spot-pair and exotic FX option semantics | generic derivative terms do not prove all FX-specific economics |
| UMI13-UNR-007 | options | barrier/digital/Asian/exotic payoff qualification | option existence != payoff-complete semantics |
| UMI13-UNR-008 | rates-term-structures / OTC | caps/floors/FRA/swaptions | external standard coverage exceeds explicit family-specific QORE owner proof |
| UMI13-UNR-009 | commodities | power/freight/weather/emissions | commodity class != specialized market/product semantics |
| UMI13-UNR-010 | crypto-digital-assets | staking/yield-bearing/tokenized products | funding observation != generic staking economics; tokenized security crosses domains |
| UMI13-UNR-011 | structured-hybrid-products | structured note / securitized payoff variants | composition framework != every product payoff/legal contract |
| UMI13-UNR-012 | volatility-variance-products | variance/correlation contracts | volatility observation != tradeable variance/correlation instrument semantics |
| UMI13-UNR-013 | securities-financing | repo/securities lending/margin lending | FSB recognizes distinct SFT forms; no dedicated certified owner found |
| UMI13-UNR-014 | event-contracts | event resolution / outcome authority | binary option shape alone does not define authoritative event resolution |
| UMI13-UNR-015 | contracts-for-difference | rolling financing / close-out / spread-betting distinction | provider/platform occurrence cannot create D04 semantics |
| UMI13-UNR-016 | funds-pooled-vehicles | unit investment trusts | pooled-vehicle inventory must not assume UMI-06 enum exhaustiveness |

Unresolved rows must survive deterministic logical material until a later certified
owner explicitly resolves them. Partial coverage cannot erase them.

---

# 8. Exclusion / deferred ledger

No material financial family discovered in the recorded sweep is silently omitted.
The following concepts are excluded from *instrument-family identity* rather than
from future QORE scope:

| Concept | Registry treatment | Reason |
|---|---|---|
| provider-native symbol | EXCLUDED AS CANONICAL FAMILY/IDENTITY | provider symbol is external mapping evidence, not economic identity |
| provider/platform catalog row | EXCLUDED AS D04 FAMILY AUTHORITY | belongs to D03 / #300 platform/provider inventory |
| execution/routing strategy | EXCLUDED AS INSTRUMENT SUPPORT PROOF | D10 authority; composition terms do not grant execution |
| valuation methodology | EXCLUDED AS REGISTRY OWNER | D07 / #350 remains separate |
| risk/margin capacity | EXCLUDED AS REGISTRY OWNER | D09 and reservation gaps remain separate |
| settlement capability | EXCLUDED AS REGISTRY OWNER | D11 remains separate |

No discovered material family is marked `EXCLUDED` merely because QORE does not yet
implement it; such families are retained as `UNRESOLVED` or `DEFERRED`.

---

# 9. Semantic collision ledger

The registry must preserve at least these distinctions:

```text
RATE != YIELD
PRICE != NAV
NAV != INDEX LEVEL
INDEX LEVEL != TRADEABLE INSTRUMENT
NOTIONAL != QUANTITY
NOTIONAL != MULTIPLIER
FUNDING TERMS != FUNDING OBSERVATION
BENCHMARK != SECURITY
REFERENCE ASSET != ECONOMIC IDENTITY OF DERIVATIVE
VENUE LISTING != CANONICAL ECONOMIC IDENTITY
PROVIDER SYMBOL != ECONOMIC IDENTITY
VIX INDEX != VIX FUTURE != VIX OPTION != VARIANCE FUTURE
ETF != ETN
BOND != ABS/MBS POOL/TRANCHE ECONOMICS
BINARY OPTION PAYOFF SHAPE != EVENT-RESOLUTION AUTHORITY
CFD PRODUCT != ROLLING SPOT FX BY IMPLICATION
REPO != SECURITIES LENDING != MARGIN LENDING
```

---

# 10. Implementation boundary

`src/qore/infrastructure/instrument_universe_registry.py` is a pure immutable
validation contract only.

It provides:

- explicit evidence refs and evidence-source category;
- explicit owner refs;
- explicit unresolved semantic refs;
- explicit reason;
- separate coverage and owner status;
- exact-date snapshot + positive revision;
- one-family-per-snapshot uniqueness;
- no dangling/orphan/duplicate evidence;
- evidence date <= snapshot date;
- QORE repository evidence requirement for `COVERED/PARTIAL`;
- deterministic sorting and `logical_values()`;
- exact family lookup.

It provides no:

- provider adapter;
- platform capability;
- network call;
- DB/storage implementation;
- mutable global registry;
- scheduler/thread/retry loop;
- order/execution/routing behavior;
- valuation model/methodology;
- risk/margin/reservation behavior;
- settlement mutation;
- currentness resolver;
- real-capital authority.

---

# 11. Adversarial obligations

Tests must falsify at least:

1. non-date / `datetime` snapshot qualification;
2. duplicate family rows;
3. conflicting coverage/owner states;
4. missing owner evidence for QORE coverage;
5. missing/dangling/orphan/duplicate evidence;
6. evidence verified after snapshot;
7. nondeterministic caller ordering;
8. unresolved semantics disappearing from `PARTIAL`;
9. provider/official evidence being promoted to QORE coverage;
10. provider symbol being accepted as `IdentityFamilyCode`;
11. registry objects gaining provider/execution/risk/valuation/settlement fields;
12. wall clock, UUID generation, network/database/thread/sleep behavior entering the module.

---

# 12. Carry-forward non-claims

UMI-13 does not close or promote:

- #333 / `GAP-FND04-TIME-01`;
- #332 / `GAP-FND07-RES-01`;
- #350 D07 valuation methodology/producer/reproducibility;
- GAP-EXEC;
- GAP-ANALYSIS-PRODUCER;
- GAP-LIN-001;
- UMI-02 cross-revision currentness/precedence resolver;
- #334 external/productive in-flight side-effect containment;
- #146 OANDA Practice evidence blocker;
- #286 methodology/operator evidence blocker;
- PR #298 HOLD;
- UPR-12 cross-platform conformance;
- #351 Level-10 cross-domain/cross-authority conformance;
- #344 Level-12 full-system E2E.

```text
UMI-13 PASS != UMI-14 PASS
UMI-13 PASS != QORE UNIVERSAL MARKET READY
UMI-13 PASS != PROVIDER READY
UMI-13 PASS != PRODUCTION READY
UMI-13 PASS != REAL-CAPITAL AUTHORITY
```

---

# 13. Candidate certification boundary

Before integration, the exact candidate must still pass:

```text
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Then:

```text
DIFF AUDIT
-> DRAFT PR
-> EXACT-HEAD CI
-> FREEZE
-> INDEPENDENT CLAUDE REVIEW
-> INTEGRATION GATE
-> EXPECTED-HEAD MERGE
-> POST-MERGE CERTIFICATION
```

This document is implementation evidence, not self-certification.
