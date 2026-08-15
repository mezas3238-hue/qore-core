# QORE-UMI-13-INSTRUMENT-UNIVERSE-REGISTRY-001

## Status

**PROGRAM D / UMI-13 — CORRECTION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #361  
Master roadmap: Issue #303  
Universal Markets / Instruments: Issue #301  
Certified starting baseline: `e429c8731f1fca4bb0aa7c1eaa8b8865cb0375f0`  
Registry candidate snapshot date: **2026-08-15**  
Integration-Gate rejected head: `866ec2a941258af2344889baf03edd286545cb80` (historical after this correction)  
Pre-final-correction frozen head: `7fbf70ade552cccb900f6a25849a497aa39fc374`  
Earlier adversarial-correction head: `3ebabc14e81aeaf8141df0e88e54d475b2927b34` (historical only)

This artifact is the canonical date-qualified UMI-13 evidence/inventory document for
D04 instrument-family coverage. It is not a provider catalog, execution universe,
asset-taxonomy owner, valuation methodology, risk authority or settlement authority.

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

The Python registry contract validates immutable declaration shape. It does not
connect to GitHub, standards bodies, exchanges or providers and therefore does not
self-certify the truth of caller-supplied owner/evidence declarations. The canonical
owner/certification claim is established only by the reviewed repository evidence
recorded in this artifact and the later independent-review/Integration-Gate process.

---

# 1. Exact-baseline evidence ledger

The certified baseline used for UMI-13 is:

- `main = e429c8731f1fca4bb0aa7c1eaa8b8865cb0375f0`;
- tree `049a3c0c466fd862765a24b1d2f97dd8a1311ee8`;
- parent1 `d157f4e42b8f60699264661e89702743cbb8be12`;
- parent2 `6c648815c2d70c42fb34ce69a0cf271afa189c66`;
- GitHub signature `verified=true`, `reason=valid`.

The baseline audit inspected UMI-01 through UMI-12, UMI-02 identity/lifecycle and
identity graph, family-local semantic owners, topology/effective-date patterns,
provider/platform registries as non-authoritative analogs, and evidence/provenance
patterns.

Decision:

`VERIFIED STRUCTURAL GAP — MINIMUM ADDITIVE UMI-13 REGISTRY VALIDATION CONTRACT REQUIRED`

The implementation reuses UMI-02 `IdentityFamilyCode`; it does not create a second
economic identity or global taxonomy owner.

---

# 2. Existing authority map

| Artifact | Classification | UMI-13 role |
|---|---|---|
| UMI-01 taxonomy audit | DOCUMENTATION / INVENTORY ONLY | discovery and collision evidence |
| `universal_instrument_identity.py` | CANONICAL REUSABLE FOUNDATION | family classification plus economic/listing/lifecycle identity authority |
| `universal_instrument_identity_graph.py` | CANONICAL REUSABLE FOUNDATION | identity graph/order pattern; not coverage registry |
| UMI-03 fixed-income economics | FAMILY SEMANTIC OWNER | bounded fixed-income owner evidence |
| UMI-04 rate term structure | FAMILY SEMANTIC OWNER | rates/curve owner evidence and as-of pattern |
| UMI-05 derivative contract semantics | FAMILY SEMANTIC OWNER | bounded futures/options/forward/swap semantics |
| UMI-06 equity/fund/corporate action | FAMILY SEMANTIC OWNER | equity/fund bounded semantics |
| UMI-07 commodity delivery | FAMILY SEMANTIC OWNER | commodity reference/delivery specialization |
| UMI-08 crypto/perpetual/funding/network | FAMILY SEMANTIC OWNER | crypto/perpetual/funding structural semantics |
| UMI-09 structured/hybrid/synthetic | FAMILY SEMANTIC OWNER | composition/payoff qualification |
| UMI-10 valuation observation | D07 OBSERVATION OWNER | typed observation only; not valuation methodology |
| UMI-11 market topology | D04 TOPOLOGY OWNER | static topology/effective intervals |
| UMI-12 conformance harness | CONFORMANCE EVIDENCE | cross-asset falsification evidence |
| provider/platform catalog structures | D03 / PLATFORM ONLY | methodology analog; no D04 authority |

