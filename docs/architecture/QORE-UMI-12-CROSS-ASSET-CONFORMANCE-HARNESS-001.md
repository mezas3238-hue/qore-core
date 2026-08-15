# QORE-UMI-12 — Cross-Asset Conformance Harness

Status: IMPLEMENTATION CANDIDATE — NOT CERTIFIED  
Tracking: #359  
Program: #301 / #303  
Certified starting baseline: `d157f4e42b8f60699264661e89702743cbb8be12`  
Predecessor: UMI-11 / #357 / PR #358 — CERTIFIED/CLOSED

## 1. Mission

UMI-12 is a **falsification harness** over already-certified UMI owner contracts. It proves that materially different financial families can coexist in one Core semantic universe without flattening their economics and without importing provider-specific or asset-specific business logic into canonical owners.

It is not a new financial semantic owner.

```text
UMI-12 = CROSS-ASSET CONTRACT CONFORMANCE
UMI-12 != CROSS-PLATFORM CONFORMANCE
UMI-12 != CROSS-DEPARTMENT SYSTEM CONFORMANCE
UMI-12 != FULL SYSTEM E2E
```

The default production delta is zero. A harness failure reopens the owning semantic stage; UMI-12 does not patch production semantics to make the test pass.

## 2. Exact starting authority map

| Material | Owner | UMI-12 treatment |
|---|---|---|
| Economic/listing/reference identity | UMI-02 / D04 | consume exact typed identities/relationships |
| Fixed-income economics | UMI-03 / D04 | consume exact terms, cash flows, price/yield semantics |
| Rates/curves | UMI-04 / D04/D07 boundary | consume exact curve/node/convention semantics |
| Futures/options/forwards/swaps | UMI-05 / D04 | consume exact derivative contract terms |
| Equity/fund/corporate action | UMI-06 / D04 | consume exact equity/fund structural semantics |
| Commodity delivery contracts | UMI-07 / D04 | consume exact commodity/reference/delivery terms |
| Crypto perpetual/funding/network qualification | UMI-08 / D04 | consume exact perpetual/funding structural semantics |
| Structured/hybrid/synthetic composition | UMI-09 / D04 | consume exact UMI-02 relationship-backed composition |
| Valuation observations | UMI-10 / D07 | consume typed valuation measures only |
| Static market topology | UMI-11 / D04 | consume static topology profiles only |
| Provider runtime capability | D03 / UPR | outside UMI-12 |
| Live market evidence | D05 | outside UMI-12 except through already-certified owner contracts where explicitly referenced |
| Current session/calendar phase | D06 | outside UMI-12 |
| Risk/capacity | D08/D09 | outside UMI-12 |
| Order/routing/execution | D10/D18 | outside UMI-12 |
| Settlement/position mutation | D11 | outside UMI-12 |

## 3. Structural-gap decision

The exact certified baseline was audited for an existing UMI-12 implementation.

Existing evidence includes:

- general architecture-conformance infrastructure;
- preparatory Level-10 cross-domain architecture in #351;
- preparatory Level-12 full-system E2E architecture in #344;
- family-local tests for UMI-02..11.

No dedicated cross-asset harness was established that simultaneously pressures materially different UMI owners while preserving their distinctions.

Classification:

`VERIFIED STRUCTURAL TEST GAP — CROSS-ASSET CONFORMANCE HARNESS REQUIRED`

The minimum delta is test/documentation only.

## 4. Production-code rule

```text
PRODUCTION SOURCE DELTA = 0 BY DEFAULT
```

Candidate files are limited to:

```text
tests/infrastructure/test_universal_cross_asset_conformance.py
tests/infrastructure/test_universal_cross_asset_conformance_guards.py
docs/architecture/QORE-UMI-12-CROSS-ASSET-CONFORMANCE-HARNESS-001.md
```

If any `src/qore/**` file must change, the candidate is no longer a pure UMI-12 harness. The failing owner must be identified and reopened with bounded correction scope before UMI-12 can continue.