---

# 3. Date qualification and evidence model

The snapshot clock is an explicit exact `date` supplied by the caller.

Rules:

- no wall clock;
- no hidden currentness inference;
- `datetime` is rejected where exact `date` is required;
- evidence `verified_on` cannot postdate snapshot `as_of`;
- one family may occur at most once in one snapshot;
- later snapshots are new explicit facts, not mutation of historical truth;
- revision is explicit and positive;
- canonical ordering and `logical_values()` are deterministic.

The runtime evidence record intentionally remains reference metadata, not retained
third-party content. The canonical UMI-13 external ledger below therefore records
**retrieval/snapshot qualification explicitly**.

Qualification vocabulary used in this document:

- `REFERENCE_ONLY_MUTABLE`: live official page; content was not retained by UMI-13;
- `VERSIONED_REFERENCE`: official/versioned standard identifier is available, but UMI-13 does not retain the source bytes;
- `ARCHIVAL_REFERENCE`: official archival/filing locator is expected to remain historically addressable;
- `QORE_EXACT_REPOSITORY`: exact QORE commit/blob evidence.

This qualification vocabulary is document-level evidence governance. It is not an
`InstrumentUniverseEvidenceSourceCategory` runtime enum and does not require one.

```text
URL + VERIFIED_ON
!= RETAINED SOURCE CONTENT

HASH
!= RETAINED SOURCE EVIDENCE

REFERENCE_ONLY_MUTABLE
!= HISTORICAL REPRODUCIBILITY PROOF
```

UMI-13 therefore makes no claim that external web content can be reconstructed
byte-for-byte from this artifact alone.

---

# 4. Coverage and owner-status semantics

Coverage states:

- `COVERED`;
- `PARTIAL`;
- `UNRESOLVED`;
- `EXCLUDED`;
- `DEFERRED`.

Owner qualification declarations:

- `CERTIFIED_CONTRACT`;
- `PARTIAL_CONTRACT`;
- `NO_CERTIFIED_OWNER`;
- `NOT_APPLICABLE`.

Important boundary:

```text
owner_status field
= RETAINED SNAPSHOT DECLARATION
!= RUNTIME CERTIFICATION ENGINE
!= PROVIDER CAPABILITY
!= EXECUTION AUTHORITY
```

`COVERED` is permitted only when the bounded D04 semantic scope represented by the
row has no known unresolved semantic material at this snapshot. A broad family must
be `PARTIAL` when material subfamily semantics remain unresolved, even if a generic
owner contract exists.

The runtime contract requires retained QORE-repository evidence for `COVERED` and
`PARTIAL`. The UMI-13 canonical document separately carries the official external
evidence ledger required by Issue #361. This is deliberate **Model B** separation:

generic validator + reviewed canonical evidence/inventory artifact.

The generic constructor is not an online GitHub/standards authenticity resolver.

---

# 5. Official evidence ledger — snapshot qualification 2026-08-15

These references prove market/product/standard existence only. They do not prove
QORE provider or execution support.

| Ref | Category | Official authority/source | Locator | Verified on | Qualification | Version/effective qualification | Relevance |
|---|---|---|---|---|---|---|---|
| EXT-FPML-01 | STANDARDS_INDUSTRY_BODY | FpML / ISDA product summary | https://www.fpml.org/about/product-summary/ | 2026-08-15 | REFERENCE_ONLY_MUTABLE | current product-summary page | IRD, FX, credit, equity, commodity and other derivative families |
| EXT-FPML-02 | STANDARDS_INDUSTRY_BODY | FpML FAQ | https://www.fpml.org/about/faqs/ | 2026-08-15 | REFERENCE_ONLY_MUTABLE | current FAQ | loans, deposits and product/underlying distinctions |
| EXT-BIS-01 | CENTRAL_BANK_OFFICIAL_REFERENCE | BIS Triennial guidance | https://www.bis.org/statistics/triennialrep/guidelines_cbanks.htm | 2026-08-15 | REFERENCE_ONLY_MUTABLE | survey/guidance series | FX and OTC derivative categories |
| EXT-TREASURY-01 | REGULATORY_OFFICIAL | U.S. TreasuryDirect marketable securities | https://www.treasurydirect.gov/marketable-securities/ | 2026-08-15 | REFERENCE_ONLY_MUTABLE | current official page | bills, notes, bonds, TIPS, FRNs, STRIPS |
| EXT-FSB-01 | REGULATORY_OFFICIAL | FSB SFT reporting guidelines | https://www.fsb.org/2018/03/securities-financing-transactions-reporting-guidelines/ | 2026-08-15 | VERSIONED_REFERENCE | 2018 guideline publication | repo, securities lending and margin lending distinctions |
| EXT-CFTC-EVENT-01 | REGULATORY_OFFICIAL | CFTC DCM event-product filings | https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationProducts?Category=Event | 2026-08-15 | REFERENCE_ONLY_MUTABLE | live filing index | event/binary listed products |
| EXT-FCA-CFD-01 | REGULATORY_OFFICIAL | FCA CFD sector page | https://www.fca.org.uk/firms/contract-for-differences | 2026-08-15 | REFERENCE_ONLY_MUTABLE | current official page | CFDs, spread betting, rolling spot FX |
| EXT-CBOE-VOL-01 | EXCHANGE_CLEARING_VENUE | Cboe VIX products | https://www.cboe.com/tradable-products/vix | 2026-08-15 | REFERENCE_ONLY_MUTABLE | current official page | VIX index vs futures/options distinction |
| EXT-SEC-ABS-01 | REGULATORY_OFFICIAL | SEC ABS release | https://www.sec.gov/newsroom/press-releases/2014-177 | 2026-08-15 | ARCHIVAL_REFERENCE | SEC release 2014-177 | ABS asset/pool/tranche distinctions |
| EXT-CME-01 | EXCHANGE_CLEARING_VENUE | CME markets | https://www.cmegroup.com/markets.html | 2026-08-15 | REFERENCE_ONLY_MUTABLE | live market catalog | futures/options/OTC/cash product discovery |
| EXT-COINBASE-01 | PROVIDER_PLATFORM_OFFICIAL | Coinbase International Exchange | https://www.coinbase.com/international-exchange | 2026-08-15 | REFERENCE_ONLY_MUTABLE | provider catalog only | digital/perpetual existence only |
| EXT-CME-TREASURY-01 | EXCHANGE_CLEARING_VENUE | CME Treasury futures conversion-factor material | https://www.cmegroup.com/articles/2024/calculating-us-treasury-futures-conversion-factors.html | 2026-08-15 | REFERENCE_ONLY_MUTABLE | 2024 article/rulebook references | deliverable grades, conversion factors, CTD specialization |
| EXT-IIFM-SUKUK-01 | STANDARDS_INDUSTRY_BODY | IIFM Sukuk standards | https://www.iifm.net/public/standards/published-standards/sukuk-standards | 2026-08-15 | VERSIONED_REFERENCE | IIFM standards 17-26 and related published standards | Shari'ah-compliant Sukuk structural semantics |
| EXT-IIFM-ISLAMIC-LIQUIDITY-01 | STANDARDS_INDUSTRY_BODY | IIFM Published Standards / liquidity-management standards | https://www.iifm.net/public/index.php/standards/published-standards | 2026-08-15 | VERSIONED_REFERENCE | current published-standards catalog; individual standards versioned | Murabahah, Wakalah/agency liquidity and collateralized Murabahah financing/liquidity structures |
| EXT-IIFM-ISLAMIC-HEDGING-01 | STANDARDS_INDUSTRY_BODY | IIFM / ISDA-IIFM hedging standards | https://www.iifm.net/public/standards/published-standards/hedging-standards | 2026-08-15 | VERSIONED_REFERENCE | published hedging standards including current versions | Shari'ah-compliant profit-rate hedging, cross-currency hedging and Islamic FX-forward structures |
| EXT-IIFM-SYNDICATED-2026-01 | STANDARDS_INDUSTRY_BODY | IIFM syndicated-financing launch | https://www.iifm.net/press-media/news-and-updates/a-historic-milestone-iifm-launches-historic-suite-of-15-standardized-agreements-for-global-syndicated-financing/122 | 2026-08-15 | ARCHIVAL_REFERENCE | IIFM launch dated 2026-06-15 | standardized Ijarah/Murabahah syndicated-financing suite |
| EXT-ICC-SCF-01 | STANDARDS_INDUSTRY_BODY | ICC Standard Definitions for Techniques of Supply Chain Finance | https://iccwbo.org/news-publications/policies-reports/standard-definitions-techniques-supply-chain-finance/ | 2026-08-15 | VERSIONED_REFERENCE | publication 2017-01-09 | receivables purchase, factoring, forfaiting, payables and advance-based SCF |
| EXT-SEC-ILS-01 | REGULATORY_OFFICIAL | SEC EDGAR filing describing catastrophe/event-linked bonds | https://www.sec.gov/Archives/edgar/data/1587982/000139834425004768/fp0092388-4_497k.htm | 2026-08-15 | ARCHIVAL_REFERENCE | archived SEC filing | catastrophe/insurance-linked trigger semantics |
| EXT-NAIC-ILS-01 | REGULATORY_OFFICIAL | NAIC insurance-linked securities topic | https://content.naic.org/insurance-topics/insurance-linked-securities | 2026-08-15 | REFERENCE_ONLY_MUTABLE | current official topic page | non-cat ILS including mortality, longevity and medical-claim-cost risk |
| EXT-SEC-ILS-TRIGGERS-01 | REGULATORY_OFFICIAL | SEC EDGAR ILS trigger disclosure | https://www.sec.gov/Archives/edgar/data/1587982/000139834421016679/fp0068048_485apos.htm | 2026-08-15 | ARCHIVAL_REFERENCE | archived SEC filing | indemnity, parametric, industry-loss, modeled-loss and hybrid trigger taxonomy |
| EXT-SEC-ILS-DERIVATIVE-01 | REGULATORY_OFFICIAL | SEC EDGAR event-linked derivative disclosure | https://www.sec.gov/Archives/edgar/data/1450011/000119312526061473/d70415d485bpos.htm | 2026-08-15 | ARCHIVAL_REFERENCE | archived SEC filing | event-linked derivative instruments, including swaps, related to longevity/mortality risk |