## 5. Specimen matrix

### 5.1 Fixed income / bond

The harness constructs an exact `FixedIncomeEconomicProfile` with:

- canonical `EconomicIdentityId`;
- denomination identity;
- face amount;
- fixed coupon terms;
- issue/maturity dates;
- settlement convention;
- yield convention;
- coupon and principal cash flows;
- canonical cash-flow schedule.

This prevents an equity-like price-only model from satisfying the cross-asset proof.

### 5.2 Rates / term structure

The harness constructs a `RateTermStructureSnapshot` with multiple typed nodes and retained observed provenance.

Required distinction:

```text
CURVE != SCALAR
ZERO RATE != YIELD != SPREAD != DISCOUNT FACTOR
```

### 5.3 Listed derivatives

The harness constructs both `FuturesContractTerms` and `OptionContractTerms`, retaining:

- contract month;
- expiry;
- multiplier;
- settlement style;
- last-trade date where supplied;
- option right;
- explicit strike basis/quote identity;
- exercise style.

No generic symbol substitutes for these terms.

### 5.4 OTC derivative

The harness constructs an exact `SwapContractTerms` with fixed and floating legs, each preserving:

- leg identity/ordinal/direction;
- notional schedule;
- fixed rate or benchmark + spread;
- day count;
- payment/reset tenor;
- fixing/schedule/settlement conventions;
- evidence.

```text
SWAP != TWO GENERIC DECIMALS
NOTIONAL != MULTIPLIER
```

### 5.5 Equity / fund

The harness constructs a `FundVehicleTerms` retaining exact `FundNavBasis`.

NAV basis remains structural; no hidden NAV calculation is introduced.

### 5.6 Commodity

The harness constructs `CommodityFuturesContractTerms` that retain exact UMI-05 futures terms plus:

- commodity class/reference identity;
- measurement-unit identity;
- grade;
- delivery location;
- delivery method;
- delivery window.

Physical-delivery semantics remain contract terms only.

```text
DELIVERY TERMS != SETTLEMENT MUTATION
```

### 5.7 Crypto perpetual

The harness constructs `CryptoPerpetualContractTerms` retaining:

- reference/settlement/collateral identities;
- UMI-05 multiplier/tick primitives;
- funding interval/sign/payment identity;
- MARK/INDEX/LAST pricing roles.

The specimen deliberately has no dated-futures lifecycle and no observed mark/index/last/funding values.

```text
PERPETUAL != DATED FUTURES
PRICING ROLE != OBSERVED PRICE
FUNDING TERMS != FUNDING OBSERVATION
```

### 5.8 Structured / hybrid / synthetic

The harness constructs a structured instrument using an exact UMI-02 `IdentityRelationship`, a typed `StructuredComponentBinding`, and a typed feature.

The relationship edge is retained; no component is flattened into a fake primitive symbol.

### 5.9 Universal valuation distinctions

The harness assigns the same `Decimal("0.0500")` magnitude to distinct typed UMI-10 measures:

- fixed-income price;
- fixed-income yield;
- zero rate;
- fund NAV;
- implied volatility.

The resulting logical type tags and Python types must remain distinct.

```text
SAME NUMERIC MAGNITUDE != SAME ECONOMIC SEMANTIC
```

This is a type/semantic conformance proof, not a valuation-methodology proof. #350 remains open.

### 5.10 Market topology

The harness binds static topology profiles to materially different economic identities, including bond-like RFQ and crypto-like AMM examples.

The examples demonstrate representational orthogonality only.

They do not claim those specific venues/providers exist or are operationally supported.

```text
TOPOLOGY != ASSET FAMILY
TOPOLOGY != PROVIDER CAPABILITY
TOPOLOGY != EXECUTION
```

## 6. Shared identity fabric

Every product-level specimen is rooted in exact UMI-02 `EconomicIdentityId` values.

The harness does not use:

- raw symbol text as economic identity;
- raw UUID as economic identity;
- provider-native identifiers as direct economic identity;
- a new UMI-12 identity wrapper.

Local terms/evidence IDs remain local IDs and do not acquire economic identity authority.

## 7. Cross-owner reuse law

Reuse is accepted only where an earlier certified owner explicitly established it.

Examples exercised by the harness:

- UMI-07 commodity futures retain exact UMI-05 `FuturesContractTerms`;
- UMI-08 perpetuals reuse UMI-05 multiplier/tick primitives without adopting dated-futures lifecycle;
- UMI-09 structured components retain exact UMI-02 identity relationships;
- UMI-10 valuation measures retain family-specific UMI-03/04/06/08 semantics;
- UMI-11 topology binds canonical economic identities but does not become product identity.

UMI-12 itself defines none of these semantics.

## 8. Provider-neutral dependency guard

The guard suite parses exact imported owner source at test runtime and rejects provider/vendor/execution-runtime dependencies in certified UMI semantic modules.

The guard targets vendor/runtime import families such as:

- OANDA-specific modules;
- cTrader-specific modules;
- Tradovate/TradeStation/Tastytrade/IBKR adapters;
- provider runtime/harness modules;
- client execution agent;
- execution orchestration/boundary/order-intent runtime modules.

It also rejects direct networking clients in UMI owner modules.

This is static dependency conformance, not a claim that external adapters do not exist elsewhere in QORE.

## 9. Harness-authority guard

The guard suite verifies the primary UMI-12 test file:

- imports real QORE owner modules rather than semantic mocks;
- defines no replacement classes;
- defines no execute/route/submit/match/best-venue/provider-capability/pricing/settlement helper;
- imports no provider-specific module;
- contains no production-source mutation calls.

Test fixtures may construct certified values; they may not implement missing business semantics.

## 10. Determinism

The harness constructs specimens exclusively from explicit retained values.

No fixture uses:

- `datetime.now()`;
- `date.today()`;
- `time.time()`;
- `uuid4()`;
- random values;
- network calls;
- provider discovery.

A combined specimen collection is materialized twice and must produce identical `logical_values()`.

Owner-specific canonical ordering remains owned by each certified contract.

## 11. Mandatory PRE-CHK disposition targets

| PRE-CHK | Concern | Required outcome |
|---|---|---|
| UMI12-00 | local pass mistaken for cross-asset pass | harness contains multiple materially different families |
| UMI12-01 | harness implements business logic | no production semantic algorithms/helpers |
| UMI12-02 | generic supertype flattening | no new cross-asset product superclass |
| UMI12-03 | symbol/identity laundering | exact UMI-02 identities only |
| UMI12-04 | same Decimal = same semantic | typed valuation test proves distinction |
| UMI12-05 | bond = price-only | fixed-income terms + cash-flow schedule retained |
| UMI12-06 | curve = scalar | multi-node term structure retained |
| UMI12-07 | rate/yield/spread collapse | certified distinct owner types retained |
| UMI12-08 | derivative terms = valuation | derivative contract terms remain non-valuation |
| UMI12-09 | notional/quantity/multiplier collapse | derivative notional and multiplier distinct |
| UMI12-10 | commodity delivery = mutation | no settle/transfer/execute authority |
| UMI12-11 | perpetual = dated future | dated lifecycle attributes absent |
| UMI12-12 | structured = fake primitive | exact relationship-backed composition retained |
| UMI12-13 | valuation family flattening | five typed measures remain distinct |
| UMI12-14 | topology = asset family | same topology contract binds different families |
| UMI12-15 | topology = provider support | no provider-capability field/method |
| UMI12-16 | provider-specific owner import | static dependency guard rejects leakage |
| UMI12-17 | helper = production authority | harness AST guard rejects authority helpers |
| UMI12-18 | cross-asset = cross-platform | explicit non-claim |
| UMI12-19 | cross-asset = E2E | explicit non-claim |
| UMI12-20 | contract fitness = operational support | explicit non-claim |
| UMI12-21 | harness patches owner defect | owner-reopen rule |
| UMI12-22 | nondeterministic specimen material | explicit deterministic fixture material |
| UMI12-23 | secret/provider credential material | no credentials/network/provider-native secrets |