QORE owner evidence remains separate and exact-repository-qualified. External source
coverage never promotes a family into QORE semantic certification by itself.

---

# 6. Candidate family coverage matrix — corrected snapshot 2026-08-15

| Family code | Coverage | QORE owner declaration | Principal retained owners | Unresolved semantics / qualifications |
|---|---|---|---|---|
| `cash-money-market` | PARTIAL | CERTIFIED_CONTRACT | UMI-02, UMI-03, UMI-04 | deposits; commercial paper/CD; repo/SFT boundary; Shari'ah-compliant liquidity/financing structures |
| `fixed-income-credit` | PARTIAL | CERTIFIED_CONTRACT | UMI-03, UMI-05 | ABS/MBS pool/tranche/prepayment; loans/facilities; Sukuk; Shari'ah-compliant financing/credit qualification; insurance-linked risk-transfer/trigger structures |
| `rates-term-structures` | PARTIAL | CERTIFIED_CONTRACT | UMI-04, UMI-05 | caps/floors/FRA/swaption specialization; benchmark construction separate; Shari'ah-compliant profit-rate hedging qualification |
| `equities` | PARTIAL | CERTIFIED_CONTRACT | UMI-06 | UMI13-UNR-023 warrant/convertible cross-family structural-payoff qualification; borrow/shortability remains outside static D04 terms and does not justify PARTIAL status |
| `funds-pooled-vehicles` | PARTIAL | CERTIFIED_CONTRACT | UMI-06 | UIT coverage; ETN explicitly not a fund by implication |
| `indices-benchmarks` | PARTIAL | CERTIFIED_CONTRACT | UMI-02, UMI-06, UMI-10 | methodology/constituent governance not owned here |
| `fx` | PARTIAL | CERTIFIED_CONTRACT | UMI-02, UMI-05 | dedicated spot-pair semantics; exotic FX options; rolling financing |
| `futures` | **PARTIAL** | CERTIFIED_CONTRACT | UMI-02, UMI-05, UMI-07 | deliverable-basket/conversion-factor specialization; product-specific final-settlement algorithms; specialized delivery qualification |
| `options` | PARTIAL | CERTIFIED_CONTRACT | UMI-05, UMI-09 | digital/barrier/Asian/exotic payoff semantics |
| `forwards-swaps-otc` | PARTIAL | CERTIFIED_CONTRACT | UMI-05 | caps/floors/FRA/swaptions; Shari'ah-compliant profit-rate/cross-currency/FX-forward hedging; insurance-linked derivative/swap semantics; full legal-programmability not claimed |
| `commodities` | PARTIAL | CERTIFIED_CONTRACT | UMI-05, UMI-07 | power, freight, weather, emissions and specialized OTC semantics |
| `crypto-digital-assets` | PARTIAL | CERTIFIED_CONTRACT | UMI-02, UMI-05, UMI-08 | staking/yield-bearing products; tokenized-security qualification |
| `structured-hybrid-products` | PARTIAL | CERTIFIED_CONTRACT | UMI-03, UMI-05, UMI-09 | structured-note variants; Sukuk/hybrid qualification; Shari'ah-compliant structured financing; insurance-linked risk-transfer/trigger structures |
| `volatility-variance-products` | PARTIAL | CERTIFIED_CONTRACT | UMI-05, UMI-10 | variance/correlation product semantics beyond observation/generic structure |
| `securities-financing` | UNRESOLVED | NO_CERTIFIED_OWNER | none | repo/reverse repo; securities lending/borrowing; margin lending |
| `cross-asset-compositions` | PARTIAL | CERTIFIED_CONTRACT | UMI-05, UMI-09 | UMI13-UNR-024 basket/spread/multi-leg product-specific composition semantics beyond bounded UMI-05/UMI-09 ownership |
| `event-contracts` | UNRESOLVED | NO_CERTIFIED_OWNER | none | event definition, resolution source, contingency/outcome/dispute semantics |
| `contracts-for-difference` | UNRESOLVED | NO_CERTIFIED_OWNER | none | rolling financing, close-out/reference-price, spread-betting qualification |
| `loans-credit-facilities` | UNRESOLVED | NO_CERTIFIED_OWNER | none | facility/drawdown/amortization/covenants/syndication; trade-receivables finance; Shari'ah-compliant syndicated Murabahah/Ijarah financing |

Correction:

```text
futures: COVERED -> PARTIAL
```

Reason: generic `FuturesContractTerms` proves important bounded contractual
semantics, but official exchange evidence demonstrates material specialized futures
semantics such as Treasury deliverable baskets/conversion factors and product-specific
final-settlement rules. These cannot be erased merely because a generic futures
contract type exists.

Explicit non-conflations:

```text
CRYPTO PERPETUAL FUNDING != GENERIC DATED FUTURES GAP
EVENT RESOLUTION AUTHORITY != GENERIC FUTURES AUTHORITY
BORROW / SHORTABILITY STATE != EQUITY D04 SEMANTIC COMPLETENESS GAP
EXECUTION / ROUTING != CROSS-ASSET D04 SEMANTIC COMPLETENESS GAP
```

Those operational/current-state authorities remain outside the UMI-13 semantic
coverage decision.

---

# 7. Explicit unresolved-semantics ledger

| Ref | Family | Unresolved material | Why open |
|---|---|---|---|
| UMI13-UNR-001 | cash-money-market | term/dual-currency deposits | external product semantics exceed inspected dedicated owner scope |
| UMI13-UNR-002 | cash-money-market | commercial paper / certificates of deposit | fixed-income existence does not prove complete money-market semantics |
| UMI13-UNR-003 | fixed-income-credit | ABS/MBS pool, tranche and prepayment | pool/tranche economics are not ordinary-bond semantics |
| UMI13-UNR-004 | loans-credit-facilities | loans/facilities | no inspected dedicated certified family owner |
| UMI13-UNR-005 | indices-benchmarks | methodology / constituent governance | index level/reference identity != construction methodology |
| UMI13-UNR-006 | fx | dedicated spot-pair and exotic FX option semantics | generic derivatives do not prove all FX economics |
| UMI13-UNR-007 | options | barrier/digital/Asian/exotic payoffs | generic option existence != payoff completeness |
| UMI13-UNR-008 | rates/OTC | caps/floors/FRA/swaptions | product-specific semantics remain broader than generic owner proof |
| UMI13-UNR-009 | commodities | power/freight/weather/emissions | specialized market semantics remain open |
| UMI13-UNR-010 | crypto-digital-assets | staking/yield-bearing/tokenized products | funding observation != staking; tokenized security crosses domains |
| UMI13-UNR-011 | structured-hybrid-products | product-specific note/securitized payoff variants | composition framework != every legal/payoff contract |
| UMI13-UNR-012 | volatility-variance-products | variance/correlation contracts | observation != complete tradeable instrument semantics |
| UMI13-UNR-013 | securities-financing | repo/securities lending/margin lending | distinct SFT forms; no dedicated owner |
| UMI13-UNR-014 | event-contracts | event-resolution / outcome authority | binary payoff shape != authoritative resolution |
| UMI13-UNR-015 | contracts-for-difference | financing/close-out/spread-betting | occurrence at provider != D04 semantics |
| UMI13-UNR-016 | funds-pooled-vehicles | unit investment trusts | pooled-vehicle inventory cannot assume enum exhaustiveness |
| UMI13-UNR-017 | futures | deliverable basket / conversion-factor specialization | Treasury and other deliverable futures need product-specific qualification |
| UMI13-UNR-018 | futures | final-settlement algorithm specialization | settlement style alone does not encode every final-settlement algorithm |
| UMI13-UNR-019 | fixed-income / structured | Sukuk / Shari'ah-compliant structural semantics | IIFM standards demonstrate certificate structures not reducible to ordinary conventional debt |
| UMI13-UNR-020 | fixed-income / structured / forwards-swaps-otc | insurance-linked risk-transfer / trigger semantics | catastrophe, mortality, longevity, medical-claim, trigger and derivative forms are not reducible to ordinary bond or event-contract semantics |
| UMI13-UNR-021 | loans-credit-facilities | trade receivables / supply-chain finance | receivables purchase, factoring, forfaiting and advance-based techniques are materially distinct |
| UMI13-UNR-022 | cash / fixed-income / rates / OTC / loans / structured | cross-family Shari'ah-compliant financing / liquidity / hedging structures | Murabahah, Ijarah, Wakalah/agency liquidity, collateralized structures and Shari'ah-compliant hedging/financing forms require explicit cross-family qualification rather than generic bond/swap/loan/spot-FX implication |
| UMI13-UNR-023 | equities | warrant / convertible cross-family structural-payoff qualification | UMI-06 static equity terms explicitly leave warrant/structured payoff economics downstream; existing bounded UMI-05/UMI-09 semantics do not by themselves certify every equity-linked warrant/convertible structure |
| UMI13-UNR-024 | cross-asset-compositions | basket / spread / multi-leg product-specific composition semantics | bounded UMI-05 LONG/SHORT/ratio composition plus UMI-09 set-like higher-order composition do not certify every product-specific composition semantic, including explicit semantic leg order where material |