Final PRE-CHK status requires exact-head CI and independent review; this document does not self-certify the table.

## 12. Boundary with UPR-12

UPR-12 asks whether materially different **platform models** can bind to provider-neutral external boundaries.

UMI-12 asks whether materially different **financial instruments/economics** can coexist without provider or asset-specific Core rewrites.

```text
CROSS-ASSET != CROSS-PLATFORM
```

No REST/FIX/terminal/streaming/provider capability claim follows from UMI-12.

## 13. Boundary with Level 10 / #351

Level 10 composes departmental authorities such as D04→D05→D07→D08→D09→D10→D11.

UMI-12 does not test that full authority chain. It tests the financial semantic foundation itself.

```text
UMI-12 PASS != CROSS-DEPARTMENT PASS
```

## 14. Boundary with Level 12 / #344

Level 12 requires complete E2E specimens, including controlled external evidence where applicable.

UMI-12 is deterministic offline contract conformance.

```text
UMI-12 PASS != FULL SYSTEM E2E PASS
```

## 15. Coverage interpretation

Because UMI-12 adds no production source module, there is no new UMI-12 source-file coverage percentage to certify.

Quality evaluation instead requires:

- complete repository QORE CI;
- exact cross-asset specimen/oracle audit;
- diff proof that `src/` did not change;
- static dependency checks;
- independent adversarial review;
- Integration Gate.

Incidental increases in coverage of existing owner modules are beneficial but are not the UMI-12 closure criterion.

## 16. Failure policy

If a test reveals that a certified owner cannot represent the required specimen without semantic distortion:

1. classify the exact owner defect;
2. do not weaken/remove the UMI-12 oracle;
3. do not implement a UMI-12 translation shortcut;
4. reopen the responsible owner stage;
5. correct under its own exact-head gate;
6. rebase/re-run UMI-12 only after the corrected owner baseline is certified.

## 17. Explicit non-claims

A favorable UMI-12 result does **not** establish:

- every instrument family in existence is exhaustively inventoried;
- UMI-13 instrument-universe registry is complete;
- UMI-14 final universal market audit is complete;
- any provider/platform/venue supports the specimens;
- UPR-12 is closed;
- #351 Level-10 cross-domain conformance is closed;
- #344 full-system E2E is closed;
- live market data exists for the specimens;
- valuation methodologies are implemented or correct;
- #350 is closed;
- execution/routing/settlement support exists;
- #332/#333/#334 are closed;
- GAP-EXEC / GAP-ANALYSIS-PRODUCER / GAP-LIN-001 are closed;
- PR #298 is promoted;
- Production or real capital is authorized;
- `QORE UNIVERSAL MARKET READY`.

## 18. Certification path

```text
EXACT BASELINE
-> WORK ORDER #359
-> TEST/DOC IMPLEMENTATION
-> ADVERSARIAL SPECIMENS
-> DIFF AUDIT: src/=0
-> DRAFT PR
-> EXACT-HEAD QORE CI
-> SEMANTIC ORACLE AUDIT
-> HEAD FREEZE
-> CLAUDE INDEPENDENT ADVERSARIAL REVIEW
-> INTEGRATION GATE
-> CORRECTION LOOP IF REQUIRED
-> READY TRANSITION
-> PROTECTED expected_head_sha MERGE
-> ACTUAL MERGE TREE/PARENTS/SIGNATURE
-> main == merge
-> compare 0/0
-> BASELINE FREEZE
-> UMI-12 CLOSED
```

`CI GREEN != APPROVAL`  
`CROSS-ASSET CONTRACT PASS != OPERATIONAL SUPPORT`  
`NO POST-MERGE BASELINE -> NO UMI-13 ACTIVATION`