---

# 8. Semantic collision ledger

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
IdentityFamilyCode != ECONOMIC IDENTITY
VIX INDEX != VIX FUTURE != VIX OPTION != VARIANCE FUTURE
ETF != ETN
BOND != ABS/MBS POOL/TRANCHE ECONOMICS
POOL != TRANCHE
LOAN FACILITY != DRAWN LOAN
BINARY OPTION PAYOFF != EVENT-RESOLUTION AUTHORITY
CFD != ROLLING SPOT FX BY IMPLICATION
REPO != SECURITIES LENDING != MARGIN LENDING
SUKUK != ORDINARY CONVENTIONAL BOND BY IMPLICATION
SUKUK != ALL ISLAMIC FINANCE
SHARI'AH-COMPLIANT FINANCING STRUCTURE != NEW TOP-LEVEL ASSET FAMILY
SHARI'AH-COMPLIANT PROFIT-RATE HEDGING != GENERIC RATE VALUE
ISLAMIC FX FORWARD != SPOT FX
SHARI'AH STRUCTURAL QUALIFICATION != PROVIDER SUPPORT
CAT BOND != ALL ILS
ILS NOTE != ORDINARY BOND
ILS SECURITY != ILS DERIVATIVE
INSURANCE TRIGGER != EVENT-CONTRACT RESOLUTION AUTHORITY
EVENT-LINKED SWAP != EVENT-CONTRACT RESOLUTION AUTHORITY
INSURANCE-LINKED PRODUCT EXISTENCE != QORE OPERATIONAL SUPPORT
OFFICIAL SOURCE EXISTS != QORE IMPLEMENTATION EXISTS
CATASTROPHE BOND != ORDINARY BOND BY IMPLICATION
RECEIVABLES PURCHASE != LOAN BY IMPLICATION
EQUITY STATIC TERMS != EVERY WARRANT / CONVERTIBLE CROSS-FAMILY PAYOFF
BOUNDED COMPOSITION != EVERY PRODUCT-SPECIFIC CROSS-ASSET COMPOSITION SEMANTIC
```

UMI-02 `IdentityFamilyCode` is intentionally extensible classification syntax. A
provider-like token satisfying that syntax does not thereby become economic identity,
provider support or a canonical family. Canonical family legitimacy comes from the
reviewed date-qualified inventory, not lexical pattern recognition.

---

# 9. Independent DeepSeek intake and Integration-Gate disposition

DeepSeek Expert and DeepSeek Coder outputs were treated as claims, not authority.
Live repository verification, primary-source verification and issue-scope analysis
produced this disposition:

| Finding | Disposition | Action |
|---|---|---|
| `futures=COVERED` overstates broad family coverage | ACCEPTED | changed to PARTIAL; added explicit futures unresolved refs |
| external evidence lacks per-source retrieval/snapshot qualification | ACCEPTED | ledger now qualifies every external source |
| additional Sukuk semantics | ACCEPTED AS SUBFAMILY GAP | retained under existing fixed-income/structured families as UMI13-UNR-019 |
| broader cross-family Shari'ah-compliant financing/liquidity/hedging structures | ACCEPTED AS INVENTORY COMPLETENESS CORRECTION | retained UNR-019 specificity; added UMI13-UNR-022 and bounded cross-family mappings; no new top-level family |
| catastrophe/insurance-linked trigger semantics | ACCEPTED AS SUBFAMILY GAP | originally retained under fixed-income/structured families |
| broader insurance-linked risk-transfer/trigger and derivative semantics | ACCEPTED AS INVENTORY PRECISION CORRECTION | broadened UMI13-UNR-020; added fixed-income/structured/OTC qualification; no new top-level family |
| trade-receivables/supply-chain finance | ACCEPTED AS SUBFAMILY GAP | retained under loans/credit-facilities |
| secret detector has realistic bypasses, including polymorphic `str` subclass laundering | ACCEPTED | exact plain-`str` validation required for canonical code/text boundaries; adversarial public-constructor tests added |
| equities PARTIAL lacked an explicit unresolved-semantic ledger ref | ACCEPTED | added UMI13-UNR-023 for warrant/convertible cross-family structural-payoff qualification; borrow/shortability removed as semantic justification |
| cross-asset-compositions PARTIAL used execution/routing as its semantic justification | ACCEPTED | added UMI13-UNR-024 for product-specific basket/spread/multi-leg composition semantics beyond bounded UMI-05/09 ownership |
| generic constructor can syntactically declare fake owner/evidence | PARTIAL / SEMANTIC BOUNDARY | owner status explicitly documented as declaration, never runtime proof; no network resolver added |
| machine-readable populated JSON/YAML registry required | REJECTED | #361 permits contract + reviewed evidence/inventory artifact; no new data format required |
| runtime must require external evidence category on every snapshot entry | REJECTED AS REQUIRED CODE CHANGE | #361 Model B is explicit: generic validator + canonical official evidence ledger |
| `IdentityFamilyCode` must reject provider-looking strings lexically | REJECTED | UMI-02 defines it as extensible classification, never identity; canonical inventory governance is semantic, not regex taxonomy |
| snapshot digest/ID required | REJECTED | no consumer/reference authority requires it; avoids absorbing UMI-02 precedence/currentness gap |
| UNRESOLVED and DEFERRED require separate structural fields | REJECTED | distinct status + governed reason is sufficient for this slice |
| expand negative-space blacklist indefinitely | REJECTED | architecture/field boundary is authoritative; blacklist remains defense-in-depth |

---

# 10. Security correction

UMI-13 evidence/reason text is retained in immutable values and may appear in
`repr()` and `logical_values()`. Canonical string/text boundaries therefore require
an exact plain `str`, not an arbitrary polymorphic `str` subclass. This prevents a
subclass from overriding operations such as `lower()`/`strip()` or custom equality/
hash behavior while its original unsafe material is retained.

The contract also rejects credential-like material, including realistic forms missed
by the first candidate:

- access-token/access_token;
- client-secret/client_secret;
- private-key/private_key;
- JWT/credential assignment;
- password/token/secret colon forms;
- URL authority containing user-info credentials;
- control characters;
- existing authorization/bearer/api-key/password/secret/token forms.

This remains deterministic validation only. No secret scanner service, network call,
regex credential extraction pipeline or sanitizer side effect is introduced.

---

# 11. Exclusion / deferred boundary

Provider-native symbols, provider catalogs, routing/execution strategy, valuation
methodology, risk/margin capacity and settlement capability are excluded as UMI-13
**authority**, not excluded from QORE as a whole.

Material financial families are not marked `EXCLUDED` merely because QORE lacks an
owner. They remain `UNRESOLVED` or `DEFERRED` with explicit evidence/reason.

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

# 13. Correction gate

Any correction changes the exact head and invalidates the earlier independent-review
package.

Required sequence:

```text
CORRECTION COMMIT
-> NEW EXACT-HEAD QORE CI
-> DIFF AUDIT
-> HEAD FREEZE
-> NEW COMPLETE INDEPENDENT CLAUDE REVIEW PACKAGE
-> INTEGRATION GATE
-> EXPECTED-HEAD MERGE
-> POST-MERGE TREE/PARENTS/SIGNATURE/MAIN 0/0 CERTIFICATION
```

No merge is authorized by this document or by CI green alone.
